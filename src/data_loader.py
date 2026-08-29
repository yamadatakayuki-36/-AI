"""データ読み込み・保存ユーティリティ（CSV/JSONによる簡易永続化）。

app/main.py から import される最低限のスタブ実装。
データは ROOT/data 配下に自動生成される。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

COMPANY_PATH = DATA_DIR / "company.json"
MEMBERS_PATH = DATA_DIR / "members.csv"
THEME_HISTORY_PATH = DATA_DIR / "theme_history.csv"
REJECTED_THEMES_PATH = DATA_DIR / "rejected_themes.csv"
SITE_NOTES_PATH = DATA_DIR / "site_notes.csv"

_DEFAULT_COMPANY = {"company_name": "架空製作所株式会社", "industry": "精密機械製造"}
_DEFAULT_MEMBERS = ["委員長 佐藤", "衛生管理者 鈴木", "産業医 田中", "現場代表 山本", "総務 高橋"]


def _ensure_csv(path: Path, columns: list[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        pd.DataFrame(columns=columns).to_csv(path, index=False)


def load_company() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not COMPANY_PATH.exists():
        COMPANY_PATH.write_text(json.dumps(_DEFAULT_COMPANY, ensure_ascii=False, indent=2), encoding="utf-8")
    return json.loads(COMPANY_PATH.read_text(encoding="utf-8"))


def load_members() -> list[str]:
    _ensure_csv(MEMBERS_PATH, ["name"])
    df = pd.read_csv(MEMBERS_PATH)
    if df.empty:
        df = pd.DataFrame({"name": _DEFAULT_MEMBERS})
        df.to_csv(MEMBERS_PATH, index=False)
    return df["name"].astype(str).tolist()


def member_labels(members: list[str]) -> list[str]:
    return list(members)


def load_theme_history() -> pd.DataFrame:
    _ensure_csv(THEME_HISTORY_PATH, ["year_month", "theme", "logged_at"])
    return pd.read_csv(THEME_HISTORY_PATH)


def append_theme_history(year_month: str, theme: str) -> None:
    _ensure_csv(THEME_HISTORY_PATH, ["year_month", "theme", "logged_at"])
    df = pd.read_csv(THEME_HISTORY_PATH)
    row = {"year_month": year_month, "theme": theme, "logged_at": datetime.now().isoformat(timespec="seconds")}
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(THEME_HISTORY_PATH, index=False)


def load_rejected_themes() -> pd.DataFrame:
    _ensure_csv(REJECTED_THEMES_PATH, ["year_month", "title", "note", "logged_at"])
    return pd.read_csv(REJECTED_THEMES_PATH)


def append_rejected_theme(year_month: str, title: str, note: str = "") -> None:
    _ensure_csv(REJECTED_THEMES_PATH, ["year_month", "title", "note", "logged_at"])
    df = pd.read_csv(REJECTED_THEMES_PATH)
    row = {
        "year_month": year_month,
        "title": title,
        "note": note,
        "logged_at": datetime.now().isoformat(timespec="seconds"),
    }
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(REJECTED_THEMES_PATH, index=False)


def load_site_notes() -> pd.DataFrame:
    _ensure_csv(SITE_NOTES_PATH, ["year_month", "note", "logged_at"])
    return pd.read_csv(SITE_NOTES_PATH)


def append_site_note(year_month: str, note: str) -> None:
    if not note:
        return
    _ensure_csv(SITE_NOTES_PATH, ["year_month", "note", "logged_at"])
    df = pd.read_csv(SITE_NOTES_PATH)
    row = {"year_month": year_month, "note": note, "logged_at": datetime.now().isoformat(timespec="seconds")}
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(SITE_NOTES_PATH, index=False)


def latest_site_note(year_month: str) -> str:
    df = load_site_notes()
    matches = df[df["year_month"] == year_month]
    if matches.empty:
        return ""
    return str(matches.sort_values("logged_at", ascending=False).iloc[0]["note"])
