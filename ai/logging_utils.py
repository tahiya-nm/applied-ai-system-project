"""Append-only JSONL event logger for all AI feature interactions."""

import json
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).parent / "pawpal_ai.log"


def log_event(feature: str, event: str, **kwargs) -> None:
    """Append a single JSON line to the AI event log.

    Args:
        feature: Which AI module is logging (e.g. "rag_assistant").
        event:   What happened (e.g. "query", "response", "guardrail_triggered").
        **kwargs: Any additional fields to include (token counts, previews, etc.).
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "feature": feature,
        "event": event,
        **kwargs,
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
