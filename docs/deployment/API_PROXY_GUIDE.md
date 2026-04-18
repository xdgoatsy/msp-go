# API 代理配置说明

## 架构对比

### 方案 1：不使用代理（分离部署）
```
用户浏览器
    ├─ http://frontend.com:80    → 前端
    └─ http://backend.com:8000   → 后端 API
```
**缺点：**
- 需要配置 CORS
- 需要两个域名或暴露端口
- HTTPS 需要两个证书

### 方案 2：使用 Nginx 代理（推荐）✅
```
用户浏览器
    ↓
http://yourdomain.com (Nginx :80)
    ├─ /              → 前端静态文件
    └─ /api/          → 代理到后端 (backend:8000)
```
**优点：**
- 统一域名，无需 CORS 配置
- 后端端口不对外暴露，更安全
- 只需一个 SSL 证书
- 便于负载均衡和扩展

## 当前配置

### 前端 (frontend/nginx.conf)
```nginx
location /api/ {
    proxy_pass http://backend:8000;
    # ... 代理配置
}
```

### 前端代码 (frontend/src/libs/http/apiClient.ts)
```typescript
baseURL: '/api/v1'  // 相对路径，自动使用当前域名
```

### Docker Compose (docker-compose.prod.yml)
```yaml
backend:
  # 后端端口不对外暴露，仅内部网络访问
  # ports:
  #   - "8000:8000"  # 已注释
```

## 访问方式

### 生产环境（使用代理）
- 前端：`http://yourdomain.com/`
- API：`http://yourdomain.com/api/v1/...`
- 后端容器：`backend:8000`（仅内部访问）

### 开发环境（Vite 代理）
- 前端：`http://localhost:5173/`
- API：`http://localhost:5173/api/v1/...` → Vite 代理到 `http://localhost:8000`
- 后端：`http://localhost:8000/api/v1/...`（直接访问）

## 安全优势

1. **端口隐藏**：后端 8000 端口不对外暴露
2. **统一入口**：所有请求通过 Nginx 过滤
3. **防火墙简化**：只需开放 80/443 端口
4. **DDoS 防护**：Nginx 可配置限流
5. **SSL 终止**：在 Nginx 层统一处理 HTTPS

## 性能优化

Nginx 配置已包含：
- Gzip 压缩
- 静态资源缓存（1年）
- 连接超时设置（适配 AI 长请求）
- HTTP/1.1 持久连接
