chmod +x start.sh
#!/bin/bash
# Iniciar bot de Telegram en segundo plano
python3 -m main &
# Iniciar Gunicorn para Flask
gunicorn --worker-tmp-dir /dev/shm --workers 4 --timeout 120 --bind 0.0.0.0:$PORT main:app
