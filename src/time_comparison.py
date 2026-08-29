"""手作業とツール利用の所要時間比較データの読み書き。"""

from __future__ import annotations

import json
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "time_comparison.json"

_DEFAULT = {
    "hand_minutes": 60.0,
    "tool_minutes": 5.0,
    "source": "estimated",
    "note": "初期値（見積もり）。実測値を記録すると更新されます。",
}


def load_time_comparison() -> dict:
    if not DATA_PATH.exists():
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        DATA_PATH.write_text(json.dumps(_DEFAULT, ensure_ascii=False, indent=2), encoding="utf-8")
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def save_time_comparison(hand_minutes: float, tool_minutes: float, source: str, note: str) -> None:
    data = {
        "hand_minutes": hand_minutes,
        "tool_minutes": tool_minutes,
        "source": source,
        "note": note,
    }
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def format_minutes(minutes: float) -> str:
    if minutes < 1:
        return f"{minutes * 60:.0f}秒"
    if minutes == int(minutes):
        return f"{int(minutes)}分"
    return f"{minutes:.1f}分"
