"""内存探针 CLI：导入增量与空闲进程 RSS 采样。"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from memory_probe_lib import (
    DEFAULT_COMMAND_TEMPLATE,
    DEFAULT_MODULES,
    parse_intervals,
    probe_import_deltas,
    probe_service_memory,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="采样导入增量与服务空闲内存")
    parser.add_argument("--modules", nargs="*", default=DEFAULT_MODULES)
    parser.add_argument("--intervals", default="60,300,600")
    parser.add_argument("--command-template", default=DEFAULT_COMMAND_TEMPLATE)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18000)
    parser.add_argument("--startup-timeout", type=int, default=45)
    parser.add_argument("--skip-service", action="store_true")
    parser.add_argument("--output-json", type=Path)
    return parser.parse_args()


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    intervals_seconds = parse_intervals(args.intervals)
    report: dict[str, Any] = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "platform": platform.platform(),
        "python_version": sys.version,
        "import_probe": probe_import_deltas(args.modules),
    }
    if not args.skip_service:
        report["service_probe"] = probe_service_memory(
            command_template=args.command_template,
            host=args.host,
            port=args.port,
            intervals_seconds=intervals_seconds,
            startup_timeout_seconds=args.startup_timeout,
        )
    return report


def main() -> None:
    args = parse_args()
    report = build_report(args)
    output_text = json.dumps(report, ensure_ascii=False, indent=2)
    print(output_text)

    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(output_text, encoding="utf-8")


if __name__ == "__main__":
    main()
