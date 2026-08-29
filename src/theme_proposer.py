"""テーマ候補の生成（発表デモ / オフラインのルールベース / OpenAIの3モード）。"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass

from data_loader import load_theme_history


@dataclass
class ThemeCandidate:
    title: str
    reason: str


_DEMO_CANDIDATES = [
    ThemeCandidate("熱中症予防対策の徹底", "夏季に発生件数が増える典型テーマで、発表デモの定番として選定。"),
    ThemeCandidate("保護具の正しい着用ルール再確認", "ヒヤリハット報告で着用不備が挙がりやすいため。"),
    ThemeCandidate("整理整頓（5S）による転倒防止", "職場巡視で指摘の多い転倒リスクへの対応。"),
]

# 現場メモのキーワードに応じて優先的に提示するテーマ
_RULE_BASE = [
    ("巻き込まれ", "旋盤・機械の巻き込まれ防止と非常停止手順の再確認"),
    ("転倒", "床面の油汚れ・段差対策と整理整頓（5S）の徹底"),
    ("腰痛", "重量物取扱いにおける腰痛予防と補助具の活用"),
    ("熱中症", "夏季の熱中症予防（WBGT管理・休憩ルール）"),
    ("感電", "電気設備点検と感電防止のための作業手順の見直し"),
]

_FALLBACK_POOL = [
    ThemeCandidate("ヒヤリハット報告の活性化", "報告件数が少ない場合、活性化そのものをテーマにするのも有効。"),
    ThemeCandidate("避難訓練・緊急時対応の再確認", "定期的な見直しが推奨される基本テーマ。"),
    ThemeCandidate("VDT作業による健康障害の予防", "デスクワーク中心の職場でも通年使える汎用テーマ。"),
    ThemeCandidate("騒音職場における難聴予防", "工場現場での聴覚保護の啓発。"),
    ThemeCandidate("メンタルヘルスケアの基礎知識", "ストレスチェック結果を踏まえた啓発テーマ。"),
]


def propose_demo(year_month: str, n: int = 3) -> tuple[list[ThemeCandidate], str]:
    return list(_DEMO_CANDIDATES[:n]), "demo"


def _offline_candidates(n: int, exclude_titles: set[str], site_note: str, seed: int) -> list[ThemeCandidate]:
    rng = random.Random(seed)
    picked: list[ThemeCandidate] = []

    if site_note:
        for keyword, title in _RULE_BASE:
            if keyword in site_note and title not in exclude_titles:
                picked.append(ThemeCandidate(title, f"現場メモの「{keyword}」に関連するテーマとして優先提案。"))

    rule_based = [ThemeCandidate(title, f"「{keyword}」に関連する定番テーマ。") for keyword, title in _RULE_BASE]
    pool = [
        c
        for c in (_FALLBACK_POOL + rule_based)
        if c.title not in exclude_titles and c.title not in [p.title for p in picked]
    ]
    rng.shuffle(pool)
    for c in pool:
        if len(picked) >= n:
            break
        picked.append(c)
    return picked[:n]


def propose_themes(
    year_month: str,
    n: int = 3,
    seed: int = 0,
    site_note: str = "",
    force_offline: bool = False,
    exclude_titles: set[str] | None = None,
) -> tuple[list[ThemeCandidate], str]:
    exclude_titles = set(exclude_titles or set())
    history_titles = set(load_theme_history()["theme"].astype(str).tolist())
    exclude_titles |= history_titles

    use_openai = (not force_offline) and bool(os.environ.get("OPENAI_API_KEY"))
    if use_openai:
        try:
            return _propose_with_openai(year_month, n, site_note, exclude_titles), "openai"
        except Exception:
            pass  # 失敗時はオフライン提案にフォールバック

    return _offline_candidates(n, exclude_titles, site_note, seed), "offline"


def _propose_with_openai(year_month: str, n: int, site_note: str, exclude_titles: set[str]) -> list[ThemeCandidate]:
    from openai import OpenAI  # 遅延import（未インストールでもデモ/オフラインは動く）

    client = OpenAI()
    prompt = (
        f"{year_month}の安全衛生委員会向けテーマ候補を{n}件、"
        "日本語で「テーマ名: 理由」の形式で改行区切りで提案してください。"
        f"現場メモ: {site_note or 'なし'}。"
        f"以下は既出のため除外してください: {', '.join(exclude_titles) or 'なし'}。"
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.choices[0].message.content or ""
    candidates: list[ThemeCandidate] = []
    for line in text.splitlines():
        if ":" in line:
            title, _, reason = line.partition(":")
            title = title.strip(" ・-")
            if title and title not in exclude_titles:
                candidates.append(ThemeCandidate(title, reason.strip() or "AI提案"))
    if not candidates:
        raise ValueError("OpenAI応答から候補を抽出できませんでした")
    return candidates[:n]
