"""
BKT 领域模型单元测试

覆盖核心算法：bkt_update, personalized, clamp_probability, apply_forgetting
"""

from math import exp

from app.domain.models.bkt import (
    DEFAULT_LAMBDA_DECAY,
    BKTParameters,
    BKTUpdateResult,
    apply_forgetting,
    bkt_update,
    clamp_probability,
)

# =========================================================================
# clamp_probability
# =========================================================================


class TestClampProbability:
    def test_within_range(self):
        assert clamp_probability(0.5) == 0.5

    def test_below_floor(self):
        assert clamp_probability(-0.1) == 0.001

    def test_above_ceiling(self):
        assert clamp_probability(1.5) == 0.999

    def test_custom_floor_ceiling(self):
        assert clamp_probability(0.0, floor=0.0, ceiling=1.0) == 0.0
        assert clamp_probability(1.0, floor=0.0, ceiling=1.0) == 1.0

    def test_exact_boundary(self):
        assert clamp_probability(0.001) == 0.001
        assert clamp_probability(0.999) == 0.999


# =========================================================================
# BKTParameters
# =========================================================================


class TestBKTParameters:
    def test_defaults(self):
        p = BKTParameters()
        assert p.p_l0 == 0.25
        assert p.p_t == 0.12
        assert p.p_g == 0.20
        assert p.p_s == 0.10

    def test_normalized_clamps(self):
        p = BKTParameters(p_l0=-1.0, p_t=2.0, p_g=0.8, p_s=-0.5)
        n = p.normalized()
        assert n.p_l0 == 0.001
        assert n.p_t == 0.6  # ceiling
        assert n.p_g == 0.4  # ceiling
        assert n.p_s == 0.001  # floor
    def test_personalized_high_difficulty(self):
        """高难度题目应降低 p_l0、增加 p_g"""
        p = BKTParameters()
        result = p.personalized(
            preferred_difficulty=0.3,
            learning_pace=1.0,
            item_difficulty=0.8,
        )
        assert result.p_l0 < p.p_l0  # 难题降低初始掌握
        assert result.p_g > p.normalized().p_g  # 难题更可能猜对

    def test_personalized_error_type_calculation(self):
        """计算错误应增加 p_s"""
        p = BKTParameters()
        base = p.personalized(
            preferred_difficulty=0.5,
            learning_pace=1.0,
            item_difficulty=0.5,
        )
        with_calc_error = p.personalized(
            preferred_difficulty=0.5,
            learning_pace=1.0,
            item_difficulty=0.5,
            error_type="calculation",
        )
        assert with_calc_error.p_s > base.p_s

    def test_personalized_error_type_conceptual(self):
        """概念错误应降低 p_g"""
        p = BKTParameters()
        base = p.personalized(
            preferred_difficulty=0.5,
            learning_pace=1.0,
            item_difficulty=0.5,
        )
        with_concept_error = p.personalized(
            preferred_difficulty=0.5,
            learning_pace=1.0,
            item_difficulty=0.5,
            error_type="conceptual",
        )
        assert with_concept_error.p_g < base.p_g


# =========================================================================
# bkt_update
# =========================================================================


class TestBKTUpdate:
    def test_correct_answer_increases_mastery(self):
        """答对应提升掌握度"""
        result = bkt_update(
            prior_mastery=0.5,
            is_correct=True,
            params=BKTParameters(),
            attempt_count=0,
        )
        assert result.posterior_after_transition > 0.5
        assert result.delta > 0

    def test_incorrect_answer_decreases_mastery(self):
        """答错应降低掌握度（或至少不大幅提升）"""
        result = bkt_update(
            prior_mastery=0.5,
            is_correct=False,
            params=BKTParameters(),
            attempt_count=0,
        )
        # 答错后后验应低于先验（考虑迁移项可能略微提升）
        assert result.posterior_before_transition < 0.5

    def test_confidence_increases_with_attempts(self):
        """置信度应随练习次数增加"""
        r1 = bkt_update(prior_mastery=0.5, is_correct=True, params=BKTParameters(), attempt_count=0)
        r2 = bkt_update(prior_mastery=0.5, is_correct=True, params=BKTParameters(), attempt_count=10)
        assert r2.confidence > r1.confidence

    def test_result_contains_params(self):
        """结果应包含归一化后的参数"""
        result = bkt_update(
            prior_mastery=0.5,
            is_correct=True,
            params=BKTParameters(),
            attempt_count=0,
        )
        assert isinstance(result, BKTUpdateResult)
        assert 0 < result.p_t < 1
        assert 0 < result.p_g < 1
        assert 0 < result.p_s < 1

    def test_extreme_prior_low(self):
        """极低先验 + 答对应显著提升"""
        result = bkt_update(
            prior_mastery=0.01,
            is_correct=True,
            params=BKTParameters(),
            attempt_count=5,
        )
        assert result.posterior_after_transition > 0.01

    def test_extreme_prior_high(self):
        """极高先验 + 答错不应崩溃"""
        result = bkt_update(
            prior_mastery=0.99,
            is_correct=False,
            params=BKTParameters(),
            attempt_count=20,
        )
        assert 0 < result.posterior_after_transition < 1

    def test_multiple_correct_converges(self):
        """连续答对应趋近 1"""
        mastery = 0.25
        for _ in range(20):
            r = bkt_update(
                prior_mastery=mastery,
                is_correct=True,
                params=BKTParameters(),
                attempt_count=0,
            )
            mastery = r.posterior_after_transition
        assert mastery > 0.9


# =========================================================================
# apply_forgetting
# =========================================================================


class TestApplyForgetting:
    def test_no_decay_when_zero_days(self):
        """0 天不衰减"""
        assert apply_forgetting(0.8, 0.0) == 0.8

    def test_no_decay_when_negative_days(self):
        """负天数不衰减"""
        assert apply_forgetting(0.8, -5.0) == 0.8

    def test_decay_after_one_day(self):
        """1 天后应有轻微衰减"""
        result = apply_forgetting(0.8, 1.0)
        assert result < 0.8
        assert result > 0.25  # 不低于 floor

    def test_decay_after_long_time(self):
        """长时间后应趋近 floor"""
        result = apply_forgetting(0.9, 100.0)
        assert abs(result - 0.25) < 0.01

    def test_floor_respected(self):
        """衰减不低于 floor"""
        result = apply_forgetting(0.5, 1000.0, floor=0.3)
        assert result >= 0.3

    def test_custom_lambda(self):
        """更大的 lambda 衰减更快"""
        slow = apply_forgetting(0.8, 10.0, lambda_decay=0.01)
        fast = apply_forgetting(0.8, 10.0, lambda_decay=0.1)
        assert fast < slow

    def test_already_at_floor(self):
        """已在 floor 不再衰减"""
        assert apply_forgetting(0.25, 10.0, floor=0.25) == 0.25

    def test_below_floor_no_change(self):
        """低于 floor 不衰减"""
        assert apply_forgetting(0.1, 10.0, floor=0.25) == 0.1

    def test_formula_correctness(self):
        """验证公式正确性"""
        mastery = 0.8
        days = 5.0
        floor = 0.25
        expected = floor + (mastery - floor) * exp(-DEFAULT_LAMBDA_DECAY * days)
        result = apply_forgetting(mastery, days, floor=floor)
        assert abs(result - expected) < 1e-6
