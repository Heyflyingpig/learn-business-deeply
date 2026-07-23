#!/usr/bin/env python3
"""只读提取 Codex 当前任务及 fork 父任务中的有效文本。"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


@dataclass
class Session:
    thread_id: str
    path: Path
    created_at: str | None
    forked_from_id: str | None
    events: list[dict[str, Any]]


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def event_time(event: dict[str, Any]) -> datetime | None:
    return parse_time(event.get("timestamp"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: JSON 解析失败: {exc}") from exc
            if isinstance(value, dict):
                events.append(value)
    return events


def session_from_path(path: Path) -> Session | None:
    events = read_jsonl(path)
    meta_event = next((item for item in events if item.get("type") == "session_meta"), None)
    if not meta_event:
        return None
    payload = meta_event.get("payload") or {}
    thread_id = payload.get("id") or payload.get("session_id")
    if not isinstance(thread_id, str):
        return None
    return Session(
        thread_id=thread_id,
        path=path,
        created_at=payload.get("timestamp") or meta_event.get("timestamp"),
        forked_from_id=payload.get("forked_from_id"),
        events=events,
    )


def find_session(thread_id: str, sessions_root: Path) -> Session | None:
    direct = sorted(sessions_root.rglob(f"*{thread_id}*.jsonl"))
    candidates = direct if direct else sorted(sessions_root.rglob("*.jsonl"))
    for path in candidates:
        try:
            session = session_from_path(path)
        except (OSError, ValueError):
            continue
        if session and session.thread_id == thread_id:
            return session
    return None


def build_lineage(thread_id: str, sessions_root: Path) -> tuple[list[tuple[Session, datetime | None]], list[str]]:
    lineage: list[tuple[Session, datetime | None]] = []
    warnings: list[str] = []
    seen: set[str] = set()
    current_id: str | None = thread_id
    child_created_at: datetime | None = None

    while current_id:
        if current_id in seen:
            warnings.append(f"检测到循环 fork 谱系: {current_id}")
            break
        seen.add(current_id)
        session = find_session(current_id, sessions_root)
        if not session:
            warnings.append(f"无法定位任务 session: {current_id}")
            break
        lineage.append((session, child_created_at))
        child_created_at = parse_time(session.created_at)
        current_id = session.forked_from_id

    lineage.reverse()
    return lineage, warnings


def text_from_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
            continue
        if not isinstance(item, dict):
            continue
        for key in ("text", "input_text", "output_text"):
            value = item.get(key)
            if isinstance(value, str):
                parts.append(value)
                break
    return "\n".join(part for part in parts if part)


def is_effective_message(role: str, text: str) -> bool:
    if role not in {"user", "assistant"} or not text.strip():
        return False
    stripped = text.strip()
    ignored_prefixes = (
        "<environment_context>",
        "<permissions instructions>",
        "<collaboration_mode>",
        "<skills_instructions>",
    )
    return not stripped.startswith(ignored_prefixes)


def extract_messages(events: Iterable[dict[str, Any]], cutoff: datetime | None) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for event in events:
        timestamp = event_time(event)
        if cutoff and timestamp and timestamp > cutoff:
            continue
        if event.get("type") != "response_item":
            continue
        payload = event.get("payload") or {}
        if payload.get("type") != "message":
            continue
        role = payload.get("role")
        text = text_from_content(payload.get("content"))
        if not isinstance(role, str) or not is_effective_message(role, text):
            continue
        messages.append(
            {
                "timestamp": event.get("timestamp"),
                "role": role,
                "text": text,
                "item_id": payload.get("id"),
            }
        )
    return messages


def extract_tool_evidence(events: Iterable[dict[str, Any]], cutoff: datetime | None) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for event in events:
        timestamp = event_time(event)
        if cutoff and timestamp and timestamp > cutoff:
            continue
        if event.get("type") != "response_item":
            continue
        payload = event.get("payload") or {}
        payload_type = str(payload.get("type") or "")
        if "call" not in payload_type and "output" not in payload_type:
            continue
        evidence.append(
            {
                "timestamp": event.get("timestamp"),
                "type": payload_type,
                "name": payload.get("name"),
                "content": payload,
            }
        )
    return evidence


def deduplicate(items: Iterable[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        raw = "\0".join(str(item.get(field) or "") for field in fields)
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        result.append(item)
    return result


def render_markdown(result: dict[str, Any]) -> str:
    lines = ["# Codex 任务谱系提取", "", "## 谱系", ""]
    for source in result["sources"]:
        cutoff = source.get("cutoff") or "任务结束"
        lines.append(f"- `{source['thread_id']}`：`{source['path']}`，读取截止 `{cutoff}`")
    lines.extend(["", "## 完整性", ""])
    if result["warnings"]:
        lines.extend(f"- 警告：{warning}" for warning in result["warnings"])
    else:
        lines.append("- 已解析完整可见 fork 谱系。")
    lines.extend(["", "## 有效对话", ""])
    for index, message in enumerate(result["messages"], 1):
        role = "用户" if message["role"] == "user" else "助手"
        lines.extend([f"### M-{index:04d} {role}", "", message["text"].rstrip(), ""])
    if result["tool_evidence"]:
        lines.extend(["## 工具证据", ""])
        for index, item in enumerate(result["tool_evidence"], 1):
            lines.extend(
                [
                    f"### T-{index:04d} {item['type']}",
                    "",
                    "```json",
                    json.dumps(item["content"], ensure_ascii=False, indent=2),
                    "```",
                    "",
                ]
            )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--thread-id", required=True, help="当前 Codex 任务 ID")
    parser.add_argument(
        "--sessions-root",
        type=Path,
        default=Path.home() / ".codex" / "sessions",
        help="Codex sessions 根目录",
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--include-tool-evidence", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.sessions_root.is_dir():
        print(f"sessions 根目录不存在: {args.sessions_root}", file=sys.stderr)
        return 2

    lineage, warnings = build_lineage(args.thread_id, args.sessions_root)
    messages: list[dict[str, Any]] = []
    tool_evidence: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []

    for session, cutoff in lineage:
        messages.extend(extract_messages(session.events, cutoff))
        if args.include_tool_evidence:
            tool_evidence.extend(extract_tool_evidence(session.events, cutoff))
        sources.append(
            {
                "thread_id": session.thread_id,
                "path": str(session.path),
                "created_at": session.created_at,
                "forked_from_id": session.forked_from_id,
                "cutoff": cutoff.isoformat() if cutoff else None,
            }
        )

    result = {
        "root_thread_id": args.thread_id,
        "complete": not warnings,
        "warnings": warnings,
        "sources": sources,
        "messages": deduplicate(messages, ("role", "text")),
        "tool_evidence": deduplicate(tool_evidence, ("type", "content")),
    }
    result["counts"] = {
        "sources": len(result["sources"]),
        "messages": len(result["messages"]),
        "user_messages": sum(item["role"] == "user" for item in result["messages"]),
        "assistant_messages": sum(item["role"] == "assistant" for item in result["messages"]),
        "tool_evidence": len(result["tool_evidence"]),
    }

    if args.format == "markdown":
        print(render_markdown(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
