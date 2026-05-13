"""
发送一封带退订链接的测试邮件到指定邮箱
运行: python tests/test_send_unsubscribe_email.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, Subscription
from src.email_sender import EmailSender
from config.email_config import EMAIL_CONFIG

# 目标邮箱和服务器地址
TO_EMAIL = "jiazhihao0111@163.com"
SERVER_HOST = os.environ.get("SERVER_HOST", "http://192.168.0.189:8092")

app = create_app()

with app.app_context():
    # 创建测试订阅
    sub = Subscription(
        email=TO_EMAIL,
        keywords="traffic flow prediction, GNN",
        username="Test",
        days_back=30,
        frequency="weekly"
    )
    db.session.add(sub)
    db.session.commit()

    manage_url = f"{SERVER_HOST}/manage/{sub.unsubscribe_token}"
    unsub_url = f"{SERVER_HOST}/unsubscribe/{sub.unsubscribe_token}"

    print(f"订阅 ID: {sub.id}")
    print(f"Token: {sub.unsubscribe_token}")
    print(f"管理链接: {manage_url}")
    print(f"退订链接: {unsub_url}")

    # 发送测试邮件
    sender = EmailSender(
        smtp_server=EMAIL_CONFIG["smtp_server"],
        smtp_port=EMAIL_CONFIG["smtp_port"],
        sender_email=EMAIL_CONFIG["sender_email"],
        sender_password=EMAIL_CONFIG["sender_password"]
    )

    test_papers = [{
        "title": "A Novel GNN-based Traffic Flow Prediction Model",
        "title_cn": "基于图神经网络的新型交通流预测模型",
        "journal_name": "IEEE T-ITS",
        "authors": ["Zhang, Wei", "Li, Ming"],
        "pub_date": "2026-03-15",
        "doi": "10.1109/example.2026.1234567",
        "url": "https://doi.org/10.1109/example.2026.1234567",
        "filter_reason": "高度相关：GNN + 交通流预测",
        "summary_cn": "该论文提出了一个融合时空注意力的图神经网络模型用于交通流预测。"
    }]

    success = sender.send_paper_report(
        to_email=TO_EMAIL,
        task_name="退订功能测试",
        keywords="traffic flow prediction, GNN",
        papers=test_papers,
        unsubscribe_url=unsub_url,
        manage_url=manage_url
    )

    if success:
        print(f"\n邮件已发送至 {TO_EMAIL}")
        print("请检查收件箱（含垃圾邮件箱），点击邮件底部的「取消订阅」或「管理订阅」链接验证。")
        print(f"订阅记录已保留 (ID={sub.id})，验证完成后可手动清理。")
    else:
        print(f"\n邮件发送失败，请检查 .env 中的 EMAIL_SENDER / EMAIL_PASSWORD 配置。")
        db.session.delete(sub)
        db.session.commit()
