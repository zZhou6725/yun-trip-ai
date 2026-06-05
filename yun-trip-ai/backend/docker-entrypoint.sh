#!/bin/sh
set -e

# 确保 volume 挂载后的数据目录存在且权限正确
mkdir -p /app/db/chroma_db /app/logs
chown -R appuser:appuser /app/db /app/logs 2>/dev/null || true

# 降级到 appuser 执行启动命令
exec gosu appuser "$@"