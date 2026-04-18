# 多阶段构建 - 前端应用
FROM node:20-alpine AS builder

# 设置工作目录
WORKDIR /app

# 复制依赖文件（单独一层，利用 Docker 缓存）
COPY package.json package-lock.json ./

# 安装依赖（添加缓存优化参数）
RUN npm ci --prefer-offline --no-audit --progress=false

# 复制源代码（单独一层，避免代码改动导致依赖重装）
COPY . .

# 构建生产版本（设置环境变量优化构建）
ENV NODE_ENV=production
RUN npm run build

# 生产阶段 - 使用 Nginx 提供静态文件
FROM nginx:alpine

# 复制自定义 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 从构建阶段复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:80/ || exit 1

# 暴露端口
EXPOSE 80

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]
