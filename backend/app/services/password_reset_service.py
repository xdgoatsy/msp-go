"""密码重置服务。"""

import logging
import secrets
import string
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.domain.models.password_reset import PasswordResetStatus
from app.infrastructure.database.models import PasswordResetRequestModel, UserModel
from app.services.auth_service import clear_login_failures_for_username

logger = logging.getLogger(__name__)

MAX_REQUESTS_PER_DAY = 3
TEMP_PASSWORD_LENGTH = 12
TEMP_PASSWORD_CHARS = string.ascii_letters + string.digits


def _generate_temp_password() -> str:
    """生成随机临时密码。"""
    return "".join(secrets.choice(TEMP_PASSWORD_CHARS) for _ in range(TEMP_PASSWORD_LENGTH))


class PasswordResetService:
    """密码重置服务。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def submit_request(
        self,
        username: str,
        email: str,
        reason: str,
    ) -> tuple[bool, str, str | None]:
        """提交重置申请。"""
        user_result = await self.db.execute(
            select(UserModel).where(
                UserModel.username == username,
                UserModel.email == email,
            )
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            return (
                True,
                "如果该账号存在，您的申请已提交，请等待管理员审批",
                None,
            )

        since = datetime.now() - timedelta(hours=24)
        count_result = await self.db.execute(
            select(func.count(PasswordResetRequestModel.id)).where(
                PasswordResetRequestModel.user_id == user.id,
                PasswordResetRequestModel.created_at >= since,
            )
        )
        request_count = count_result.scalar() or 0
        if request_count >= MAX_REQUESTS_PER_DAY:
            return False, "申请过于频繁，请 24 小时后再试", None

        pending_result = await self.db.execute(
            select(PasswordResetRequestModel).where(
                PasswordResetRequestModel.user_id == user.id,
                PasswordResetRequestModel.status == PasswordResetStatus.PENDING,
            )
        )
        if pending_result.scalar_one_or_none() is not None:
            return True, "您已有待处理申请，请耐心等待管理员审批", None

        request_model = PasswordResetRequestModel(
            user_id=user.id,
            username=user.username,
            email=user.email,
            reason=reason,
            status=PasswordResetStatus.PENDING,
            created_at=datetime.now(),
        )
        self.db.add(request_model)
        await self.db.flush()
        await self.db.refresh(request_model)

        logger.info("密码重置申请已提交: user_id=%s, request_id=%s", user.id, request_model.id)
        return True, "申请已提交，请等待管理员审批", request_model.id

    async def get_user_request_status(
        self,
        username: str,
        email: str,
    ) -> tuple[bool, str | None, datetime | None]:
        """查询用户最近一次申请状态。"""
        result = await self.db.execute(
            select(PasswordResetRequestModel)
            .join(UserModel, UserModel.id == PasswordResetRequestModel.user_id)
            .where(
                UserModel.username == username,
                UserModel.email == email,
            )
            .order_by(PasswordResetRequestModel.created_at.desc())
            .limit(1)
        )
        request = result.scalar_one_or_none()
        if request is None:
            return False, None, None

        return (
            request.status == PasswordResetStatus.PENDING,
            request.status.value,
            request.created_at,
        )

    async def list_requests(
        self,
        status_filter: PasswordResetStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[PasswordResetRequestModel], int, int]:
        """管理员获取重置申请列表。"""
        query = select(PasswordResetRequestModel)
        count_query = select(func.count(PasswordResetRequestModel.id))

        if status_filter:
            query = query.where(PasswordResetRequestModel.status == status_filter)
            count_query = count_query.where(PasswordResetRequestModel.status == status_filter)

        query = query.order_by(PasswordResetRequestModel.created_at.desc())
        total = (await self.db.execute(count_query)).scalar() or 0

        pending_count_query = select(func.count(PasswordResetRequestModel.id)).where(
            PasswordResetRequestModel.status == PasswordResetStatus.PENDING
        )
        pending_count = (await self.db.execute(pending_count_query)).scalar() or 0

        offset = (page - 1) * page_size
        items_result = await self.db.execute(query.offset(offset).limit(page_size))
        items = list(items_result.scalars().all())
        return items, total, pending_count

    async def review_request(
        self,
        request_id: str,
        admin_id: str,
        action: str,
        reject_reason: str | None = None,
    ) -> tuple[bool, str, str | None]:
        """审批密码重置申请。"""
        request_result = await self.db.execute(
            select(PasswordResetRequestModel).where(
                PasswordResetRequestModel.id == request_id
            )
        )
        request = request_result.scalar_one_or_none()
        if request is None:
            return False, "申请不存在", None

        if request.status != PasswordResetStatus.PENDING:
            return False, "该申请已处理", None

        if action == "approve":
            user_result = await self.db.execute(
                select(UserModel).where(UserModel.id == request.user_id)
            )
            user = user_result.scalar_one_or_none()
            if user is None:
                return False, "用户不存在", None

            temp_password = _generate_temp_password()
            user.hashed_password = get_password_hash(temp_password)
            request.status = PasswordResetStatus.APPROVED
            request.reviewed_by = admin_id
            request.reviewed_at = datetime.now()

            await self.db.flush()
            await clear_login_failures_for_username(request.username)

            logger.info(
                "密码重置申请已通过: request_id=%s, user_id=%s, admin_id=%s",
                request_id,
                request.user_id,
                admin_id,
            )
            return True, "已通过审批，请线下安全告知用户临时密码", temp_password

        if action == "reject":
            request.status = PasswordResetStatus.REJECTED
            request.reviewed_by = admin_id
            request.reviewed_at = datetime.now()
            request.reject_reason = reject_reason
            await self.db.flush()

            logger.info(
                "密码重置申请已拒绝: request_id=%s, admin_id=%s",
                request_id,
                admin_id,
            )
            return True, "已拒绝该申请", None

        return False, "无效的操作", None

    async def get_pending_count(self) -> int:
        """获取待处理申请数量。"""
        result = await self.db.execute(
            select(func.count(PasswordResetRequestModel.id)).where(
                PasswordResetRequestModel.status == PasswordResetStatus.PENDING
            )
        )
        return result.scalar() or 0
