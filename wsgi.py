"""
WSGI 入口文件
用于生产环境部署 (gunicorn wsgi:app)
本地开发请运行: python web_app.py
"""
from web_app import app

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=8093)