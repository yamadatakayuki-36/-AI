"""安全衛生委員会サポートAI — Streamlitアプリ。"""

from __future__ import annotations

import logging
import sys
import time
from datetime import date
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")

# OpenAI呼び出し失敗時のフォールバック理由などをターミナルに残す（開発者本人の運用向け）
logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(name)s] %(message)s")

from agenda_generator import (  # noqa: E402
    AgendaDocument,
    agenda_to_docx_bytes,
    agenda_to_text,
    build_agenda,
    format_datetime_label,
    safe_filename_theme,
    third_friday,
)
from copilot_export import build_copilot_prompt, theme_history_to_excel_bytes  # noqa: E402
from slide_generator import agenda_to_pptx_bytes  # noqa: E402
from data_loader import (  # noqa: E402
    append_rejected_theme,
    append_site_note,
    append_theme_history,
    latest_site_note,
    load_company,
    load_members,
    load_rejected_themes,
    load_site_notes,
    load_theme_history,
    member_labels,
)
from theme_proposer import propose_demo, propose_themes  # noqa: E402
from time_comparison import format_minutes, load_time_comparison, save_time_comparison  # noqa: E402

st.set_page_config(
    page_title="安全衛生委員会サポートAI",
    page_icon="🛡️",
    layout="centered",
)

company = load_company()

# --- セッション初期化 ---
defaults = {
    "step": 1,
    "year_month": "2026-09",
    "candidates": [],
    "mode": "",
    "selected_theme": "",
    "regen_count": 0,
    "shown_titles": [],
    "agenda_doc": None,
    "agenda_text": "",
    "agenda_docx": b"",
    "agenda_pptx": b"",
    "flow_started_at": None,
    "measured_tool_seconds": None,
    "demo_mode": True,
    "site_note": "",
    "history_saved": False,
    "year_month_select": "2026-09",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

history = load_theme_history()
time_cmp = load_time_comparison()
rejected_themes = load_rejected_themes()

STEPS = ["月を選ぶ", "テーマを選ぶ", "アジェンダ完成"]


def render_step_indicator(current: int) -> None:
    # st.progress は内部DOMの付け替えで removeChild が起きやすい。
    # ラベルも常に同じ markdown 1本にする。
    parts: list[str] = []
    for i, label in enumerate(STEPS, start=1):
        if i == current:
            parts.append(f"**🔵 {i}. {label}**")
        elif i < current:
            parts.append(f"✅ {i}. {label}")
        else:
            parts.append(f"⚪ {i}. {label}")
    st.markdown(f"STEP {current} / {len(STEPS)}")
    st.markdown("　".join(parts))


def refresh_agenda_outputs(doc: AgendaDocument) -> None:
    st.session_state.agenda_doc = doc
    st.session_state.agenda_text = agenda_to_text(doc)
    st.session_state.agenda_docx = agenda_to_docx_bytes(doc)
    st.session_state.agenda_pptx = agenda_to_pptx_bytes(doc)


def go_to_agenda(theme: str) -> None:
    if st.session_state.flow_started_at is not None:
        st.session_state.measured_tool_seconds = max(
            1, int(time.time() - st.session_state.flow_started_at)
        )
    agenda_doc = build_agenda(st.session_state.year_month, theme)
    refresh_agenda_outputs(agenda_doc)
    st.session_state.selected_theme = theme
    st.session_state.step = 3
    # 履歴CSVへの保存はSTEP3での明示的な確定操作まで遅らせる（誤クリック対策）
    st.session_state.history_saved = False


def confirm_theme_selection() -> None:
    """STEP3で内容を確認したうえでの確定操作。ここで初めて履歴CSVへ書き込む。"""
    if st.session_state.history_saved:
        return
    theme = st.session_state.selected_theme
    note = (st.session_state.get("site_note") or "").strip()
    if note:
        append_site_note(st.session_state.year_month, note)
    append_theme_history(st.session_state.year_month, theme)
    # 表示されたが選ばれなかった候補は「却下」として記録し、次回以降の提案改善に使う
    for c in st.session_state.candidates:
        if c.title != theme:
            append_rejected_theme(st.session_state.year_month, c.title, note="テーマ確定のため不採用")
    st.session_state.history_saved = True


def start_theme_proposal() -> None:
    """STEP1→2。on_clickで先に状態を更新し、同一描画での画面差し替えを避ける。"""
    year_month = st.session_state.year_month_select
    site_note = (st.session_state.get("site_note_input") or "").strip()
    st.session_state.flow_started_at = time.time()
    st.session_state.measured_tool_seconds = None
    st.session_state.site_note = site_note
    if st.session_state.demo_mode:
        candidates, mode = propose_demo(year_month, n=3)
    else:
        candidates, mode = propose_themes(year_month, n=3, seed=0, site_note=site_note)
    st.session_state.year_month = year_month
    st.session_state.candidates = candidates
    st.session_state.mode = mode
    st.session_state.regen_count = 0
    st.session_state.shown_titles = [c.title for c in candidates]
    st.session_state.selected_theme = ""
    st.session_state.step = 2


def regenerate_candidates() -> None:
    ym = st.session_state.year_month
    for c in st.session_state.candidates:
        append_rejected_theme(ym, c.title, note="再生成でスキップ")
    st.session_state.regen_count += 1
    exclude = set(st.session_state.shown_titles)
    candidates, mode = propose_themes(
        ym,
        n=3,
        force_offline=(st.session_state.mode == "offline"),
        exclude_titles=exclude,
        seed=st.session_state.regen_count + 100,
        site_note=st.session_state.get("site_note", ""),
    )
    st.session_state.candidates = candidates
    st.session_state.mode = mode
    st.session_state.shown_titles = list(
        dict.fromkeys(st.session_state.shown_titles + [c.title for c in candidates])
    )


def back_to_step1() -> None:
    st.session_state.step = 1


def back_to_step2() -> None:
    st.session_state.step = 2


def go_manual_theme() -> None:
    title = (st.session_state.get("manual_theme") or "").strip()
    if len(title) >= 4:
        go_to_agenda(title)


def reset_flow() -> None:
    demo_mode = st.session_state.get("demo_mode", True)
    for k, v in defaults.items():
        st.session_state[k] = v
    st.session_state.demo_mode = demo_mode


st.title("安全衛生委員会サポートAI")
st.caption(
    f"{company['company_name']}（{company['industry']}・架空）"
    "｜今月の委員会アジェンダを、AIと一緒に準備します"
)
render_step_indicator(st.session_state.step)
st.divider()

months = [
    m
    for m in [f"{y}-{m:02d}" for y in range(2026, 2028) for m in range(1, 13)]
    if "2026-08" <= m <= "2027-07"
]
if st.session_state.year_month_select not in months:
    st.session_state.year_month_select = "2026-09"

# ステップ切替でウィジェットを増減させると removeChild が起きる。
# 1〜3の枠は毎回同じ順番で描画し、中身だけ更新する。
st.subheader("1. 対象月を選ぶ")
year_month = st.selectbox(
    "対象月",
    options=months,
    format_func=lambda s: f"{s[:4]}年{int(s[5:])}月",
    key="year_month_select",
)
st.markdown(f"過去{len(history)}ヶ月分のテーマ履歴を読み込み済み")

recent = history.sort_values("year_month", ascending=False).head(3)
with st.expander("直近のテーマ（参考）", expanded=False):
    for _, row in recent.iterrows():
        ym = row["year_month"]
        st.write(f"・{ym[:4]}年{int(ym[5:])}月：{row['theme']}")

if st.session_state.get("_site_note_ym") != year_month:
    st.session_state.site_note_input = latest_site_note(year_month)
    st.session_state._site_note_ym = year_month
st.text_area(
    "現場メモ（任意）",
    placeholder="例：先月、旋盤エリアでヒヤリハット（巻き込まれ）が2件あった",
    height=80,
    key="site_note_input",
)
st.caption("入力すると、関連するテーマ候補を優先して提案します（会社独自の記録として蓄積）")
st.button(
    "テーマ候補を出す",
    type="primary",
    use_container_width=True,
    on_click=start_theme_proposal,
)

st.divider()
st.subheader("2. テーマを選ぶ")
ym = st.session_state.year_month
y, m = ym.split("-")
st.markdown(f"{y}年{int(m)}月のテーマ候補")
mode_label = {
    "openai": "AI（OpenAI）",
    "demo": "発表デモ（定番セット）",
    "offline": "オフライン（ルールベース）",
}.get(st.session_state.mode, st.session_state.mode or "未生成")
st.caption(
    f"過去に使用していないテーマのみ表示｜生成モード: {mode_label}"
    f"｜{len(st.session_state.candidates)}件生成"
)

slots = list(st.session_state.candidates)[:3]
while len(slots) < 3:
    slots.append(None)
for i, c in enumerate(slots):
    with st.container(border=True):
        st.markdown(f"### {c.title if c else '候補はまだありません'}")
        st.write(c.reason if c else "上の「テーマ候補を出す」を押してください")
        st.button(
            "選択",
            key=f"select_{i}",
            type="primary",
            use_container_width=True,
            disabled=c is None,
            on_click=go_to_agenda,
            args=(c.title if c else "",),
        )

st.markdown("気に入らない場合は「他の候補を出す」、または自分でテーマを入力できます")
st.button("他の候補を出す", use_container_width=True, on_click=regenerate_candidates)
st.button("← 月選択に戻る", use_container_width=True, on_click=back_to_step1)
st.markdown("##### 自分でテーマを入力")
manual = st.text_input(
    "テーマ名",
    placeholder="例：保護メガネの着用徹底",
    label_visibility="collapsed",
    key="manual_theme",
)
manual_valid = bool(manual and len(manual.strip()) >= 4)
st.caption("テーマ名は4文字以上で入力してください" if manual and not manual_valid else "　")
st.button(
    "このテーマでアジェンダを作る",
    disabled=not manual_valid,
    on_click=go_manual_theme,
)

st.divider()
st.subheader("3. アジェンダ完成")
if st.session_state.selected_theme:
    st.markdown(f"テーマ「{st.session_state.selected_theme}」でアジェンダ案を作成しました")
else:
    st.markdown("テーマを選ぶと、ここにアジェンダが出ます")
if st.session_state.history_saved:
    st.markdown("✓ テーマ履歴CSVへ保存済み（次回以降の重複回避に使われます）")
else:
    st.markdown(
        "内容を確認のうえ、下のボタンでこのテーマを確定してください（確定するまで履歴には保存されません）"
    )
st.button(
    "✅ このテーマで確定する（履歴に保存）",
    type="primary",
    use_container_width=True,
    disabled=not st.session_state.selected_theme or st.session_state.history_saved,
    on_click=confirm_theme_selection,
)

agenda = st.session_state.agenda_text or "テーマを選ぶと、ここにプレビューが出ます。"
with st.container(border=True):
    st.markdown("##### プレビュー")
    st.text(agenda)

doc = st.session_state.agenda_doc
links = doc.reference_links if doc is not None else []
with st.expander("参考資料（関連WEBサイト）", expanded=False):
    st.caption("会議での深掘り用に、事前に選定した公式サイトのリンクです。")
    if links:
        for link in links:
            st.markdown(f"- [{link['title']}]({link['url']})")
    else:
        st.markdown("テーマを選ぶと、関連リンクが出ます。")

st.markdown("##### ダウンロード")
theme_slug = safe_filename_theme(st.session_state.selected_theme or "draft")
base_name = f"agenda_{st.session_state.year_month}_{theme_slug}"
st.download_button(
    label="Wordでダウンロード（.docx）",
    data=st.session_state.agenda_docx or b" ",
    file_name=f"{base_name}.docx",
    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    type="primary",
    use_container_width=True,
    disabled=not st.session_state.agenda_docx,
)
st.download_button(
    label="スライドでダウンロード（.pptx）",
    data=st.session_state.agenda_pptx or b" ",
    file_name=f"{base_name}.pptx",
    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    use_container_width=True,
    disabled=not st.session_state.agenda_pptx,
)
st.download_button(
    label="テキストでダウンロード（.txt）",
    data=(st.session_state.agenda_text or " ").encode("utf-8"),
    file_name=f"{base_name}.txt",
    mime="text/plain",
    use_container_width=True,
    disabled=not st.session_state.agenda_text,
)

roster = member_labels(load_members())
if doc is not None:
    try:
        default_day = date.fromisoformat(doc.meeting_date) if doc.meeting_date else third_friday(doc.year_month)
    except ValueError:
        default_day = third_friday(doc.year_month)
    default_attendees = doc.attendees if doc.attendees else roster
    place_default = doc.meeting_place
    action_default = doc.action_owner
    due_default = doc.due_label
    points_default = "\n".join(doc.theme_points)
else:
    default_day = third_friday(st.session_state.year_month)
    default_attendees = roster
    place_default = "会議室A"
    action_default = ""
    due_default = ""
    points_default = ""

with st.expander("アジェンダを手直しする（日時・出席者・討議ポイント）", expanded=False):
    with st.form("agenda_edit_form"):
        meeting_day = st.date_input("開催日", value=default_day)
        meeting_place = st.text_input("場所", value=place_default)
        selected_attendees = st.multiselect(
            "出席予定者",
            options=roster,
            default=[a for a in default_attendees if a in roster],
        )
        action_owner = st.text_input("担当", value=action_default)
        due_label = st.text_input("期限", value=due_default)
        points_text = st.text_area("討議ポイント（1行＝1項目）", value=points_default, height=140)
        submitted = st.form_submit_button("反映してプレビュー更新", type="primary")
        if submitted and doc is not None:
            points = [p.strip(" ・\t") for p in points_text.splitlines() if p.strip()]
            updated = AgendaDocument(
                meeting_no=doc.meeting_no,
                year_month=doc.year_month,
                theme=doc.theme,
                company_name=doc.company_name,
                committee_name=doc.committee_name,
                meeting_place=meeting_place.strip() or doc.meeting_place,
                meeting_date=meeting_day.isoformat(),
                datetime_label=format_datetime_label(meeting_day),
                attendees=selected_attendees or list(roster),
                theme_points=points or doc.theme_points,
                reference_links=doc.reference_links,
                action_owner=action_owner.strip() or doc.action_owner,
                due_label=due_label.strip() or doc.due_label,
            )
            refresh_agenda_outputs(updated)

st.divider()
st.markdown("##### 時間短縮効果")
hand = float(time_cmp["hand_minutes"])
tool = float(time_cmp["tool_minutes"])
saved = max(0.0, hand - tool)
st.markdown(
    f"従来（手書き） {format_minutes(hand)} ／ ツール利用後 {format_minutes(tool)} ／ 短縮 {format_minutes(saved)}"
)
source_label = "実測値" if time_cmp.get("source") == "measured" else "見積もり"
st.caption(f"表示中: {source_label}｜{time_cmp.get('note', '')}")
measured_sec = st.session_state.measured_tool_seconds
if measured_sec is not None:
    st.caption(
        f"今回の操作実測: {measured_sec}秒（{format_minutes(measured_sec / 60)}）"
        "｜「テーマ候補を出す」からアジェンダ完成まで"
    )
else:
    st.caption("　")

with st.expander("実測値を記録する（発表用）", expanded=False):
    hand_in = st.number_input(
        "手書きの所要時間（分）",
        min_value=1.0,
        max_value=180.0,
        value=float(hand),
        step=1.0,
    )
    tool_in = st.number_input(
        "ツール利用の所要時間（分）",
        min_value=0.1,
        max_value=60.0,
        value=float(tool if measured_sec is None else round(measured_sec / 60, 1)),
        step=0.1,
    )
    if st.button("この数値を発表用に保存", type="primary"):
        save_time_comparison(
            hand_minutes=hand_in,
            tool_minutes=tool_in,
            source="measured",
            note="操作実測を反映",
        )

st.button("テーマ選択に戻る", use_container_width=True, on_click=back_to_step2)
st.button("最初からやり直す", use_container_width=True, on_click=reset_flow)

# --- サイドバー ---
with st.sidebar:
    st.header("テーマ履歴")
    hist_lines = ["| 年月 | テーマ |", "|---|---|"]
    for _, row in history.sort_values("year_month", ascending=False).head(12).iterrows():
        hist_lines.append(f"| {row['year_month']} | {row['theme']} |")
    st.markdown("\n".join(hist_lines))
    st.caption(f"全{len(history)}件")
    st.download_button(
        label="履歴をExcelでダウンロード",
        data=theme_history_to_excel_bytes(),
        file_name="theme_history.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    with st.expander("Copilot 365用プロンプトを作る", expanded=False):
        st.markdown(
            "Copilot 365への自動連携ではありません。"
            "下記をコピーして、自分でCopilot 365のチャットに貼り付けて使う手動コピペ用です。"
        )
        st.caption(
            "社内はCopilot Studioが使えないため、履歴Excel＋このプロンプトを"
            "Copilot 365にそのまま貼り付けて使う運用の補助です。"
        )
        prompt_year_month = st.session_state.get("year_month", "2026-09")
        st.code(build_copilot_prompt(prompt_year_month), language="text")
        st.caption(
            "使い方：①上のプロンプトをコピー ②「履歴をExcelでダウンロード」を実行 "
            "③Copilot 365のチャットを開く ④プロンプトを貼り付け＋Excelを添付して送信"
        )

    st.divider()
    st.header("会社独自の記録")
    st.caption(
        f"現場メモ {len(load_site_notes())}件｜却下テーマ {len(rejected_themes)}件"
        "（使うほど蓄積され、提案の精度が上がります）"
    )
    with st.expander("却下テーマの履歴（参考）", expanded=False):
        if rejected_themes.empty:
            st.markdown("まだありません。")
        else:
            rej_lines = ["| 年月 | テーマ | メモ |", "|---|---|---|"]
            for _, row in rejected_themes.sort_values("logged_at", ascending=False).head(10).iterrows():
                rej_lines.append(f"| {row['year_month']} | {row['title']} | {row['note']} |")
            st.markdown("\n".join(rej_lines))

    st.divider()
    st.caption(
        f"時間比較: 手書き {format_minutes(float(time_cmp['hand_minutes']))}"
        f" / ツール {format_minutes(float(time_cmp['tool_minutes']))}"
    )

    with st.expander("開発者向け設定", expanded=False):
        st.caption("※ 会社名・履歴データはすべて架空のデモ用データです。")
        st.toggle(
            "発表デモモード",
            key="demo_mode",
            help="ONだと、モックに近い定番テーマ3件から開始します。",
        )
        st.markdown("**デモ手順（要約）**")
        st.markdown(
            """
1. 対象月を **2026年9月** にする
2. **テーマ候補を出す**
3. 先頭テーマを **選択**
4. **Wordでダウンロード** を見せる
5. 時間短縮の数字を指す
6. 将来構想（PDF読み取り／Copilot運用）を口頭で

詳細はプロジェクト内の `DEMO.md` を参照。
            """.strip()
        )
        st.caption("OpenAIを使う場合はプロジェクト直下の `.env` に `OPENAI_API_KEY` を設定してください。")
