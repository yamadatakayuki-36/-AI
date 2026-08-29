"""Copilot 365向けプロンプト生成と、テーマ履歴のExcelエクスポート。"""

from __future__ import annotations

from io import BytesIO

from data_loader import load_theme_history


def build_copilot_prompt(year_month: str) -> str:
    return (
        f"あなたは安全衛生委員会の事務局担当です。添付のExcel（テーマ履歴）を参照し、"
        f"{year_month}の委員会で扱うのに適した安全衛生テーマを3つ、"
        "理由付きで日本語で提案してください。過去に使用済みのテーマは避けてください。"
    )


def theme_history_to_excel_bytes() -> bytes:
    df = load_theme_history()
    buf = BytesIO()
    df.to_excel(buf, index=False, sheet_name="theme_history")
    return buf.getvalue()
