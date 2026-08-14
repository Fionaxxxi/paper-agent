"""将已验证 Research Plan 编译为有界、可审计的执行波次。"""

from __future__ import annotations

from typing import Any


def build_schedule(plan: dict[str, Any]) -> dict[str, Any]:
    tasks = list(plan.get("tasks", []))
    max_parallel = max(1, min(int(plan.get("max_parallel_tasks", 2)), 2))
    if not tasks:
        return {"enabled": False, "waves": [], "max_parallel_tasks": max_parallel,
                "task_count": 0, "status": "empty_plan"}

    pending = {task["task_id"]: dict(task) for task in tasks}
    completed: set[str] = set()
    waves: list[dict[str, Any]] = []
    wave_index = 1
    while pending:
        ready = [
            task for task in pending.values()
            if set(task.get("depends_on", [])).issubset(completed)
        ]
        if not ready:
            return {"enabled": False, "waves": waves,
                    "max_parallel_tasks": max_parallel,
                    "task_count": len(tasks), "status": "blocked_dependencies"}
        for offset in range(0, len(ready), max_parallel):
            batch = ready[offset:offset + max_parallel]
            scheduled = []
            for task in batch:
                scheduled.append({
                    **task,
                    "wave": wave_index,
                    "task_kind": (
                        "synthesis" if task.get("source") == "evidence_store"
                        else "retrieval"
                    ),
                    "status": "scheduled",
                })
                pending.pop(task["task_id"])
                completed.add(task["task_id"])
            waves.append({"wave": wave_index, "tasks": scheduled})
            wave_index += 1
    return {"enabled": True, "waves": waves,
            "max_parallel_tasks": max_parallel,
            "task_count": len(tasks), "status": "scheduled"}
