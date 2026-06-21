import json
from pathlib import Path
from typing import Dict, List, Any


MEMORY_DIR = Path("data/memory")


def ensure_memory_dir() -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def get_memory_path(conversation_id: str) -> Path:
    safe_id = conversation_id.replace("/", "_").replace("\\", "_")
    return MEMORY_DIR / f"{safe_id}.json"


def load_history(conversation_id: str, max_messages: int = 6) -> List[Dict[str, Any]]:
    """
    读取指定 conversation_id 的历史对话。

    max_messages 控制最多读取最近几条，避免 prompt 过长。
    """
    ensure_memory_dir()
    memory_path = get_memory_path(conversation_id)

    if not memory_path.exists():
        return []

    try:
        with memory_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        messages = data.get("messages", [])
        return messages[-max_messages:]

    except Exception as e:
        print(f"[Memory Error] 读取历史失败：{type(e).__name__}: {e}")
        return []


def save_message(conversation_id: str, role: str, content: str) -> None:
    """
    保存一条对话消息。
    role 可以是 user 或 assistant。
    """
    ensure_memory_dir()
    memory_path = get_memory_path(conversation_id)

    data = {
        "conversation_id": conversation_id,
        "messages": [],
    }

    if memory_path.exists():
        try:
            with memory_path.open("r", encoding="utf-8") as f:
                data = json.load(f)

        except Exception as e:
            print(f"[Memory Error] 读取旧历史失败：{type(e).__name__}: {e}")

    data.setdefault("messages", [])

    data["messages"].append(
        {
            "role": role,
            "content": content,
        }
    )

    try:
        with memory_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"[Memory Error] 保存历史失败：{type(e).__name__}: {e}")


def format_history_text(history: List[Dict[str, Any]]) -> str:
    """
    将历史消息格式化成 prompt 可用文本。
    """
    if not history:
        return "无历史对话。"

    lines = []

    for message in history:
        role = message.get("role", "")
        content = message.get("content", "")

        if role == "user":
            lines.append(f"用户：{content}")
        elif role == "assistant":
            lines.append(f"助手：{content}")

    return "\n".join(lines)