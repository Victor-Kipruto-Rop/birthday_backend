# Render forwards traffic to the port named by $PORT (default 10000) and
# requires the process to listen on 0.0.0.0, not 127.0.0.1.
web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120
