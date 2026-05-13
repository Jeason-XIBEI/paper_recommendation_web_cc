"""
Crossref API 客户端
用于获取学术论文元数据
"""

import requests
from datetime import datetime, timedelta
import time
import re
from typing import List, Dict, Optional


class CrossrefClient:
    """Crossref API 客户端"""
    
    def __init__(self, user_agent: str = "PaperRecommendationAgent/1.0 (mailto:your-email@example.com)"):
        """
        初始化Crossref客户端
        
        Args:
            user_agent: 请求头中的User-Agent，建议包含邮箱（礼貌模式）
        """
        self.base_url = "https://api.crossref.org"
        self.headers = {
            "User-Agent": user_agent
        }
        self.last_request_time = 0  # 用于请求频率控制
    
    def _rate_limit(self):
        """控制请求频率，避免触发限流"""
        now = time.time()
        if now - self.last_request_time < 0.5:  # 每秒最多2个请求
            time.sleep(0.5 - (now - self.last_request_time))
        self.last_request_time = time.time()
    
    def get_recent_papers(self, identifier: str, source_name: str, days_back: int = 7, max_results: int = 10) -> List[Dict]:
        """
        获取论文（自动识别ISSN或Prefix）
        
        Args:
            identifier: ISSN号 或 DOI前缀（如10.1109）
            source_name: 期刊或会议名称
            days_back: 获取最近多少天的论文
            max_results: 最多返回多少篇
            
        Returns:
            论文元数据列表
        """
        self._rate_limit()
        
        # 确保参数是整数类型
        days_back = int(days_back)
        max_results = int(max_results)
        
        # 计算起始日期
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        # 判断是Prefix还是ISSN
        if identifier.startswith('10.'):
            # 是Prefix（DOI前缀），获取会议论文
            url = f"{self.base_url}/prefixes/{identifier}/works"
            params = {
                "filter": f"from-pub-date:{from_date},type:proceedings-article",
                "rows": max_results,
                "sort": "published-online",
                "order": "desc"
            }
        else:
            # 是ISSN，获取期刊论文
            url = f"{self.base_url}/journals/{identifier}/works"
            params = {
                "filter": f"from-pub-date:{from_date}",
                "rows": max_results,
                "sort": "published-online",
                "order": "desc"
            }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            papers = []
            for item in data.get("message", {}).get("items", []):
                paper = self._parse_paper(item)
                if paper:
                    paper['journal_name'] = source_name
                    papers.append(paper)
            
            print(f"✅ 成功获取 {source_name}: {len(papers)} 篇论文")
            return papers
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 获取 {source_name} 失败: {e}")
            return []
    
    def _parse_paper(self, item: Dict) -> Optional[Dict]:
        """
        解析单篇论文的元数据
        
        Args:
            item: Crossref API返回的单篇论文数据
            
        Returns:
            格式化后的论文信息
        """
        try:
            # 提取DOI
            doi = item.get("DOI", "")
            if not doi:
                return None
            
            # 提取标题
            title = item.get("title", [""])[0] if item.get("title") else ""
            if not title:
                return None
            
            # 提取摘要（可能不存在）
            abstract = item.get("abstract", "")
            # 清理HTML标签
            if abstract:
                abstract = re.sub(r'<.*?>', '', abstract)
            
            # 提取作者
            authors = []
            for author in item.get("author", []):
                given = author.get("given", "")
                family = author.get("family", "")
                if given or family:
                    authors.append(f"{given} {family}".strip())
            
            # 提取发表日期
            pub_date = item.get("published-print", {}).get("date-parts", [[]])[0]
            if not pub_date:
                pub_date = item.get("published-online", {}).get("date-parts", [[]])[0]
            pub_date_str = "-".join(map(str, pub_date)) if pub_date else ""
            
            # 提取期刊名称
            journal = item.get("container-title", [""])[0] if item.get("container-title") else ""
            
            return {
                "doi": doi,
                "title": title,
                "abstract": abstract,
                "authors": authors,
                "pub_date": pub_date_str,
                "journal": journal,
                "url": f"https://doi.org/{doi}"
            }
            
        except Exception as e:
            print(f"⚠️ 解析论文失败: {e}")
            return None
    
    def get_paper_by_doi(self, doi: str) -> Optional[Dict]:
        """
        通过DOI获取单篇论文的详细信息
        
        Args:
            doi: 论文DOI
            
        Returns:
            论文元数据
        """
        self._rate_limit()
        
        url = f"{self.base_url}/works/{doi}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            return self._parse_paper(data.get("message", {}))
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 获取论文 {doi} 失败: {e}")
            return None


# 测试代码
if __name__ == "__main__":
    client = CrossrefClient()
    
    # 测试获取期刊
    print("=" * 40)
    print("测试获取期刊论文")
    print("=" * 40)
    papers = client.get_recent_papers("0028-0836", "Nature", days_back=7, max_results=3)
    
    for i, paper in enumerate(papers, 1):
        print(f"\n--- 论文 {i} ---")
        print(f"标题: {paper['title']}")
        print(f"DOI: {paper['doi']}")
        print(f"作者: {', '.join(paper['authors'][:3])}")
        print(f"发表日期: {paper['pub_date']}")
    
    # 测试获取会议（Prefix）
    print("\n" + "=" * 40)
    print("测试获取会议论文")
    print("=" * 40)
    conf_papers = client.get_recent_papers("10.1109", "IEEE_CVPR", days_back=365, max_results=5)
    
    for i, paper in enumerate(conf_papers, 1):
        print(f"\n--- 会议论文 {i} ---")
        print(f"标题: {paper['title']}")
        print(f"DOI: {paper['doi']}")