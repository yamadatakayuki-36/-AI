"""アジェンダからのスライド（.pptx）生成。"""

from __future__ import annotations

from io import BytesIO

from agenda_generator import AgendaDocument, agenda_to_text, build_agenda_items

try:
    from pptx import Presentation
except ImportError:  # python-pptx 未インストール時のフォールバック
    Presentation = None


def agenda_to_pptx_bytes(doc: AgendaDocument) -> bytes:
    if Presentation is None:
        # python-pptx 未インストール時はテキストを返す（拡張子はそのまま.pptxとして保存される）
        return agenda_to_text(doc).encode("utf-8")

    items = build_agenda_items(doc)
    prs = Presentation()

    title_slide = prs.slides.add_slide(prs.slide_layouts[0])
    title_slide.shapes.title.text = f"第{doc.meeting_no}回 {doc.committee_name}"
    title_slide.placeholders[1].text = f"{doc.company_name}\n{doc.datetime_label}"

    agenda_slide = prs.slides.add_slide(prs.slide_layouts[1])
    agenda_slide.shapes.title.text = "本日の流れ"
    agenda_body = agenda_slide.placeholders[1].text_frame
    agenda_body.text = f"{items[0].no}. {items[0].title}（{items[0].duration_min}分）"
    for item in items[1:]:
        p = agenda_body.add_paragraph()
        p.text = f"{item.no}. {item.title}（{item.duration_min}分）"

    theme_slide = prs.slides.add_slide(prs.slide_layouts[1])
    theme_slide.shapes.title.text = f"議題：{doc.theme}"
    body = theme_slide.placeholders[1].text_frame
    body.text = doc.theme_points[0] if doc.theme_points else ""
    for point in doc.theme_points[1:]:
        p = body.add_paragraph()
        p.text = point

    action_slide = prs.slides.add_slide(prs.slide_layouts[1])
    action_slide.shapes.title.text = "アクション"
    action_body = action_slide.placeholders[1].text_frame
    action_body.text = f"担当：{doc.action_owner}"
    p = action_body.add_paragraph()
    p.text = f"期限：{doc.due_label}"

    buf = BytesIO()
    prs.save(buf)
    return buf.getvalue()
