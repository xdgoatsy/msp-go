"""
BKT（Bayesian Knowledge Tracing）领域模型

面向 CPU 环境的轻量级知识状态更新逻辑，适用于实时与高并发场景。
"""

from dataclasses import dataclass
from math import exp

_EPSILON = 1e-6

# 默认遗忘衰减系数（每天），值越大遗忘越快
DEFAULT_LAMBDA_DECAY = 0.05


def clamp_probability(
    value: float,
    *,
    floor: float = 0.001,
    ceiling: float = 0.999,
) -> float:
    """将概率约束在有效区间内，避免数值不稳定。"""
    if value < floor:
        return floor
    if value > ceiling:
        return ceiling
    return value


@dataclass(frozen=True, slots=True)
class BKTParameters:
    """BKT 参数集。"""

    p_l0: float = 0.25  # 初始掌握概率
    p_t: float = 0.12   # 学习迁移概率
    p_g: float = 0.20   # 猜对概率
    p_s: float = 0.10   # 失误概率

    def normalized(self) -> "BKTParameters":
        """归一化参数，确保各概率可用。"""
        return BKTParameters(
            p_l0=clamp_probability(self.p_l0),
            p_t=clamp_probability(self.p_t, floor=0.001, ceiling=0.6),
            p_g=clamp_probability(self.p_g, floor=0.001, ceiling=0.4),
            p_s=clamp_probability(self.p_s, floor=0.001, ceiling=0.4),
        )

    def personalized(
        self,
        *,
        preferred_difficulty: float,
        learning_pace: float,
        item_difficulty: float,
        error_type: str | None = None,
    ) -> "BKTParameters":
        """
        基于学生画像与题目难度生成个性化参数。

        - preferred_difficulty：学生偏好难度
        - learning_pace：学习节奏
        - item_difficulty：当前题目难度
        - error_type：错误类型（仅在答错时辅助微调）
        """
        base = self.normalized()

        preferred = clamp_probability(preferred_difficulty, floor=0.0, ceiling=1.0)
        difficulty = clamp_probability(item_difficulty, floor=0.0, ceiling=1.0)
        pace = max(0.2, learning_pace)

        difficulty_bias = difficulty - preferred
        pace_delta = max(-0.5, min(0.8, pace - 1.0))

        p_l0 = base.p_l0 + 0.10 * (preferred - difficulty) + 0.05 * pace_delta
        p_t = base.p_t * (1.0 + 0.35 * pace_delta) * (1.0 - 0.15 * max(difficulty_bias, 0.0))
        p_g = base.p_g + 0.08 * difficulty_bias
        p_s = base.p_s + 0.12 * difficulty_bias - 0.03 * pace_delta

        # 错误类型微调：
        # - 计算/符号错误更可能是 slip（会做但失误）
        # - 概念/逻辑错误更偏向未掌握（降低猜对概率）
        if error_type in {"calculation", "symbolic"}:
            p_s += 0.04
        elif error_type in {"conceptual", "logical"}:
            p_g -= 0.03

        return BKTParameters(
            p_l0=p_l0,
            p_t=p_t,
            p_g=p_g,
            p_s=p_s,
        ).normalized()


@dataclass(frozen=True, slots=True)
class BKTUpdateResult:
    """单次作答后的 BKT 更新结果。"""

    posterior_before_transition: float
    posterior_after_transition: float
    p_t: float
    p_g: float
    p_s: float
    confidence: float
    delta: float


def bkt_update(
    *,
    prior_mastery: float,
    is_correct: bool,
    params: BKTParameters,
    attempt_count: int,
) -> BKTUpdateResult:
    """
    执行一次标准 BKT 更新。

    先根据观测结果更新后验，再加入学习迁移项。
    """
    normalized = params.normalized()
    prior = clamp_probability(prior_mastery)

    if is_correct:
        numerator = prior * (1.0 - normalized.p_s)
        denominator = numerator + (1.0 - prior) * normalized.p_g
    else:
        numerator = prior * normalized.p_s
        denominator = numerator + (1.0 - prior) * (1.0 - normalized.p_g)

    posterior_obs = clamp_probability(numerator / max(denominator, _EPSILON))
    posterior_next = clamp_probability(
        posterior_obs + (1.0 - posterior_obs) * normalized.p_t,
    )

    effective_attempts = max(attempt_count, 0) + 1
    confidence = clamp_probability(
        1.0 - exp(-effective_attempts / 6.0),
        floor=0.0,
        ceiling=1.0,
    )

    return BKTUpdateResult(
        posterior_before_transition=posterior_obs,
        posterior_after_transition=posterior_next,
        p_t=normalized.p_t,
        p_g=normalized.p_g,
        p_s=normalized.p_s,
        confidence=confidence,
        delta=round(posterior_next - prior, 4),
    )


def apply_forgetting(
    mastery: float,
    days_since_last: float,
    *,
    lambda_decay: float = DEFAULT_LAMBDA_DECAY,
    floor: float = 0.25,
) -> float:
    """
    对掌握度施加时间衰减（遗忘因子）。

    基于 Ebbinghaus 遗忘曲线的指数衰减模型：
        decayed = floor + (mastery - floor) * exp(-λ * days)

    - mastery：当前掌握度
    - days_since_last：距上次练习的天数
    - lambda_decay：衰减系数，越大遗忘越快
    - floor：衰减下限（默认 p_l0 = 0.25），不会低于初始掌握概率
    """
    if days_since_last <= 0 or mastery <= floor:
        return mastery

    decayed = floor + (mastery - floor) * exp(-lambda_decay * days_since_last)
    return clamp_probability(decayed)
