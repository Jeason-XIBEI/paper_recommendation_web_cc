"""数据库模型"""

import uuid
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class SearchTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_name = db.Column(db.String(200), default="未命名任务")
    keywords = db.Column(db.String(500))
    days_back = db.Column(db.Integer, default=30)
    email = db.Column(db.String(200))
    temperature = db.Column(db.Float, default=0.3)
    status = db.Column(db.String(50), default='pending')
    progress = db.Column(db.Integer, default=0)
    result_file = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.now)
    completed_at = db.Column(db.DateTime)
    paper_count = db.Column(db.Integer, default=0)
    selected_journals = db.Column(db.Text, default='')


class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    email = db.Column(db.String(200))
    keywords = db.Column(db.String(500))
    days_back = db.Column(db.Integer, default=30)
    frequency = db.Column(db.String(50), default='weekly')
    is_active = db.Column(db.Boolean, default=True)
    unsubscribe_token = db.Column(db.String(64), unique=True, default=lambda ctx: str(uuid.uuid4()))
    last_run = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)
