"""Save raw chat responses for a question set.

This script calls the running API and writes the per-case responses to disk.

Input supports the same formats as `scripts/benchmark_chat.py`:
- JSON list or {"cases": [...]}
- JSONL
- TXT with one question per line

Output:
- JSON summary file with all cases and raw responses
- JSONL file with one result per line
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any
import sys

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchmark_chat import build_summary, load_cases, run_case


def write_outputs(output_dir: Path, results: list[dict[str, Any]], source_name: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{Path(source_name).stem}_{stamp}"

    json_path = output_dir / f"{base}.json"
    jsonl_path = output_dir / f"{base}.jsonl"

    summary = build_summary(results)
    payload = {
        "source": source_name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": summary,
        "results": results,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in results:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    return json_path, jsonl_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Call the chat API and save raw results to disk.")
    parser.add_argument("input", type=Path, help="Path to JSON, JSONL, or TXT question file")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000/api/chat")
    parser.add_argument("--api-key", default="demo_hr_001")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--output-dir", type=Path, default=Path("docs"))
    args = parser.parse_args()

    cases = load_cases(args.input)
    session_prefix = "save-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    results: list[dict[str, Any]] = []

    with httpx.Client(timeout=args.timeout) as client:
        for index, case in enumerate(cases, start=1):
            result = run_case(client, args.endpoint, case, args.api_key, session_prefix, index)
            results.append(result)
            print(f"{result['id']}: saved latency={result['latency_ms']}ms intent={result.get('actual_intent')}")

    json_path, jsonl_path = write_outputs(args.output_dir, results, args.input.name)

    summary = build_summary(results)
    print()
    print(f"Saved JSON: {json_path}")
    print(f"Saved JSONL: {jsonl_path}")
    print(f"Total: {summary['total_questions']}")
    print(f"Request errors: {summary['request_errors']}")
    print(f"Accuracy: {summary['accuracy'] if summary['accuracy'] is not None else 'N/A'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
