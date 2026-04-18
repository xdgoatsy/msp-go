# 部署运维文档

本目录包含数学学习平台的部署和运维相关文档。

---

## 📄 文档列表

### 1. [DEPLOYMENT.md](./DEPLOYMENT.md)
Docker 生产环境部署完整指南，包括：
- 前置准备和环境要求
- 首次部署流程
- 更新部署流程
- 域名和 HTTPS 配置
- 常见问题解决
- 维护建议

### 2. [API_PROXY_GUIDE.md](./API_PROXY_GUIDE.md)
API 代理配置指南，包括：
- Nginx 反向代理配置
- 负载均衡设置
- SSL/TLS 配置
- 性能优化

---

## 🚀 快速部署

### 最小化部署（开发环境）

```bash
# 1. 克隆仓库
git clone https://github.com/fraternity-z/MathStudyPlatform.git
cd MathStudyPlatform

# 2. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env 填入必要配置

# 3. 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 4. 初始化数据库
docker exec msp_backend alembic upgrade head
```

### 生产环境部署

```bash
# 使用部署脚本（推荐）
chmod +x scripts/deploy.sh
sudo ./scripts/deploy.sh your-domain.com
```

详细步骤请参考 [DEPLOYMENT.md](./DEPLOYMENT.md)

---

## 📋 部署检查清单

### 部署前

- [ ] 服务器满足最低配置要求（2GB RAM, 20GB 磁盘）
- [ ] 已安装 Docker 和 Docker Compose
- [ ] 已配置域名解析（如使用域名）
- [ ] 已准备好必要的 API Key（DeepSeek 等）
- [ ] 已设置强密码（数据库、Redis、JWT）

### 部署中

- [ ] 环境变量配置正确
- [ ] Docker 镜像拉取成功
- [ ] 所有容器正常启动
- [ ] 数据库迁移执行成功
- [ ] Nginx 配置正确（如使用）

### 部署后

- [ ] 健康检查接口返回正常
- [ ] 前端页面可以访问
- [ ] 用户可以正常登录
- [ ] API 接口响应正常
- [ ] HTTPS 证书配置正确（生产环境）
- [ ] 日志输出正常
- [ ] 监控系统配置完成

---

## 🔧 常用运维命令

### 服务管理

```bash
# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 停止服务
docker-compose -f docker-compose.prod.yml down

# 重启服务
docker-compose -f docker-compose.prod.yml restart

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

### 数据库管理

```bash
# 进入数据库
docker exec -it msp_postgres psql -U postgres -d math_platform

# 备份数据库
docker exec msp_postgres pg_dump -U postgres math_platform > backup.sql

# 恢复数据库
cat backup.sql | docker exec -i msp_postgres psql -U postgres -d math_platform

# 运行迁移
docker exec msp_backend alembic upgrade head
```

### 容器管理

```bash
# 进入后端容器
docker exec -it msp_backend bash

# 进入前端容器
docker exec -it msp_frontend sh

# 查看容器资源使用
docker stats

# 清理未使用资源
docker system prune -a
```

---

## 📊 监控指标

### 关键指标

1. **服务可用性**
   - 容器运行状态
   - 健康检查响应
   - API 响应时间

2. **资源使用**
   - CPU 使用率
   - 内存使用率
   - 磁盘空间
   - 网络流量

3. **数据库性能**
   - 连接数
   - 查询响应时间
   - 慢查询日志

4. **应用性能**
   - 请求成功率
   - 错误率
   - 并发用户数

### 监控工具推荐

- **容器监控**: Docker Stats, cAdvisor
- **日志管理**: ELK Stack, Loki
- **性能监控**: Prometheus + Grafana
- **应用监控**: Sentry, New Relic

---

## 🔒 安全建议

### 基础安全

1. **使用强密码**
   - 数据库密码至少 16 位
   - JWT Secret 至少 32 位
   - Redis 密码至少 16 位

2. **启用 HTTPS**
   - 使用 Let's Encrypt 免费证书
   - 配置 HSTS 头
   - 禁用 TLS 1.0/1.1

3. **限制访问**
   - 数据库仅允许内网访问
   - Redis 仅允许内网访问
   - 配置防火墙规则

4. **定期更新**
   - 及时更新系统补丁
   - 更新 Docker 镜像
   - 更新依赖包

### 高级安全

- 配置 WAF（Web Application Firewall）
- 启用 DDoS 防护
- 实施日志审计
- 配置入侵检测系统
- 定期安全扫描

---

## 🔄 更新记录

### 2026-02-15
- 整合部署文档到统一目录
- 添加部署检查清单和运维命令

### 2026-02-12
- 添加 Docker 部署指南

### 2026-02-09
- 添加 API 代理配置指南

---

## 🔗 相关文档

- [架构设计](../architecture/) - 了解系统架构
- [API 接口规范](../api/API接口规范.md) - 了解 API 接口
- [文档中心](../README.md) - 返回文档首页
