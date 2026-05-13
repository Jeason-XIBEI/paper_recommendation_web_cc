"""Flask 应用工厂"""

import os
import logging
import sys

from flask import Flask

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import db
from app.tasks import recover_stuck_tasks


def create_app(testing=False):
    app = Flask(__name__, template_folder='../templates')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///papers.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your-secret-key-here'

    db.init_app(app)

    os.makedirs("data", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # 日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler('logs/app.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    # 注册路由
    from app.routes.main import main_bp
    from app.routes.api import api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    # 数据库初始化
    with app.app_context():
        db.create_all()

        # 数据库迁移
        try:
            db.session.execute(db.text(
                "ALTER TABLE search_task ADD COLUMN selected_journals TEXT DEFAULT ''"
            ))
            db.session.commit()
        except Exception:
            pass  # 列已存在

        try:
            db.session.execute(db.text(
                "ALTER TABLE subscription ADD COLUMN unsubscribe_token TEXT DEFAULT ''"
            ))
            db.session.commit()
        except Exception:
            pass  # 列已存在

        # 为已有订阅补填 token
        try:
            rows = db.session.execute(db.text(
                "SELECT id FROM subscription WHERE unsubscribe_token IS NULL OR unsubscribe_token = ''"
            )).fetchall()
            for (sid,) in rows:
                import uuid
                db.session.execute(db.text(
                    "UPDATE subscription SET unsubscribe_token = :tok WHERE id = :sid"
                ), {"tok": str(uuid.uuid4()), "sid": sid})
            db.session.commit()
        except Exception:
            pass

        recover_stuck_tasks(app)

    return app
