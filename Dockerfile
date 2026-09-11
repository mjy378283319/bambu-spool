FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# curl_cffi 需要的系统库在 wheel 里自带，只需证书。
# gosu 用于启动时降权，装不上也不影响构建（入口脚本会自动回退）。
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && (apt-get install -y --no-install-recommends gosu \
        || echo "gosu 不可用，运行时将回退到 setpriv") \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY tests ./tests

# 入口脚本负责把数据目录调整为 PUID/PGID 所有，再降权运行。
# 这样在 Unraid（appdata 归 nobody:users）上不会因为写不了 SQLite 而启动失败。
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh \
    && chmod +x /usr/local/bin/docker-entrypoint.sh \
    && mkdir -p /data

ENV DATA_DIR=/data \
    PORT=8971 \
    PUID=99 \
    PGID=100

EXPOSE 8971

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8971'), timeout=4)" || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8971}"]
