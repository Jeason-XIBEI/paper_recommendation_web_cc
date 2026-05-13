"""
邮件配置
"""

import os
from dotenv import load_dotenv

load_dotenv()

EMAIL_CONFIG = {
    "smtp_server": os.getenv("EMAIL_SMTP_SERVER", "smtp.qq.com"),
    "smtp_port": int(os.getenv("EMAIL_SMTP_PORT", 587)),
    "sender_email": os.getenv("EMAIL_SENDER", ""),
    "sender_password": os.getenv("EMAIL_PASSWORD", ""),
}