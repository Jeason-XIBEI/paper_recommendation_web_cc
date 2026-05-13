"""
论文推荐系统 - 开发入口
使用 Flask 应用工厂模式
"""

import socket
from app import create_app

app = create_app()

if __name__ == '__main__':
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "127.0.0.1"

    print("=" * 50)
    print("论文推荐系统启动中...")
    print(f"本机访问: http://localhost:8093")
    print(f"内网访问: http://{local_ip}:8093")
    print("✅ 数据源: 期刊 + arXiv + 会议论文")
    print("✅ 导出格式: JSON / BibTeX / CSV")
    print("✅ SSE 实时进度推送已启用")
    print("=" * 50)

    app.run(debug=False, host='0.0.0.0', port=8093)
