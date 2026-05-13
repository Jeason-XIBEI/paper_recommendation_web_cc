"""
论文导出服务
支持 JSON / BibTeX / CSV 格式
"""

import json
import csv
import io
from datetime import datetime


def export_json(papers: list) -> str:
    """导出为 JSON 格式"""
    return json.dumps(papers, ensure_ascii=False, indent=2)


def export_csv(papers: list) -> str:
    """导出为 CSV 格式"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["序号", "中文标题", "英文标题", "期刊/会议", "作者", "发表时间", "DOI", "URL", "AI摘要"])

    for i, p in enumerate(papers, 1):
        writer.writerow([
            i,
            p.get("title_cn", ""),
            p.get("title", ""),
            p.get("journal_name", p.get("journal", "")),
            "; ".join(p.get("authors", [])),
            p.get("pub_date", ""),
            p.get("doi", ""),
            p.get("url", ""),
            p.get("summary_cn", ""),
        ])

    return output.getvalue()


def export_bibtex(papers: list) -> str:
    """导出为 BibTeX 格式（用于 Zotero/Mendeley 等引用管理器）"""
    entries = []

    for i, p in enumerate(papers):
        # 生成引用键
        first_author = (p.get("authors", ["Unknown"])[0] if p.get("authors") else "Unknown")
        first_author_key = first_author.split()[-1] if " " in first_author else first_author
        year = p.get("pub_date", "0000")[:4]
        title_words = p.get("title", "paper").split()[:3]
        title_key = "".join(w.capitalize()[:1] for w in title_words)
        cite_key = f"{first_author_key}{year}{title_key}"

        entry_type = "article"
        if p.get("source") == "arxiv":
            entry_type = "misc"

        entry_lines = [f"@{entry_type}{{{cite_key},"]

        # 标题
        title = p.get("title", "").replace("{", "\\{").replace("}", "\\}")
        entry_lines.append(f"  title = {{{title}}},")

        # 作者
        authors = p.get("authors", [])
        if authors:
            author_str = " and ".join(authors)
            entry_lines.append(f"  author = {{{author_str}}},")

        # 期刊
        journal = p.get("journal_name", p.get("journal", ""))
        if journal:
            entry_lines.append(f"  journal = {{{journal}}},")

        # 年份
        if year != "0000":
            entry_lines.append(f"  year = {{{year}}},")
        pub_date = p.get("pub_date", "")
        if pub_date:
            entry_lines.append(f"  date = {{{pub_date}}},")

        # DOI 与 URL
        doi = p.get("doi", "")
        if doi:
            entry_lines.append(f"  doi = {{{doi}}},")
        url = p.get("url", "")
        if url:
            entry_lines.append(f"  url = {{{url}}},")

        # 摘要
        summary = p.get("summary_cn", "")
        if summary:
            summary_clean = summary.replace("{", "\\{").replace("}", "\\}")
            entry_lines.append(f"  abstract = {{{summary_clean}}},")

        # 去尾逗号
        entry_lines[-1] = entry_lines[-1].rstrip(",")

        entry_lines.append("}")
        entries.append("\n".join(entry_lines))


    return "\n\n".join(entries)
