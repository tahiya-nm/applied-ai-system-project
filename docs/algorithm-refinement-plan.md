# Algorithm Refinement Plan: detect_conflicts

## Context

Two readability/maintainability issues exist in the current `detect_conflicts` method ([pawpal_system.py:177-203](../pawpal_system.py)):

1. **Duplicated `HH:MM → minutes` conversion** — the same `split(":")` math appears independently in both `sort_by_time` (line 157) and `detect_conflicts` (line 187). If the time format ever changes, both must be updated.

2. **`range(len(...))` double-loop** — the pair comparison uses index arithmetic (`for i ... for j in range(i+1, ...)`) which is harder to read than Python's built-in `itertools.combinations`.

No performance change is needed — O(n²) is appropriate for small pet task lists. This is a readability refactor only.

---

## Proposed Changes

### 1. Add `itertools` import

```python
from itertools import combinations
```

### 2. Extract `_to_minutes` as a private static method on `Scheduler`

Eliminates the duplicated conversion in both `sort_by_time` and `detect_conflicts`:

```python
@staticmethod
def _to_minutes(time_str: str) -> int:
    h, m = time_str.split(":")
    return int(h) * 60 + int(m)
```

### 3. Update `sort_by_time` to call `_to_minutes`

**Before:**
```python
def sort_by_time(self, tasks: list[Task]) -> list[Task]:
    def to_minutes(t: Task) -> int:
        if t.scheduled_time is None:
            return float("inf")
        h, m = t.scheduled_time.split(":")
        return int(h) * 60 + int(m)
    return sorted(tasks, key=lambda t: to_minutes(t))
```

**After:**
```python
def sort_by_time(self, tasks: list[Task]) -> list[Task]:
    return sorted(
        tasks,
        key=lambda t: self._to_minutes(t.scheduled_time) if t.scheduled_time else float("inf")
    )
```

### 4. Simplify `detect_conflicts` with `combinations`

**Before (nested index loop):**
```python
for i in range(len(timed)):
    for j in range(i + 1, len(timed)):
        pet_a, task_a, start_a, end_a = timed[i]
        pet_b, task_b, start_b, end_b = timed[j]
        if start_a < end_b and start_b < end_a:
            ...
```

**After (`combinations`):**
```python
for (pet_a, task_a, start_a, end_a), (pet_b, task_b, start_b, end_b) in combinations(timed, 2):
    if start_a < end_b and start_b < end_a:
        ...
```

Also replaces the inline `split(":")` with `self._to_minutes(task.scheduled_time)` in the timed-list build step.

---

## Why `combinations` is better here

| Old approach | New approach |
|---|---|
| `for i in range(len(timed))` | `combinations(timed, 2)` |
| Requires manual index arithmetic | Iterates pairs directly |
| Easy to introduce off-by-one errors | No index bookkeeping |
| 3 lines to unpack | 1-line tuple unpack in for-statement |

`itertools.combinations(iterable, 2)` yields every unique pair exactly once — identical semantics to the `i < j` nested loop, with no behavior change.

---

## Critical file

- [pawpal_system.py](../pawpal_system.py) — lines 1 (import), ~151 (new `_to_minutes`), 152–160 (`sort_by_time`), 177–203 (`detect_conflicts`)

---

## Verification

```bash
python main.py
```

Expected: identical output to before the refactor — same 2 conflict warnings, same sorted task list. No behavior change.
