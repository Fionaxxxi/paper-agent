from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class StrategyVersionRegistry:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"registry_version": "1.0", "active_version": "baseline", "versions": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def register(self, record: dict[str, Any]) -> dict[str, Any]:
        payload = self.load()
        version = str(record["version"])
        if any(item.get("version") == version for item in payload["versions"]):
            raise ValueError(f"strategy version already registered: {version}")
        payload["versions"].append({
            **record,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "auto_applied": False,
        })
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.path)
        return payload
