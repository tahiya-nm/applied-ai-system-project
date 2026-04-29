"""Reliability tests for the PawPal AI features.

Two tiers:
  - Deterministic: no API key required. Tests guardrails, retrieval logic,
    and logging format.
  - LLM-as-judge: skipped without OPENAI_API_KEY. Uses a second OpenAI call
    to evaluate the quality of RAG responses.
"""

import json
import os

import pytest

from pawpal_system import Owner, Pet, Task, Priority
from ai.guidelines_kb import retrieve_guidelines, CARE_GUIDELINES
from ai import rag_assistant, logging_utils


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_dog_owner() -> Owner:
    owner = Owner("Test", 60)
    dog = Pet("Buddy", "dog")
    dog.add_task(Task("Morning walk", 30, Priority.HIGH))
    dog.add_task(Task("Feeding", 5, Priority.HIGH))
    owner.add_pet(dog)
    return owner


def make_cat_owner() -> Owner:
    owner = Owner("Test", 60)
    cat = Pet("Whiskers", "cat")
    cat.add_task(Task("Clean litter box", 10, Priority.HIGH))
    cat.add_task(Task("Playtime", 15, Priority.MEDIUM))
    owner.add_pet(cat)
    return owner


# ── Knowledge base retrieval ──────────────────────────────────────────────────

def test_retrieve_dog_walk():
    results = retrieve_guidelines("dog", "morning walk")
    keys = [r["key"] for r in results]
    assert "dog/walk" in keys


def test_retrieve_cat_litter():
    results = retrieve_guidelines("cat", "clean litter box")
    keys = [r["key"] for r in results]
    assert "cat/litter" in keys


def test_retrieve_case_insensitive():
    lower = retrieve_guidelines("dog", "walk")
    upper = retrieve_guidelines("dog", "WALK")
    assert len(lower) == len(upper)


def test_retrieve_fallback_to_other_for_unknown_species():
    results = retrieve_guidelines("rabbit", "feeding")
    assert len(results) >= 1
    assert all(r["key"].startswith("other/") for r in results)


def test_retrieve_no_match_returns_empty():
    results = retrieve_guidelines("dog", "xyzgibberish123")
    assert results == []


def test_retrieve_result_has_required_fields():
    results = retrieve_guidelines("dog", "walk")
    assert len(results) >= 1
    for r in results:
        assert "key" in r
        assert "min_duration_minutes" in r
        assert "recommended_frequency" in r
        assert "notes" in r


def test_retrieve_unknown_species_uses_other_key_prefix():
    results = retrieve_guidelines("hamster", "feeding")
    for r in results:
        assert r["key"].startswith("other/")


# ── Guardrail short-circuits (no API call) ────────────────────────────────────

def test_guardrail_empty_query():
    owner = make_dog_owner()
    result = rag_assistant.ask("", owner)
    assert "please" in result.lower() or "ask" in result.lower()


def test_guardrail_whitespace_query():
    owner = make_dog_owner()
    result = rag_assistant.ask("   \t  ", owner)
    assert "please" in result.lower() or "ask" in result.lower()


def test_guardrail_no_pets():
    owner = Owner("Empty", 60)
    result = rag_assistant.ask("How often should I walk my dog?", owner)
    assert "pet" in result.lower()


def test_guardrail_no_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    owner = make_dog_owner()
    result = rag_assistant.ask("How long should Buddy's walk be?", owner)
    assert "api_key" in result.lower() or "key" in result.lower() or "openai" in result.lower()


# ── Logging ───────────────────────────────────────────────────────────────────

def test_log_event_writes_valid_jsonl(tmp_path, monkeypatch):
    log_file = tmp_path / "test.log"
    monkeypatch.setattr(logging_utils, "LOG_PATH", log_file)
    logging_utils.log_event("test_feature", "test_event", extra="data")
    lines = log_file.read_text().strip().split("\n")
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["feature"] == "test_feature"
    assert entry["event"] == "test_event"
    assert entry["extra"] == "data"


def test_log_event_required_fields_present(tmp_path, monkeypatch):
    log_file = tmp_path / "test.log"
    monkeypatch.setattr(logging_utils, "LOG_PATH", log_file)
    logging_utils.log_event("rag_assistant", "query")
    entry = json.loads(log_file.read_text().strip())
    assert "timestamp" in entry
    assert "feature" in entry
    assert "event" in entry


def test_log_event_appends_multiple_lines(tmp_path, monkeypatch):
    log_file = tmp_path / "test.log"
    monkeypatch.setattr(logging_utils, "LOG_PATH", log_file)
    logging_utils.log_event("f", "e1")
    logging_utils.log_event("f", "e2")
    lines = log_file.read_text().strip().split("\n")
    assert len(lines) == 2
    for line in lines:
        json.loads(line)  # each line must be valid JSON


def test_guardrail_triggers_log_entry(tmp_path, monkeypatch):
    log_file = tmp_path / "test.log"
    monkeypatch.setattr(logging_utils, "LOG_PATH", log_file)
    owner = make_dog_owner()
    rag_assistant.ask("", owner)
    entries = [json.loads(l) for l in log_file.read_text().strip().split("\n")]
    guardrail_events = [e for e in entries if e["event"] == "guardrail_triggered"]
    assert len(guardrail_events) >= 1
    assert guardrail_events[0]["reason"] == "empty_query"


# ── LLM-as-judge evaluation (requires OPENAI_API_KEY) ────────────────────────

needs_api_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set — skipping live API tests",
)


@needs_api_key
def test_rag_returns_non_empty_response():
    owner = make_dog_owner()
    result = rag_assistant.ask("How long should Buddy's walk be?", owner)
    assert len(result.strip()) > 20


@needs_api_key
def test_rag_response_mentions_relevant_topic():
    owner = make_dog_owner()
    result = rag_assistant.ask("How long should Buddy's walk be?", owner)
    lower = result.lower()
    assert any(word in lower for word in ("walk", "minute", "exercise", "daily"))


@needs_api_key
def test_rag_response_cites_only_retrieved_context():
    """Judge test: verify the model doesn't introduce claims outside the provided guidelines."""
    import openai

    owner = make_dog_owner()
    response = rag_assistant.ask("How long should Buddy's walk be?", owner)

    walk_guideline = CARE_GUIDELINES["dog"]["walk"]
    context = (
        f"Min duration: {walk_guideline['min_duration_minutes']} min. "
        f"Frequency: {walk_guideline['recommended_frequency']}. "
        f"Notes: {walk_guideline['notes']}"
    )

    client = openai.OpenAI()
    judge = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=10,
        messages=[{
            "role": "user",
            "content": (
                f"The AI was given only this context:\n{context}\n\n"
                f"The AI responded:\n{response}\n\n"
                "Did the AI introduce any specific factual claims clearly NOT present "
                "in the provided context? Answer only YES or NO."
            ),
        }],
    )
    verdict = judge.choices[0].message.content.strip().upper()
    assert verdict == "NO", f"Judge detected hallucination. Response was:\n{response}"


@needs_api_key
def test_rag_admits_when_topic_not_in_guidelines():
    """The assistant should acknowledge when it lacks relevant guidelines."""
    owner = make_dog_owner()
    result = rag_assistant.ask("What is the best brand of dog food to buy?", owner)
    lower = result.lower()
    assert any(
        phrase in lower
        for phrase in ("guideline", "vet", "not cover", "don't have", "cannot", "consult", "no specific")
    )


@needs_api_key
def test_rag_cat_litter_response():
    owner = make_cat_owner()
    result = rag_assistant.ask("How often should I clean Whiskers' litter box?", owner)
    lower = result.lower()
    assert any(word in lower for word in ("daily", "scoop", "litter", "box"))
