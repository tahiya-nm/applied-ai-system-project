# PawPal+

**PawPal+** is an AI-powered pet care assistant that helps multi-pet owners plan daily care schedules, detect conflicts, and get grounded answers to species-specific care questions — all in a single Streamlit app.

---

## Original Project

This project extends **PawPal Pet Management System** (Modules 1–3), a Python-based CLI tool for managing tasks across multiple pets with a shared daily time budget. The original app let owners add pets and care tasks, generate a priority-ordered schedule, detect time conflicts, and mark recurring tasks as complete. It had no AI features — scheduling logic was purely algorithmic, and care advice required the owner to look things up elsewhere.

PawPal+ adds a RAG-powered chat assistant that answers pet care questions using a curated species-specific knowledge base, with guardrails and structured logging built in.

---

## Why It Matters

Pet owners juggling multiple animals often struggle to balance care tasks across a limited daily time budget, and generic AI chatbots give inconsistent advice when asked about pet care specifics. PawPal+ solves both problems in one place: a scheduler grounded in real constraints, plus a care assistant grounded in documented guidelines — not model hallucinations.

---

## Architecture Overview

![System Architecture](images/final-system-diagram.png)

The system has two layers:

**Core scheduling layer** — Five Python classes handle all domain logic: `Owner` holds the shared time budget and list of pets; `Pet` owns a task list; `Task` stores title, duration, priority, recurrence, and due date; `Scheduler` runs a greedy priority-first algorithm over all of an owner's pets; and `Plan` holds the structured output with per-task reasons.

**AI layer** — The `ai/` package contains three modules. `guidelines_kb.py` is a static knowledge base of species-specific care facts (dogs, cats, rabbits, birds, fish, and an "other" fallback). `rag_assistant.py` retrieves relevant guidelines by keyword matching before every OpenAI call, injects them into a constrained system prompt, fires four input guardrails, and logs every event. `logging_utils.py` writes structured JSONL to `ai/pawpal_ai.log` with timestamps, token counts, and content previews.

The Streamlit UI in `app.py` wires both layers together: scheduling features are always available, while the AI chat sidebar appears only after an owner and at least one pet are configured and an API key is present.

---

## Setup Instructions

```bash
# 1. Clone the repo and enter the directory
git clone https://github.com/tmahi/applied-ai-system-project.git
cd applied-ai-system-project

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your OpenAI API key (required for the AI chat sidebar)
export OPENAI_API_KEY=your-key-here   # Windows: set OPENAI_API_KEY=your-key-here

# 5. Run the app
streamlit run app.py
```

The scheduling features work without an API key. The AI chat sidebar is hidden automatically when no key is set.

---

## Sample Interactions

### 1 — Generating a daily schedule

**Setup:** Owner "Alex" with a 60-minute budget; one dog (Buddy) with three tasks — Morning walk (30 min, HIGH), Medication (5 min, HIGH), Extended playtime (40 min, LOW).

**Generated plan output:**
```
Scheduled:
  ✓ Morning walk — 30 min (HIGH)   [reason: high priority]
  ✓ Medication   —  5 min (HIGH)   [reason: high priority]

Skipped:
  ✗ Extended playtime — 40 min (LOW)  [reason: only 25 min remaining]

Time used: 35 / 60 min  ████████░░░░░░░░  58%
```

### 2 — Conflict detection warning

**Setup:** Same owner; two tasks with overlapping scheduled times — Morning walk at 08:00 (30 min, ends 08:30) and Vet checkup at 08:15 (20 min).

**Inline warning shown in task list:**
```
⚠ Conflict: "Morning walk" (08:00–08:30) overlaps with "Vet checkup" (08:15–08:35)
```

### 3 — RAG care assistant

**User question:** "How often should I walk my dog and for how long?"

**AI response (grounded in retrieved guideline `dog/walk`):**
```
Based on the care guidelines for Buddy (dog):

Dogs need at least 20–30 minutes of walking per day. Larger or more active breeds
benefit from 45–60 minutes. Daily walks support both physical and mental health —
skipping more than one day in a row is not recommended. Given Buddy's current
30-minute morning walk task, this aligns with the minimum daily recommendation.
```

---

## Design Decisions

**Greedy scheduling over optimization.** The scheduler sorts tasks by priority (HIGH → MEDIUM → LOW) and duration (shortest-first as a tie-breaker), then walks the list once and fits tasks into the remaining budget. A knapsack-style optimizer would find tighter solutions, but for daily pet care — short durations, small budgets, clear priority ordering — greedy produces acceptable plans with far less complexity.

**`Scheduler` takes `Owner`, not individual pets.** Early designs passed `Owner` + `Pet` separately, which would apply the full time budget per pet and effectively multiply available time. Taking only `Owner` and iterating `owner.pets` puts all tasks into a single shared pool under one budget, which matches how a real owner's day works.

**RAG over fine-tuning.** A fine-tuned model would be expensive to update when care guidelines change. Keyword-based retrieval from a local knowledge base is fast, cheap, auditable, and easy to extend — add a new species key to `CARE_GUIDELINES` and it's immediately available.

**Constrained system prompt.** The assistant is explicitly told to answer only from retrieved guidelines and to say so clearly when it can't. This trades recall (it won't draw on broad model knowledge) for reliability — responses stay grounded and consistent across runs.

**`Priority` as an enum.** Using raw strings would allow values like `"urgent"` or `"HIGH"` to silently corrupt sorting. An enum makes invalid priorities a hard error at construction time.

---

## Testing Summary

The test suite has **44 tests** across two files.

```bash
python -m pytest tests/ -v
```

| File | Tests | Scope |
|------|-------|-------|
| `tests/test_pawpal.py` | 24 | Core domain logic |
| `tests/test_ai_features.py` | 15 deterministic + 5 LLM-as-judge | AI features |

**Core domain (24 tests)** — Covers chronological sorting (untimed tasks always last), daily and weekly recurrence (no double-spawning on repeat calls), conflict detection (overlapping vs. back-to-back), plan generation (priority order, shortest-first tie-break, zero-budget edge case, exact-fit task), and `get_filtered_tasks` (by status, pet name, case-insensitivity, nonexistent pet).

**AI features (20 tests)** — 15 deterministic tests cover knowledge-base retrieval for each species, all four guardrails (empty query, no pets, query too long, missing API key), and JSONL log format correctness. 5 LLM-as-judge tests make live OpenAI calls to evaluate response quality against criteria like groundedness and relevance; they skip automatically when no API key is set.

**What worked:** The deterministic tests caught two real bugs — a double-spawn edge case in recurrence and a case where back-to-back tasks were incorrectly flagged as conflicts. The LLM-as-judge tests were valuable for verifying that the constrained prompt actually kept responses on-topic.

**What didn't:** LLM-as-judge tests are non-deterministic and occasionally flake on borderline responses. Running them in CI without a stable scoring rubric would produce noisy failures.

**What I'd add next:** Property-based tests for the scheduler (randomized task sets, budget values) and snapshot tests for the RAG prompt structure to catch regressions when the knowledge base changes.

---

## Reflection

Building PawPal+ clarified something that's easy to miss when AI tools feel magical: a system is only as reliable as the constraints you build around the model. The RAG assistant works not because GPT-4o-mini is inherently accurate about pet care, but because the prompt tells it to refuse anything outside the retrieved context. Removing that constraint in testing produced responses that sounded confident but cited frequencies and durations inconsistent with the knowledge base.

The bigger lesson was about where AI fits in a system versus where it doesn't. The scheduler — the core value of the app — required no AI at all. A well-designed greedy algorithm with clear priority rules solves the scheduling problem better than a language model would, because it's deterministic, testable, and explainable. AI earned its place in the layer where the problem is genuinely unstructured: "what's the right way to care for this specific animal?" is a question with too many variables for hand-coded rules, and that's exactly where retrieval-augmented generation shines.

Working iteratively with Claude Code also changed how I think about software design collaboration. The most useful AI contributions weren't code generation — they were constraint discovery. When I described the multi-pet scheduling problem, the model immediately surfaced the shared-budget issue that would have broken the design. I still had to evaluate whether that concern was real and how to fix it, but having a fast, skeptical second opinion during design accelerated the thinking significantly.
