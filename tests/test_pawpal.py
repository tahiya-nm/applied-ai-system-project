import sys
import os
from datetime import date, timedelta
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pawpal_system import Task, Pet, Owner, Plan, Scheduler, Priority


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TODAY = date(2026, 3, 31)
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)


def make_task(title="Task", duration=10, priority=Priority.MEDIUM,
              scheduled_time=None, recurrence=None, due_date=None, completed=False):
    t = Task(
        title=title,
        duration_minutes=duration,
        priority=priority,
        scheduled_time=scheduled_time,
        recurrence=recurrence,
        due_date=due_date or TODAY,
    )
    t.completed = completed
    return t


def make_owner(available_minutes=120):
    return Owner(name="Jordan", available_minutes=available_minutes)


# ---------------------------------------------------------------------------
# Existing smoke tests
# ---------------------------------------------------------------------------

def test_mark_complete_changes_status():
    task = Task(title="Morning Walk", duration_minutes=20, priority=Priority.HIGH)
    assert task.completed is False
    task.mark_complete()
    assert task.completed is True


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Buddy", species="dog")
    assert len(pet.get_tasks()) == 0
    pet.add_task(Task(title="Fetch Training", duration_minutes=15, priority=Priority.MEDIUM))
    assert len(pet.get_tasks()) == 1


# ---------------------------------------------------------------------------
# Sorting Correctness (H4, E8)
# ---------------------------------------------------------------------------

def test_sort_by_time_chronological_order():
    """Tasks come back earliest → latest."""
    scheduler = Scheduler(make_owner())
    tasks = [
        make_task("C", scheduled_time="14:00"),
        make_task("A", scheduled_time="08:00"),
        make_task("B", scheduled_time="09:30"),
    ]
    result = scheduler.sort_by_time(tasks)
    assert [t.title for t in result] == ["A", "B", "C"]


def test_sort_by_time_none_goes_last():
    """Tasks with no scheduled_time sort after all timed tasks."""
    scheduler = Scheduler(make_owner())
    tasks = [
        make_task("Untimed", scheduled_time=None),
        make_task("Early", scheduled_time="07:00"),
        make_task("Late", scheduled_time="20:00"),
    ]
    result = scheduler.sort_by_time(tasks)
    assert result[-1].title == "Untimed"
    assert result[0].title == "Early"


def test_sort_by_time_all_none_no_crash():
    """All None scheduled_time should not raise."""
    scheduler = Scheduler(make_owner())
    tasks = [make_task(f"T{i}", scheduled_time=None) for i in range(3)]
    result = scheduler.sort_by_time(tasks)
    assert len(result) == 3


# ---------------------------------------------------------------------------
# Recurrence Logic (H2, H3, E6, E11)
# ---------------------------------------------------------------------------

@patch("pawpal_system.date")
def test_daily_recurrence_spawns_next_day(mock_date):
    mock_date.today.return_value = TODAY
    pet = Pet(name="Buddy", species="dog")
    task = make_task("Meds", recurrence="daily", due_date=TODAY, completed=True)
    pet.add_task(task)
    owner = make_owner()
    owner.add_pet(pet)

    spawned = Scheduler(owner).apply_recurrence()

    assert len(spawned) == 1
    _, new_task = spawned[0]
    assert new_task.completed is False
    assert new_task.due_date == TODAY + timedelta(days=1)
    assert len(pet.get_tasks()) == 2  # original + new


@patch("pawpal_system.date")
def test_weekly_recurrence_spawns_seven_days_later(mock_date):
    mock_date.today.return_value = TODAY
    pet = Pet(name="Luna", species="cat")
    task = make_task("Bath", recurrence="weekly", due_date=TODAY, completed=True)
    pet.add_task(task)
    owner = make_owner()
    owner.add_pet(pet)

    spawned = Scheduler(owner).apply_recurrence()

    _, new_task = spawned[0]
    assert new_task.due_date == TODAY + timedelta(weeks=1)


def test_non_recurring_task_does_not_spawn():
    """Completed task with recurrence=None must not create a new task."""
    pet = Pet(name="Buddy", species="dog")
    task = make_task("Vet Visit", recurrence=None, completed=True)
    pet.add_task(task)
    owner = make_owner()
    owner.add_pet(pet)

    spawned = Scheduler(owner).apply_recurrence()

    assert spawned == []
    assert len(pet.get_tasks()) == 1


def test_apply_recurrence_idempotent_on_second_call():
    """Calling apply_recurrence twice must not spawn a second next-occurrence."""
    pet = Pet(name="Buddy", species="dog")
    task = make_task("Meds", recurrence="daily", due_date=TODAY, completed=True)
    pet.add_task(task)
    owner = make_owner()
    owner.add_pet(pet)
    scheduler = Scheduler(owner)

    scheduler.apply_recurrence()
    scheduler.apply_recurrence()  # second call

    assert len(pet.get_tasks()) == 2  # still just original + one new


# ---------------------------------------------------------------------------
# Conflict Detection (H5, E3)
# ---------------------------------------------------------------------------

def test_detect_conflicts_flags_overlapping_tasks():
    """Two tasks at the same start time must produce a warning."""
    pet = Pet(name="Buddy", species="dog")
    pet.add_task(make_task("Walk", duration=30, scheduled_time="09:00"))
    pet.add_task(make_task("Feed", duration=15, scheduled_time="09:00"))
    owner = make_owner()
    owner.add_pet(pet)

    warnings = Scheduler(owner).detect_conflicts()

    assert len(warnings) == 1
    assert "Walk" in warnings[0]
    assert "Feed" in warnings[0]


def test_detect_conflicts_back_to_back_is_not_a_conflict():
    """Task A ends at 09:30; task B starts at 09:30 — no overlap."""
    pet = Pet(name="Buddy", species="dog")
    pet.add_task(make_task("Walk", duration=30, scheduled_time="09:00"))   # ends 09:30
    pet.add_task(make_task("Feed", duration=15, scheduled_time="09:30"))   # starts 09:30
    owner = make_owner()
    owner.add_pet(pet)

    warnings = Scheduler(owner).detect_conflicts()

    assert warnings == []


def test_detect_conflicts_cross_pet_overlap():
    """Overlapping tasks across two different pets also produce a warning."""
    pet_a = Pet(name="Buddy", species="dog")
    pet_b = Pet(name="Luna", species="cat")
    pet_a.add_task(make_task("Walk", duration=60, scheduled_time="08:00"))
    pet_b.add_task(make_task("Playtime", duration=30, scheduled_time="08:30"))
    owner = make_owner()
    owner.add_pet(pet_a)
    owner.add_pet(pet_b)

    warnings = Scheduler(owner).detect_conflicts()

    assert len(warnings) == 1
    assert "Buddy" in warnings[0] and "Luna" in warnings[0]


def test_detect_conflicts_no_timed_tasks_returns_empty():
    pet = Pet(name="Buddy", species="dog")
    pet.add_task(make_task("Untimed", scheduled_time=None))
    owner = make_owner()
    owner.add_pet(pet)

    assert Scheduler(owner).detect_conflicts() == []


# ---------------------------------------------------------------------------
# generate_plan (H1, E1, E2, E4, E5, E7, E10)
# ---------------------------------------------------------------------------

@patch("pawpal_system.date")
def test_generate_plan_schedules_fitting_tasks(mock_date):
    mock_date.today.return_value = TODAY
    pet = Pet(name="Buddy", species="dog")
    pet.add_task(make_task("Walk", duration=30, priority=Priority.HIGH, due_date=TODAY))
    pet.add_task(make_task("Feed", duration=20, priority=Priority.MEDIUM, due_date=TODAY))
    owner = make_owner(available_minutes=60)
    owner.add_pet(pet)

    plan = Scheduler(owner).generate_plan()

    assert len(plan.scheduled) == 2
    assert plan.total_time_used == 50


@patch("pawpal_system.date")
def test_generate_plan_pet_with_no_tasks(mock_date):
    mock_date.today.return_value = TODAY
    pet = Pet(name="Ghost", species="other")
    owner = make_owner()
    owner.add_pet(pet)

    plan = Scheduler(owner).generate_plan()

    assert plan.scheduled == []
    assert plan.skipped == []


@patch("pawpal_system.date")
def test_generate_plan_zero_available_minutes(mock_date):
    mock_date.today.return_value = TODAY
    pet = Pet(name="Buddy", species="dog")
    pet.add_task(make_task("Walk", duration=10, due_date=TODAY))
    owner = make_owner(available_minutes=0)
    owner.add_pet(pet)

    plan = Scheduler(owner).generate_plan()

    assert plan.scheduled == []
    assert len(plan.skipped) == 1
    assert "only 0 left" in plan.skipped[0][2]


@patch("pawpal_system.date")
def test_generate_plan_excludes_future_tasks(mock_date):
    mock_date.today.return_value = TODAY
    pet = Pet(name="Buddy", species="dog")
    pet.add_task(make_task("Future Walk", duration=10, due_date=TOMORROW))
    owner = make_owner()
    owner.add_pet(pet)

    plan = Scheduler(owner).generate_plan()

    assert plan.scheduled == []
    assert plan.skipped == []


@patch("pawpal_system.date")
def test_generate_plan_includes_overdue_tasks(mock_date):
    mock_date.today.return_value = TODAY
    pet = Pet(name="Buddy", species="dog")
    pet.add_task(make_task("Overdue Walk", duration=10, due_date=YESTERDAY))
    owner = make_owner()
    owner.add_pet(pet)

    plan = Scheduler(owner).generate_plan()

    assert len(plan.scheduled) == 1


@patch("pawpal_system.date")
def test_generate_plan_same_priority_shortest_first(mock_date):
    mock_date.today.return_value = TODAY
    pet = Pet(name="Buddy", species="dog")
    pet.add_task(make_task("Long", duration=30, priority=Priority.HIGH, due_date=TODAY))
    pet.add_task(make_task("Short", duration=10, priority=Priority.HIGH, due_date=TODAY))
    owner = make_owner(available_minutes=35)  # only fits Short + partial Long
    owner.add_pet(pet)

    plan = Scheduler(owner).generate_plan()

    assert plan.scheduled[0][1].title == "Short"


@patch("pawpal_system.date")
def test_generate_plan_task_exactly_fills_budget(mock_date):
    mock_date.today.return_value = TODAY
    pet = Pet(name="Buddy", species="dog")
    pet.add_task(make_task("Exact", duration=60, due_date=TODAY))
    owner = make_owner(available_minutes=60)
    owner.add_pet(pet)

    plan = Scheduler(owner).generate_plan()

    assert len(plan.scheduled) == 1
    assert plan.total_time_used == 60


# ---------------------------------------------------------------------------
# get_filtered_tasks (H6, H7, E9)
# ---------------------------------------------------------------------------

def test_get_filtered_tasks_by_completion_status():
    pet = Pet(name="Buddy", species="dog")
    pet.add_task(make_task("Done Task", completed=True))
    pet.add_task(make_task("Pending Task", completed=False))
    owner = make_owner()
    owner.add_pet(pet)

    incomplete = owner.get_filtered_tasks(completed=False)
    assert len(incomplete) == 1
    assert incomplete[0][1].title == "Pending Task"


def test_get_filtered_tasks_by_pet_name_case_insensitive():
    buddy = Pet(name="Buddy", species="dog")
    luna = Pet(name="Luna", species="cat")
    buddy.add_task(make_task("Walk"))
    luna.add_task(make_task("Playtime"))
    owner = make_owner()
    owner.add_pet(buddy)
    owner.add_pet(luna)

    results = owner.get_filtered_tasks(pet_name="buddy")  # lowercase

    assert len(results) == 1
    assert results[0][0].name == "Buddy"


def test_get_filtered_tasks_nonexistent_pet_returns_empty():
    pet = Pet(name="Buddy", species="dog")
    pet.add_task(make_task("Walk"))
    owner = make_owner()
    owner.add_pet(pet)

    results = owner.get_filtered_tasks(pet_name="Ghost")

    assert results == []


# ---------------------------------------------------------------------------
# Plan.summary (H8)
# ---------------------------------------------------------------------------

def test_plan_summary_contains_expected_fields():
    owner = make_owner(available_minutes=60)
    pet = Pet(name="Buddy", species="dog")
    task = make_task("Walk", duration=30)
    plan = Plan(
        owner=owner,
        scheduled=[(pet, task, "fits")],
        skipped=[],
        total_time_used=30,
    )

    summary = plan.summary()

    assert "Jordan" in summary
    assert "30/60" in summary
    assert "Walk" in summary
    assert "Scheduled Tasks" in summary
    assert "Skipped Tasks" in summary
