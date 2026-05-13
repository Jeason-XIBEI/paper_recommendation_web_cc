"""
Gunicorn 生产环境配置
"""

# 绑定地址和端口
bind = "0.0.0.0:8092"

# Worker 数量（CPU核心数 * 2 + 1）
workers = 3

# Worker 类型
worker_class = "sync"

# 超时时间（论文搜索可能较慢，设置为5分钟）
timeout = 600

# 保持连接
keepalive = 5

# 日志配置
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"

# 防止内存泄漏，每个worker处理1000个请求后重启
max_requests = 1000
max_requests_jitter = 50
