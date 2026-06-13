from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from supabase import Client, create_client


def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required")
    return create_client(url, key)


JOB_DATA_BUCKET = os.getenv("JOB_DATA_BUCKET", "job-data")


def ensure_job_data_bucket() -> None:
    """Create the job-data bucket if it does not exist (service role required)."""
    sb = get_supabase()
    bucket_exists = False
    try:
        sb.storage.get_bucket(JOB_DATA_BUCKET)
        bucket_exists = True
    except Exception:
        try:
            buckets = sb.storage.list_buckets()
            names = {b.get("name") or b.get("id") for b in (buckets or [])}
            bucket_exists = JOB_DATA_BUCKET in names
        except Exception:
            bucket_exists = False

    if bucket_exists:
        return

    try:
        sb.storage.create_bucket(JOB_DATA_BUCKET, options={"public": False})
        print(f"[agent] Created Supabase storage bucket: {JOB_DATA_BUCKET}")
    except Exception as exc:
        err = str(exc).lower()
        if "already exists" in err or "duplicate" in err:
            return
        raise RuntimeError(
            f"Supabase storage bucket '{JOB_DATA_BUCKET}' is missing and could not be created: {exc}. "
            f"Create it manually in Supabase → Storage → New bucket → name it '{JOB_DATA_BUCKET}'."
        ) from exc


def _storage_upload(bucket: str, path: str, payload: bytes, content_type: str) -> None:
    sb = get_supabase()
    opts = {"content-type": content_type, "x-upsert": "true"}
    storage = sb.storage.from_(bucket)
    try:
        storage.upload(path, payload, file_options=opts)
    except TypeError:
        storage.upload(path, payload, opts)


def upload_job_prepared_files(
    job_id: str,
    metadata_path: str,
    csv_path: str = "",
) -> None:
    """Upload preprocess artifacts so the Cloud Run worker can download them."""
    meta = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
    prepared_csv = csv_path or str(meta.get("outputCsvPath") or "")
    if not prepared_csv or not Path(prepared_csv).is_file():
        raise FileNotFoundError(f"Prepared CSV not found: {prepared_csv!r}")

    ensure_job_data_bucket()
    meta_bytes = Path(metadata_path).read_bytes()
    csv_bytes = Path(prepared_csv).read_bytes()
    _storage_upload(JOB_DATA_BUCKET, f"{job_id}/meta.json", meta_bytes, "application/json")
    _storage_upload(JOB_DATA_BUCKET, f"{job_id}/prepared.csv", csv_bytes, "text/csv")
    print(f"[agent] Uploaded prepared data to {JOB_DATA_BUCKET}/{job_id}/")


def create_job(row: dict[str, Any]) -> dict[str, Any]:
    sb = get_supabase()
    try:
        result = sb.table("training_jobs").insert(row).execute()
    except Exception as e:
        err = str(e)
        if "PGRST204" in err or "schema cache" in err.lower():
            raise RuntimeError(
                "training_jobs table is missing columns. Run docs/training-jobs-migration.sql "
                "in the Supabase SQL Editor, then retry."
            ) from e
        raise
    return result.data[0]


def get_job(job_id: str, user_account_id: str = "") -> Optional[dict[str, Any]]:
    sb = get_supabase()
    query = sb.table("training_jobs").select("*").eq("id", job_id)
    if user_account_id:
        query = query.eq("user_account_id", user_account_id)
    try:
        result = query.single().execute()
    except Exception:
        return None
    return result.data


def list_jobs(limit: int = 50, user_account_id: str = "") -> list[dict[str, Any]]:
    sb = get_supabase()
    query = sb.table("training_jobs").select("*")
    if user_account_id:
        query = query.eq("user_account_id", user_account_id)
    result = query.order("created_at", desc=True).limit(limit).execute()
    return result.data or []


# --- Chat persistence (uses base schema: title + content only) ---


def _encode_assistant_content(text: str, extra: Optional[dict[str, Any]] = None) -> str:
    payload: dict[str, Any] = dict(extra or {})
    if text:
        payload["text"] = text
    if len(payload) == 1 and "text" in payload:
        return payload["text"]
    if not payload:
        return ""
    return json.dumps(payload)


def _decode_message_content(role: str, content: str) -> tuple[str, dict[str, Any]]:
    if role != "assistant" or not content:
        return content or "", {}
    stripped = content.strip()
    if not stripped.startswith("{"):
        return content, {}
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return content, {}
    if not isinstance(data, dict):
        return content, {}
    text = str(data.pop("text", "") or "")
    return text, data


def create_thread(
    title: str,
    use_case: str = "",
    architecture_id: str = "",
    user_account_id: str = "",
) -> dict[str, Any]:
    sb = get_supabase()
    label = (use_case or title or "New chat")[:200]
    row: dict[str, Any] = {"title": label}
    if user_account_id:
        row["user_account_id"] = user_account_id
    result = sb.table("chat_threads").insert(row).execute()
    return result.data[0]


def update_thread(
    thread_id: str,
    *,
    title: Optional[str] = None,
    use_case: Optional[str] = None,
    architecture_id: Optional[str] = None,
) -> None:
    sb = get_supabase()
    patch: dict[str, Any] = {}
    if title is not None:
        patch["title"] = title[:200]
    elif use_case is not None:
        patch["title"] = use_case[:200]
    if patch:
        sb.table("chat_threads").update(patch).eq("id", thread_id).execute()


def list_threads(limit: int = 30, user_account_id: str = "") -> list[dict[str, Any]]:
    sb = get_supabase()
    query = sb.table("chat_threads").select("id, title, created_at, user_account_id")
    if user_account_id:
        query = query.eq("user_account_id", user_account_id)
    result = query.order("created_at", desc=True).limit(limit).execute()
    return result.data or []


def get_thread(thread_id: str, user_account_id: str = "") -> Optional[dict[str, Any]]:
    sb = get_supabase()
    query = (
        sb.table("chat_threads")
        .select("id, title, created_at, user_account_id")
        .eq("id", thread_id)
    )
    if user_account_id:
        query = query.eq("user_account_id", user_account_id)
    try:
        result = query.single().execute()
    except Exception:
        return None
    return result.data


def list_messages(thread_id: str) -> list[dict[str, Any]]:
    sb = get_supabase()
    result = (
        sb.table("chat_messages")
        .select("id, role, content, created_at")
        .eq("thread_id", thread_id)
        .order("created_at", desc=False)
        .execute()
    )
    return result.data or []


def save_message(
    thread_id: str,
    role: str,
    content: str,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    sb = get_supabase()
    stored = content
    if role == "assistant" and metadata:
        stored = _encode_assistant_content(content, metadata)
    row = {
        "thread_id": thread_id,
        "role": role,
        "content": stored,
    }
    result = sb.table("chat_messages").insert(row).execute()
    return result.data[0]


def messages_to_agent_history(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    from llm_context import trim_history

    history: list[dict[str, str]] = []
    for row in messages:
        role = row.get("role", "user")
        if role not in ("user", "assistant"):
            continue
        if role == "assistant":
            text, _ = _decode_message_content(role, row.get("content") or "")
        else:
            text = row.get("content") or ""
        if text.strip():
            history.append({"role": role, "content": text})
    return trim_history(history)


def message_row_to_chat_block(row: dict[str, Any]) -> dict[str, Any]:
    role = row.get("role", "user")
    content = row.get("content") or ""
    if role == "user":
        return {"role": "user", "text": content}
    text, meta = _decode_message_content(role, content)
    block: dict[str, Any] = {"role": "assistant"}
    if text:
        block["text"] = text
    if meta.get("dataset"):
        block["dataset"] = meta["dataset"]
    if meta.get("datasets"):
        block["datasets"] = meta["datasets"]
    if meta.get("job"):
        block["job"] = meta["job"]
    return block
