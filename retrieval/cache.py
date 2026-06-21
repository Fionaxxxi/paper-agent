import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import settings


CACHE_DIR = Path(settings.CACHE_DIR)


def ensure_cache_dir() -> None:
    """
    确保缓存目录存在。
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def build_cache_key(query: str) -> str:
    """
    根据查询词生成稳定的缓存 key。
    使用 md5 是为了避免文件名过长或包含特殊字符。
    """
    normalized_query = query.strip().lower()
    return hashlib.md5(normalized_query.encode("utf-8")).hexdigest()


def get_cache_path(query: str) -> Path:
    """
    根据 query 得到对应缓存文件路径。
    """
    cache_key = build_cache_key(query)
    return CACHE_DIR / f"{cache_key}.json"


def load_cached_papers(query: str) -> Optional[List[Dict[str, Any]]]:
    """
    读取缓存。

    返回：
    - None：没有缓存或缓存读取失败
    - List[Dict]：缓存中的论文列表
    """
    ensure_cache_dir()
    cache_path = get_cache_path(query)

    if not cache_path.exists():
        return None

    try:
        with cache_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return data.get("papers", [])

    except Exception as e:
        print(f"[Cache Error] 读取缓存失败：{type(e).__name__}: {e}")
        return None


def save_cached_papers(query: str, papers: List[Dict[str, Any]]) -> None:
    """
    保存论文检索结果到本地 JSON 文件。
    """
    ensure_cache_dir()
    cache_path = get_cache_path(query)

    data = {
        "query": query,
        "papers": papers,
    }

    try:
        with cache_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"[Cache Error] 保存缓存失败：{type(e).__name__}: {e}")