from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd, cwd=ROOT):
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class HarnessTests(unittest.TestCase):
    def make_fake_osworld(self, tmp: Path) -> tuple[Path, str]:
        osw = tmp / "OSWorld"
        domains = {
            "chrome": [f"chrome-{i}" for i in range(7)],
            "multi_apps": [f"multi-{i}" for i in range(6)] + ["gdrive-1"],
        }
        nogdrive = {
            "chrome": domains["chrome"],
            "multi_apps": [task for task in domains["multi_apps"] if task != "gdrive-1"],
        }
        write_json(osw / "evaluation_examples/test_all.json", domains)
        write_json(osw / "evaluation_examples/test_nogdrive.json", nogdrive)
        for domain, task_ids in domains.items():
            for task_id in task_ids:
                instruction = "Open Google Drive" if task_id == "gdrive-1" else f"Do {task_id}"
                write_json(
                    osw / "evaluation_examples" / "examples" / domain / f"{task_id}.json",
                    {"id": task_id, "instruction": instruction, "related_apps": [domain]},
                )
        for rel in ["scripts/python/run_multienv_qwen3vl.py", "mm_agents/qwen3vl_agent.py", "lib_run_single.py"]:
            path = osw / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# fake upstream\n", encoding="utf-8")
        run(["git", "init"], cwd=osw)
        run(["git", "add", "."], cwd=osw)
        run(["git", "-c", "user.email=test@example.com", "-c", "user.name=Test", "commit", "-m", "init"], cwd=osw)
        commit = run(["git", "rev-parse", "HEAD"], cwd=osw).stdout.strip()
        return osw, commit

    def test_sampler_records_exclusions_and_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            osw, commit = self.make_fake_osworld(tmp)
            out = tmp / "sample.json"
            meta = tmp / "sample_meta.json"
            exclusions = tmp / "exclusions.json"
            cmd = [
                sys.executable,
                str(ROOT / "scripts/sample_osworld_tasks.py"),
                "--osworld-home",
                str(osw),
                "--expected-commit",
                commit,
                "--seed",
                "36035",
                "--out",
                str(out),
                "--meta-out",
                str(meta),
                "--exclusions-out",
                str(exclusions),
                "--validate-no-gdrive",
            ]
            run(cmd)
            first = out.read_bytes()
            run(cmd)
            self.assertEqual(first, out.read_bytes())
            manifest = json.loads(out.read_text())
            exclusion_manifest = json.loads(exclusions.read_text())
            self.assertEqual(manifest["total_sampled"], 10)
            self.assertEqual(exclusion_manifest["excluded_count"], 1)
            self.assertEqual(exclusion_manifest["excluded_tasks"][0]["excluded_reason"], "google_drive")
            self.assertEqual(len(json.loads(meta.read_text())["chrome"]), 5)
            self.assertEqual(len(json.loads(meta.read_text())["multi_apps"]), 5)

    def test_index_and_report_preserve_unknown_separation(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            manifest = {
                "sample_seed": 36035,
                "osworld_commit": "abc",
                "sample_manifest_sha256": "samplehash",
                "tasks": [
                    {"task_id": "t1", "domain": "chrome", "instruction": "Click button", "config_path": "x", "sample_rank_within_domain": 1},
                    {"task_id": "t2", "domain": "chrome", "instruction": "No run", "config_path": "y", "sample_rank_within_domain": 2},
                ],
            }
            manifest_path = tmp / "manifest.json"
            write_json(manifest_path, manifest)
            task_dir = tmp / "results/pyautogui/screenshot/Qwen__Qwen3.6-35B-A3B/chrome/t1"
            task_dir.mkdir(parents=True)
            (task_dir / "traj.jsonl").write_text('{"event":"initial_observation","screenshot_file":"initial_state.png"}\n', encoding="utf-8")
            (task_dir / "initial_state.png").write_bytes(b"png")
            write_json(task_dir / "status.json", {"status": "unknown", "recording_absence_reason": "test"})
            index = tmp / "index.jsonl"
            run([
                sys.executable,
                str(ROOT / "scripts/index_trajectories.py"),
                "--results-dir",
                str(tmp / "results"),
                "--manifest",
                str(manifest_path),
                "--out",
                str(index),
                "--validate-contract",
            ])
            rows = [json.loads(line) for line in index.read_text().splitlines()]
            self.assertEqual(rows[0]["status"], "unknown")
            self.assertEqual(rows[0]["failure_tags"], [])
            report = tmp / "report.md"
            run([sys.executable, str(ROOT / "scripts/analyze_failures.py"), "--trajectory-index", str(index), "--out", str(report), "--check-report-links"])
            text = report.read_text()
            self.assertIn("unknown: 1", text)
            self.assertIn("not observed in this sample", text)

    def test_validate_run_manifest_hashes(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            sample = tmp / "sample.json"
            excl = tmp / "exclusions.json"
            write_json(sample, {"ok": True})
            write_json(excl, {"excluded_tasks": []})
            import hashlib
            def h(path):
                return hashlib.sha256(path.read_bytes()).hexdigest()
            manifest = {
                "run_id": "run-test",
                "created_at": "2026-04-17T00:00:00Z",
                "config_hash": "abc",
                "sample_seed": 36035,
                "sample_manifest": str(sample),
                "sample_manifest_hash": h(sample),
                "exclusion_manifest": str(excl),
                "exclusion_manifest_hash": h(excl),
                "osworld_commit": "abc",
                "model_id": "Qwen/Qwen3.6-35B-A3B",
                "serving_backend": "vllm",
                "endpoint_redacted": "http://127.0.0.1:8000/v1",
                "decoding": {"temperature": 0},
                "max_steps": 15,
                "retry_policy": {"environment_failure_retries": 1},
                "provider": {"name": "docker"},
                "artifact_roots": {"runs": "runs"},
            }
            run_manifest = tmp / "run_manifest.json"
            write_json(run_manifest, manifest)
            run([sys.executable, str(ROOT / "scripts/validate_run_manifest.py"), "--run-manifest", str(run_manifest)])


if __name__ == "__main__":
    unittest.main()
