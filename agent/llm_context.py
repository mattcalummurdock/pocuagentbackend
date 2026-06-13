from __future__ import annotations

import json
import os
from typing import Any

MAX_HISTORY_MESSAGES = int(os.getenv("AGENT_MAX_HISTORY_MESSAGES", "8"))
MAX_MESSAGE_CHARS = int(os.getenv("AGENT_MAX_MESSAGE_CHARS", "1500"))
MAX_TOOL_RESULT_CHARS = int(os.getenv("AGENT_MAX_TOOL_RESULT_CHARS", "2500"))
MAX_LLM_PAYLOAD_CHARS = int(os.getenv("AGENT_MAX_LLM_PAYLOAD_CHARS", "28000"))


def truncate_text(text: str, max_chars: int, suffix: str = "… [truncated]") -> str:
    text = text or ""
    if len(text) <= max_chars:
        return text
    keep = max(0, max_chars - len(suffix))
    return text[:keep] + suffix


def trim_history(history: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep only recent, short messages for LLM context."""
    trimmed: list[dict[str, str]] = []
    for row in history[-MAX_HISTORY_MESSAGES:]:
        role = row.get("role", "user")
        content = truncate_text(str(row.get("content") or ""), MAX_MESSAGE_CHARS)
        if content.strip():
            trimmed.append({"role": role, "content": content})
    return trimmed


def compact_job_status(job: dict[str, Any]) -> dict[str, Any]:
    logs = str(job.get("logs") or "")
    return {
        "id": job.get("id"),
        "status": job.get("status"),
        "use_case": job.get("use_case"),
        "architecture_id": job.get("architecture_id"),
        "error_message": job.get("error_message"),
        "acp_status": job.get("acp_status"),
        "acp_progress_pct": job.get("acp_progress_pct"),
        "onchain_job_id": job.get("onchain_job_id"),
        "logs_tail": truncate_text(logs, 400) if logs else None,
    }


def compact_tool_result(name: str, result: str) -> str:
    """Shrink tool JSON before it is fed back into the LLM."""
    try:
        data = json.loads(result)
    except json.JSONDecodeError:
        return truncate_text(result, MAX_TOOL_RESULT_CHARS)

    if name == "get_training_job" and isinstance(data, dict):
        return json.dumps(compact_job_status(data), indent=2)

    if name == "list_architectures_tool" and isinstance(data, list):
        compact = [
            {
                "id": a.get("id"),
                "name": a.get("name"),
                "tier": a.get("tier"),
                "taskType": a.get("taskType"),
            }
            for a in data
        ]
        return json.dumps(compact, indent=2)

    if name == "search_kaggle_datasets" and isinstance(data, dict):
        if data.get("mode") == "list" and isinstance(data.get("datasets"), list):
            data = {
                **data,
                "datasets": [
                    {
                        "ref": d.get("ref"),
                        "title": d.get("title"),
                        "size_mb": d.get("size_mb"),
                    }
                    for d in data["datasets"][:8]
                ],
            }
        elif data.get("dataset"):
            d = data["dataset"]
            data = {
                **data,
                "dataset": {
                    "ref": d.get("ref"),
                    "title": d.get("title"),
                    "size_mb": d.get("size_mb"),
                },
            }
        return json.dumps(data, indent=2)

    if name == "download_and_prepare_dataset" and isinstance(data, dict):
        return json.dumps(
            {
                "job_id": data.get("job_id"),
                "input_dim": data.get("input_dim"),
                "num_classes": data.get("num_classes"),
                "target_column": data.get("target_column"),
                "task_type": data.get("task_type"),
                "data_hash": data.get("data_hash"),
                "metadata_path": data.get("metadata_path"),
            },
            indent=2,
        )

    if name == "inspect_kaggle_dataset_tool" and isinstance(data, dict):
        files = data.get("files") or []
        return json.dumps(
            {
                "ok": data.get("ok"),
                "total_mb": data.get("total_mb"),
                "files": [{"name": f.get("name"), "size_mb": f.get("size_mb")} for f in files[:10]],
            },
            indent=2,
        )

    return truncate_text(result, MAX_TOOL_RESULT_CHARS)


def message_content_chars(message: Any) -> int:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return len(json.dumps(content, default=str))
    return len(str(content or ""))


def prune_messages(messages: list[Any]) -> list[Any]:
    """Drop older turns when the payload is too large for Groq TPM limits."""
    total = sum(message_content_chars(m) for m in messages)
    if total <= MAX_LLM_PAYLOAD_CHARS:
        return messages
    if len(messages) <= 3:
        return messages
    head = messages[:1]
    tail = messages[-6:]
    if head[0] is tail[0]:
        return tail
    return head + tail
