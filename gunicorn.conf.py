# Gunicorn configuration file
import multiprocessing

# Server socket
bind = '0.0.0.0:8080'
backlog = 2048

# Worker processes - using fewer workers to reduce session synchronization issues
workers = 2  # Reduced from multiprocessing.cpu_count() * 2 + 1
worker_class = 'uvicorn.workers.UvicornWorker'
worker_connections = 1000
timeout = 300
keepalive = 2

# Process naming
proc_name = 'aibox'

# Logging
errorlog = 'logs/gunicorn.log'
loglevel = 'debug'  # Changed to debug for more detailed logging
capture_output = True
enable_stdio_inheritance = True

# Worker settings
max_requests = 1000
max_requests_jitter = 50
graceful_timeout = 120

# SSL
# keyfile = 'ssl/key.pem'
# certfile = 'ssl/cert.pem'
