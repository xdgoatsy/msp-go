"""
管理员用户管理服务

提供用户账户管理的业务逻辑
"""

import logging
from datetime import datetime

from sqlalchemy import case, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.domain.models.student import UserRole, UserStatus
from app.infrastructure.database.models import (
    ContentAclModel,
    ContentAttemptModel,
    ContentModel,
    ImportJobModel,
    LearningSessionModel,
    SessionMessageModel,
    StudentProfileModel,
    UserModel,
)
from app.services.utils import (
    build_user_search_condition,
    calculate_offset,
    calculate_total_pages,
    validate_enum,
)

logger = logging.getLogger(__name__)


class AdminUserService:
    """管理员用户管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_account_stats(self) -> dict[str, int]:
        """
        获取账户统计数据

        Returns:
            包含各状态账户数量的字典
        """
        result = await self.db.execute(
            select(
                func.count(UserModel.id).label("total"),
                func.count(case((UserModel.status == UserStatus.ACTIVE, 1))).label(
                    "active"
                ),
                func.count(
                    case((UserModel.status == UserStatus.SUSPENDED, 1))
                ).label("suspended"),
            )
        )
        row = result.one()
        return {
            "total": row.total,
            "active": row.active,
            "suspended": row.suspended,
        }

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        role: str | None = None,
        status: str | None = None,
    ) -> dict:
        """
        分页查询用户列表

        Args:
            page: 页码（从 1 开始）
            page_size: 每页数量
            search: 搜索关键词（用户名、邮箱、显示名称）
            role: 角色筛选
            status: 状态筛选

        Returns:
            包含用户列表和分页信息的字典
        """
        # 构建基础查询
        query = select(UserModel)
        count_query = select(func.count(UserModel.id))

        # 搜索条件（使用工具函数）
        search_condition = build_user_search_condition(UserModel, search)
        if search_condition is not None:
            query = query.where(search_condition)
            count_query = count_query.where(search_condition)

        # 角色筛选（使用工具函数）
        role_enum = validate_enum(role, UserRole)
        if role_enum:
            query = query.where(UserModel.role == role_enum)
            count_query = count_query.where(UserModel.role == role_enum)

        # 状态筛选（使用工具函数）
        status_enum = validate_enum(status, UserStatus)
        if status_enum:
            query = query.where(UserModel.status == status_enum)
            count_query = count_query.where(UserModel.status == status_enum)

        # 查询总数
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 计算分页（使用工具函数）
        total_pages = calculate_total_pages(total, page_size)
        offset = calculate_offset(page, page_size)

        # 查询数据（按创建时间倒序）
        query = query.order_by(UserModel.created_at.desc()).offset(offset).limit(page_size)
        result = await self.db.execute(query)
        users = result.scalars().all()

        # 转换为字典列表
        items = [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "display_name": user.display_name,
                "role": user.role.value,
                "status": user.status.value if user.status else UserStatus.ACTIVE.value,
                "created_at": user.created_at,
            }
            for user in users
        ]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    async def update_user_status(
        self, user_id: str, new_status: str
    ) -> UserModel | None:
        """
        更新用户状态

        Args:
            user_id: 用户 ID
            new_status: 新状态

        Returns:
            更新后的用户，如果用户不存在则返回 None
        """
        # 查询用户
        result = await self.db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            return None

        # 更新状态
        try:
            status_enum = UserStatus(new_status)
            user.status = status_enum
            user.updated_at = datetime.now()

            # 同步更新 is_active 字段
            user.is_active = status_enum == UserStatus.ACTIVE

            await self.db.commit()
            await self.db.refresh(user)

            logger.info(f"用户状态已更新: user_id={user_id}, status={new_status}")
            return user
        except ValueError:
            logger.error(f"无效的用户状态: {new_status}")
            return None

    async def delete_user(self, user_id: str) -> bool:
        """
        删除用户（物理删除）

        Args:
            user_id: 用户 ID

        Returns:
            是否删除成功
        """
        # 查询用户
        result = await self.db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            return False

        # 删除关联数据（按依赖顺序）
        # 1. 删除会话消息（依赖学习会话）
        session_ids_result = await self.db.execute(
            select(LearningSessionModel.id).where(
                LearningSessionModel.student_id == user_id
            )
        )
        session_ids = [row[0] for row in session_ids_result.fetchall()]
        if session_ids:
            await self.db.execute(
                delete(SessionMessageModel).where(
                    SessionMessageModel.session_id.in_(session_ids)
                )
            )

        # 2. 删除学习会话
        await self.db.execute(
            delete(LearningSessionModel).where(
                LearningSessionModel.student_id == user_id
            )
        )

        # 3. 删除学生画像
        await self.db.execute(
            delete(StudentProfileModel).where(
                StudentProfileModel.student_id == user_id
            )
        )

        # 4. 删除内容协作权限
        await self.db.execute(
            delete(ContentAclModel).where(ContentAclModel.teacher_id == user_id)
        )

        # 5. 删除练习尝试记录（包括该用户作为学生的记录，以及该用户拥有内容的尝试记录）
        await self.db.execute(
            delete(ContentAttemptModel).where(
                ContentAttemptModel.student_id == user_id
            )
        )

        # 6. 删除用户拥有内容的尝试记录（其他学生对该用户内容的尝试）
        owned_content_ids_result = await self.db.execute(
            select(ContentModel.id).where(ContentModel.owner_teacher_id == user_id)
        )
        owned_content_ids = [row[0] for row in owned_content_ids_result.fetchall()]
        if owned_content_ids:
            await self.db.execute(
                delete(ContentAttemptModel).where(
                    ContentAttemptModel.content_id.in_(owned_content_ids)
                )
            )
            # 7. 删除用户拥有的内容（assets, acl, embeddings, favorites 会通过 cascade 自动删除）
            await self.db.execute(
                delete(ContentModel).where(ContentModel.owner_teacher_id == user_id)
            )

        # 8. 删除导入任务
        await self.db.execute(
            delete(ImportJobModel).where(ImportJobModel.created_by == user_id)
        )

        # 9. 物理删除用户（favorites 会通过 cascade 自动删除）
        await self.db.delete(user)
        await self.db.commit()

        logger.info(f"用户已删除: user_id={user_id}")
        return True

    async def get_user_by_id(self, user_id: str) -> UserModel | None:
        """
        根据 ID 获取用户

        Args:
            user_id: 用户 ID

        Returns:
            用户对象，如果不存在则返回 None
        """
        result = await self.db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        return result.scalar_one_or_none()

    async def update_user(
        self,
        user_id: str,
        display_name: str | None = None,
        password: str | None = None,
    ) -> tuple[UserModel | None, str]:
        """
        更新用户信息

        Args:
            user_id: 用户 ID
            display_name: 显示名称（可选）
            password: 新密码（可选）

        Returns:
            (用户对象, 消息) 元组，如果失败则用户对象为 None
        """
        # 查询用户
        result = await self.db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            return None, "用户不存在"

        # 更新字段
        if display_name is not None:
            user.display_name = display_name

        if password is not None:
            user.hashed_password = get_password_hash(password)

        user.updated_at = datetime.now()

        await self.db.commit()
        await self.db.refresh(user)

        logger.info(f"用户信息已更新: user_id={user_id}")
        return user, "用户信息更新成功"

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        role: str = "student",
        display_name: str | None = None,
    ) -> tuple[UserModel | None, str]:
        """
        创建新用户

        Args:
            username: 用户名
            email: 邮箱
            password: 密码
            role: 角色
            display_name: 显示名称

        Returns:
            (用户对象, 消息) 元组，如果失败则用户对象为 None
        """
        # 检查用户名是否已存在
        existing = await self.db.execute(
            select(UserModel).where(
                or_(UserModel.username == username, UserModel.email == email)
            )
        )
        existing_user = existing.scalar_one_or_none()

        if existing_user:
            if existing_user.username == username:
                return None, f"用户名 '{username}' 已存在"
            return None, f"邮箱 '{email}' 已被使用"

        # 创建用户
        try:
            role_enum = UserRole(role)
        except ValueError:
            return None, f"无效的角色: {role}"

        hashed_password = get_password_hash(password)

        user = UserModel(
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=role_enum,
            status=UserStatus.ACTIVE,
            display_name=display_name,
            is_active=True,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        logger.info(f"创建用户成功: username={username}, role={role}")
        return user, "用户创建成功"

    async def export_users(
        self,
        search: str | None = None,
        role: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        """
        导出用户列表

        Args:
            search: 搜索关键词
            role: 角色筛选
            status: 状态筛选

        Returns:
            用户列表（字典格式），不包含管理员账户
        """
        query = select(UserModel)

        # 排除管理员账户（导出数据不应包含管理员信息）
        query = query.where(UserModel.role != UserRole.ADMIN)

        # 搜索条件（使用工具函数）
        search_condition = build_user_search_condition(UserModel, search)
        if search_condition is not None:
            query = query.where(search_condition)

        # 角色筛选（使用工具函数）
        role_enum = validate_enum(role, UserRole)
        if role_enum:
            query = query.where(UserModel.role == role_enum)

        # 状态筛选（使用工具函数）
        status_enum = validate_enum(status, UserStatus)
        if status_enum:
            query = query.where(UserModel.status == status_enum)

        # 按创建时间倒序
        query = query.order_by(UserModel.created_at.desc())

        result = await self.db.execute(query)
        users = result.scalars().all()

        return [
            {
                "username": user.username,
                "email": user.email,
                "display_name": user.display_name or "",
                "role": user.role.value,
                "status": user.status.value if user.status else "active",
                "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S") if user.created_at else "",
            }
            for user in users
        ]

    async def import_users(
        self,
        users_data: list[dict],
    ) -> dict:
        """
        批量导入用户

        Args:
            users_data: 用户数据列表，每项包含 username, email, password, role, display_name

        Returns:
            导入结果统计
        """
        results = {
            "total": len(users_data),
            "created": 0,
            "failed": 0,
            "skipped": 0,
            "details": [],
        }

        for idx, user_data in enumerate(users_data, start=1):
            username = user_data.get("username", "").strip()
            email = user_data.get("email", "").strip()
            password = user_data.get("password", "").strip()
            role = user_data.get("role", "student").strip()
            display_name = user_data.get("display_name", "").strip() or None

            # 验证必填字段
            if not username or not email or not password:
                results["failed"] += 1
                results["details"].append({
                    "row": idx,
                    "username": username or "(空)",
                    "success": False,
                    "message": "用户名、邮箱和密码为必填项",
                })
                continue

            # 检查是否已存在
            existing = await self.db.execute(
                select(UserModel).where(
                    or_(UserModel.username == username, UserModel.email == email)
                )
            )
            existing_user = existing.scalar_one_or_none()

            if existing_user:
                results["skipped"] += 1
                if existing_user.username == username:
                    msg = f"用户名 '{username}' 已存在"
                else:
                    msg = f"邮箱 '{email}' 已被使用"
                results["details"].append({
                    "row": idx,
                    "username": username,
                    "success": False,
                    "message": msg,
                })
                continue

            # 验证角色
            try:
                role_enum = UserRole(role)
            except ValueError:
                results["failed"] += 1
                results["details"].append({
                    "row": idx,
                    "username": username,
                    "success": False,
                    "message": f"无效的角色: {role}",
                })
                continue

            # 创建用户
            try:
                hashed_password = get_password_hash(password)
                user = UserModel(
                    username=username,
                    email=email,
                    hashed_password=hashed_password,
                    role=role_enum,
                    status=UserStatus.ACTIVE,
                    display_name=display_name,
                    is_active=True,
                )
                self.db.add(user)
                await self.db.flush()

                results["created"] += 1
                results["details"].append({
                    "row": idx,
                    "username": username,
                    "success": True,
                    "message": "创建成功",
                })
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "row": idx,
                    "username": username,
                    "success": False,
                    "message": f"创建失败: {str(e)}",
                })

        # 提交事务
        await self.db.commit()

        logger.info(
            f"批量导入用户完成: total={results['total']}, "
            f"created={results['created']}, failed={results['failed']}, "
            f"skipped={results['skipped']}"
        )

        return results
