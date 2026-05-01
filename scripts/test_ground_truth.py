"""Send questions from ground-truth file to the live API and report answers + latency."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.request
import uuid
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
GROUND_TRUTH_PATH = SCRIPT_DIR / "ground_truth_rag.json"
if not GROUND_TRUTH_PATH.exists():
    GROUND_TRUTH_PATH = REPO_ROOT / "ground_truth_rag.json"

_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_GREEN  = "\033[32m"
_RED    = "\033[31m"
_YELLOW = "\033[33m"
_CYAN   = "\033[36m"


def _c(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}" if sys.stdout.isatty() else text


def _load_ground_truth(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Ground truth file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    if not items:
        raise ValueError("Ground truth file contains no items.")
    return items


def _pick_samples(
    items: list[dict],
    count: int | None,
    start: int,
    topic: str,
    source: str,
) -> list[dict]:
    if start < 0:
        raise ValueError("--start must be >= 0")
    filtered = items[start:]
    if topic:
        filtered = [i for i in filtered if i.get("topic", "") == topic]
    if source:
        filtered = [i for i in filtered if source.lower() in i.get("source_file", "").lower()]
    if count is not None:
        if count <= 0:
            raise ValueError("--count must be > 0")
        filtered = filtered[:count]
    return filtered


def _check_health(api_url: str, timeout: int) -> bool:
    base = api_url.split("/api/")[0]
    health_url = base + "/health"
    try:
        with urllib.request.urlopen(health_url, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def _call_api(api_url: str, api_key: str, message: str, session_id: str, timeout: int) -> dict:
    payload = json.dumps(
        {"message": message, "session_id": session_id},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _call_with_retry(
    api_url: str,
    api_key: str,
    message: str,
    session_id: str,
    timeout: int,
    retries: int,
) -> dict:
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return _call_api(api_url, api_key, message, session_id, timeout)
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                wait = 1.5 * (attempt + 1)
                print(f"    {_c('retry', _YELLOW)} ({attempt + 1}/{retries}) after {wait:.1f}s — {exc}")
                time.sleep(wait)
    raise last_exc  # type: ignore[misc]


def _run_one(
    item: dict,
    api_url: str,
    api_key: str,
    timeout: int,
    retries: int,
    run_id: str,
) -> dict:
    session_id = f"gt-{run_id}-{item['id']}"
    start = time.perf_counter()
    try:
        response = _call_with_retry(
            api_url=api_url,
            api_key=api_key,
            message=item["question"],
            session_id=session_id,
            timeout=timeout,
            retries=retries,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "id": item["id"],
            "question": item["question"],
            "answer": response.get("answer") or "",
            "intent": response.get("intent"),
            "sources": response.get("sources") or [],
            "latency_ms": round(elapsed_ms, 2),
            "error": None,
        }
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "id": item["id"],
            "question": item["question"],
            "answer": "",
            "intent": None,
            "sources": [],
            "latency_ms": round(elapsed_ms, 2),
            "error": str(exc),
        }


def _print_results(results: list[dict]) -> None:
    latencies = [r["latency_ms"] for r in results]
    errors = [r for r in results if r["error"]]

    sep = _c("=" * 68, _BOLD)
    print()
    print(sep)
    print(_c("KẾT QUẢ", _BOLD))
    print(sep)
    print(f"  Tổng câu hỏi : {len(results)}")
    print(f"  Lỗi          : {_c(str(len(errors)), _RED if errors else _GREEN)}")
    if latencies:
        avg = statistics.mean(latencies)
        p95 = max(latencies) if len(latencies) < 20 else statistics.quantiles(latencies, n=20)[18]
        print(f"  Latency avg  : {avg:.0f} ms")
        print(f"  Latency p95  : {p95:.0f} ms")
        print(f"  Latency min  : {min(latencies):.0f} ms")
        print(f"  Latency max  : {max(latencies):.0f} ms")
    print(sep)
    print()

    for r in results:
        intent_tag = f"  [{r['intent']}]" if r["intent"] else ""
        latency_str = f"{r['latency_ms']:.0f} ms"
        latency_color = _GREEN if r["latency_ms"] < 5000 else _YELLOW if r["latency_ms"] < 10000 else _RED
        print(f"{_c(r['id'], _CYAN)}{intent_tag}  {_c(latency_str, latency_color)}")
        print(f"  Q: {r['question']}")
        if r["error"]:
            print(f"  {_c('ERROR', _RED)}: {r['error']}")
        else:
            print(f"  A: {r['answer']}")
        if r["sources"]:
            names = ", ".join(
                str(src.get("file") or src.get("title") or "?")
                for src in r["sources"]
                if isinstance(src, dict)
            )
            print(f"  Sources: {names}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gửi từng câu hỏi trong file ground-truth tới API và in câu trả lời + latency.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Ví dụ:\n"
            "  python scripts/test_ground_truth.py\n"
            "  python scripts/test_ground_truth.py --count 5\n"
            "  python scripts/test_ground_truth.py --topic nghi_phep\n"
            "  python scripts/test_ground_truth.py --api-key demo_hr_001\n"
        ),
    )
    parser.add_argument("--count", type=int, default=None, help="Số câu hỏi cần test (mặc định: tất cả).")
    parser.add_argument("--start", type=int, default=0, help="Bắt đầu từ index nào (mặc định: 0).")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000/api/chat", help="URL endpoint chat.")
    parser.add_argument("--api-key", default="demo_employee_001", help="Giá trị X-API-Key.")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout mỗi request (giây, mặc định: 120).")
    parser.add_argument("--retries", type=int, default=2, help="Số lần retry khi lỗi (mặc định: 2).")
    parser.add_argument("--topic", type=str, default="", help="Lọc theo topic.")
    parser.add_argument("--source", type=str, default="", help="Lọc theo source_file chứa chuỗi này.")
    parser.add_argument("--no-health-check", action="store_true", help="Bỏ qua kiểm tra /health.")
    parser.add_argument("--output", type=str, default="", help="Lưu kết quả JSON ra file (tùy chọn).")
    args = parser.parse_args()

    if not args.no_health_check:
        print(f"Kiểm tra server tại {args.api_url.split('/api/')[0]}/health ...", end=" ", flush=True)
        if _check_health(args.api_url, timeout=10):
            print(_c("OK", _GREEN))
        else:
            print(_c("KHÔNG KẾT NỐI ĐƯỢC", _RED))
            print("\n  Khởi động server trước:")
            print("    uvicorn app.main:app --reload --port 8000")
            print("\n  Hoặc bỏ qua: --no-health-check")
            return 1

    items = _load_ground_truth(GROUND_TRUTH_PATH)
    samples = _pick_samples(items, args.count, args.start, args.topic, args.source)

    if not samples:
        print(_c("Không có câu hỏi nào khớp với bộ lọc.", _YELLOW))
        return 1

    print(
        f"\nGửi {_c(str(len(samples)), _BOLD)} câu hỏi"
        f" → {_c(args.api_url, _CYAN)}"
        f"  (key={args.api_key}, timeout={args.timeout}s)\n"
    )

    run_id = uuid.uuid4().hex[:8]
    results: list[dict] = []
    width = len(str(len(samples)))
    for idx, item in enumerate(samples, 1):
        print(
            f"  [{idx:>{width}}/{len(samples)}] {_c(item['id'], _CYAN)}"
            f" — {item['question'][:60]}",
            end=" ... ",
            flush=True,
        )
        result = _run_one(item, args.api_url, args.api_key, args.timeout, args.retries, run_id)
        results.append(result)
        if result["error"]:
            print(_c(f"ERROR ({result['latency_ms']:.0f} ms)", _RED))
        else:
            latency_color = _GREEN if result["latency_ms"] < 5000 else _YELLOW if result["latency_ms"] < 10000 else _RED
            print(_c(f"{result['latency_ms']:.0f} ms", latency_color))

    _print_results(results)

    if args.output:
        output_path = Path(args.output)
        payload = {
            "count": len(results),
            "avg_latency_ms": statistics.mean(r["latency_ms"] for r in results) if results else 0.0,
            "results": results,
        }
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Đã lưu kết quả vào {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
