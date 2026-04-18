"""
高性能 JSON 序列化工具

优先使用 orjson（比标准库快 3-10 倍），自动降级到标准库。
在 SSE 流、缓存序列化等热路径中使用。
"""

from typing import Any

try:
    import orjson

    def json_dumps(obj: Any) -> str:
        """高性能 JSON 序列化（返回 str）"""
        return orjson.dumps(obj, option=orjson.OPT_NON_STR_KEYS).decode("utf-8")

    def json_dumps_bytes(obj: Any) -> bytes:
        """高性能 JSON 序列化（返回 bytes，避免 decode 开销）"""
        return orjson.dumps(obj, option=orjson.OPT_NON_STR_KEYS)

    def json_loads(data: str | bytes) -> Any:
        """高性能 JSON 反序列化"""
        return orjson.loads(data)

except ImportError:
    import json

    def json_dumps(obj: Any) -> str:  # type: ignore[misc]
        """标准库 JSON 序列化（降级）"""
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

    def json_dumps_bytes(obj: Any) -> bytes:  # type: ignore[misc]
        """标准库 JSON 序列化为 bytes（降级）"""
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    def json_loads(data: str | bytes) -> Any:  # type: ignore[misc]
        """标准库 JSON 反序列化（降级）"""
        return json.loads(data)
