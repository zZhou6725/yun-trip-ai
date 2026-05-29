# =============================================================================
# 云途 AI 行程规划 - 后端服务 Dockerfile
# =============================================================================
# 使用多阶段构建，减小最终镜像体积。
# 构建命令：docker build -t yun-trip-ai-backend .
# =============================================================================

# ---------- 阶段一：依赖安装 ----------
FROM python:3.11-slim AS builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖（chromadb 需要 gcc 编译部分扩展）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件，利用 Docker 缓存层
COPY requirements.txt .

# 在 builder 阶段安装依赖到 /install 目录
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---------- 阶段二：运行镜像 ----------
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装运行时必需的系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 阶段复制已安装的 Python 包
COPY --from=builder /install /usr/local

# 复制应用源码
COPY . .

# 创建非 root 用户，提升安全性
RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查：每 30 秒探测 /health 接口
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 启动命令：使用 uvicorn 运行 FastAPI 应用
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]