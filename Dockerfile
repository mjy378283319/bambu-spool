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

# 图标也放到镜像根，方便从容器里直接取（Unraid 模板/其他编排工具可用）。
# 标准 OCI 注解 org.opencontainers.image.* 见下方 LABEL。
COPY icon.png icon.svg /app/brand/

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

# 标准 OCI 注解。CI 里 docker/metadata-action 会另给一份（那边的覆盖这里的，本地构建用这份）。
# 取图标（Unraid 模板 / 编排工具可读）：
#   容器内 /app/brand/icon.png、/app/brand/icon.svg
#   HTTP  /static/icon.svg、/favicon.ico
LABEL org.opencontainers.image.title="拓竹耗材管家 / Bambu Spool Manager" \
      org.opencontainers.image.description="拓竹 3D 打印机耗材库存管理：料盘台账、AMS 槽位绑定、自动扣重、中文 Web 界面" \
      org.opencontainers.image.source="https://github.com/mjy378283319/bambu-spool" \
      org.opencontainers.image.url="https://github.com/mjy378283319/bambu-spool" \
      org.opencontainers.image.licenses="MIT"

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8971'), timeout=4)" || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8971}"]
