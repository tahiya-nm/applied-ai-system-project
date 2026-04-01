from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum


class Priority(Enum):
    HIGH = 3
    MEDIUM = 2
    LOW = 1


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: Priority  # Priority.HIGH, Priority.MEDIUM, or Priority.LOW
    completed: bool = False
    scheduled_time: str | None = None  # "HH:MM" format, e.g. "08:30"
    recurrence: str | None = None      # "daily", "weekly", or None
    due_date: date = field(default_factory=date.today)

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def next_occurrence(self) -> "Task":
        """Return a new Task for the next recurrence cycle.

        Advances due_date by 1 day (daily) or 7 days (weekly). If recurrence
        is None, due_date is unchanged. The new task is always incomplete.

        Returns:
            A copy of this task with completed=False and an updated due_date.
        """
        if self.recurrence == "daily":
            next_due = self.due_date + timedelta(days=1)
        elif self.recurrence == "weekly":
            next_due = self.due_date + timedelta(weeks=1)
        else:
            next_due = self.due_date
        return Task(
            title=self.title,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            completed=False,
            scheduled_time=self.scheduled_time,
            recurrence=self.recurrence,
            due_date=next_due,
        )

    def priority_value(self) -> int:
        """Return the numeric value of this task's priority for sorting."""
        return self.priority.value

    def __repr__(self) -> str:
        """Return a readable string representation of the task."""
        return f"Task('{self.title}', {self.duration_minutes} mins, {self.priority})"


@dataclass
class Pet:
    name: str
    species: str  # "dog", "cat", or "other"
    _tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a task to this pet's task list."""
        self._tasks.append(task)

    def remove_task(self, title: str) -> None:
        """Remove the first task matching the given title from this pet's task list."""
        for i, task in enumerate(self._tasks):
            if task.title == title:
                del self._tasks[i]
                return

    def get_tasks(self) -> list[Task]:
        """Return all tasks associated with this pet."""
        return self._tasks


@dataclass
class Owner:
    name: str
    available_minutes: int  # total time available per day across all pets
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Add a pet to this owner's pet list."""
        self.pets.append(pet)

    def get_filtered_tasks(
        self,
        completed: bool = None,
        pet_name: str = None
    ) -> list:
        """
        Filter tasks across all owned pets.

        Args:
            completed: If provided, filter tasks by completion status.
            pet_name: If provided, filter tasks belonging to the specified pet
                      (case-insensitive comparison).

        Returns:
            A list of (Pet, Task) tuples matching the specified filters.
        """
        results = []
        for pet in self.pets:
            if pet_name is not None and pet.name.lower() != pet_name.lower():
                continue
            for task in pet.get_tasks():
                if completed is not None and task.completed != completed:
                    continue
                results.append((pet, task))
        return results


@dataclass
class Plan:
    owner: Owner
    scheduled: list[tuple[Pet, Task, str]] = field(default_factory=list)  # (pet, task, reason included)
    skipped: list[tuple[Pet, Task, str]] = field(default_factory=list)    # (pet, task, reason skipped)
    total_time_used: int = 0

    def summary(self) -> str:
        """Return a formatted summary of scheduled and skipped tasks with time budget usage."""
        lines = []
        lines.append(f"Plan for {self.owner.name} "
                     f"({self.total_time_used}/{self.owner.available_minutes} mins used)")
        lines.append("")

        lines.append("Scheduled Tasks:")
        if self.scheduled:
            for pet, task, _ in self.scheduled:
                lines.append(f"- {pet.name}: {task.title} ({task.duration_minutes} mins)")
        else:
            lines.append("- None")

        lines.append("")

        lines.append("Skipped Tasks:")
        if self.skipped:
            for pet, task, reason in self.skipped:
                lines.append(
                    f"- {task.title} ({task.duration_minutes} mins) — {reason}"
                )
        else:
            lines.append("- None")

        return "\n".join(lines)


class Scheduler:
    def __init__(self, owner: Owner):
        """Initialize the scheduler with the owner whose pets will be scheduled."""
        self.owner = owner

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Sort tasks by their scheduled_time in ascending order.

        Tasks without a scheduled_time (None) are placed after all timed tasks.
        The original list is not mutated.

        Args:
            tasks: The tasks to sort.

        Returns:
            A new list of tasks ordered earliest to latest, untimed tasks last.
        """
        def to_minutes(t: Task) -> int:
            if t.scheduled_time is None:
                return float("inf")
            h, m = t.scheduled_time.split(":")
            return int(h) * 60 + int(m)

        return sorted(tasks, key=lambda t: to_minutes(t))

    def apply_recurrence(self) -> list[Task]:
        """
        Scan all pets for completed recurring tasks. For each one found,
        append a fresh next occurrence (completed=False) — the original stays.
        Returns the list of newly created Task instances.
        """
        refreshed = []
        for pet in self.owner.pets:
            for task in list(pet.get_tasks()):  # copy so append mid-loop is safe
                if task.completed and task.recurrence in ("daily", "weekly"):
                    next_task = task.next_occurrence()
                    pet.add_task(next_task)
                    refreshed.append((pet, next_task))
        return refreshed

    def detect_conflicts(self) -> list[str]:
        """
        Lightweight conflict check: compare every pair of timed tasks and return
        a warning string for each overlap. Never raises — always returns a list
        (empty means no conflicts).
        """
        timed = []
        for pet in self.owner.pets:
            for task in pet.get_tasks():
                if task.scheduled_time is not None:
                    h, m = task.scheduled_time.split(":")
                    start = int(h) * 60 + int(m)
                    timed.append((pet, task, start, start + task.duration_minutes))

        warnings = []
        for i in range(len(timed)):
            for j in range(i + 1, len(timed)):
                pet_a, task_a, start_a, end_a = timed[i]
                pet_b, task_b, start_b, end_b = timed[j]
                if start_a < end_b and start_b < end_a:
                    who = "same pet" if pet_a.name == pet_b.name else f"{pet_a.name} & {pet_b.name}"
                    warnings.append(
                        f"WARNING ({who}): '{task_a.title}' ({task_a.scheduled_time}, "
                        f"{task_a.duration_minutes} mins) overlaps "
                        f"'{task_b.title}' ({task_b.scheduled_time}, {task_b.duration_minutes} mins)"
                    )
        return warnings

    def generate_plan(self) -> Plan:
        """Build a daily schedule using a greedy priority-first algorithm.

        Only tasks due today or earlier are considered. Tasks are sorted by
        priority (HIGH → LOW) with duration as a tie-breaker (shortest first).
        Each task is scheduled if it fits within the owner's remaining time
        budget; otherwise it is skipped with a reason.

        Returns:
            A Plan containing scheduled tasks, skipped tasks, and total time used.
        """
        # 1. Flatten: only include tasks due today or earlier
        today = date.today()
        all_tasks: list[tuple[Task, Pet]] = []
        for pet in self.owner.pets:
            for task in pet.get_tasks():
                if task.due_date <= today:
                    all_tasks.append((task, pet))

        # 2. Sort: highest priority first; shortest duration as tie-breaker
        all_tasks.sort(key=lambda tp: (-tp[0].priority_value(), tp[0].duration_minutes))

        # 3. Iterate and schedule
        scheduled: list[tuple[Pet, Task, str]] = []
        skipped: list[tuple[Pet, Task, str]] = []
        remaining_minutes = self.owner.available_minutes

        for task, pet in all_tasks:
            if task.duration_minutes <= remaining_minutes:
                scheduled.append((pet, task, "High priority and fits in remaining time."))
                remaining_minutes -= task.duration_minutes
            else:
                skipped.append((
                    pet, task,
                    f"Insufficient remaining time (needs {task.duration_minutes} mins, "
                    f"only {remaining_minutes} left)."
                ))

        # 4. Return a Plan
        return Plan(
            owner=self.owner,
            scheduled=scheduled,
            skipped=skipped,
            total_time_used=self.owner.available_minutes - remaining_minutes,
        )


if __name__ == '__main__':
    today = date.today()
    tomorrow = today + timedelta(days=1)
    next_week = today + timedelta(weeks=1)

    print("=" * 50)
    print("  RECURRENCE SPAWN VERIFICATION")
    print("=" * 50)

    # --- Step 1: Create a pet and a daily recurring task ---
    buddy = Pet(name="Buddy", species="dog")
    meds = Task(
        title="Morning Meds",
        duration_minutes=5,
        priority=Priority.HIGH,
        recurrence="daily",
        due_date=today,
    )
    buddy.add_task(meds)

    owner = Owner(name="Jordan", available_minutes=60)
    owner.add_pet(buddy)

    print(f"\n  Today    : {today}")
    print(f"  Tomorrow : {tomorrow}")
    print(f"  Next week: {next_week}")

    print("\n  BEFORE completion — Buddy's task list:")
    for t in buddy.get_tasks():
        status = "done" if t.completed else "pending"
        print(f"    [{status}] '{t.title}'  due={t.due_date}  recurrence={t.recurrence}")

    # --- Step 2: Complete the task ---
    meds.mark_complete()
    Scheduler(owner).apply_recurrence()

    # --- Step 3: Inspect the task list — expect original (done) + new (pending, tomorrow) ---
    print("\n  AFTER completion + apply_recurrence() — Buddy's task list:")
    for t in buddy.get_tasks():
        status = "done" if t.completed else "pending"
        print(f"    [{status}] '{t.title}'  due={t.due_date}  recurrence={t.recurrence}")

    # --- Frequency math table ---
    print("\n  FREQUENCY MATH")
    print("  " + "-" * 40)
    weekly_task = Task(title="Bath Time", duration_minutes=20, priority=Priority.LOW,
                       recurrence="weekly", due_date=today)
    one_time    = Task(title="Vet Visit", duration_minutes=30, priority=Priority.HIGH,
                       recurrence=None, due_date=today)

    for t in [meds, weekly_task, one_time]:
        if t.recurrence == "daily":
            result = f"{t.due_date} + 1 day  → {t.due_date + timedelta(days=1)}"
        elif t.recurrence == "weekly":
            result = f"{t.due_date} + 1 week → {t.due_date + timedelta(weeks=1)}"
        else:
            result = "one-time, no new instance"
        print(f"  {str(t.recurrence):8}  {result}")

    print("\n" + "=" * 50)
