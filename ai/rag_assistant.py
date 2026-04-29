"""RAG-powered care assistant.

Retrieves species-specific guidelines from the local knowledge base before
every OpenAI call so that answers are grounded in documented care facts rather
than general model knowledge.
"""

import os

import openai

from pawpal_system import Owner
from ai.guidelines_kb import retrieve_guidelines
from ai import logging_utils

MAX_QUERY_LENGTH = 500

SYSTEM_PROMPT = (
    "You are PawPal's AI care assistant. You help pet owners make informed care decisions. "
    "You MUST only use information from the care guidelines provided in the user message. "
    "Do not introduce external facts, veterinary advice, or claims not present in the guidelines. "
    "If the guidelines do not cover the question, say so clearly and suggest consulting a veterinarian. "
    "Keep your response under 150 words and be practical and specific."
)


def _build_user_message(question: str, owner: Owner) -> tuple[str, list[str]]:
    """Assemble the RAG prompt and return (message_text, retrieved_keys)."""
    # Retrieve guidelines for every pet's tasks AND for keywords in the question
    retrieved_map: dict[str, dict] = {}
    for pet in owner.pets:
        for task in pet.get_tasks():
            for g in retrieve_guidelines(pet.species, task.title):
                retrieved_map[g["key"]] = g
        for g in retrieve_guidelines(pet.species, question):
            retrieved_map[g["key"]] = g

    retrieved = list(retrieved_map.values())
    retrieved_keys = [g["key"] for g in retrieved]

    # Pet context block
    pet_lines = []
    for pet in owner.pets:
        titles = [t.title for t in pet.get_tasks()] or ["no tasks yet"]
        pet_lines.append(f"- {pet.name} ({pet.species}): {', '.join(titles)}")
    pet_context = "\n".join(pet_lines)

    # Guidelines block
    if retrieved:
        guideline_lines = [
            f"[{g['key']}] Min duration: {g['min_duration_minutes']} min. "
            f"Frequency: {g['recommended_frequency']}. Notes: {g['notes']}"
            for g in retrieved
        ]
        guidelines_text = "\n".join(guideline_lines)
    else:
        guidelines_text = "No specific guidelines found for these pets and tasks."

    message = (
        f"Pet context:\n{pet_context}\n\n"
        f"Retrieved care guidelines:\n{guidelines_text}\n\n"
        f"Question: {question}"
    )
    return message, retrieved_keys


def ask(question: str, owner: Owner) -> str:
    """Answer a pet care question using retrieved guidelines as context.

    Guardrails fire before the API call and return canned messages for
    invalid inputs. All events are logged to ai/pawpal_ai.log.
    """
    # Guardrail: empty or whitespace-only query
    if not question.strip():
        logging_utils.log_event("rag_assistant", "guardrail_triggered", reason="empty_query")
        return "Please ask a question about your pet's care."

    # Guardrail: no pets set up
    if not owner.pets:
        logging_utils.log_event("rag_assistant", "guardrail_triggered", reason="no_pets")
        return "Add a pet first — I need to know your pet's species to look up care guidelines."

    # Guardrail: query too long (truncate silently)
    if len(question) > MAX_QUERY_LENGTH:
        logging_utils.log_event(
            "rag_assistant", "guardrail_triggered",
            reason="query_truncated",
            original_length=len(question),
        )
        question = question[:MAX_QUERY_LENGTH]

    # Guardrail: no API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "AI features require an OPENAI_API_KEY environment variable to be set."

    user_message, retrieved_keys = _build_user_message(question, owner)

    logging_utils.log_event(
        "rag_assistant", "query",
        content_preview=question[:100],
        retrieved_chunks=retrieved_keys,
        num_pets=len(owner.pets),
    )

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=300,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        response_text = response.choices[0].message.content or ""

        logging_utils.log_event(
            "rag_assistant", "response",
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            retrieved_chunks=retrieved_keys,
            content_preview=response_text[:100],
        )

        return response_text

    except openai.OpenAIError as e:
        logging_utils.log_event("rag_assistant", "api_error", error=str(e))
        return "Sorry, I couldn't reach the AI service right now. Please try again in a moment."
