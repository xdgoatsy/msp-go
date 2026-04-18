"""内存探针核心能力：导入增量与空闲 RSS 采样。"""

from __future__ import annotations

import gc
import importlib
import json
import os
import platform
import shlex
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

DEFAULT_MODULES = [
    "app.config",
    "app.infrastructure.database.session",
    "app.infrastructure.cache.redis",
    "app.agents.core.llm_client",
    "app.services.student_portrait_service",
    "app.services.ai_config_service",
    "app.services.xidian_service",
    "app.api.v1.router",
    "app.main",
]
DEFAULT_COMMAND_TEMPLATE = (
    "{python} -m uvicorn app.main:app --host 127.0.0.1 --port {port} --lifespan off"
)


class MemoryProbeError(RuntimeError):
    """内存探针运行错误。"""


def _rss_mb_windows(pid: int) -> float:
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            f"(Get-Process -Id {pid}).WorkingSet64",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise MemoryProbeError(f"PowerShell 读取进程内存失败: pid={pid}")

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise MemoryProbeError(f"PowerShell 输出为空: pid={pid}")

    value_bytes = int(lines[-1])
    return value_bytes / 1024 / 1024


def _rss_mb_linux(pid: int) -> float:
    status_path = Path(f"/proc/{pid}/status")
    if not status_path.exists():
        raise MemoryProbeError(f"进程不存在: pid={pid}")

    for line in status_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("VmRSS:"):
            value_kb = float(line.split()[1])
            return value_kb / 1024
    raise MemoryProbeError(f"无法在 /proc 状态中解析 VmRSS: pid={pid}")


def rss_mb_for_pid(pid: int) -> float:
    if os.name == "nt":
        return _rss_mb_windows(pid)

    if sys.platform.startswith("linux"):
        return _rss_mb_linux(pid)

    raise MemoryProbeError(f"不支持的平台: {platform.system()}")


def _child_pids_linux(pid: int) -> list[int]:
    children_path = Path(f"/proc/{pid}/task/{pid}/children")
    if not children_path.exists():
        return []
    raw_text = children_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        return []
    return [int(item) for item in raw_text.split() if item.isdigit()]


def _process_tree_pids_windows(root_pid: int) -> list[int]:
    script = (
        "$pending = New-Object System.Collections.Generic.Queue[int];"
        f"$pending.Enqueue({root_pid});"
        "$visited = New-Object System.Collections.Generic.HashSet[int];"
        "while ($pending.Count -gt 0) {"
        "$current = $pending.Dequeue();"
        "if (-not $visited.Add($current)) { continue }"
        "$children = Get-CimInstance Win32_Process -Filter \"ParentProcessId = $current\" | "
        "Select-Object -ExpandProperty ProcessId;"
        "foreach ($child in $children) { $pending.Enqueue([int]$child) }"
        "}"
        "$visited"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return [root_pid]
    return [int(line.strip()) for line in result.stdout.splitlines() if line.strip().isdigit()]


def process_tree_pids(root_pid: int) -> list[int]:
    if os.name == "nt":
        return _process_tree_pids_windows(root_pid)
    if sys.platform.startswith("linux"):
        root_children = _child_pids_linux(root_pid)
        return [root_pid, *root_children]
    return [root_pid]


def rss_breakdown_for_process_tree(root_pid: int) -> list[dict[str, float | int]]:
    entries: list[dict[str, float | int]] = []
    for pid in process_tree_pids(root_pid):
        try:
            rss_mb = rss_mb_for_pid(pid)
        except MemoryProbeError:
            continue
        entries.append({"pid": pid, "rss_mb": round(rss_mb, 2)})
    return entries


def parse_intervals(raw_value: str) -> list[int]:
    values = [int(item.strip()) for item in raw_value.split(",") if item.strip()]
    intervals = sorted({item for item in values if item > 0})
    if not intervals:
        raise MemoryProbeError("--intervals 必须包含至少一个正整数")
    return intervals


def probe_import_deltas(modules: list[str]) -> dict[str, Any]:
    baseline_rss_mb = rss_mb_for_pid(os.getpid())
    entries: list[dict[str, Any]] = []

    for module_name in modules:
        before_rss_mb = rss_mb_for_pid(os.getpid())
        started_at = time.perf_counter()
        importlib.import_module(module_name)
        gc.collect()
        elapsed_seconds = round(time.perf_counter() - started_at, 4)
        after_rss_mb = rss_mb_for_pid(os.getpid())
        entries.append(
            {
                "module": module_name,
                "before_rss_mb": round(before_rss_mb, 2),
                "after_rss_mb": round(after_rss_mb, 2),
                "delta_rss_mb": round(after_rss_mb - before_rss_mb, 2),
                "elapsed_seconds": elapsed_seconds,
            }
        )

    final_rss_mb = rss_mb_for_pid(os.getpid())
    return {
        "baseline_rss_mb": round(baseline_rss_mb, 2),
        "final_rss_mb": round(final_rss_mb, 2),
        "total_delta_rss_mb": round(final_rss_mb - baseline_rss_mb, 2),
        "entries": entries,
    }


def wait_for_port(host: str, port: int, timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            if sock.connect_ex((host, port)) == 0:
                return
        time.sleep(0.2)
    raise MemoryProbeError(f"服务启动超时: {host}:{port}")


def render_command(command_template: str, port: int) -> list[str]:
    command_text = command_template.format(port=port, python="{python}")
    tokens = shlex.split(command_text, posix=os.name != "nt")
    command: list[str] = []
    for token in tokens:
        normalized = token.strip('"\'')
        if normalized == "{python}":
            command.append(sys.executable)
            continue
        command.append(token)
    return command


def _terminate_process(process: subprocess.Popen[str]) -> tuple[str, str]:
    if process.poll() is None:
        process.terminate()
    try:
        stdout, stderr = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate(timeout=5)
    return stdout, stderr


def probe_service_memory(
    command_template: str,
    host: str,
    port: int,
    intervals_seconds: list[int],
    startup_timeout_seconds: int,
) -> dict[str, Any]:
    command = render_command(command_template, port)
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    samples: list[dict[str, Any]] = []
    try:
        wait_for_port(host, port, startup_timeout_seconds)
        started_at = time.monotonic()
        for elapsed_seconds in intervals_seconds:
            target_time = started_at + elapsed_seconds
            sleep_seconds = max(0.0, target_time - time.monotonic())
            time.sleep(sleep_seconds)
            if process.poll() is not None:
                raise MemoryProbeError(f"服务提前退出，退出码: {process.returncode}")
            rss_by_pid = rss_breakdown_for_process_tree(process.pid)
            rss_mb = sum(item["rss_mb"] for item in rss_by_pid)
            samples.append(
                {
                    "elapsed_seconds": elapsed_seconds,
                    "rss_mb": round(rss_mb, 2),
                    "rss_by_pid": rss_by_pid,
                }
            )
    except Exception as error:
        stdout, stderr = _terminate_process(process)
        details = {
            "error": str(error),
            "stdout_tail": stdout[-4000:],
            "stderr_tail": stderr[-4000:],
        }
        raise MemoryProbeError(json.dumps(details, ensure_ascii=False)) from error
    else:
        stdout, stderr = _terminate_process(process)
        return {
            "command": command,
            "samples": samples,
            "stdout_tail": stdout[-2000:],
            "stderr_tail": stderr[-2000:],
        }
