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
    - **Time**: The owner's daily time budget (in minutes) is the primary constraint. The scheduler must fit tasks within this limit, skipping any that would exceed it.
    - **Priority**: Each task has a priority level (HIGH, MEDIUM, LOW). The scheduler must order tasks by priority, scheduling all HIGH before any MEDIUM, and all MEDIUM before any LOW.
    - **Duration**: Among tasks of the same priority, shorter tasks are scheduled before longer ones to maximize the number of tasks that fit within the time budget.
    - **Recurrence**: Tasks can be one-time, daily, or weekly. The scheduler must only consider tasks that are due today (or overdue), and must automatically spawn the next occurrence of recurring tasks after completion.
    - **Conflict detection**: The scheduler must detect and warn about any overlapping timed tasks across all pets, as these represent scheduling conflicts that the owner should be aware of.
- How did you decide which constraints mattered most?
    - The time budget is the hard limit that defines what can and cannot be scheduled, so it is the most critical constraint. Priority is the next most important factor, as it reflects the real-world urgency of tasks (e.g., medication is more urgent than a walk). Duration is a tie-breaker that helps fit more tasks within the budget. Recurrence is important for realistic task management but doesn't affect the scheduling of today's plan directly. Conflict detection is a user-friendly feature that helps surface issues but doesn't prevent scheduling on its own.

**b. Tradeoffs**

The scheduler uses a **greedy first-fit algorithm**: it sorts all tasks by priority, then walks the list once and schedules each task that fits in the remaining time budget — never reconsidering earlier decisions.

This means a single large HIGH-priority task (e.g., a 40-minute vet checkup) can consume so much of the budget that several smaller, also-important tasks get skipped entirely. A smarter approach — like checking whether swapping a scheduled task for a skipped one would yield a better overall outcome — would produce tighter, more balanced plans.

The tradeoff is reasonable here because pet care tasks are short (5–40 minutes), budgets are small (≤120 minutes), and the priority ordering reflects real urgency. For typical daily use, greedy scheduling produces an acceptable plan without the added complexity of backtracking or optimization.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
    - I used AI for design brainstorming to help identify key classes and their relationships, which led to a more robust initial design. 
    - I also used it for debugging specific issues in the scheduling logic, such as correctly handling the shared time budget across multiple pets. 
    - I used Gemini to help navigate Claude's Agent Mode. 
    - Finally, I used AI for refactoring code to improve readability and maintainability, especially in the `generate_plan()` method where the scheduling logic is implemented.
- What kinds of prompts or questions were most helpful?
    - Prompts that asked for specific design patterns (e.g., "How would you design a pet care scheduler with multiple pets and shared time budgets?") were helpful for structuring the initial classes. 
    - For debugging, prompts that included code snippets and asked for explanations of why certain logic wasn't working (e.g., "Why is my scheduler allowing multiple pets to exceed the time budget?") were effective. 
    - For refactoring, prompts that asked for more readable or efficient code while maintaining the same functionality were useful.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
    - One moment was when the AI suggested that `Scheduler` should take both `Owner` and `Pet` as parameters. I realized that this would lead to a design where each pet's tasks are scheduled independently, which would break the shared time budget constraint. 
    - I chose to reject this suggestion and instead refactor the design so that `Scheduler` only takes `Owner`, allowing it to access all pets and their tasks in a single pass.
- How did you evaluate or verify what the AI suggested?
    - I evaluated the AI's suggestion by considering the implications of having `Scheduler` take both `Owner` and `Pet`. I realized that this would lead to a situation where each pet's tasks are scheduled without regard to the shared time budget, effectively allowing the total scheduled time to exceed the owner's limit. This was a critical flaw in the design, so I rejected the suggestion and refactored accordingly.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
    - I tested the sorting behavior to ensure tasks are returned in chronological order and that untimed tasks always sort last. 
    - I also tested the recurrence logic to verify that completed daily tasks spawn a new instance due the next day, weekly tasks advance by 7 days, and non-recurring tasks never spawn. 
    - I tested conflict detection to confirm that overlapping timed tasks produce a warning string, while back-to-back tasks do not. 
    - I tested plan generation to ensure that high-priority tasks are scheduled first, same-priority tasks pick shortest-first, and that tasks due tomorrow are excluded while overdue tasks are included. 
    - Finally, I tested filtering to verify that `get_filtered_tasks` correctly filters by completion status, pet name (case-insensitive), and nonexistent pets return an empty list.
- Why were these tests important?
    - These tests were important to verify that the core functionalities of the scheduler work as intended. 
    - Sorting ensures that tasks are presented in a logical order. 
    - Recurrence is crucial for realistic task management. 
    - Conflict detection helps surface scheduling issues to the user. 
    - Plan generation tests confirm that the scheduling logic correctly prioritizes and fits tasks within the time budget. 
    - Filtering tests ensure that users can effectively manage and view their tasks based on different criteria.

**b. Confidence**

- How confident are you that your scheduler works correctly?
    - I am reasonably confident that the scheduler works correctly for typical use cases, as the tests cover a wide range of behaviors and edge cases. 
    - However, there may still be edge cases that I haven't thought of or tested yet, such as handling tasks with zero duration, tasks that exactly match the remaining time budget, or how the system behaves when all tasks are untimed.
- What edge cases would you test next if you had more time?
    - I would test how the scheduler handles tasks with zero duration, as these could potentially be scheduled without affecting the time budget. 
    - I would also test tasks that exactly match the remaining time budget to ensure they are scheduled correctly. 
    - Additionally, I would test the behavior when all tasks are untimed to confirm that they are sorted last and do not interfere with the scheduling of timed tasks.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
    - I am most satisfied with the overall design of the system, particularly how the classes interact and how the scheduling logic is structured. 
    - The use of a shared time budget across multiple pets was a key design decision that I believe adds realism and complexity to the scheduler. 
    - I am also pleased with the implementation of conflict detection, as it provides valuable feedback to users about potential scheduling issues.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
    - If I had another iteration, I would improve the scheduling algorithm to consider swapping out lower-priority tasks for higher-priority ones that come later in the list, rather than using a strict greedy approach. 
    - This would allow for more optimal scheduling and better utilization of the time budget. 
    - I would also consider adding user preferences (e.g., "I prefer walks in the morning") to further customize the scheduling logic.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
    - One important thing I learned is that while AI can provide valuable suggestions and help with brainstorming, it's crucial to critically evaluate those suggestions in the context of the overall system design. 
    - Not all AI-generated ideas will fit well with the specific constraints and requirements of the project, so human judgement is essential in deciding which suggestions to accept, modify, or reject. 
    - Additionally, having a clear understanding of the problem domain and the relationships between different components of the system helps in making informed decisions about design and implementation.
