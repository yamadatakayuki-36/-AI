"""テーマ候補の生成（発表デモ / オフラインのルールベース / OpenAIの3モード）。

対象月（year_month）の季節性を候補選定に反映させ、月ごとに異なるテーマが
出るようにしている。あわせて、過去に確定・却下したテーマも除外対象に含める。
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass

from data_loader import load_rejected_themes, load_theme_history


@dataclass
class ThemeCandidate:
    title: str
    reason: str


# 月ごとの季節テーマ（発表デモ／オフライン提案の両方で使用）。
# 1〜12月をキーに、その時期に扱われやすい安全衛生テーマを3件ずつ用意している。
_SEASONAL_POOL: dict[int, list[ThemeCandidate]] = {
    1: [
        ThemeCandidate("積雪・凍結路面での転倒防止", "冬季は凍結による転倒災害が増える時期のため。"),
        ThemeCandidate("インフルエンザ等感染症対策", "年始は感染症の流行期にあたるため。"),
        ThemeCandidate("空気の乾燥と火災予防", "乾燥する時期の火気取扱いへの注意喚起として。"),
    ],
    2: [
        ThemeCandidate("花粉症と職場での対応", "花粉飛散が本格化する時期のため。"),
        ThemeCandidate("凍結路面での転倒災害防止（継続）", "冬季の転倒災害への継続的な注意喚起。"),
        ThemeCandidate("インフルエンザ流行期の振り返り", "流行期の総括と次年度への申し送り。"),
    ],
    3: [
        ThemeCandidate("新年度に向けた安全衛生教育の準備", "年度替わりに向けた教育計画の見直し時期。"),
        ThemeCandidate("花粉症対策の継続", "花粉飛散のピークが続く時期のため。"),
        ThemeCandidate("年度末繁忙期の疲労管理", "決算期など繁忙による疲労蓄積への対応。"),
    ],
    4: [
        ThemeCandidate("新入社員への安全衛生教育", "新年度で新任者が増える時期のため。"),
        ThemeCandidate("新任者の労働災害防止", "経験の浅い従業員の災害防止に焦点を当てる。"),
        ThemeCandidate("通勤経路・通勤手段の再確認", "異動・入社に伴う通勤ルート変更への対応。"),
    ],
    5: [
        ThemeCandidate("熱中症予防の早期準備", "本格的な夏を前に、対策を先取りする時期。"),
        ThemeCandidate("屋外作業における紫外線対策", "日差しが強くなり始める時期のため。"),
        ThemeCandidate("大型連休明けの体調管理", "生活リズムの乱れによる不調防止。"),
    ],
    6: [
        ThemeCandidate("梅雨時期の転倒・感電防止", "雨天による足元不良や漏電リスクの増加。"),
        ThemeCandidate("食中毒予防", "気温・湿度が上がり食中毒リスクが高まる時期。"),
        ThemeCandidate("熱中症の初期症状と対応", "本格的な暑さを前にした基礎知識の共有。"),
    ],
    7: [
        ThemeCandidate("熱中症予防対策の徹底", "夏季に発生件数が増える典型テーマ。"),
        ThemeCandidate("屋外作業の休憩ルール見直し", "高温期の作業計画の適正化。"),
        ThemeCandidate("水分・塩分補給の徹底", "熱中症予防の基本行動の再徹底。"),
    ],
    8: [
        ThemeCandidate("熱中症予防対策の徹底（継続）", "引き続き熱中症リスクが高い時期のため。"),
        ThemeCandidate("夏季休暇明けの健康管理", "休暇明けの生活リズム・体調管理。"),
        ThemeCandidate("換気と空調管理の徹底", "熱中症予防と感染症対策を兼ねた換気の見直し。"),
    ],
    9: [
        ThemeCandidate("台風・自然災害時の対応確認", "台風シーズンに備えた避難・BCP確認。"),
        ThemeCandidate("秋の交通安全（通勤・業務移動）", "日没が早まる時期の交通災害防止。"),
        ThemeCandidate("熱中症対策の総括と振り返り", "夏季対策の効果検証と改善点の洗い出し。"),
    ],
    10: [
        ThemeCandidate("繁忙期に向けた疲労管理", "年末に向けて業務量が増える時期への備え。"),
        ThemeCandidate("落ち葉・雨天時の転倒防止", "路面状況が悪化しやすい時期の注意喚起。"),
        ThemeCandidate("乾燥・換気対策の準備", "空気が乾燥し始める時期の火災・感染症予防。"),
    ],
    11: [
        ThemeCandidate("防火・防災訓練の実施確認", "秋の全国火災予防運動に合わせた注意喚起。"),
        ThemeCandidate("暖房機器の安全な使用", "暖房使用開始時期の火災・やけど防止。"),
        ThemeCandidate("インフルエンザ予防の呼びかけ", "流行が始まる時期の早めの注意喚起。"),
    ],
    12: [
        ThemeCandidate("年末年始の交通安全", "帰省・繁忙期の交通災害防止。"),
        ThemeCandidate("忘年会等における飲酒運転防止", "会食機会が増える時期の注意喚起。"),
        ThemeCandidate("大掃除時の労働災害防止", "高所作業・重量物運搬を伴う大掃除への注意。"),
    ],
}

# 現場メモのキーワードに応じて優先的に提示するテーマ（季節を問わず共通）
_RULE_BASE = [
    ("巻き込まれ", "旋盤・機械の巻き込まれ防止と非常停止手順の再確認"),
    ("転倒", "床面の油汚れ・段差対策と整理整頓（5S）の徹底"),
    ("腰痛", "重量物取扱いにおける腰痛予防と補助具の活用"),
    ("熱中症", "夏季の熱中症予防（WBGT管理・休憩ルール）"),
    ("感電", "電気設備点検と感電防止のための作業手順の見直し"),
]

_GENERIC_POOL = [
    ThemeCandidate("ヒヤリハット報告の活性化", "報告件数が少ない場合、活性化そのものをテーマにするのも有効。"),
    ThemeCandidate("避難訓練・緊急時対応の再確認", "定期的な見直しが推奨される基本テーマ。"),
    ThemeCandidate("VDT作業による健康障害の予防", "デスクワーク中心の職場でも通年使える汎用テーマ。"),
    ThemeCandidate("騒音職場における難聴予防", "工場現場での聴覚保護の啓発。"),
    ThemeCandidate("メンタルヘルスケアの基礎知識", "ストレスチェック結果を踏まえた啓発テーマ。"),
]


def _month_of(year_month: str) -> int:
    return int(year_month.split("-")[1])


def propose_demo(year_month: str, n: int = 3) -> tuple[list[ThemeCandidate], str]:
    """発表デモ用：対象月に応じた季節テーマを返す（再現性重視のため乱数は使わない）。"""
    pool = _SEASONAL_POOL.get(_month_of(year_month), _GENERIC_POOL)
    return list(pool[:n]), "demo"


def _offline_candidates(
    year_month: str, n: int, exclude_titles: set[str], site_note: str, seed: int
) -> list[ThemeCandidate]:
    picked: list[ThemeCandidate] = []

    # 1. 現場メモのキーワードに一致するテーマを最優先
    if site_note:
        for keyword, title in _RULE_BASE:
            if keyword in site_note and title not in exclude_titles:
                picked.append(ThemeCandidate(title, f"現場メモの「{keyword}」に関連するテーマとして優先提案。"))

    # 2. 対象月の季節テーマ
    seasonal = [c for c in _SEASONAL_POOL.get(_month_of(year_month), []) if c.title not in exclude_titles]

    # 3. 季節を問わない汎用テーマ
    rule_based = [ThemeCandidate(title, f"「{keyword}」に関連する定番テーマ。") for keyword, title in _RULE_BASE]
    generic = [c for c in (_GENERIC_POOL + rule_based) if c.title not in exclude_titles]

    # 年月をシードに含めることで、月が変われば並び順（＝出てくる候補）も変わるようにする
    rng = random.Random(f"{year_month}:{seed}")
    rng.shuffle(seasonal)
    rng.shuffle(generic)

    for c in seasonal + generic:
        if len(picked) >= n:
            break
        if c.title not in [p.title for p in picked]:
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
    rejected_titles = set(load_rejected_themes()["title"].astype(str).tolist())
    exclude_titles |= history_titles | rejected_titles

    use_openai = (not force_offline) and bool(os.environ.get("OPENAI_API_KEY"))
    if use_openai:
        try:
            return _propose_with_openai(year_month, n, site_note, exclude_titles), "openai"
        except Exception:
            pass  # 失敗時はオフライン提案にフォールバック

    return _offline_candidates(year_month, n, exclude_titles, site_note, seed), "offline"


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
