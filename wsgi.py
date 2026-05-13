"""
WSGI 入口文件
用于生产环境部署
"""
from web_app import app

if __name__ == "__main__":
    app.run()