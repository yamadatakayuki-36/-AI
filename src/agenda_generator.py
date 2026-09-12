"""アジェンダ（次第）の組み立てとファイル出力（テキスト／Word）。

会議の「開催概要」と、時間配分付きの「議事次第」（開会→本日のテーマ討議→
決定事項→連絡事項→閉会）を組み立てる。議事次第は theme_points から
build_agenda_items() が都度組み立てるため、STEP3の編集フォームで
theme_points を書き換えれば、時間配分もそれに合わせて自動的に再計算される。
"""

from __future__ import annotations

import re
from calendar import Calendar
from dataclasses import dataclass, field
from datetime import date
from io import BytesIO

from data_loader import load_company, load_members, load_theme_history, member_labels

try:
    from docx import Document
except ImportError:  # python-docx 未インストール時のフォールバック
    Document = None


@dataclass
class AgendaDocument:
    meeting_no: int
    year_month: str
    theme: str
    company_name: str
    committee_name: str
    meeting_place: str
    meeting_date: str
    datetime_label: str
    attendees: list[str]
    theme_points: list[str]
    reference_links: list[dict] = field(default_factory=list)
    action_owner: str = ""
    due_label: str = ""


@dataclass
class AgendaItem:
    no: int
    title: str
    duration_min: int
    details: list[str] = field(default_factory=list)


def third_friday(year_month: str) -> date:
    """指定した年月（YYYY-MM）の第3金曜日を返す。"""
    year, month = (int(x) for x in year_month.split("-"))
    fridays = [d for d in Calendar().itermonthdates(year, month) if d.month == month and d.weekday() == 4]
    return fridays[2] if len(fridays) >= 3 else fridays[-1]


def format_datetime_label(d: date) -> str:
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    return f"{d.year}年{d.month}月{d.day}日（{weekdays[d.weekday()]}）14:00〜15:00"


def safe_filename_theme(theme: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\s]+', "_", theme.strip())
    return cleaned[:40] or "theme"


_DEFAULT_LINKS = [
    {"title": "厚生労働省 職場のあんぜんサイト", "url": "https://anzeninfo.mhlw.go.jp/"},
    {"title": "中央労働災害防止協会（JISHA）", "url": "https://www.jisha.or.jp/"},
]

_DEFAULT_POINTS_TEMPLATE = [
    "先月の労働災害・ヒヤリハット報告の共有",
    "テーマに関する現状の課題整理",
    "具体的な対策案の検討",
    "次回までのアクションと担当決め",
]

# 60分（14:00〜15:00）の会議を想定した時間配分。本日のテーマ討議に最も時間を割く。
_OPENING_MIN = 5
_THEME_TOTAL_MIN = 35
_DECISION_MIN = 10
_NOTICE_MIN = 5
_CLOSING_MIN = 5


def build_agenda(year_month: str, theme: str, points: list[str] | None = None) -> AgendaDocument:
    """アジェンダを組み立てる。

    points（テーマ固有の討議ポイント）が渡された場合はそれを使い、
    無い場合（自分でテーマを入力した場合やOpenAI提案など）は汎用テンプレートにフォールバックする。
    """
    company = load_company()
    meeting_day = third_friday(year_month)
    meeting_no = len(load_theme_history()) + 1
    roster = member_labels(load_members())
    theme_points = list(points) if points else list(_DEFAULT_POINTS_TEMPLATE)
    return AgendaDocument(
        meeting_no=meeting_no,
        year_month=year_month,
        theme=theme,
        company_name=company["company_name"],
        committee_name="安全衛生委員会",
        meeting_place="会議室A",
        meeting_date=meeting_day.isoformat(),
        datetime_label=format_datetime_label(meeting_day),
        attendees=roster,
        theme_points=theme_points,
        reference_links=list(_DEFAULT_LINKS),
        action_owner=roster[0] if roster else "",
        due_label="次回委員会まで",
    )


def build_agenda_items(doc: AgendaDocument) -> list[AgendaItem]:
    """開会〜閉会までの時間配分付き議事次第を組み立てる。

    討議ポイント（theme_points）の数に応じて、本日のテーマ討議に割り当てた
    時間を均等割りする。theme_pointsが編集されれば、ここで再計算されるため
    常に内容と時間配分が連動する。
    """
    n_points = max(len(doc.theme_points), 1)
    base = _THEME_TOTAL_MIN // n_points
    remainder = _THEME_TOTAL_MIN - base * n_points
    point_minutes = [base + (1 if i < remainder else 0) for i in range(n_points)]
    theme_details = [f"{p}（約{m}分）" for p, m in zip(doc.theme_points, point_minutes)]

    return [
        AgendaItem(1, "開会・前回議事の確認", _OPENING_MIN, ["前回の議事録・決定事項の確認"]),
        AgendaItem(2, f"本日のテーマ：{doc.theme}", _THEME_TOTAL_MIN, theme_details),
        AgendaItem(
            3,
            "対策・アクションの決定",
            _DECISION_MIN,
            [f"担当：{doc.action_owner or '未定'}　期限：{doc.due_label or '未定'}"],
        ),
        AgendaItem(4, "連絡事項・次回予定", _NOTICE_MIN, []),
        AgendaItem(5, "閉会", _CLOSING_MIN, []),
    ]


def agenda_to_text(doc: AgendaDocument) -> str:
    items = build_agenda_items(doc)
    lines = [
        f"第{doc.meeting_no}回 {doc.committee_name} 開催案内",
        f"{doc.company_name}",
        "",
        "【開催概要】",
        f"日時：{doc.datetime_label}",
        f"場所：{doc.meeting_place}",
        f"出席予定者：{'、'.join(doc.attendees)}",
        f"議題：{doc.theme}",
        "",
        "【議事次第】",
    ]
    for item in items:
        lines.append(f"{item.no}. {item.title}（{item.duration_min}分）")
        lines += [f"　　・{d}" for d in item.details]
    if doc.reference_links:
        lines += ["", "【参考資料】"]
        lines += [f"　・{link['title']}：{link['url']}" for link in doc.reference_links]
    return "\n".join(lines)


def agenda_to_docx_bytes(doc: AgendaDocument) -> bytes:
    if Document is None:
        # python-docx 未インストール時はテキストを返す（拡張子はそのまま.docxとして保存される）
        return agenda_to_text(doc).encode("utf-8")

    items = build_agenda_items(doc)
    document = Document()
    document.add_heading(f"第{doc.meeting_no}回 {doc.committee_name} 開催案内", level=1)
    document.add_paragraph(doc.company_name)

    document.add_heading("開催概要", level=2)
    overview_rows = [
        ("日時", doc.datetime_label),
        ("場所", doc.meeting_place),
        ("出席予定者", "、".join(doc.attendees)),
        ("議題", doc.theme),
    ]
    overview_table = document.add_table(rows=len(overview_rows), cols=2)
    overview_table.style = "Light Grid Accent 1"
    for row, (label, value) in zip(overview_table.rows, overview_rows):
        row.cells[0].text = label
        row.cells[1].text = value

    document.add_heading("議事次第", level=2)
    agenda_table = document.add_table(rows=1, cols=3)
    agenda_table.style = "Light Grid Accent 1"
    header_cells = agenda_table.rows[0].cells
    header_cells[0].text = "項目"
    header_cells[1].text = "内容"
    header_cells[2].text = "時間"
    for item in items:
        cells = agenda_table.add_row().cells
        cells[0].text = f"{item.no}. {item.title}"
        cells[1].text = "\n".join(item.details) if item.details else "－"
        cells[2].text = f"{item.duration_min}分"

    if doc.reference_links:
        document.add_heading("参考資料", level=2)
        for link in doc.reference_links:
            document.add_paragraph(f"{link['title']}：{link['url']}")

    buf = BytesIO()
    document.save(buf)
    return buf.getvalue()
