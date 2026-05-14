"""
订阅邮件定时推送脚本
用法: python send_subscription_emails.py
配置 cron 定时执行即可，脚本内部会根据 frequency 和 last_run 判断是否推送

示例 crontab（每天早上8点检查）:
  0 8 * * * cd /opt/paper_recommendation_web_cc && python3 send_subscription_emails.py >> logs/subscription.log 2>&1
"""

import os
import sys
import logging
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, Subscription
from src.crossref_client import CrossrefClient
from src.llm_client import GLMClient
from src.email_sender import EmailSender
from config.settings import ZHIPU_API_KEY, ZHIPU_API_URL, JOURNALS, ARXIV_CATEGORIES, CONFERENCES
from config.email_config import EMAIL_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

SERVER_HOST = os.environ.get("SERVER_HOST", "http://192.168.0.189:8093")


def should_run(sub):
    """根据订阅频率和上次运行时间判断是否需要执行"""
    if sub.last_run is None:
        return True
    now = datetime.now()
    delta = now - sub.last_run
    if sub.frequency == 'daily' and delta >= timedelta(days=1):
        return True
    if sub.frequency == 'weekly' and delta >= timedelta(days=7):
        return True
    if sub.frequency == 'monthly' and delta >= timedelta(days=28):
        return True
    return False


def main():
    app = create_app()

    with app.app_context():
        subs = Subscription.query.filter_by(is_active=True).all()
        if not subs:
            logger.info("没有活跃订阅，跳过")
            return

        # 筛选需要本轮的订阅
        due_subs = [s for s in subs if should_run(s)]
        if not due_subs:
            logger.info(f"共 {len(subs)} 个活跃订阅，均未到推送时间，跳过")
            return

        logger.info(f"开始处理 {len(due_subs)} 个到期订阅")

        crossref = CrossrefClient()
        llm = GLMClient(ZHIPU_API_KEY, ZHIPU_API_URL)
        sender = EmailSender(
            smtp_server=EMAIL_CONFIG["smtp_server"],
            smtp_port=EMAIL_CONFIG["smtp_port"],
            sender_email=EMAIL_CONFIG["sender_email"],
            sender_password=EMAIL_CONFIG["sender_password"]
        )

        for sub in due_subs:
            logger.info(f"处理订阅 ID={sub.id} email={sub.email} keywords={sub.keywords[:50]}")

            try:
                # 搜索所有期刊
                all_papers = []
                journal_list = list(JOURNALS.items())
                days = min(sub.days_back, 30)

                for name, issn in journal_list:
                    try:
                        papers = crossref.get_recent_papers(issn, name, days_back=days, max_results=5)
                        if papers:
                            all_papers.extend(papers)
                    except Exception as e:
                        logger.warning(f"获取 {name} 失败: {e}")

                logger.info(f"订阅 {sub.id}: 获取 {len(all_papers)} 篇论文，开始AI筛选")

                # AI 筛选与去重
                relevant_papers = []
                seen_dois = set()

                for paper in all_papers:
                    doi = paper.get('doi', '')
                    if doi and doi in seen_dois:
                        continue
                    if doi:
                        seen_dois.add(doi)

                    try:
                        result = llm.filter_paper_with_temp(
                            paper['title'], paper.get('abstract', ''),
                            sub.keywords, temperature=0.3
                        )
                        if result.get('is_relevant', False):
                            paper['filter_reason'] = result.get('reason', '')
                            paper['summary_cn'] = llm.summarize_paper(
                                paper['title'], paper.get('abstract', '')
                            )
                            paper['title_cn'] = llm.translate_title(paper['title'])
                            relevant_papers.append(paper)
                    except Exception as e:
                        logger.warning(f"筛选失败: {e}")

                logger.info(f"订阅 {sub.id}: {len(relevant_papers)} 篇相关论文")

                # 发送邮件
                unsub_url = f"{SERVER_HOST}/unsubscribe/{sub.unsubscribe_token}"
                manage_url = f"{SERVER_HOST}/manage/{sub.unsubscribe_token}"

                if relevant_papers:
                    sender.send_paper_report(
                        to_email=sub.email,
                        task_name=f"{sub.frequency}订阅: {sub.keywords[:30]}",
                        keywords=sub.keywords,
                        papers=relevant_papers,
                        unsubscribe_url=unsub_url,
                        manage_url=manage_url
                    )
                else:
                    # 没有相关论文也发通知
                    sender.send_paper_report(
                        to_email=sub.email,
                        task_name=f"{sub.frequency}订阅: {sub.keywords[:30]}",
                        keywords=sub.keywords,
                        papers=[],
                        unsubscribe_url=unsub_url,
                        manage_url=manage_url
                    )

                # 更新最后执行时间
                sub.last_run = datetime.now()
                db.session.commit()
                logger.info(f"订阅 {sub.id} 处理完成，邮件已发送")

            except Exception as e:
                logger.error(f"订阅 {sub.id} 处理失败: {e}", exc_info=True)
                db.session.rollback()

        logger.info("所有到期订阅处理完毕")


if __name__ == '__main__':
    main()
