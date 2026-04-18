"""
种子题库数据脚本

向 contents 表插入高等数学基础练习题，覆盖极限、导数、积分、级数等知识点。
每道题的 meta 字段包含标准答案（LaTeX）、答案类型、提示等。

用法：
    cd backend
    python -m scripts.seed_exercises
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

# 确保可以导入 app 模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.infrastructure.database.models import ContentModel, ContentStatus, ContentType
from app.infrastructure.database.session import get_session

# 教师 ID 占位（需要替换为实际的教师用户 ID）
SEED_TEACHER_ID = "00000000-0000-0000-0000-000000000001"

EXERCISES = [
    # ========== 极限 (5题) ==========
    {
        "title": "求极限：x→0 时 sin(x)/x",
        "body": "求极限 $\\lim_{x \\to 0} \\frac{\\sin x}{x}$",
        "difficulty": 0.2,
        "concept_ids": ["极限", "三角函数极限"],
        "tags": ["极限", "基础"],
        "meta": {
            "answer": "1",
            "answer_type": "expression",
            "type": "short_answer",
            "hints": ["这是一个重要极限", "可以用洛必达法则或等价无穷小"],
            "estimated_time_seconds": 120,
        },
    },
    {
        "title": "求极限：x→∞ 时 (1+1/x)^x",
        "body": "求极限 $\\lim_{x \\to \\infty} \\left(1 + \\frac{1}{x}\\right)^x$",
        "difficulty": 0.3,
        "concept_ids": ["极限", "自然常数"],
        "tags": ["极限", "基础"],
        "meta": {
            "answer": "e",
            "answer_type": "expression",
            "type": "short_answer",
            "hints": ["这是第二个重要极限", "结果是自然常数 e"],
            "estimated_time_seconds": 120,
        },
    },
    {
        "title": "求极限：洛必达法则",
        "body": "求极限 $\\lim_{x \\to 0} \\frac{e^x - 1}{x}$",
        "difficulty": 0.25,
        "concept_ids": ["极限", "洛必达法则"],
        "tags": ["极限", "基础"],
        "meta": {
            "answer": "1",
            "answer_type": "expression",
            "type": "short_answer",
            "hints": ["分子分母同时趋于0，可用洛必达法则"],
            "estimated_time_seconds": 150,
        },
    },
    {
        "title": "求极限：多项式比",
        "body": "求极限 $\\lim_{x \\to \\infty} \\frac{3x^2 + 2x - 1}{x^2 - 5}$",
        "difficulty": 0.2,
        "concept_ids": ["极限", "无穷大"],
        "tags": ["极限", "基础"],
        "meta": {
            "answer": "3",
            "answer_type": "expression",
            "type": "short_answer",
            "hints": ["分子分母同除以最高次幂 x²"],
            "estimated_time_seconds": 120,
        },
    },
    {
        "title": "求极限：夹逼准则",
        "body": "求极限 $\\lim_{x \\to 0} x^2 \\sin\\frac{1}{x}$",
        "difficulty": 0.35,
        "concept_ids": ["极限", "夹逼准则"],
        "tags": ["极限", "中等"],
        "meta": {
            "answer": "0",
            "answer_type": "expression",
            "type": "short_answer",
            "hints": ["|sin(1/x)| ≤ 1，所以 |x²sin(1/x)| ≤ x²"],
            "estimated_time_seconds": 180,
        },
    },
    # ========== 导数 (5题) ==========
    {
        "title": "求导：幂函数",
        "body": "求 $f(x) = x^3 + 2x^2 - 5x + 1$ 的导数 $f'(x)$",
        "difficulty": 0.15,
        "concept_ids": ["导数", "幂函数求导"],
        "tags": ["导数", "基础"],
        "meta": {
            "answer": "3x^2 + 4x - 5",
            "answer_type": "expression",
            "type": "short_answer",
            "hints": ["使用幂函数求导公式 (x^n)' = nx^{n-1}"],
            "estimated_time_seconds": 90,
        },
    },
    {
        "title": "求导：三角函数",
        "body": "求 $f(x) = \\sin(2x) + \\cos(3x)$ 的导数 $f'(x)$",
        "difficulty": 0.3,
        "concept_ids": ["导数", "三角函数求导", "链式法则"],
        "tags": ["导数", "中等"],
        "meta": {
            "answer": "2\\cos(2x) - 3\\sin(3x)",
            "answer_type": "expression",
            "type": "short_answer",
            "hints": ["使用链式法则", "(sin u)' = cos u · u'"],
            "estimated_time_seconds": 150,
        },
    },
    {
        "title": "求导：乘法法则",
        "body": "求 $f(x) = x^2 e^x$ 的导数 $f'(x)$",
        "difficulty": 0.35,
        "concept_ids": ["导数", "乘法法则"],
        "tags": ["导数", "中等"],
        "meta": {
            "answer": "2x e^x + x^2 e^x",
            "answer_type": "expression",
            "type": "short_answer",
            "hints": ["使用乘法法则 (uv)' = u'v + uv'"],
            "estimated_time_seconds": 150,
        },
    },
    {
        "title": "求导：对数函数",
        "body": "求 $f(x) = \\ln(x^2 + 1)$ 的导数 $f'(x)$",
        "difficulty": 0.3,
        "concept_ids": ["导数", "对数函数求导", "链式法则"],
        "tags": ["导数", "中等"],
        "meta": {
            "answer": "\\frac{2x}{x^2 + 1}",
            "answer_type": "expression",
            "type": "short_answer",
            "hints": ["使用链式法则", "(ln u)' = u'/u"],
            "estimated_time_seconds": 120,
        },
    },
    {
        "title": "求导：隐函数",
        "body": "设 $x^2 + y^2 = 25$，求 $\\frac{dy}{dx}$",
        "difficulty": 0.45,
        "concept_ids": ["导数", "隐函数求导"],
        "tags": ["导数", "进阶"],
        "meta": {
            "answer": "-\\frac{x}{y}",
            "answer_type": "expression",
            "type": "short_answer",
            "hints": ["对等式两边同时对 x 求导", "注意 y 是 x 的函数"],
            "estimated_time_seconds": 180,
        },
    },
    # ========== 积分 (5题) ==========
    {
        "title": "不定积分：幂函数",
        "body": "求不定积分 $\\int x^2 \\, dx$",
        "difficulty": 0.15,
        "concept_ids": ["积分", "不定积分", "幂函数积分"],
        "tags": ["积分", "基础"],
        "meta": {
            "answer": "\\frac{x^3}{3} + C",
            "answer_type": "expression",
            "type": "short_answer",
            "hints": ["使用幂函数积分公式 ∫x^n dx = x^{n+1}/(n+1) + C"],
            "estimated_time_seconds": 60,
        },
    },
    {
        "title": "不定积分：三角函数",
        "body": "求不定积分 $\\int \\cos(x) \\, dx$",
        "difficulty": 0.15,
        "concept_ids": ["积分", "不定积分", "三角函数积分"],
        "tags": ["积分", "基础"],
        "meta": {
            "answer": "\\sin(x) + C",
            "answer_type": "expression",
            "type": "short_answer",
            "hints": ["cos(x) 的原函数是 sin(x)"],
            "estimated_time_seconds": 60,
        },
    },
    {
        "title": "不定积分：换元法",
        "body": "求不定积分 $\\int 2x \\cdot e^{x^2} \\, dx$",
        "difficulty": 0.4,
        "concept_ids": ["积分", "不定积分", "换元积分法"],
        "tags": ["积分", "中等"],
        "meta": {
            "answer": "e^{x^2} + C",
            "answer_type": "expression",
            "type": "short_answer",
            "hints": ["令 u = x²，则 du = 2x dx"],
            "estimated_time_seconds": 180,
        },
    },
    {
        "title": "定积分：基本计算",
        "body": "求定积分 $\\int_0^1 3x^2 \\, dx$",
        "difficulty": 0.2,
        "concept_ids": ["积分", "定积分"],
        "tags": ["积分", "基础"],
        "meta": {
            "answer": "1",
            "answer_type": "expression",
            "type": "short_answer",
            "hints": ["先求原函数 x³，再代入上下限"],
            "estimated_time_seconds": 120,
        },
    },
    {
        "title": "定积分：分部积分",
        "body": "求定积分 $\\int_0^1 x e^x \\, dx$",
        "difficulty": 0.5,
        "concept_ids": ["积分", "定积分", "分部积分法"],
        "tags": ["积分", "进阶"],
        "meta": {
            "answer": "1",
            "answer_type": "expression",
            "type": "short_answer",
            "hints": ["使用分部积分法", "令 u=x, dv=e^x dx"],
            "estimated_time_seconds": 240,
        },
    },
    # ========== 级数 (5题) ==========
    {
        "title": "等比级数求和",
        "body": "求级数 $\\sum_{n=0}^{\\infty} \\left(\\frac{1}{2}\\right)^n$ 的和",
        "difficulty": 0.25,
        "concept_ids": ["级数", "等比级数"],
        "tags": ["级数", "基础"],
        "meta": {
            "answer": "2",
            "answer_type": "expression",
            "type": "short_answer",
            "hints": ["等比级数求和公式 S = a/(1-r)，其中 |r| < 1"],
            "estimated_time_seconds": 120,
        },
    },
    {
        "title": "级数收敛性判断",
        "body": "判断级数 $\\sum_{n=1}^{\\infty} \\frac{1}{n^2}$ 是否收敛，若收敛求其和",
        "difficulty": 0.4,
        "concept_ids": ["级数", "p级数", "收敛性"],
        "tags": ["级数", "中等"],
        "meta": {
            "answer": "\\frac{\\pi^2}{6}",
            "answer_type": "expression",
            "type": "short_answer",
            "hints": ["这是 p=2 的 p 级数，收敛", "巴塞尔问题的结果"],
            "estimated_time_seconds": 180,
        },
    },
    {
        "title": "泰勒展开",
        "body": "写出 $e^x$ 在 $x=0$ 处的泰勒展开式（前4项）",
        "difficulty": 0.35,
        "concept_ids": ["级数", "泰勒展开"],
        "tags": ["级数", "中等"],
        "meta": {
            "answer": "1 + x + \\frac{x^2}{2} + \\frac{x^3}{6}",
            "answer_type": "expression",
            "type": "short_answer",
            "hints": ["e^x 的各阶导数都是 e^x", "在 x=0 处值为 1"],
            "estimated_time_seconds": 180,
        },
    },
    {
        "title": "交错级数",
        "body": "求级数 $\\sum_{n=1}^{\\infty} \\frac{(-1)^{n+1}}{n} = 1 - \\frac{1}{2} + \\frac{1}{3} - \\cdots$ 的和",
        "difficulty": 0.5,
        "concept_ids": ["级数", "交错级数"],
        "tags": ["级数", "进阶"],
        "meta": {
            "answer": "\\ln 2",
            "answer_type": "expression",
            "type": "short_answer",
            "hints": ["这是 ln(1+x) 在 x=1 处的泰勒展开"],
            "estimated_time_seconds": 240,
        },
    },
    {
        "title": "幂级数收敛半径",
        "body": "求幂级数 $\\sum_{n=0}^{\\infty} \\frac{x^n}{n!}$ 的收敛半径",
        "difficulty": 0.35,
        "concept_ids": ["级数", "幂级数", "收敛半径"],
        "tags": ["级数", "中等"],
        "meta": {
            "answer": "\\infty",
            "answer_type": "expression",
            "type": "short_answer",
            "hints": ["使用比值判别法", "这就是 e^x 的泰勒展开"],
            "estimated_time_seconds": 180,
        },
    },
]


async def seed():
    """插入种子数据"""
    async for db in get_session():
        # 检查是否已有种子数据
        count_stmt = select(ContentModel).where(
            ContentModel.type == ContentType.PROBLEM,
            ContentModel.tags.contains(["基础"]),
        ).limit(1)
        existing = await db.execute(count_stmt)
        if existing.scalar_one_or_none():
            print("种子数据已存在，跳过插入")
            return

        for ex in EXERCISES:
            model = ContentModel(
                id=str(uuid4()),
                type=ContentType.PROBLEM,
                owner_teacher_id=SEED_TEACHER_ID,
                status=ContentStatus.PUBLISHED,
                title=ex["title"],
                body=ex["body"],
                difficulty=ex["difficulty"],
                concept_ids=ex["concept_ids"],
                tags=ex["tags"],
                meta=ex["meta"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                published_at=datetime.now(),
            )
            db.add(model)

        await db.commit()
        print(f"成功插入 {len(EXERCISES)} 道种子题目")


if __name__ == "__main__":
    asyncio.run(seed())

