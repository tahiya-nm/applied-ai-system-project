# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

PawPal+ is designed around three core user actions that drive the entire system:

1. **Add a pet** — The user enters basic owner and pet information (owner name, pet name, species, and how many minutes per day are available for care). An owner can have multiple pets; the daily time budget is shared across all of them.

2. **Add and manage care tasks** — The user creates individual tasks such as walks, feeding, medications, grooming, or enrichment activities. Each task has a title, a duration in minutes, and a priority level (`Priority.HIGH`, `Priority.MEDIUM`, or `Priority.LOW`). Tasks can be added or removed at any time.

3. **Generate and view today's plan** — The user triggers schedule generation. The system collects tasks across all of the owner's pets, selects and orders them based on priority and shared available time, then displays the resulting daily plan alongside a plain-language explanation of why each task was included or excluded (e.g., "Medication was scheduled first because it is high priority" or "Extended walk was skipped — not enough time remaining").

These three actions map to five classes: `Owner` (holds owner info, the shared daily time budget, and a list of pets), `Pet` (holds pet info and its task list), `Task` (title, duration, priority), `Scheduler` (takes an owner and produces a plan across all their pets), and `Plan` (the structured output of the scheduler).

- What classes did you include, and what responsibilities did you assign to each?
    - `Owner`: Stores owner name, shared daily time budget (`available_minutes`), and a list of `Pet` objects. Has an `add_pet()` method. The budget is intentionally shared across all pets so that scheduling two pets doesn't accidentally double-count available time.
    - `Pet`: Stores pet name and species, and owns a private list of care tasks (`_tasks`). Exposes `add_task()`, `remove_task()`, and `get_tasks()` to control access to the task list. Making `_tasks` private enforces that all mutation goes through these methods.
    - `Task`: Represents a single care activity with a title, duration in minutes, and a `Priority` enum value. Uses a `Priority` enum (instead of a raw string) to prevent invalid values like `"urgent"` or `"HIGH"` from silently breaking the sort. Has a `priority_value()` method that returns the enum's numeric value for sorting.
    - `Plan`: The output of the scheduler. References the `Owner` it was built for (so `summary()` can display context like the owner's name and budget). Holds two lists — scheduled and skipped tasks — each as `(Pet, Task, reason)` tuples so it's clear which pet each task belongs to, plus the total time used.
    - `Scheduler`: Contains the scheduling logic. Takes only an `Owner` (not a separate `Pet`) and iterates over `owner.pets` to collect all tasks into a single shared pool. Sorts by priority, fits as many as possible within `owner.available_minutes`, and returns a `Plan` with reasoning for each decision. Taking the owner (rather than a single pet) is what makes the shared budget work correctly.

**b. Design changes**

Yes, the design changed in four ways after reviewing the skeleton for missing relationships and logic gaps.

1. **`Owner` gained a `pets` list and `add_pet()`.** The original design had no link between `Owner` and `Pet` — they were only joined inside `Scheduler`. Adding `pets: list[Pet]` makes the ownership relationship explicit in the model itself.

2. **`Scheduler` takes only `Owner`, not `Owner` + `Pet`.** The original single-pet design would apply the full time budget to each pet independently, effectively doubling it for owners with multiple pets. Taking only `Owner` and iterating `owner.pets` puts all tasks into one shared pool under a single budget.

3. **`Plan` now holds an `Owner` reference and `(Pet, Task, reason)` tuples.** The original `(Task, reason)` tuples had no pet context, and `Plan` had no way to know whose plan it was. Both are needed for `summary()` to produce meaningful output when multiple pets are involved.

4. **`priority` changed from `str` to a `Priority` enum.** Raw strings allow invalid values like `"urgent"` to silently reach `priority_value()` and break sorting. An enum makes invalid priorities a hard error at construction time.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

The scheduler uses a **greedy first-fit algorithm**: it sorts all tasks by priority, then walks the list once and schedules each task that fits in the remaining time budget — never reconsidering earlier decisions.

This means a single large HIGH-priority task (e.g., a 40-minute vet checkup) can consume so much of the budget that several smaller, also-important tasks get skipped entirely. A smarter approach — like checking whether swapping a scheduled task for a skipped one would yield a better overall outcome — would produce tighter, more balanced plans.

The tradeoff is reasonable here because pet care tasks are short (5–40 minutes), budgets are small (≤120 minutes), and the priority ordering reflects real urgency. For typical daily use, greedy scheduling produces an acceptable plan without the added complexity of backtracking or optimization.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
