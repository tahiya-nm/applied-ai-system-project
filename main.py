from pawpal_system import Owner, Pet, Task, Priority, Scheduler

# Create owner with 90 available minutes
owner = Owner(name="Jordan", available_minutes=90)

# Create pets
buddy = Pet(name="Buddy", species="dog")
whiskers = Pet(name="Whiskers", species="cat")
coco = Pet(name="Coco", species="other")

# Add tasks OUT OF ORDER (intentionally scrambled scheduled_time values)
buddy.add_task(Task(title="Morning Walk",       duration_minutes=30, priority=Priority.HIGH,   scheduled_time="09:30"))
buddy.add_task(Task(title="Obedience Training", duration_minutes=20, priority=Priority.MEDIUM, scheduled_time="14:00"))
buddy.add_task(Task(title="Bath Time",          duration_minutes=25, priority=Priority.LOW,    scheduled_time="07:15"))

whiskers.add_task(Task(title="Vet Checkup", duration_minutes=40, priority=Priority.HIGH,   scheduled_time="11:00"))
whiskers.add_task(Task(title="Grooming",    duration_minutes=15, priority=Priority.MEDIUM, scheduled_time="08:00"))
whiskers.add_task(Task(title="Playtime",    duration_minutes=10, priority=Priority.LOW,    scheduled_time="06:45"))

coco.add_task(Task(title="Cage Cleaning",  duration_minutes=20, priority=Priority.HIGH,   scheduled_time="10:30"))
coco.add_task(Task(title="Feeding & Water", duration_minutes=5, priority=Priority.MEDIUM, scheduled_time="07:00"))

# Intentional conflicts for detection demo
# Buddy: "Obedience Training" starts at 09:45 — overlaps "Morning Walk" (09:30–10:00)
buddy.add_task(Task(title="Obedience Training 2", duration_minutes=20, priority=Priority.MEDIUM, scheduled_time="09:45"))
# Whiskers & Coco: "Feeding" starts at 10:40 — overlaps Coco's "Cage Cleaning" (10:30–10:50)
whiskers.add_task(Task(title="Feeding",           duration_minutes=10, priority=Priority.MEDIUM, scheduled_time="10:40"))

# Register pets with owner
owner.add_pet(buddy)
owner.add_pet(whiskers)
owner.add_pet(coco)

# Generate plan
plan = Scheduler(owner).generate_plan()

# Print Today's Schedule
print("=" * 45)
print("         PAWPAL+ — TODAY'S SCHEDULE")
print("=" * 45)
print(f"  Owner : {plan.owner.name}")
print(f"  Budget: {plan.owner.available_minutes} mins available")
print(f"  Used  : {plan.total_time_used} mins scheduled")
print("=" * 45)

print("\n  SCHEDULED TASKS")
print("  " + "-" * 41)
for pet, task, _ in plan.scheduled:
    priority_label = task.priority.name.capitalize()
    print(f"  [{priority_label:6}] {pet.name:10} — {task.title} ({task.duration_minutes} mins)")

if plan.skipped:
    print("\n  SKIPPED TASKS")
    print("  " + "-" * 41)
    for pet, task, reason in plan.skipped:
        print(f"  {pet.name:10} — {task.title} ({task.duration_minutes} mins)")
        print(f"             Reason: {reason}")

print("\n" + "=" * 45)

# --- sort_by_time demo ---
scheduler = Scheduler(owner)
all_tasks = [task for pet in owner.pets for task in pet.get_tasks()]
sorted_tasks = scheduler.sort_by_time(all_tasks)

print("\n  ALL TASKS — SORTED BY TIME")
print("  " + "-" * 41)
for task in sorted_tasks:
    time_label = task.scheduled_time if task.scheduled_time else "?????  "
    print(f"  [{time_label}] {task.title} ({task.duration_minutes} mins, {task.priority.name})")

# --- get_filtered_tasks demo ---
# Mark Buddy's Bath Time as completed so the completed filter has something to find
for pet, task in owner.get_filtered_tasks(pet_name="Buddy"):
    if task.title == "Bath Time":
        task.mark_complete()

print("\n  FILTER — Completed Tasks")
print("  " + "-" * 41)
for pet, task in owner.get_filtered_tasks(completed=True):
    print(f"  {pet.name:10} — {task.title}")

print("\n  FILTER — Whiskers' Tasks Only")
print("  " + "-" * 41)
for pet, task in owner.get_filtered_tasks(pet_name="Whiskers"):
    status = "done" if task.completed else "pending"
    print(f"  {pet.name:10} — {task.title} [{status}]")

print("\n" + "=" * 45)

# --- conflict detection ---
warnings = scheduler.detect_conflicts()
print("\n  CONFLICT WARNINGS")
print("  " + "-" * 41)
if warnings:
    for w in warnings:
        print(f"  {w}")
else:
    print("  No conflicts detected.")
print("\n" + "=" * 45)
