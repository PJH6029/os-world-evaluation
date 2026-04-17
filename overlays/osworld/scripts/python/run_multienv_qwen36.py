#!/usr/bin/env python3
"""Run OSWorld sampled tasks with Qwen3.6 while preserving partial trajectories.

Provenance:
- Adapted for OSWorld commit e8ba8fde29889ae7e4377f6f325d736818434a04.
- Based on upstream `scripts/python/run_multienv_qwen3vl.py`, but intentionally
  avoids destructive cleanup of incomplete task directories and writes initial
  observations before the first model call.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import signal
import sys
import time
from multiprocessing import Manager, Process, current_process
from pathlib import Path
from typing import Any

# Add OSWorld project root to path when run from scripts/python.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from desktop_env.desktop_env import DesktopEnv  # noqa: E402
from mm_agents.qwen36_openai_agent import Qwen36OpenAIAgent  # noqa: E402

logger = logging.getLogger("desktopenv.experiment")
active_environments: list[Any] = []
processes: list[Process] = []
is_terminating = False


def config() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run OSWorld sample with Qwen3.6")
    parser.add_argument("--path_to_vm", type=str, default=None)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--action_space", type=str, default="pyautogui")
    parser.add_argument("--observation_type", choices=["screenshot", "a11y_tree", "screenshot_a11y_tree", "som"], default="screenshot")
    parser.add_argument("--sleep_after_execution", type=float, default=3.0)
    parser.add_argument("--max_steps", type=int, default=15)
    parser.add_argument("--test_config_base_dir", type=str, default="evaluation_examples")
    parser.add_argument("--model", type=str, default=os.environ.get("QWEN36_MODEL", "Qwen/Qwen3.6-35B-A3B"))
    parser.add_argument("--temperature", type=float, default=float(os.environ.get("QWEN36_TEMPERATURE", "0")))
    parser.add_argument("--top_p", type=float, default=float(os.environ.get("QWEN36_TOP_P", "0.9")))
    parser.add_argument("--max_tokens", type=int, default=int(os.environ.get("QWEN36_MAX_TOKENS", "32768")))
    parser.add_argument("--coord", choices=["absolute", "relative"], default="relative")
    parser.add_argument("--domain", type=str, default="all")
    parser.add_argument("--test_all_meta_path", type=str, default="evaluation_examples/test_nogdrive.json")
    parser.add_argument("--result_dir", type=str, default="./results_qwen36")
    parser.add_argument("--num_envs", type=int, default=1)
    parser.add_argument("--log_level", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default="INFO")
    parser.add_argument("--region", type=str, default="us-east-1")
    parser.add_argument("--provider_name", type=str, default="docker", choices=["aws", "virtualbox", "vmware", "docker", "azure", "aliyun"])
    parser.add_argument("--client_password", type=str, default="password")
    parser.add_argument("--screen_width", type=int, default=1920)
    parser.add_argument("--screen_height", type=int, default=1080)
    return parser.parse_args()


def setup_logging(level: str) -> None:
    logging.getLogger().setLevel(getattr(logging, level.upper()))
    Path("logs").mkdir(exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d@%H%M%S")
    formatter = logging.Formatter("[%(asctime)s %(levelname)s %(module)s/%(lineno)d-%(processName)s] %(message)s")
    for handler in [logging.StreamHandler(sys.stdout), logging.FileHandler(f"logs/qwen36-{ts}.log", encoding="utf-8")]:
        handler.setFormatter(formatter)
        handler.setLevel(getattr(logging, level.upper()))
        logging.getLogger().addHandler(handler)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def append_jsonl(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, sort_keys=True))
        f.write("\n")


def distribute_tasks(test_all_meta: dict[str, list[str]]) -> list[tuple[str, str]]:
    return [(domain, str(example_id)) for domain in sorted(test_all_meta) for example_id in test_all_meta[domain]]


def safe_end_recording(env: Any, result_dir: Path) -> str | None:
    recording = result_dir / "recording.mp4"
    controller = getattr(env, "controller", None)
    if controller is None:
        return "env.controller unavailable"
    try:
        controller.end_recording(str(recording))
        return None if recording.exists() else "controller ended recording but file is absent"
    except Exception as exc:  # noqa: BLE001
        return f"end_recording failed: {exc}"


def run_single_preserving(agent: Qwen36OpenAIAgent, env: DesktopEnv, example: dict[str, Any], args: argparse.Namespace, result_dir: Path, shared_scores: Any) -> None:
    result_dir.mkdir(parents=True, exist_ok=True)
    traj = result_dir / "traj.jsonl"
    runtime_log = result_dir / "runtime.log"
    runtime_logger = logging.getLogger(f"desktopenv.example.{example.get('id', 'unknown')}")
    runtime_logger.setLevel(logging.DEBUG)
    runtime_logger.addHandler(logging.FileHandler(runtime_log, encoding="utf-8"))

    status: dict[str, Any] = {
        "task_id": example.get("id"),
        "instruction": example.get("instruction"),
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "unknown",
    }
    write_json(result_dir / "task_metadata.json", {"example": example, "args": vars(args)})

    obs: dict[str, Any] | None = None
    try:
        env.reset(task_config=example)
        try:
            agent.reset(runtime_logger, vm_ip=getattr(env, "vm_ip", None))
        except TypeError:
            agent.reset(runtime_logger)
        time.sleep(60)
        obs = env._get_obs()
        if obs and "screenshot" in obs:
            (result_dir / "initial_state.png").write_bytes(obs["screenshot"])
        append_jsonl(traj, {"event": "initial_observation", "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(), "screenshot_file": "initial_state.png", "instruction": example.get("instruction"), "task_id": example.get("id")})

        controller = getattr(env, "controller", None)
        if controller is not None:
            try:
                controller.start_recording()
            except Exception as exc:  # noqa: BLE001
                append_jsonl(traj, {"event": "recording_start_error", "error": repr(exc)})

        done = False
        step_idx = 0
        while not done and step_idx < args.max_steps:
            try:
                response, actions = agent.predict(example["instruction"], obs)
            except Exception as exc:  # noqa: BLE001
                status.update({"status": "environment_invalid", "error": f"model_or_endpoint_error: {exc!r}"})
                append_jsonl(traj, {"event": "model_error", "step_num": step_idx + 1, "error": repr(exc), "model_input_file": None})
                break

            model_input_file = f"model_input_step_{step_idx + 1}.json"
            if agent.last_model_payload is not None:
                write_json(result_dir / model_input_file, agent.last_model_payload)

            if not actions:
                status.update({"status": "model_failure", "error": "no_parseable_action"})
                append_jsonl(traj, {"event": "no_parseable_action", "step_num": step_idx + 1, "response": response, "model_input_file": model_input_file})
                break

            for action in actions:
                action_ts = dt.datetime.now().strftime("%Y%m%d@%H%M%S%f")
                try:
                    obs, reward, done, info = env.step(action, args.sleep_after_execution)
                    screenshot_file = f"step_{step_idx + 1}_{action_ts}.png"
                    if obs and "screenshot" in obs:
                        (result_dir / screenshot_file).write_bytes(obs["screenshot"])
                    append_jsonl(
                        traj,
                        {
                            "event": "step",
                            "step_num": step_idx + 1,
                            "action_timestamp": action_ts,
                            "action": action,
                            "all_parsed_actions": actions,
                            "response": response,
                            "model_input_file": model_input_file,
                            "reward": reward,
                            "done": done,
                            "info": info,
                            "screenshot_file": screenshot_file,
                        },
                    )
                except Exception as exc:  # noqa: BLE001
                    status.update({"status": "environment_invalid", "error": f"env_step_error: {exc!r}"})
                    append_jsonl(traj, {"event": "env_step_error", "step_num": step_idx + 1, "action": action, "response": response, "error": repr(exc), "model_input_file": model_input_file})
                    done = True
                    break
                if done:
                    break
            step_idx += 1

        result = None
        if status["status"] == "unknown":
            time.sleep(20)
            try:
                result = float(env.evaluate())
                (result_dir / "result.txt").write_text(f"{result}\n", encoding="utf-8")
                shared_scores.append(result)
                status.update({"status": "success" if result >= 1.0 else "model_failure", "result": result})
            except Exception as exc:  # noqa: BLE001
                status.update({"status": "environment_invalid", "error": f"evaluate_error: {exc!r}"})
                append_jsonl(traj, {"event": "evaluate_error", "error": repr(exc)})
    except Exception as exc:  # noqa: BLE001
        status.update({"status": "environment_invalid", "error": f"task_exception: {exc!r}"})
        append_jsonl(traj, {"event": "task_exception", "error": repr(exc)})
    finally:
        absence = safe_end_recording(env, result_dir) if obs is not None else "recording never started"
        if absence:
            status["recording_absence_reason"] = absence
        status["completed_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        write_json(result_dir / "status.json", status)


def run_env_tasks(task_queue: Any, args: argparse.Namespace, shared_scores: Any) -> None:
    env = None
    try:
        screen_size = (args.screen_width, args.screen_height)
        env = DesktopEnv(
            path_to_vm=args.path_to_vm,
            action_space=args.action_space,
            provider_name=args.provider_name,
            region=args.region,
            snapshot_name="init_state",
            screen_size=screen_size,
            headless=args.headless,
            os_type="Ubuntu",
            require_a11y_tree=args.observation_type in ["a11y_tree", "screenshot_a11y_tree", "som"],
            enable_proxy=True,
            client_password=args.client_password,
        )
        active_environments.append(env)
        agent = Qwen36OpenAIAgent(model=args.model, max_tokens=args.max_tokens, top_p=args.top_p, temperature=args.temperature, action_space=args.action_space, coordinate_type=args.coord)
        while True:
            try:
                domain, example_id = task_queue.get(timeout=5)
            except Exception:
                break
            config_file = Path(args.test_config_base_dir) / "examples" / domain / f"{example_id}.json"
            try:
                example = json.loads(config_file.read_text(encoding="utf-8"))
                example_result_dir = Path(args.result_dir) / args.action_space / args.observation_type / args.model.replace("/", "__") / domain / example_id
                run_single_preserving(agent, env, example, args, example_result_dir, shared_scores)
            except Exception as exc:  # noqa: BLE001
                logger.error("Task-level error in %s %s/%s: %r", current_process().name, domain, example_id, exc)
    finally:
        if env is not None:
            try:
                env.close()
            except Exception as exc:  # noqa: BLE001
                logger.error("Error closing env: %r", exc)


def signal_handler(signum: int, frame: Any) -> None:
    global is_terminating
    if is_terminating:
        return
    is_terminating = True
    logger.info("Received signal %s; preserving partial artifacts and shutting down", signum)
    for env in active_environments:
        try:
            env.close()
        except Exception:
            pass
    for p in processes:
        if p.is_alive():
            p.terminate()
    sys.exit(0)


def get_unfinished(action_space: str, model: str, observation_type: str, result_dir: str, total_file_json: dict[str, list[str]]) -> dict[str, list[str]]:
    """Return unfinished tasks without deleting any partial task artifacts."""
    target_dir = Path(result_dir) / action_space / observation_type / model.replace("/", "__")
    if not target_dir.exists():
        return total_file_json
    remaining: dict[str, list[str]] = {}
    for domain, task_ids in total_file_json.items():
        remaining[domain] = []
        for task_id in task_ids:
            task_dir = target_dir / domain / str(task_id)
            if not (task_dir / "result.txt").exists():
                remaining[domain].append(str(task_id))
    return remaining


def test(args: argparse.Namespace, test_all_meta: dict[str, list[str]]) -> None:
    all_tasks = distribute_tasks(test_all_meta)
    logger.info("Total tasks: %d", len(all_tasks))
    with Manager() as manager:
        shared_scores = manager.list()
        task_queue = manager.Queue()
        for item in all_tasks:
            task_queue.put(item)
        for idx in range(args.num_envs):
            p = Process(target=run_env_tasks, args=(task_queue, args, shared_scores), name=f"EnvProcess-{idx + 1}")
            p.daemon = True
            p.start()
            processes.append(p)
        for p in processes:
            p.join()
        scores = list(shared_scores)
    logger.info("Average score: %.4f", sum(scores) / len(scores) if scores else 0.0)


def main() -> int:
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    args = config()
    setup_logging(args.log_level)
    Path(args.result_dir).mkdir(parents=True, exist_ok=True)
    args_path = Path(args.result_dir) / args.action_space / args.observation_type / args.model.replace("/", "__") / "args.json"
    write_json(args_path, vars(args))
    test_all_meta = json.loads(Path(args.test_all_meta_path).read_text(encoding="utf-8"))
    if args.domain != "all":
        test_all_meta = {args.domain: test_all_meta[args.domain]}
    test_file_list = get_unfinished(args.action_space, args.model, args.observation_type, args.result_dir, test_all_meta)
    logger.info("Left tasks:\n%s", "\n".join(f"{d}: {len(v)}" for d, v in test_file_list.items()))
    test(args, test_file_list)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
