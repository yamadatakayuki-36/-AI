"""アジェンダ（次第）の組み立てとファイル出力（テキスト／Word）。"""

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


def agenda_to_text(doc: AgendaDocument) -> str:
    lines = [
        f"第{doc.meeting_no}回 {doc.committee_name}",
        f"{doc.company_name}",
        f"日時：{doc.datetime_label}",
        f"場所：{doc.meeting_place}",
        f"出席予定者：{'、'.join(doc.attendees)}",
        "",
        f"議題：{doc.theme}",
        "",
        "討議ポイント：",
    ]
    lines += [f"　・{p}" for p in doc.theme_points]
    lines += ["", f"担当：{doc.action_owner}　期限：{doc.due_label}"]
    if doc.reference_links:
        lines += ["", "参考資料："]
        lines += [f"　・{link['title']}：{link['url']}" for link in doc.reference_links]
    return "\n".join(lines)


def agenda_to_docx_bytes(doc: AgendaDocument) -> bytes:
    if Document is None:
        # python-docx 未インストール時はテキストを返す（拡張子はそのまま.docxとして保存される）
        return agenda_to_text(doc).encode("utf-8")
    document = Document()
    document.add_heading(f"第{doc.meeting_no}回 {doc.committee_name}", level=1)
    document.add_paragraph(doc.company_name)
    document.add_paragraph(f"日時：{doc.datetime_label}")
    document.add_paragraph(f"場所：{doc.meeting_place}")
    document.add_paragraph(f"出席予定者：{'、'.join(doc.attendees)}")
    document.add_heading(f"議題：{doc.theme}", level=2)
    document.add_heading("討議ポイント", level=3)
    for point in doc.theme_points:
        document.add_paragraph(point, style="List Bullet")
    document.add_paragraph(f"担当：{doc.action_owner}　期限：{doc.due_label}")
    if doc.reference_links:
        document.add_heading("参考資料", level=3)
        for link in doc.reference_links:
            document.add_paragraph(f"{link['title']}：{link['url']}")
    buf = BytesIO()
    document.save(buf)
    return buf.getvalue()
