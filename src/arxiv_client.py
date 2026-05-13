"""
arXiv API 客户端
获取 cs.AI / cs.CV / cs.CL 等领域预印本
"""

import requests
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class ArxivClient:
    """arXiv API 客户端"""

    BASE_URL = "http://export.arxiv.org/api/query"

    def __init__(self):
        self.headers = {"User-Agent": "PaperRecommendationAgent/1.0"}

    def _build_query(self, categories: List[str], days_back: int, max_results: int = 10) -> str:
        cat_query = " OR ".join(f"cat:{c}" for c in categories)
        # arXiv API: "submittedDate" filter not supported for exact days,
        # so we use sortBy=submittedDate and order descending
        params = {
            "search_query": cat_query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": str(max_results),
        }
        return "&".join(f"{k}={urllib.parse.quote_plus(v)}" for k, v in params.items())

    def search(self, categories: List[str], days_back: int = 30, max_results: int = 10) -> List[Dict]:
        url = f"{self.BASE_URL}?{self._build_query(categories, days_back, max_results)}"

        try:
            resp = requests.get(url, headers=self.headers, timeout=30)
            resp.raise_for_status()
            return self._parse_response(resp.text, days_back)
        except requests.exceptions.RequestException as e:
            print(f"arXiv API 请求失败: {e}")
            return []

    def _parse_response(self, xml_text: str, days_back: int) -> List[Dict]:
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }
        ET.register_namespace("", ns["atom"])

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        papers = []
        cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_back)

        for entry in root.findall("atom:entry", ns):
            try:
                title_el = entry.find("atom:title", ns)
                title = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else ""

                summary_el = entry.find("atom:summary", ns)
                abstract = summary_el.text.strip().replace("\n", " ") if summary_el is not None and summary_el.text else ""

                # Parse published date
                pub_el = entry.find("atom:published", ns)
                if pub_el is not None and pub_el.text:
                    pub_date = pub_el.text[:10]  # yyyy-mm-dd
                else:
                    pub_date = ""

                authors = []
                for auth_el in entry.findall("atom:author", ns):
                    name_el = auth_el.find("atom:name", ns)
                    if name_el is not None and name_el.text:
                        authors.append(name_el.text)

                # Extract arxiv ID from the <id> element
                id_el = entry.find("atom:id", ns)
                arxiv_id = ""
                if id_el is not None and id_el.text:
                    # e.g. http://arxiv.org/abs/2501.12345v1
                    parts = id_el.text.split("/abs/")
                    if len(parts) > 1:
                        arxiv_id = parts[1]

                # Category
                cats = []
                for cat_el in entry.findall("arxiv:primary_category", ns):
                    term = cat_el.get("term", "")
                    if term:
                        cats.append(term)

                papers.append({
                    "doi": f"arxiv:{arxiv_id}",
                    "title": title,
                    "abstract": abstract,
                    "authors": authors,
                    "pub_date": pub_date,
                    "journal": f"arXiv ({', '.join(cats)})",
                    "url": f"https://arxiv.org/abs/{arxiv_id}",
                    "source": "arxiv",
                })

            except Exception as e:
                print(f"arXiv 解析条目失败: {e}")
                continue

        print(f"arXiv: 获取 {len(papers)} 篇预印本")
        return papers


# 测试
if __name__ == "__main__":
    client = ArxivClient()
    papers = client.search(["cs.AI", "cs.CV", "cs.CL"], days_back=7, max_results=5)
    for i, p in enumerate(papers, 1):
        print(f"\n--- {i} ---")
        print(f"Title: {p['title']}")
        print(f"Authors: {', '.join(p['authors'][:3])}")
        print(f"URL: {p['url']}")
