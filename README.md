# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Smarter Scheduling

PawPal+ now includes several algorithmic enhancements to the core `Scheduler` class:

- **Priority-first scheduling** — `generate_plan()` greedily schedules tasks ordered by priority (HIGH → LOW), using duration as a tie-breaker (shortest first), and skips tasks that exceed the owner's remaining time budget.
- **Recurring tasks** — Tasks can be marked `daily` or `weekly`. After completion, `apply_recurrence()` automatically spawns the next instance with an advanced due date so the owner never has to re-enter repeating care routines.
- **Conflict detection** — `detect_conflicts()` scans all timed tasks and warns when two tasks overlap on the same schedule, preventing double-booking across pets.
- **Time-ordered view** — `sort_by_time()` returns tasks sorted chronologically by `scheduled_time`; untimed tasks appear last.
- **Flexible filtering** — `Owner.get_filtered_tasks()` lets the UI filter tasks by completion status, pet name, or both at once.

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
