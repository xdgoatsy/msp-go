"""
学生画像服务

提供学生画像的获取、生成和清除功能
"""

import logging
import re
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import (
    ContentAttemptModel,
    StudentProfileModel,
    XidianSnapshotModel,
)

logger = logging.getLogger(__name__)

_OUTER_FENCED_BLOCK_RE = re.compile(
    r"^\s*(?P<fence>```|~~~)[^\n]*\r?\n(?P<body>.*)\r?\n[ \t]*(?P=fence)\s*$",
    re.DOTALL,
)


def _unwrap_outer_fenced_block(text: str) -> str:
    """解包 LLM 常见的整段 ```markdown ... ``` 包裹，避免前端把整篇报告渲染成代码块。"""
    if not text:
        return text

    match = _OUTER_FENCED_BLOCK_RE.match(text)
    if not match:
        return text

    return match.group("body")


class StudentPortraitService:
    """学生画像服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_portrait(self, user_id: str) -> StudentProfileModel:
        """
        获取学生画像

        若 profile 不存在则创建空 profile
        """
        stmt = select(StudentProfileModel).where(
            StudentProfileModel.student_id == user_id
        )
        result = await self.db.execute(stmt)
        profile = result.scalar_one_or_none()

        if profile is None:
            profile = StudentProfileModel(student_id=user_id)
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)

        return profile

    async def generate_portrait(self, user_id: str) -> StudentProfileModel:
        """
        生成/重新生成学生画像

        收集学生数据 -> 构建 prompt -> 调用 LLM -> 持久化
        """
        profile = await self.get_portrait(user_id)
        student_data = await self._collect_student_data(user_id, profile)

        prompt = self._build_prompt(student_data)
        system_prompt = (
            "你是一位资深的高等数学教育专家，擅长分析学生的学习情况。"
            "请根据提供的学生数据，生成一份详细的学生画像分析报告。"
            "使用 Markdown 格式输出，包含清晰的标题和结构。"
            "请直接输出 Markdown 文本，不要使用 ```markdown 代码块（或任何代码块）包裹整篇内容。"
            "语言风格应专业但易于理解，给出具体可操作的建议。"
        )

        try:
            from app.agents.core.llm_client import create_llm_client_from_config

            llm = await create_llm_client_from_config("portrait")
            content = await llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=2000,
            )
        except Exception as e:
            logger.error(f"LLM 生成画像失败: {e}")
            raise

        profile.portrait_content = _unwrap_outer_fenced_block(content).strip()
        profile.portrait_generated_at = datetime.now()
        profile.portrait_version += 1
        await self.db.commit()
        await self.db.refresh(profile)

        return profile

    async def clear_portrait(self, user_id: str) -> None:
        """清除学生画像"""
        profile = await self.get_portrait(user_id)
        profile.portrait_content = None
        profile.portrait_generated_at = None
        profile.portrait_version = 0
        await self.db.commit()

    async def _collect_student_data(
        self, user_id: str, profile: StudentProfileModel
    ) -> dict:
        """聚合学生数据用于画像生成"""
        data: dict = {
            "total_exercises": profile.total_exercises,
            "correct_count": profile.correct_count,
            "correct_rate": (
                round(profile.correct_count / profile.total_exercises, 2)
                if profile.total_exercises > 0
                else 0
            ),
            "total_study_time_minutes": profile.total_study_time_minutes,
            "preferred_difficulty": profile.preferred_difficulty,
            "learning_pace": profile.learning_pace,
            "mastery_vector": profile.mastery_vector or {},
            "error_tendency": profile.error_tendency or {},
            "recent_concepts": profile.recent_concepts or [],
        }

        # 聚合西电成绩数据
        stmt = (
            select(XidianSnapshotModel)
            .where(
                XidianSnapshotModel.user_id == user_id,
                XidianSnapshotModel.data_type == "scores",
            )
            .order_by(XidianSnapshotModel.fetched_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        snapshot = result.scalar_one_or_none()
        if snapshot and snapshot.payload:
            scores = snapshot.payload.get("scores", [])
            data["xidian_scores"] = scores[:30]  # 限制数量

        # 聚合做题记录
        stmt = (
            select(ContentAttemptModel)
            .where(ContentAttemptModel.student_id == user_id)
            .order_by(ContentAttemptModel.started_at.desc())
            .limit(20)
        )
        result = await self.db.execute(stmt)
        attempts = result.scalars().all()
        if attempts:
            data["recent_attempts"] = [
                {
                    "is_correct": a.is_correct,
                    "score": a.score,
                    "time_spent_seconds": a.time_spent_seconds,
                }
                for a in attempts
            ]

        return data

    def _build_prompt(self, data: dict) -> str:
        """构建 LLM prompt"""
        parts = ["请根据以下学生学习数据，生成一份全面的学生画像分析报告。\n"]

        parts.append("## 学习概况")
        parts.append(f"- 总练习次数: {data['total_exercises']}")
        parts.append(f"- 正确次数: {data['correct_count']}")
        parts.append(f"- 正确率: {data['correct_rate']:.0%}")
        parts.append(
            f"- 总学习时长: {data['total_study_time_minutes']} 分钟"
        )
        parts.append(f"- 偏好难度: {data['preferred_difficulty']}")
        parts.append(f"- 学习节奏系数: {data['learning_pace']}")

        if data.get("mastery_vector"):
            parts.append("\n## 知识点掌握度")
            for concept, mastery in list(data["mastery_vector"].items())[:15]:
                parts.append(f"- {concept}: {mastery:.0%}")

        if data.get("error_tendency"):
            parts.append("\n## 错误倾向")
            for error_type, count in data["error_tendency"].items():
                parts.append(f"- {error_type}: {count} 次")

        if data.get("xidian_scores"):
            parts.append("\n## 教务系统成绩")
            for s in data["xidian_scores"]:
                name = s.get("name", "未知")
                score = s.get("score", "-")
                credit = s.get("credit", "-")
                parts.append(f"- {name}: {score} 分 (学分: {credit})")

        if data.get("recent_attempts"):
            parts.append("\n## 近期做题记录")
            correct = sum(1 for a in data["recent_attempts"] if a["is_correct"])
            total = len(data["recent_attempts"])
            parts.append(f"- 近 {total} 次做题正确率: {correct}/{total}")
            avg_time = sum(a["time_spent_seconds"] for a in data["recent_attempts"]) / total
            parts.append(f"- 平均用时: {avg_time:.0f} 秒")

        parts.append(
            "\n请从以下维度进行分析："
            "\n1. **学习概况总结** - 整体学习状态评估"
            "\n2. **知识掌握分析** - 强项与薄弱环节"
            "\n3. **问题诊断** - 常见错误模式和原因"
            "\n4. **学习风格** - 学习习惯和偏好特征"
            "\n5. **改进建议** - 具体可操作的提升方案"
        )

        return "\n".join(parts)


def get_student_portrait_service(db: AsyncSession) -> StudentPortraitService:
    """工厂函数：创建学生画像服务实例"""
    return StudentPortraitService(db)
