#!/bin/bash
# 数据库初始化脚本 - 启用 pgvector 扩展

set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- 启用 pgvector 扩展
    CREATE EXTENSION IF NOT EXISTS vector;

    -- 验证扩展安装
    SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
EOSQL

echo "✅ pgvector 扩展已启用"
