"""内存门禁：重复采样并按中位数阈值阻断发布。"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_COMMAND_TEMPLATE = (
    "{python} -m uvicorn app.main:app --host 127.0.0.1 --port {port} --lifespan off"
)


class MemoryGateError(RuntimeError):
    """内存门禁执行失败。"""


def run_probe_once(
    working_directory: Path,
    command_template: str,
    intervals: str,
    startup_timeout: int,
    port: int,
) -> dict[str, Any]:
    probe_script = Path(__file__).with_name("memory_probe.py")
    command = [
        sys.executable,
        str(probe_script),
        "--intervals",
        intervals,
        "--command-template",
        command_template,
        "--startup-timeout",
        str(startup_timeout),
        "--port",
        str(port),
    ]
    result = subprocess.run(
        command,
        cwd=working_directory,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        details = {
            "returncode": result.returncode,
            "stdout_tail": result.stdout[-4000:],
            "stderr_tail": result.stderr[-4000:],
        }
        raise MemoryGateError(json.dumps(details, ensure_ascii=False))

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        details = {
            "error": str(error),
            "stdout_tail": result.stdout[-4000:],
            "stderr_tail": result.stderr[-4000:],
        }
        raise MemoryGateError(json.dumps(details, ensure_ascii=False)) from error


def get_final_rss_mb(report: dict[str, Any]) -> float:
    service_probe = report.get("service_probe")
    if not isinstance(service_probe, dict):
        raise MemoryGateError("缺少 service_probe 结果")

    samples = service_probe.get("samples")
    if not isinstance(samples, list) or not samples:
        raise MemoryGateError("service_probe.samples 为空")

    final_sample = samples[-1]
    rss_mb = final_sample.get("rss_mb")
    if not isinstance(rss_mb, (int, float)):
        raise MemoryGateError("service_probe.samples[-1].rss_mb 非数字")
    return float(rss_mb)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="执行内存门禁并在超阈值时失败")
    parser.add_argument("--threshold-mb", type=float, default=250.0)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--intervals", default="60,300,600")
    parser.add_argument("--startup-timeout", type=int, default=45)
    parser.add_argument("--base-port", type=int, default=18000)
    parser.add_argument("--command-template", default=DEFAULT_COMMAND_TEMPLATE)
    parser.add_argument("--working-directory", default=".")
    parser.add_argument("--output-json", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.repeats <= 0:
        raise MemoryGateError("--repeats 必须大于 0")

    working_directory = Path(args.working_directory).resolve()
    run_results: list[dict[str, Any]] = []
    final_rss_values: list[float] = []

    for index in range(args.repeats):
        port = args.base_port + index
        report = run_probe_once(
            working_directory=working_directory,
            command_template=args.command_template,
            intervals=args.intervals,
            startup_timeout=args.startup_timeout,
            port=port,
        )
        final_rss_mb = get_final_rss_mb(report)
        run_results.append(
            {
                "run_index": index + 1,
                "port": port,
                "final_rss_mb": final_rss_mb,
                "report": report,
            }
        )
        final_rss_values.append(final_rss_mb)

    median_rss_mb = statistics.median(final_rss_values)
    summary = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "threshold_mb": args.threshold_mb,
        "repeats": args.repeats,
        "intervals": args.intervals,
        "final_rss_values_mb": final_rss_values,
        "median_rss_mb": median_rss_mb,
        "passed": median_rss_mb < args.threshold_mb,
        "runs": run_results,
    }

    summary_text = json.dumps(summary, ensure_ascii=False, indent=2)
    print(summary_text)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(summary_text, encoding="utf-8")

    if not summary["passed"]:
        raise SystemExit(
            f"Memory gate failed: median_rss_mb={median_rss_mb:.2f} >= threshold_mb={args.threshold_mb:.2f}"
        )


if __name__ == "__main__":
    main()
