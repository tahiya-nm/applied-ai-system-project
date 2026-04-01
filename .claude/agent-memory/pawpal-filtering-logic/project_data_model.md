---
name: PawPal Data Model Attribute Names
description: Exact attribute names and relationships for Owner, Pet, and Task classes in pawpal_system.py
type: project
---

Owner -> Pet -> Task relationship chain:
- `Owner.pets` — list[Pet], populated via `Owner.add_pet(pet)`
- `Pet.name` — str, the pet's display name
- `Pet.get_tasks()` — returns internal `Pet._tasks` list[Task]; prefer this accessor over `_tasks` directly
- `Task.completed` — bool, default False; set to True via `Task.mark_complete()`
- `Task.title` — str, task display name
- `Task.duration_minutes` — int, used in plan output
- `Task.priority` — Priority enum (HIGH=3, MEDIUM=2, LOW=1)
- `Task.scheduled_time` — str | None, "HH:MM" format

**Why:** These names are non-obvious (e.g., `_tasks` is private, access via `get_tasks()`; completion flag is `completed` not `is_done`).
**How to apply:** Any future filtering, querying, or display code on these classes must use exactly these attribute/method names.
