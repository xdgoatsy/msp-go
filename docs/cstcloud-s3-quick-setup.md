# 中国科技云对象存储快速配置指南

本文档提供中国科技云 (cstcloud.cn) S3 兼容对象存储的快速配置步骤。

## 配置信息

根据主人提供的信息：

- **服务商**: 中国科技云 (cstcloud.cn)
- **端点**: `s3.cstcloud.cn`
- **桶名**: `bfaf7c53ca9e49f59476cd52050d61e3`
- **签名版本**: v4

## 快速配置步骤

### 1. 安装依赖

```bash
cd backend
pip install boto3>=1.35.0
```

### 2. 配置环境变量

编辑 `backend/.env` 文件，添加以下配置：

```bash
# 存储后端配置
STORAGE_BACKEND=s3

# S3 兼容对象存储配置（中国科技云）
S3_ENDPOINT_URL=https://s3.cstcloud.cn
S3_ACCESS_KEY=<你的 Access Key>
S3_SECRET_KEY=<你的 Secret Key>
S3_BUCKET_NAME=bfaf7c53ca9e49f59476cd52050d61e3
S3_REGION=us-east-1
S3_PUBLIC_URL_BASE=
S3_PRIVATE_BUCKET=false
S3_URL_EXPIRE_SECONDS=3600
```

**注意**：请将 `<你的 Access Key>` 和 `<你的 Secret Key>` 替换为实际的密钥。

### 3. 验证配置

启动应用并测试：

```bash
# 启动后端服务
cd backend
uvicorn app.main:app --reload

# 在另一个终端测试上传
curl -X POST "http://localhost:8000/api/v1/upload/image" \
  -H "Authorization: Bearer <your-token>" \
  -F "file=@test.jpg"
```

### 4. 检查日志

查看应用日志，确认存储后端初始化成功：

```
INFO - 已初始化 S3 兼容存储后端: https://s3.cstcloud.cn
INFO - S3 上传成功: key=images/xxx.jpg, size=12345 bytes
```

## 配置说明

### 公开桶 vs 私有桶

当前配置为**公开桶** (`S3_PRIVATE_BUCKET=false`)，文件 URL 可直接访问。

如果需要使用**私有桶**，修改配置：

```bash
S3_PRIVATE_BUCKET=true
S3_URL_EXPIRE_SECONDS=3600  # 预签名 URL 有效期（秒）
```

### CDN 加速（可选）

如果中国科技云提供了 CDN 域名，可以配置：

```bash
S3_PUBLIC_URL_BASE=https://cdn.cstcloud.cn
```

这样生成的文件 URL 将使用 CDN 域名，提升访问速度。

### 区域配置

中国科技云可能不需要特定区域，保持默认值 `us-east-1` 即可。如果遇到问题，可以尝试其他值（如 `cn-north-1`）。

## 常见问题

### 1. 上传失败：403 Forbidden

**原因**：Access Key 或 Secret Key 错误，或者没有写入权限。

**解决方案**：
- 检查密钥是否正确
- 确认账户对该桶有写入权限
- 检查桶的访问策略

### 2. 上传失败：SignatureDoesNotMatch

**原因**：签名计算错误，可能是端点 URL 或区域配置不正确。

**解决方案**：
- 确认 `S3_ENDPOINT_URL` 是否正确（`https://s3.cstcloud.cn`）
- 尝试修改 `S3_REGION` 参数
- 检查系统时间是否准确（签名依赖时间戳）

### 3. 文件 URL 无法访问

**原因**：桶为私有桶，或者 URL 生成方式不正确。

**解决方案**：
- 如果是私有桶，设置 `S3_PRIVATE_BUCKET=true`
- 如果是公开桶，检查桶的访问策略是否允许公开读取
- 配置 `S3_PUBLIC_URL_BASE` 使用正确的访问域名

### 4. 如何获取 Access Key 和 Secret Key？

登录中国科技云控制台：
1. 进入对象存储服务
2. 找到"密钥管理"或"访问密钥"页面
3. 创建或查看现有密钥

### 5. 如何测试连接？

使用 AWS CLI 测试（需要先安装 `awscli`）：

```bash
# 配置 AWS CLI
aws configure set aws_access_key_id <your-access-key>
aws configure set aws_secret_access_key <your-secret-key>
aws configure set default.region us-east-1

# 测试列举桶内容
aws s3 ls s3://bfaf7c53ca9e49f59476cd52050d61e3 \
  --endpoint-url https://s3.cstcloud.cn

# 测试上传文件
aws s3 cp test.jpg s3://bfaf7c53ca9e49f59476cd52050d61e3/test.jpg \
  --endpoint-url https://s3.cstcloud.cn
```

## 回退到七牛云

如果遇到问题需要回退，修改 `.env` 文件：

```bash
STORAGE_BACKEND=qiniu
```

重启应用即可恢复使用七牛云。

## 生产环境部署

### 1. 安全建议

- 使用环境变量或密钥管理服务存储 Access Key 和 Secret Key
- 不要将密钥提交到代码仓库
- 定期轮换密钥
- 使用最小权限原则配置 IAM 策略

### 2. 性能优化

- 启用 CDN 加速（配置 `S3_PUBLIC_URL_BASE`）
- 使用私有桶时，合理设置 URL 有效期（`S3_URL_EXPIRE_SECONDS`）
- 考虑使用多区域部署提升可用性

### 3. 监控告警

- 监控存储用量和流量
- 设置费用告警
- 监控 API 错误率和延迟

## 技术支持

如有问题，请参考：
- [完整迁移指南](./storage-migration-guide.md)
- 中国科技云官方文档
- 项目技术支持团队

---

**最后更新**: 2026-02-23
