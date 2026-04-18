# 对象存储迁移指南

本文档介绍如何将对象存储从七牛云迁移到其他厂商（如中国科技云 S3 兼容存储）。

## 架构说明

项目采用统一的存储抽象层设计，支持多种存储后端：

```
┌─────────────────────────────────────┐
│      API Layer (upload.py)          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Business Layer (upload_service.py)│
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│  Storage Interface (ABC Protocol)   │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┬───────────┐
       │               │           │
┌──────▼─────┐  ┌─────▼────┐  ┌──▼─────┐
│   Local    │  │  Qiniu   │  │  S3    │
│  Storage   │  │ Storage  │  │Storage │
└────────────┘  └──────────┘  └────────┘
```

## 支持的存储后端

- **local**: 本地文件系统
- **qiniu**: 七牛云对象存储
- **s3**: S3 兼容对象存储（AWS S3、阿里云 OSS、腾讯云 COS、MinIO、中国科技云等）

## 迁移步骤

### 1. 安装依赖

```bash
cd backend
pip install boto3>=1.35.0
```

### 2. 配置新的存储后端

编辑 `.env` 文件，添加 S3 配置：

```bash
# 存储后端配置（切换为 s3）
STORAGE_BACKEND=s3

# S3 兼容对象存储配置
S3_ENDPOINT_URL=https://s3.cstcloud.cn
S3_ACCESS_KEY=your-access-key-here
S3_SECRET_KEY=your-secret-key-here
S3_BUCKET_NAME=bfaf7c53ca9e49f59476cd52050d61e3
S3_REGION=us-east-1
S3_PUBLIC_URL_BASE=
S3_PRIVATE_BUCKET=false
S3_URL_EXPIRE_SECONDS=3600
```

### 3. 配置说明

#### 中国科技云 (cstcloud.cn) 配置示例

```bash
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=https://s3.cstcloud.cn
S3_ACCESS_KEY=<你的 Access Key>
S3_SECRET_KEY=<你的 Secret Key>
S3_BUCKET_NAME=bfaf7c53ca9e49f59476cd52050d61e3
S3_REGION=us-east-1
S3_PRIVATE_BUCKET=false
```

#### AWS S3 配置示例

```bash
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=https://s3.amazonaws.com
S3_ACCESS_KEY=<你的 Access Key>
S3_SECRET_KEY=<你的 Secret Key>
S3_BUCKET_NAME=your-bucket-name
S3_REGION=us-east-1
S3_PRIVATE_BUCKET=false
```

#### 阿里云 OSS (S3 兼容模式) 配置示例

```bash
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=https://oss-cn-hangzhou.aliyuncs.com
S3_ACCESS_KEY=<你的 Access Key>
S3_SECRET_KEY=<你的 Secret Key>
S3_BUCKET_NAME=your-bucket-name
S3_REGION=oss-cn-hangzhou
S3_PRIVATE_BUCKET=false
```

#### MinIO (自建) 配置示例

```bash
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=your-bucket-name
S3_REGION=us-east-1
S3_PRIVATE_BUCKET=false
```

### 4. 测试新配置

启动应用并测试文件上传功能：

```bash
# 启动后端服务
uvicorn app.main:app --reload

# 测试上传接口
curl -X POST "http://localhost:8000/api/v1/upload/image" \
  -H "Authorization: Bearer <your-token>" \
  -F "file=@test.jpg"
```

### 5. 数据迁移（可选）

如果需要迁移现有文件，使用迁移脚本：

```bash
# 模拟运行（不实际迁移）
python scripts/migrate_storage.py --from qiniu --to s3 --dry-run

# 实际执行迁移
python scripts/migrate_storage.py --from qiniu --to s3 --execute
```

**注意**：当前迁移脚本为基础版本，需要手动指定文件列表。完整的迁移功能需要扩展存储抽象层，添加 `list_files` 和 `download_data` 方法。

### 6. 验证迁移结果

1. 检查新存储后端中的文件是否完整
2. 验证文件 URL 是否可访问
3. 测试文件上传、下载、删除功能

### 7. 切换生产环境

确认测试无误后，更新生产环境配置：

```bash
# 更新生产环境 .env 文件
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=https://s3.cstcloud.cn
S3_ACCESS_KEY=<生产环境 Access Key>
S3_SECRET_KEY=<生产环境 Secret Key>
S3_BUCKET_NAME=bfaf7c53ca9e49f59476cd52050d61e3
S3_REGION=us-east-1
S3_PRIVATE_BUCKET=false

# 重启应用
systemctl restart math-platform-backend
```

## 配置参数说明

### 通用配置

- `STORAGE_BACKEND`: 存储后端类型（`local`、`qiniu`、`s3`）

### S3 配置

- `S3_ENDPOINT_URL`: S3 端点 URL（必填）
- `S3_ACCESS_KEY`: Access Key ID（必填）
- `S3_SECRET_KEY`: Secret Access Key（必填）
- `S3_BUCKET_NAME`: 存储桶名称（必填）
- `S3_REGION`: 区域（默认 `us-east-1`）
- `S3_PUBLIC_URL_BASE`: 公开访问的 CDN 域名（可选）
- `S3_PRIVATE_BUCKET`: 是否为私有桶（默认 `false`）
- `S3_URL_EXPIRE_SECONDS`: 私有桶预签名 URL 有效期（默认 `3600` 秒）

### 七牛云配置（保留用于回退）

- `QINIU_ACCESS_KEY`: 七牛云 AccessKey
- `QINIU_SECRET_KEY`: 七牛云 SecretKey
- `QINIU_BUCKET_NAME`: 存储空间名称
- `QINIU_DOMAIN`: 绑定的访问域名
- `QINIU_PRIVATE_BUCKET`: 是否为私有空间
- `QINIU_URL_EXPIRE_SECONDS`: 私有空间下载链接有效期

## 常见问题

### 1. 如何回退到七牛云？

修改 `.env` 文件：

```bash
STORAGE_BACKEND=qiniu
```

重启应用即可。

### 2. 如何同时保留多个存储后端？

当前设计支持通过环境变量切换，不支持同时使用多个后端。如需同时使用，可以扩展 `upload_service.py`，添加多后端支持。

### 3. 私有桶和公开桶的区别？

- **公开桶**：文件 URL 可直接访问，无需签名
- **私有桶**：文件 URL 需要预签名，有时效限制

根据业务需求选择合适的桶类型。

### 4. 如何处理 CDN 加速？

如果使用 CDN，配置 `S3_PUBLIC_URL_BASE` 参数：

```bash
S3_PUBLIC_URL_BASE=https://cdn.example.com
```

这样生成的文件 URL 将使用 CDN 域名。

### 5. 迁移过程中如何保证服务不中断？

建议采用以下策略：

1. **双写模式**：同时写入新旧两个存储后端
2. **读取优先级**：优先从新存储读取，失败时回退到旧存储
3. **逐步迁移**：分批迁移文件，降低风险
4. **灰度发布**：先在测试环境验证，再逐步切换生产环境

当前实现为单后端模式，如需双写模式，需要扩展 `upload_service.py`。

## 技术细节

### SOLID 原则应用

1. **单一职责 (S)**：每个存储适配器只负责一种存储服务
2. **开闭原则 (O)**：通过抽象接口扩展，不修改现有代码
3. **里氏替换 (L)**：所有存储实现可互相替换
4. **接口隔离 (I)**：定义最小化的存储接口
5. **依赖倒置 (D)**：业务层依赖抽象接口，不依赖具体实现

### 文件组织结构

```
backend/
├── app/
│   ├── services/
│   │   ├── storage/
│   │   │   ├── __init__.py          # 模块导出
│   │   │   ├── base.py              # 抽象接口
│   │   │   ├── factory.py           # 工厂类
│   │   │   ├── local_backend.py     # 本地存储实现
│   │   │   ├── qiniu_backend.py     # 七牛云实现
│   │   │   └── s3_backend.py        # S3 兼容实现
│   │   ├── upload_service.py        # 上传服务（使用抽象层）
│   │   └── qiniu_storage_service.py # 旧的七牛云服务（已废弃）
│   └── config.py                    # 配置管理
├── scripts/
│   └── migrate_storage.py           # 数据迁移脚本
└── pyproject.toml                   # 依赖管理
```

## 联系支持

如有问题，请联系技术支持团队。
