# =============================================================================
# 云途 AI 行程规划 - 前端 Dockerfile（多阶段构建）
# =============================================================================
# 阶段一：Node 构建
# 阶段二：Nginx 运行
# =============================================================================

# ---------- 阶段一：构建前端 ----------
FROM node:20-alpine AS builder

WORKDIR /app

# 利用 Docker 缓存层
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build


# ---------- 阶段二：Nginx 运行 ----------
FROM nginx:1.27-alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]