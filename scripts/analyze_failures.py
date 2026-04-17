#!/usr/bin/env python3
"""Generate a trajectory-backed qualitative failure-analysis report."""

from __future__ import annotations

import argparse
import collections
import re
from pathlib import Path
from typing import Any

from osworld_eval_common import PRIMARY_FAILURE_TAGS, iter_jsonl, repo_root

CATEGORY_TITLES = {
    "visual_perception": "Bad visual perception",
    "action_grounding": "Bad action grounding",
    "planning": "Planning errors",
    "tool_ui_confusion": "Tool/UI confusion",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trajectory-index", required=True)
    parser.add_argument("--out", default="reports/qwen36_osworld_failure_analysis.md")
    parser.add_argument("--check-report-links", action="store_true")
    parser.add_argument("--max-examples-per-category", type=int, default=3)
    return parser.parse_args()


def load_rows(path: Path) -> list[dict[str, Any]]:
    return list(iter_jsonl(path))


def md_link(path: str | None, label: str) -> str:
    if not path:
        return f"{label}: unavailable"
    return f"[{label}]({path})"


def pick_examples(rows: list[dict[str, Any]], tag: str, max_examples: int) -> list[dict[str, Any]]:
    return [row for row in rows if tag in row.get("failure_tags", [])][:max_examples]


def format_case(row: dict[str, Any]) -> str:
    task = f"{row.get('domain')}/{row.get('task_id')}"
    links = ", ".join(
        [
            md_link(row.get("traj_file"), "traj"),
            md_link(row.get("initial_observation_file"), "initial observation"),
            md_link(row.get("recording_file"), "recording") if row.get("recording_file") else f"recording absent: {row.get('recording_absence_reason')}",
        ]
    )
    return (
        f"- **{task}** — status `{row.get('status')}`, score `{row.get('result_score')}`.\n"
        f"  - Instruction: {row.get('instruction') or 'unavailable'}\n"
        f"  - Evidence: {links}\n"
        f"  - Suggested tags: {', '.join(row.get('failure_tags') or ['none'])} (`{row.get('tag_source')}`)\n"
    )


def write_report(rows: list[dict[str, Any]], out: Path, max_examples: int) -> None:
    counts = collections.Counter(row.get("status", "unknown") for row in rows)
    attempted = len([row for row in rows if row.get("status") != "not_run"])
    lines: list[str] = []
    lines.append("# Qwen3.6 OSWorld Qualitative Failure Analysis\n")
    lines.append("This report is generated from trajectory artifacts. Failure tags are **agent-suggested** unless later manually verified. It is a sampled no-Google-Drive qualitative evaluation, not a full OSWorld leaderboard result.\n")
    lines.append("## Status counts\n")
    lines.append(f"- Sampled: {len(rows)}")
    lines.append(f"- Attempted: {attempted}")
    for status in ["success", "model_failure", "environment_invalid", "unknown", "not_run"]:
        lines.append(f"- {status}: {counts.get(status, 0)}")
    lines.append("")
    if attempted == 0:
        lines.append("> No sampled task has been attempted yet; this report is a pre-run artifact scaffold, not a qualitative model-failure finding.\n")

    by_domain: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for row in rows:
        by_domain[str(row.get("domain"))][str(row.get("status", "unknown"))] += 1
    no_parseable = len([row for row in rows if "no_parseable_action" in str(row.get("status_reason", ""))])
    zero_score = len([row for row in rows if row.get("status") == "model_failure" and row.get("result_score") == 0.0])
    result_backed = len([row for row in rows if row.get("result_score") is not None])
    lines.append("## Qualitative headline observations\n")
    valid_attempts = max(1, attempted - counts.get("environment_invalid", 0))
    lines.append(f"- Successes: {counts.get('success', 0)}/{len(rows)} sampled tasks ({counts.get('success', 0)}/{valid_attempts} excluding environment-invalid rows).")
    lines.append(f"- Model failures: {counts.get('model_failure', 0)}, including {no_parseable} runs that ended because no parseable action was produced and {zero_score} evaluated runs with score 0.0.")
    lines.append(f"- Result-backed evaluations: {result_backed}; the remaining model-failure rows are still trajectory-backed but ended before OSWorld produced `result.txt`.")
    lines.append("- Domain status counts:")
    for domain in sorted(by_domain):
        lines.append(f"  - {domain}: " + ", ".join(f"{k}={v}" for k, v in sorted(by_domain[domain].items())))
    lines.append("")
    lines.append("## Failure taxonomy coverage\n")
    for tag in PRIMARY_FAILURE_TAGS:
        title = CATEGORY_TITLES[tag]
        examples = pick_examples(rows, tag, max_examples)
        lines.append(f"### {title}\n")
        if not examples:
            lines.append("not observed in this sample\n")
            continue
        for example in examples:
            lines.append(format_case(example))
        lines.append("")
    mixed = [row for row in rows if "mixed_uncertain" in row.get("failure_tags", [])]
    lines.append("## Mixed or uncertain cases\n")
    if mixed:
        for row in mixed[:max_examples]:
            lines.append(format_case(row))
    else:
        lines.append("not observed in this sample\n")
    invalid = [row for row in rows if row.get("status") == "environment_invalid"]
    unknown = [row for row in rows if row.get("status") == "unknown"]
    lines.append("## Environment-invalid and unknown cases\n")
    lines.append(f"- Environment invalid: {len(invalid)}")
    lines.append(f"- Unknown: {len(unknown)}")
    if invalid or unknown:
        for row in (invalid + unknown)[:max_examples]:
            lines.append(format_case(row))
    lines.append("\n## Suggestions for manual follow-up\n")
    lines.append("1. Inspect action-grounding cases by comparing click coordinates against the referenced screenshots.")
    lines.append("2. Inspect visual-perception cases by checking whether the relevant text/icon/state was visible in the observation.")
    lines.append("3. For planning/tool-confusion cases, replay the action sequence and decide whether the model misunderstood the task or the app state.")
    lines.append("4. Keep environment-invalid and unknown rows out of model-failure counts until manually resolved.")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def check_links(report_path: Path) -> None:
    text = report_path.read_text(encoding="utf-8")
    problems: list[str] = []
    for target in re.findall(r"\]\(([^)]+)\)", text):
        if target.startswith(("http://", "https://", "#")):
            continue
        path = Path(target)
        if not path.is_absolute():
            path = repo_root() / path
        if not path.exists():
            problems.append(f"missing report link target: {target}")
    if problems:
        raise SystemExit("Report link check failed:\n" + "\n".join(problems))


def main() -> int:
    args = parse_args()
    index = Path(args.trajectory_index)
    if not index.is_absolute():
        index = repo_root() / index
    out = Path(args.out)
    if not out.is_absolute():
        out = repo_root() / out
    rows = load_rows(index)
    write_report(rows, out, args.max_examples_per_category)
    if args.check_report_links:
        check_links(out)
    print(f"Wrote report: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
