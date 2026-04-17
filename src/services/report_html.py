"""報告 HTML 列印樣板 — 將 Markdown 轉為可列印 HTML。

提供 `render_report_html()` 將報告內容包裝為含列印樣式的 HTML，
瀏覽器載入後可自動觸發列印對話框，使用者選擇「另存為 PDF」即可。
此方案不依賴任何 Python PDF 套件，保持系統輕量。
"""

from __future__ import annotations

import re
from html import escape


def _md_to_html(md: str) -> str:
    """極簡 Markdown → HTML 轉換（標題、表格、列表、粗體、分隔線）。"""
    out: list[str] = []
    in_table = False
    for raw in md.split("\n"):
        line = raw.rstrip()
        if line.startswith("### "):
            out.append(f"<h3>{escape(line[4:])}</h3>")
            continue
        if line.startswith("## "):
            out.append(f"<h2>{escape(line[3:])}</h2>")
            continue
        if line.startswith("# "):
            out.append(f"<h1>{escape(line[2:])}</h1>")
            continue
        if re.match(r"^\|.+\|$", line):
            if not in_table:
                out.append('<table class="rpt-table">')
                in_table = True
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if all(re.fullmatch(r"-+", c) for c in cells):
                continue
            cols = "".join(f"<td>{escape(c)}</td>" for c in cells)
            out.append(f"<tr>{cols}</tr>")
            continue
        if in_table:
            out.append("</table>")
            in_table = False
        if line.strip() == "":
            out.append("<br/>")
        elif line.strip() == "---":
            out.append("<hr/>")
        else:
            bolded = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escape(line))
            if line.startswith("- "):
                out.append(f"<li>{bolded[2:]}</li>")
            else:
                out.append(f"<p>{bolded}</p>")
    if in_table:
        out.append("</table>")
    return "\n".join(out)


_CSS = """
body { font-family: 'Helvetica Neue', 'PingFang TC', 'Microsoft JhengHei', sans-serif;
       line-height: 1.6; color: #222; max-width: 900px; margin: 2rem auto; padding: 0 1.5rem; }
h1 { border-bottom: 3px solid #1a5276; padding-bottom: 0.3rem; color: #1a5276; }
h2 { border-left: 4px solid #2e86c1; padding-left: 0.6rem; color: #2e86c1; margin-top: 1.5rem; }
h3 { color: #1a5276; }
.rpt-table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 0.9rem; }
.rpt-table td { border: 1px solid #ddd; padding: 6px 10px; }
.rpt-table tr:first-child td { background: #2e86c1; color: white; font-weight: 600; }
.rpt-table tr:nth-child(even) { background: #f8f9fa; }
hr { border: 0; border-top: 2px solid #ecf0f1; margin: 1.5rem 0; }
strong { color: #1a5276; }
li { margin: 0.3rem 0; }
@media print { body { margin: 0; max-width: 100%; } .no-print { display: none; } }
"""


def render_report_html(title: str, markdown: str, auto_print: bool = False) -> str:
    """將 Markdown 包裝為可列印 HTML。

    Args:
        title: 報告標題，用作 HTML <title>。
        markdown: 原始 Markdown 內容。
        auto_print: 若為 True，頁面載入後自動呼叫 window.print()。
    """
    body = _md_to_html(markdown)
    auto_js = "<script>window.addEventListener('load', () => setTimeout(() => window.print(), 300));</script>" if auto_print else ""
    return (
        "<!DOCTYPE html><html lang=\"zh-TW\"><head>"
        f"<meta charset=\"utf-8\"><title>{escape(title)}</title>"
        f"<style>{_CSS}</style></head><body>"
        f"{body}{auto_js}</body></html>"
    )
