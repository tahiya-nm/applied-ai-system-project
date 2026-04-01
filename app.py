import streamlit as st
from pawpal_system import Owner, Pet, Task, Priority, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# ── Formatting helpers ────────────────────────────────────────────────────────

SPECIES_EMOJI = {"dog": "🐕", "cat": "🐈", "other": "🐾"}

PRIORITY_BADGE = {
    "HIGH":   '<span style="background:#ffb3b3;color:#7a1a1a;padding:2px 8px;border-radius:4px;font-size:0.8em;font-weight:600;">🔴 HIGH</span>',
    "MEDIUM": '<span style="background:#ffdda0;color:#7a4800;padding:2px 8px;border-radius:4px;font-size:0.8em;font-weight:600;">🟡 MEDIUM</span>',
    "LOW":    '<span style="background:#b3f0c6;color:#155724;padding:2px 8px;border-radius:4px;font-size:0.8em;font-weight:600;">🟢 LOW</span>',
}

STATUS_BADGE = {
    True:  '<span style="background:#b3f0c6;color:#155724;padding:2px 8px;border-radius:4px;font-size:0.8em;font-weight:600;">✅ Done</span>',
    False: '<span style="background:#c8d8ee;color:#1a3a5c;padding:2px 8px;border-radius:4px;font-size:0.8em;font-weight:600;">⏳ Pending</span>',
}

RECURRENCE_ICON = {
    "daily":  "🔁 Daily",
    "weekly": "📅 Weekly",
    None:     "⬜ One-time",
}


def species_label(species: str) -> str:
    icon = SPECIES_EMOJI.get(species, "🐾")
    return f"{icon} {species.capitalize()}"


def task_time_label(t: Task) -> str:
    return f"🕐 {t.scheduled_time}" if t.scheduled_time else "🕐 —"


# ── Page header ───────────────────────────────────────────────────────────────

st.title("🐾 PawPal+")
st.caption("Your daily pet care scheduler")

# ── Owner setup ───────────────────────────────────────────────────────────────

if "owner" not in st.session_state:
    st.session_state.owner = None

st.subheader("👤 Owner")
owner_name = st.text_input("Owner name", value="Jordan")
available_minutes = st.number_input("Available minutes per day", min_value=1, max_value=480, value=60)

if st.button("Set Owner"):
    st.session_state.owner = Owner(name=owner_name, available_minutes=available_minutes)
    st.success(f"✅ Owner set: **{owner_name}** — {available_minutes} mins/day")

if st.session_state.owner is None:
    st.info("👆 Set an owner above to get started.")
    st.stop()

owner: Owner = st.session_state.owner

st.divider()

# ── Add Pet ───────────────────────────────────────────────────────────────────

st.subheader("🐾 Add a Pet")
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"], format_func=species_label)

if st.button("Add Pet"):
    pet = Pet(name=pet_name, species=species)
    owner.add_pet(pet)
    icon = SPECIES_EMOJI.get(species, "🐾")
    st.success(f"{icon} Added **{pet_name}** the {species}.")

if owner.pets:
    pet_pills = "  ".join(
        f"{SPECIES_EMOJI.get(p.species,'🐾')} **{p.name}**" for p in owner.pets
    )
    st.markdown(f"**Your pets:** {pet_pills}")

st.divider()

# ── Add Task ──────────────────────────────────────────────────────────────────

st.subheader("📋 Add a Task")

if not owner.pets:
    st.info("Add a pet first before adding tasks.")
else:
    selected_pet_name = st.selectbox(
        "Assign to pet",
        [p.name for p in owner.pets],
        format_func=lambda n: f"{SPECIES_EMOJI.get(next(p.species for p in owner.pets if p.name == n), '🐾')} {n}",
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    with col3:
        priority_str = st.selectbox("Priority", ["low", "medium", "high"], index=2)

    col4, col5 = st.columns(2)
    with col4:
        scheduled_time_str = st.text_input("Scheduled time (HH:MM, optional)", placeholder="e.g. 08:30")
    with col5:
        recurrence_str = st.selectbox("Recurrence", ["none", "daily", "weekly"])

    if st.button("Add Task"):
        priority_map = {"high": Priority.HIGH, "medium": Priority.MEDIUM, "low": Priority.LOW}
        scheduled_time = scheduled_time_str.strip() if scheduled_time_str.strip() else None
        task = Task(
            title=task_title,
            duration_minutes=int(duration),
            priority=priority_map[priority_str],
            scheduled_time=scheduled_time,
            recurrence=recurrence_str if recurrence_str != "none" else None,
        )
        for pet in owner.pets:
            if pet.name == selected_pet_name:
                pet.add_task(task)
                st.success(f"📌 Added **'{task_title}'** to {selected_pet_name}.")
                break

    # ── Conflict warnings ─────────────────────────────────────────────────────
    scheduler = Scheduler(owner)
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        with st.container(border=True):
            st.warning(f"⚠️ **{len(conflicts)} scheduling conflict(s) detected — tasks overlap in time:**")
            for msg in conflicts:
                st.warning(f"⚠️ {msg}")

    # ── Task list sorted by scheduled time ────────────────────────────────────
    for pet in owner.pets:
        tasks = pet.get_tasks()
        if tasks:
            sorted_tasks = scheduler.sort_by_time(tasks)
            pet_icon = SPECIES_EMOJI.get(pet.species, "🐾")
            st.markdown(f"**{pet_icon} {pet.name}'s tasks** — sorted by time")

            for t in sorted_tasks:
                col_check, col_info = st.columns([1, 9])
                with col_check:
                    checked = st.checkbox(
                        "Done",
                        value=t.completed,
                        key=f"task_{pet.name}_{t.title}",
                        label_visibility="collapsed",
                    )
                    if checked and not t.completed:
                        t.mark_complete()
                        st.rerun()
                with col_info:
                    title_md = f"~~{t.title}~~" if t.completed else f"**{t.title}**"
                    recurrence_label = RECURRENCE_ICON.get(t.recurrence, "⬜ One-time")
                    st.markdown(
                        f"{title_md} &nbsp; {PRIORITY_BADGE[t.priority.name]} &nbsp; {STATUS_BADGE[t.completed]}<br>"
                        f"<small>{task_time_label(t)} &nbsp;|&nbsp; ⏱ {t.duration_minutes} mins &nbsp;|&nbsp; {recurrence_label}</small>",
                        unsafe_allow_html=True,
                    )

st.divider()

# ── Filter Tasks ──────────────────────────────────────────────────────────────

st.subheader("🔍 Filter Tasks")

if not owner.pets:
    st.info("No pets yet.")
else:
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filter_pet = st.selectbox("Filter by pet", ["All"] + [p.name for p in owner.pets])
    with col_f2:
        filter_status = st.selectbox("Filter by status", ["All", "Pending", "Completed"])

    filter_pet_arg = None if filter_pet == "All" else filter_pet
    filter_done_arg = {"All": None, "Pending": False, "Completed": True}[filter_status]

    filtered = owner.get_filtered_tasks(completed=filter_done_arg, pet_name=filter_pet_arg)
    if filtered:
        rows_html = ""
        for pet, task in filtered:
            pet_icon = SPECIES_EMOJI.get(pet.species, "🐾")
            priority_badge = PRIORITY_BADGE[task.priority.name]
            status_badge = STATUS_BADGE[task.completed]
            recurrence_label = RECURRENCE_ICON.get(task.recurrence, "⬜ One-time")
            title_cell = f"<s>{task.title}</s>" if task.completed else task.title
            rows_html += (
                f"<tr>"
                f"<td>{pet_icon} {pet.name}</td>"
                f"<td>{title_cell}</td>"
                f"<td>⏱ {task.duration_minutes} mins</td>"
                f"<td>{priority_badge}</td>"
                f"<td>{status_badge}</td>"
                f"<td>{recurrence_label}</td>"
                f"</tr>"
            )
        table_html = f"""
        <style>
          .pawpal-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
          }}
          .pawpal-table th {{
            background: #e8eaf6;
            color: #2c3060;
            padding: 8px 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #c5cae9;
          }}
          .pawpal-table td {{
            padding: 7px 12px;
            border-bottom: 1px solid #e8eaf6;
            vertical-align: middle;
          }}
          .pawpal-table tr:hover td {{
            background: #f3f4fc;
          }}
        </style>
        <table class="pawpal-table">
          <thead>
            <tr>
              <th>Pet</th><th>Task</th><th>Duration</th>
              <th>Priority</th><th>Status</th><th>Recurrence</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
        """
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.info("No tasks match your filter.")

st.divider()

# ── Generate Schedule ─────────────────────────────────────────────────────────

st.subheader("📅 Build Schedule")

if st.button("Generate Schedule"):
    scheduler = Scheduler(owner)

    conflicts = scheduler.detect_conflicts()
    if conflicts:
        with st.container(border=True):
            st.warning(
                f"⚠️ **Heads up: {len(conflicts)} time conflict(s) found. "
                "Consider adjusting task times before committing to this schedule.**"
            )
            for msg in conflicts:
                st.warning(f"⚠️ {msg}")

    plan = scheduler.generate_plan()

    # Time budget
    budget_fraction = min(plan.total_time_used / owner.available_minutes, 1.0)
    budget_pct = round(budget_fraction * 100)

    col_b1, col_b2 = st.columns([3, 1])
    with col_b1:
        st.markdown(f"**⏱ Time Budget** — {plan.total_time_used} / {owner.available_minutes} mins used ({budget_pct}%)")
        st.progress(budget_fraction)
    with col_b2:
        remaining = owner.available_minutes - plan.total_time_used
        st.metric("Remaining", f"{remaining} min")

    # Scheduled tasks
    st.markdown("#### ✅ Scheduled Tasks")
    if plan.scheduled:
        for pet, task, _ in plan.scheduled:
            pet_icon = SPECIES_EMOJI.get(pet.species, "🐾")
            time_part = f" &nbsp;🕐 {task.scheduled_time}" if task.scheduled_time else ""
            recurrence_label = RECURRENCE_ICON.get(task.recurrence, "⬜ One-time")
            st.markdown(
                f"""<div style="background:#e0f4e8;border-left:4px solid #80cfa0;
                    padding:8px 14px;border-radius:6px;margin-bottom:6px;">
                  {pet_icon} <strong>{pet.name}</strong>: {task.title}
                  &nbsp; {PRIORITY_BADGE[task.priority.name]}
                  <br><small>⏱ {task.duration_minutes} mins{time_part} &nbsp;|&nbsp; {recurrence_label}</small>
                </div>""",
                unsafe_allow_html=True,
            )
    else:
        st.info("No tasks could be scheduled.")

    # Skipped tasks
    st.markdown("#### ❌ Skipped Tasks")
    if plan.skipped:
        for pet, task, reason in plan.skipped:
            st.markdown(
                f"""<div style="background:#fde8e8;border-left:4px solid #f4a0a0;
                    padding:8px 14px;border-radius:6px;margin-bottom:6px;">
                  <strong>{task.title}</strong> &nbsp; {PRIORITY_BADGE[task.priority.name]}
                  <br><small>⏱ {task.duration_minutes} mins &nbsp;|&nbsp; ⛔ {reason}</small>
                </div>""",
                unsafe_allow_html=True,
            )
    else:
        st.info("🎉 All tasks fit within your time budget!")
