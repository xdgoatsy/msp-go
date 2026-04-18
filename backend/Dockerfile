# 多阶段构建 - 后端服务
FROM python:3.11-slim AS builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件和 README（单独一层，利用 Docker 缓存）
COPY pyproject.toml README.md ./

# 安装 Python 依赖（添加缓存优化）
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[ai]"

# 生产阶段
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装运行时依赖（合并到一层减少镜像层数）
RUN apt-get update && apt-get install -y \
    libpq5 \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 从构建阶段复制 Python 包
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用代码（单独一层，避免代码改动导致依赖重装）
COPY . .

# 创建非 root 用户（合并命令减少层数）
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/health')"

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
