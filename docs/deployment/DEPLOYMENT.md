# Docker 生产环境部署指南

本文档介绍如何在生产服务器上部署 MathStudyPlatform。

## 📋 目录

- [前置准备](#前置准备)
- [首次部署](#首次部署)
- [更新部署](#更新部署)
- [域名和 HTTPS 配置](#域名和-https-配置)
- [常见问题](#常见问题)

---

## 前置准备

### 1. 服务器要求

- **操作系统**: Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- **内存**: 最低 2GB，推荐 4GB+
- **磁盘**: 最低 20GB，推荐 50GB+
- **CPU**: 最低 2 核，推荐 4 核+

### 2. 安装 Docker 和 Docker Compose

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh

# 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

### 3. 配置 GitHub Secrets（用于 CI/CD）

在 GitHub 仓库中配置：

1. 进入仓库 → Settings → Secrets and variables → Actions
2. 添加以下 Secrets：
   - `DOCKER_USERNAME`: Docker Hub 用户名
   - `DOCKER_PASSWORD`: Docker Hub Access Token

---

## 首次部署

### 1. 克隆仓库

```bash
# 克隆到服务器
git clone https://github.com/fraternity-z/MathStudyPlatform.git
cd MathStudyPlatform

# 赋予脚本执行权限
chmod +x scripts/deploy.sh scripts/update.sh
```

### 2. 运行部署脚本

```bash
# 使用域名部署（推荐）
sudo ./scripts/deploy.sh your-domain.com

# 或使用 IP 部署
sudo ./scripts/deploy.sh
```

部署脚本会自动：
- ✅ 检查环境依赖（Docker、Docker Compose、Nginx）
- ✅ 配置环境变量（引导编辑 `backend/.env`）
- ✅ 设置 Docker Hub 用户名
- ✅ 拉取 Docker 镜像
- ✅ 先启动 PostgreSQL / Redis
- ✅ 运行数据库迁移
- ✅ 再启动后端与前端服务
- ✅ 配置 Nginx 反向代理（如果提供域名）

### 3. 配置环境变量

部署脚本会提示编辑 `backend/.env`，必须配置：

```env
# 数据库配置
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=math_platform
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis 配置
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password_here

# JWT 与加密密钥（必须修改）
JWT_SECRET_KEY=your_secret_key_at_least_32_characters_long
FERNET_SECRET_KEY=your_fernet_secret_key_here

# LLM 配置
OPENAI_API_KEY=your_api_key
OPENAI_API_BASE=https://api.openai.com/v1

# 应用配置
DEBUG=false
ENVIRONMENT=production
CORS_ORIGINS=["https://your-domain.com","https://www.your-domain.com"]
```

### 4. 验证部署

```bash
# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 测试后端健康检查
curl http://localhost:8000/health

# 测试前端访问
curl http://localhost:9000
```

---

## 更新部署

### 方式 1: 使用更新脚本（推荐）

```bash
# 设置 Docker Hub 用户名（如果未设置）
export DOCKER_USERNAME=your-dockerhub-username

# 更新到最新版本
./scripts/update.sh

# 更新到指定版本
./scripts/update.sh v1.0.0
```

更新脚本会自动：
- ✅ 备份当前配置
- ✅ 拉取最新镜像
- ✅ 停止旧容器
- ✅ 先启动 PostgreSQL / Redis
- ✅ 运行数据库迁移
- ✅ 再启动后端与前端服务
- ✅ 健康检查
- ✅ 清理旧镜像

### 方式 2: 手动更新

```bash
# 1. 设置环境变量
export DOCKER_USERNAME=your-dockerhub-username

# 2. 拉取最新镜像
docker pull ${DOCKER_USERNAME}/backend:latest
docker pull ${DOCKER_USERNAME}/frontend:latest

# 3. 重启服务
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# 4. 运行数据库迁移
docker exec msp_backend alembic upgrade head
```

---

## 域名和 HTTPS 配置

### 1. 配置域名解析

在域名服务商处添加 A 记录：
```
类型: A
主机记录: @ 或 www
记录值: 服务器公网 IP
```

### 2. 配置 HTTPS（使用 Let's Encrypt）

```bash
# 安装 Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# 自动配置 HTTPS
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# 测试自动续期
sudo certbot renew --dry-run
```

Certbot 会自动：
- ✅ 申请 SSL 证书
- ✅ 修改 Nginx 配置
- ✅ 设置自动续期

### 3. 手动配置 Nginx HTTPS

如果需要手动配置，编辑 `/etc/nginx/sites-available/mathplatform.conf`：

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 50M;

    location / {
        proxy_pass http://localhost:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

重载 Nginx：
```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 常见问题

### 1. 如何查看日志？

```bash
# 查看所有服务日志
docker-compose -f docker-compose.prod.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f frontend

# 查看最近 100 行
docker-compose -f docker-compose.prod.yml logs --tail=100
```

### 2. 如何进入容器调试？

```bash
# 进入后端容器
docker exec -it msp_backend bash

# 进入前端容器
docker exec -it msp_frontend sh

# 进入数据库容器
docker exec -it msp_postgres psql -U postgres -d math_platform
```

### 3. 如何备份数据？

```bash
# 备份数据库
docker exec msp_postgres pg_dump -U postgres math_platform > backup_$(date +%Y%m%d).sql

# 备份上传文件
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz backend/uploads/

# 备份 Redis
docker exec msp_redis redis-cli SAVE
docker cp msp_redis:/data/dump.rdb redis_backup_$(date +%Y%m%d).rdb
```

### 4. 如何恢复数据？

```bash
# 恢复数据库
cat backup_20260212.sql | docker exec -i msp_postgres psql -U postgres -d math_platform

# 恢复上传文件
tar -xzf uploads_backup_20260212.tar.gz

# 恢复 Redis
docker cp redis_backup_20260212.rdb msp_redis:/data/dump.rdb
docker-compose -f docker-compose.prod.yml restart redis
```

### 5. 如何回滚版本？

```bash
# 使用备份目录回滚
BACKUP_DIR=backups/20260212_143000
docker-compose -f docker-compose.prod.yml down
cp $BACKUP_DIR/.env.prod backend/
docker-compose -f docker-compose.prod.yml up -d
```

### 6. 端口被占用怎么办？

```bash
# 查看端口占用
sudo lsof -i :8000
sudo lsof -i :9000

# 修改 docker-compose.prod.yml 中的端口映射
# 例如将 9000:80 改为 9001:80
```

### 7. 环境变量 DOCKER_USERNAME 未设置？

```bash
# 检查是否设置
echo $DOCKER_USERNAME

# 临时设置
export DOCKER_USERNAME=your-dockerhub-username

# 永久设置
echo 'export DOCKER_USERNAME=your-dockerhub-username' >> ~/.bashrc
source ~/.bashrc
```

### 8. 如何监控服务状态？

```bash
# 查看容器状态
docker-compose -f docker-compose.prod.yml ps

# 查看资源使用
docker stats

# 查看磁盘使用
docker system df

# 清理未使用资源
docker system prune -a
```

---

## 维护建议

### 定期任务

1. **每周备份数据库和文件**
2. **每月检查磁盘空间**
3. **每月清理 Docker 未使用资源**
4. **定期更新系统和 Docker**

### 监控指标

- 容器运行状态
- CPU 和内存使用率
- 磁盘空间
- 数据库连接数
- API 响应时间

### 安全建议

- ✅ 使用强密码
- ✅ 启用 HTTPS
- ✅ 定期更新依赖
- ✅ 限制数据库外部访问
- ✅ 配置防火墙规则
- ✅ 定期备份数据

---

## 相关文档

- [Docker 文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [Nginx 文档](https://nginx.org/en/docs/)
- [Let's Encrypt 文档](https://letsencrypt.org/docs/)
