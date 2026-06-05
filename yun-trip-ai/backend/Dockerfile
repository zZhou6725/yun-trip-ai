# =============================================================================
# 云途 AI 行程规划 - 后端服务 Dockerfile
# =============================================================================
# 使用多阶段构建，减小最终镜像体积。
# 构建命令：docker build -t yun-trip-ai-backend .
# =============================================================================

# ---------- 阶段一：依赖安装 ----------
FROM python:3.11-slim AS builder

WORKDIR /app

# chromadb 需要 gcc/g++ 编译部分原生扩展
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# 安装依赖到独立目录，便于后续复制到运行阶段，减小镜像体积
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---------- 阶段二：运行镜像 ----------
FROM python:3.11-slim

WORKDIR /app

# libgomp1: chromadb 运行时依赖
# gosu: 用于 entrypoint 修复权限后降级运行
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    gosu \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

COPY . .

RUN useradd --create-home --shell /bin/bash appuser \
    && chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]