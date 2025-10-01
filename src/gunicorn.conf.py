bind = "0.0.0.0:8000"
workers = 2
worker_class = "sync"
worker_connections = 1000
timeout = 300
graceful_timeout = 300
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
preload_app = True

# Логирование
accesslog = "-"
errorlog = "-"
loglevel = "info"