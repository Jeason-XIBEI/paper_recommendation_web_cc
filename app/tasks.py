"""后台任务队列与论文搜索"""

import json
import os
import time as time_module
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from app.models import db, SearchTask

logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor(max_workers=5)
_api_cache = {}
CACHE_TTL = 3600


def recover_stuck_tasks(app):
    """恢复上次运行中被中断的任务"""
    with app.app_context():
        stuck = SearchTask.query.filter_by(status='running').all()
        if stuck:
            logger.info(f"发现 {len(stuck)} 个中断任务，重置为 pending")
            for task in stuck:
                task.status = 'pending'
                task.progress = 0
            db.session.commit()


def get_cached_or_fetch(crossref, issn, journal_name, days_back, max_results=10):
    cache_key = (issn, days_back)
    if cache_key in _api_cache:
        ts, papers = _api_cache[cache_key]
        if time_module.time() - ts < CACHE_TTL:
            return list(papers)
    papers = crossref.get_recent_papers(issn, journal_name, days_back=days_back, max_results=max_results)
    _api_cache[cache_key] = (time_module.time(), list(papers))
    return papers


def push_event(task_id, msg):
    from app.sse import push_task_event
    push_task_event(task_id, msg)


def run_search_task(app, task_id, selected_journals=None):
    """后台论文搜索任务"""
    with app.app_context():
        task = None
        relevant_papers = []

        try:
            task = db.session.get(SearchTask, task_id)
            if not task:
                return

            task.status = 'running'
            db.session.commit()
            push_event(task_id, {'type': 'status', 'status': 'running', 'message': '开始搜索...'})

            # 动态导入（避免循环依赖）
            from src.crossref_client import CrossrefClient
            from src.llm_client import GLMClient
            from src.arxiv_client import ArxivClient
            from config.settings import (
                ZHIPU_API_KEY, ZHIPU_API_URL, JOURNALS, ARXIV_CATEGORIES, CONFERENCES
            )

            crossref = CrossrefClient()
            llm = GLMClient(ZHIPU_API_KEY, ZHIPU_API_URL)
            arxiv = ArxivClient()

            journal_list = []
            arxiv_cats = []
            conf_list = []

            if selected_journals and len(selected_journals) > 0:
                for name in selected_journals:
                    if name in JOURNALS:
                        journal_list.append((name, JOURNALS[name]))
                    elif name in ARXIV_CATEGORIES:
                        arxiv_cats.append(ARXIV_CATEGORIES[name])
                    elif name in CONFERENCES:
                        conf_list.append((name, CONFERENCES[name]))
            else:
                journal_list = list(JOURNALS.items())

            all_papers = []
            total_journals = len(journal_list)
            completed = 0
            days = min(task.days_back, 30)

            # 并行获取期刊
            with ThreadPoolExecutor(max_workers=5) as fetch_executor:
                future_to_journal = {
                    fetch_executor.submit(get_cached_or_fetch, crossref, issn, name, days): name
                    for name, issn in journal_list
                }

                for future in as_completed(future_to_journal):
                    completed += 1
                    task.progress = int((completed / max(total_journals, 1)) * 50)
                    db.session.commit()
                    push_event(task_id, {
                        'type': 'progress', 'stage': 'fetch',
                        'progress': task.progress,
                        'message': f'获取期刊 ({completed}/{total_journals})'
                    })

                    journal_name = future_to_journal[future]
                    try:
                        papers = future.result()
                        if papers:
                            all_papers.extend(papers)
                    except Exception as e:
                        logger.warning(f"获取 {journal_name} 异常: {e}")

            # arXiv
            if arxiv_cats:
                try:
                    arxiv_papers = arxiv.search(arxiv_cats, days_back=days, max_results=20)
                    all_papers.extend(arxiv_papers)
                    logger.info(f"arXiv 获取 {len(arxiv_papers)} 篇")
                except Exception as e:
                    logger.warning(f"arXiv 异常: {e}")

            # 会议
            for conf_name, conf_info in conf_list:
                try:
                    conf_papers = crossref.get_recent_papers(
                        conf_info["prefix"], conf_name, days_back=365, max_results=10
                    )
                    all_papers.extend(conf_papers)
                except Exception as e:
                    logger.warning(f"会议 {conf_name} 异常: {e}")

            logger.info(f"共获取 {len(all_papers)} 篇论文，开始AI筛选")
            push_event(task_id, {
                'type': 'progress', 'stage': 'screen', 'progress': 50,
                'message': f'AI筛选中 ({len(all_papers)} 篇)'
            })

            # LLM 筛选去重
            seen_dois = set()
            for idx, paper in enumerate(all_papers):
                task.progress = 50 + int((idx / max(len(all_papers), 1)) * 50)
                push_event(task_id, {
                    'type': 'progress', 'stage': 'screen',
                    'progress': task.progress,
                    'message': f'AI筛选中 ({idx + 1}/{len(all_papers)})'
                })
                if idx % 5 == 0:
                    db.session.commit()

                doi = paper.get('doi', '')
                if doi and doi in seen_dois:
                    continue
                if doi:
                    seen_dois.add(doi)

                try:
                    result = llm.filter_paper_with_temp(
                        paper['title'], paper['abstract'],
                        task.keywords, task.temperature
                    )
                    if result.get('is_relevant', False):
                        paper['filter_reason'] = result.get('reason', '')
                        paper['summary_cn'] = llm.summarize_paper(paper['title'], paper['abstract'])
                        paper['title_cn'] = llm.translate_title(paper['title'])
                        relevant_papers.append(paper)
                except Exception as e:
                    logger.warning(f"筛选失败: {e}")

            # 保存结果
            os.makedirs("data", exist_ok=True)
            result_file = f"data/result_{task_id}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(relevant_papers, f, ensure_ascii=False, indent=2)

            task.status = 'completed'
            task.progress = 100
            task.result_file = result_file
            task.paper_count = len(relevant_papers)
            task.completed_at = datetime.now()
            db.session.commit()

            logger.info(f"任务 {task_id} 完成！{len(relevant_papers)} 篇")
            push_event(task_id, {
                'type': 'done', 'status': 'completed',
                'paper_count': len(relevant_papers),
                'message': f'完成！找到 {len(relevant_papers)} 篇相关论文'
            })

            # 发送邮件
            if task.email and task.email.strip() and relevant_papers:
                try:
                    from src.email_sender import EmailSender
                    from config.email_config import EMAIL_CONFIG
                    email_sender = EmailSender(
                        smtp_server=EMAIL_CONFIG["smtp_server"],
                        smtp_port=EMAIL_CONFIG["smtp_port"],
                        sender_email=EMAIL_CONFIG["sender_email"],
                        sender_password=EMAIL_CONFIG["sender_password"]
                    )
                    email_sender.send_paper_report(
                        to_email=task.email,
                        task_name=task.task_name,
                        keywords=task.keywords,
                        papers=relevant_papers
                    )
                except Exception as e:
                    logger.warning(f"邮件发送失败: {e}")

        except Exception as e:
            logger.error(f"任务 {task_id} 失败: {e}", exc_info=True)
            push_event(task_id, {
                'type': 'error', 'status': 'failed',
                'message': f'任务失败: {str(e)}'
            })
            try:
                if task:
                    task.status = 'failed'
                    db.session.commit()
            except Exception:
                pass
