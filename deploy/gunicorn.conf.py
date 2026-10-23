import multiprocessing

bind = "unix:/run/crm-tabere/gunicorn.sock"
# Socket readable by group www-data (nginx), nobody else.
umask = 0o007
workers = multiprocessing.cpu_count() * 2 + 1
timeout = 30
accesslog = "-"
errorlog = "-"
