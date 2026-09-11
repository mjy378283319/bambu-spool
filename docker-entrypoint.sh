#!/bin/sh
# 把挂载出来的数据目录 chown 成 PUID/PGID，再以该身份运行主程序。
#
# 为什么需要它：镜像里如果写死一个 uid 运行，而在 Unraid 上 /data 绑定的是
# appdata 目录（归 nobody:users = 99:100 所有），进程就会因为写不了 SQLite
# 而启动失败。这里在启动时按宿主的实际归属调整一次。
#
# PUID=0 表示不做降权，直接以 root 运行。
set -e

PUID="${PUID:-99}"
PGID="${PGID:-100}"
DATA="${DATA_DIR:-/data}"

if [ "$(id -u)" = "0" ]; then
  if [ "$PUID" != "0" ]; then
    mkdir -p "$DATA"
    chown -R "$PUID:$PGID" "$DATA" 2>/dev/null || true

    if command -v gosu >/dev/null 2>&1; then
      exec gosu "$PUID:$PGID" "$@"
    fi
    if command -v setpriv >/dev/null 2>&1; then
      exec setpriv --reuid="$PUID" --regid="$PGID" --clear-groups "$@"
    fi
    if command -v su-exec >/dev/null 2>&1; then
      exec su-exec "$PUID:$PGID" "$@"
    fi
    echo "[警告] 未找到可用的降权工具（gosu / setpriv / su-exec），将以 root 运行" >&2
  fi
fi

exec "$@"
