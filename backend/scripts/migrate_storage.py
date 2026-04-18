"""
对象存储数据迁移脚本

用于在不同存储后端之间迁移文件数据。
支持：
- 七牛云 -> S3 兼容存储
- 本地 -> S3 兼容存储
- S3 兼容存储 -> 七牛云
- 本地 -> 七牛云

使用方法：
    python scripts/migrate_storage.py --from qiniu --to s3 --dry-run
    python scripts/migrate_storage.py --from qiniu --to s3 --execute
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Literal

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.storage import StorageBackend
from app.services.storage.local_backend import LocalStorageBackend
from app.services.storage.qiniu_backend import QiniuStorageBackend
from app.services.storage.s3_backend import S3StorageBackend

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class StorageMigrator:
    """存储迁移器"""

    def __init__(
        self,
        source_backend: StorageBackend,
        target_backend: StorageBackend,
        dry_run: bool = True,
    ):
        self.source = source_backend
        self.target = target_backend
        self.dry_run = dry_run
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
        }

    def migrate_file(self, key: str) -> bool:
        """
        迁移单个文件

        Args:
            key: 文件 key

        Returns:
            是否迁移成功
        """
        try:
            # 检查源文件是否存在
            if not self.source.file_exists(key):
                logger.warning("源文件不存在，跳过: %s", key)
                self.stats["skipped"] += 1
                return False

            # 检查目标文件是否已存在
            if self.target.file_exists(key):
                logger.info("目标文件已存在，跳过: %s", key)
                self.stats["skipped"] += 1
                return True

            if self.dry_run:
                logger.info("[DRY RUN] 将迁移文件: %s", key)
                self.stats["success"] += 1
                return True

            # 从源下载文件（这里需要实现下载逻辑）
            # 注意：当前抽象层没有 download_data 方法，需要扩展
            logger.warning("文件下载功能尚未实现，跳过: %s", key)
            self.stats["skipped"] += 1
            return False

        except Exception as e:
            logger.error("迁移文件失败: key=%s, error=%s", key, e)
            self.stats["failed"] += 1
            return False

    def migrate_directory(self, prefix: str) -> None:
        """
        迁移目录下的所有文件

        Args:
            prefix: 目录前缀（如 "images/"）
        """
        logger.info("开始迁移目录: %s", prefix)
        # 注意：当前抽象层没有 list_files 方法，需要扩展
        logger.warning("目录列举功能尚未实现")

    def print_stats(self) -> None:
        """打印迁移统计信息"""
        logger.info("=" * 60)
        logger.info("迁移统计:")
        logger.info("  总文件数: %d", self.stats["total"])
        logger.info("  成功: %d", self.stats["success"])
        logger.info("  失败: %d", self.stats["failed"])
        logger.info("  跳过: %d", self.stats["skipped"])
        logger.info("=" * 60)


def create_backend(
    backend_type: Literal["local", "qiniu", "s3"]
) -> StorageBackend:
    """
    创建存储后端实例

    Args:
        backend_type: 后端类型

    Returns:
        StorageBackend 实例
    """
    if backend_type == "local":
        upload_dir = Path(__file__).parent.parent / "uploads"
        return LocalStorageBackend(upload_dir)
    elif backend_type == "qiniu":
        return QiniuStorageBackend()
    elif backend_type == "s3":
        return S3StorageBackend()
    else:
        raise ValueError(f"不支持的后端类型: {backend_type}")


def main() -> None:
    """主函数"""
    parser = argparse.ArgumentParser(description="对象存储数据迁移工具")
    parser.add_argument(
        "--from",
        dest="source",
        required=True,
        choices=["local", "qiniu", "s3"],
        help="源存储后端",
    )
    parser.add_argument(
        "--to",
        dest="target",
        required=True,
        choices=["local", "qiniu", "s3"],
        help="目标存储后端",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅模拟迁移，不实际执行",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="执行实际迁移",
    )
    parser.add_argument(
        "--prefix",
        default="",
        help="仅迁移指定前缀的文件（如 images/）",
    )

    args = parser.parse_args()

    if args.source == args.target:
        logger.error("源和目标存储后端不能相同")
        sys.exit(1)

    if not args.dry_run and not args.execute:
        logger.error("必须指定 --dry-run 或 --execute")
        sys.exit(1)

    dry_run = args.dry_run or not args.execute

    logger.info("=" * 60)
    logger.info("对象存储迁移工具")
    logger.info("=" * 60)
    logger.info("源存储: %s", args.source)
    logger.info("目标存储: %s", args.target)
    logger.info("模式: %s", "模拟运行" if dry_run else "实际执行")
    logger.info("前缀过滤: %s", args.prefix or "无")
    logger.info("=" * 60)

    try:
        # 创建存储后端
        source_backend = create_backend(args.source)
        target_backend = create_backend(args.target)

        # 创建迁移器
        migrator = StorageMigrator(source_backend, target_backend, dry_run)

        # 执行迁移
        if args.prefix:
            migrator.migrate_directory(args.prefix)
        else:
            logger.warning("未指定前缀，将迁移所有文件")
            logger.warning("注意：当前版本需要手动指定文件列表")

        # 打印统计信息
        migrator.print_stats()

    except Exception as e:
        logger.error("迁移失败: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
