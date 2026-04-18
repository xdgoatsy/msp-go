"""
AI 配置领域模型单元测试
"""

from datetime import datetime

import pytest

from app.domain.models.ai_config import (
    AGENT_TYPE_DISPLAY_NAMES,
    AgentModelConfig,
    AgentType,
    LLMModel,
    LLMProvider,
    ResolvedAgentConfig,
)


class TestAgentTypeConstants:
    """AgentType 常量测试"""

    def test_math_solver_value(self):
        assert AgentType.MATH_SOLVER == "math_solver"

    def test_tutor_value(self):
        assert AgentType.TUTOR == "tutor"

    def test_diagnostician_value(self):
        assert AgentType.DIAGNOSTICIAN == "diagnostician"

    def test_portrait_value(self):
        assert AgentType.PORTRAIT == "portrait"


class TestAgentTypeAllTypes:
    """AgentType.all_types() 测试"""

    def test_returns_four_types(self):
        """返回全部 4 个类型"""
        types = AgentType.all_types()
        assert len(types) == 4

    def test_contains_all_constants(self):
        """包含所有已定义常量"""
        types = AgentType.all_types()
        assert AgentType.MATH_SOLVER in types
        assert AgentType.TUTOR in types
        assert AgentType.DIAGNOSTICIAN in types
        assert AgentType.PORTRAIT in types

    def test_returns_list(self):
        assert isinstance(AgentType.all_types(), list)


class TestAgentTypeIsValid:
    """AgentType.is_valid() 测试"""

    def test_valid_math_solver(self):
        assert AgentType.is_valid("math_solver") is True

    def test_valid_tutor(self):
        assert AgentType.is_valid("tutor") is True

    def test_valid_diagnostician(self):
        assert AgentType.is_valid("diagnostician") is True

    def test_valid_portrait(self):
        assert AgentType.is_valid("portrait") is True

    def test_invalid_empty_string(self):
        assert AgentType.is_valid("") is False

    def test_invalid_unknown_type(self):
        assert AgentType.is_valid("unknown_agent") is False

    def test_invalid_partial_match(self):
        """部分匹配不算有效"""
        assert AgentType.is_valid("math") is False


class TestAgentTypeDisplayNames:
    """AGENT_TYPE_DISPLAY_NAMES 映射测试"""

    def test_has_entry_for_all_agent_types(self):
        """所有智能体类型都有对应的显示名称"""
        for agent_type in AgentType.all_types():
            assert agent_type in AGENT_TYPE_DISPLAY_NAMES, (
                f"{agent_type} 缺少显示名称"
            )

    def test_display_names_are_strings(self):
        """显示名称均为字符串"""
        for name in AGENT_TYPE_DISPLAY_NAMES.values():
            assert isinstance(name, str)
            assert len(name) > 0

    def test_math_solver_display_name(self):
        assert AGENT_TYPE_DISPLAY_NAMES[AgentType.MATH_SOLVER] == "数学求解智能体"

    def test_tutor_display_name(self):
        assert AGENT_TYPE_DISPLAY_NAMES[AgentType.TUTOR] == "导师智能体"

    def test_diagnostician_display_name(self):
        assert AGENT_TYPE_DISPLAY_NAMES[AgentType.DIAGNOSTICIAN] == "诊断智能体"

    def test_portrait_display_name(self):
        assert AGENT_TYPE_DISPLAY_NAMES[AgentType.PORTRAIT] == "学生画像"


class TestLLMProvider:
    """LLMProvider 创建测试"""

    def test_creation_with_required_fields(self):
        """提供必填字段时正确创建"""
        provider = LLMProvider(
            id="p1",
            name="DeepSeek",
            code="deepseek",
            base_url="https://api.deepseek.com/v1",
        )
        assert provider.id == "p1"
        assert provider.name == "DeepSeek"
        assert provider.code == "deepseek"
        assert provider.base_url == "https://api.deepseek.com/v1"

    def test_is_active_default_true(self):
        provider = LLMProvider(
            id="p1", name="X", code="x", base_url="https://x.com"
        )
        assert provider.is_active is True

    def test_description_default_none(self):
        provider = LLMProvider(
            id="p1", name="X", code="x", base_url="https://x.com"
        )
        assert provider.description is None

    def test_timestamps_are_datetime(self):
        provider = LLMProvider(
            id="p1", name="X", code="x", base_url="https://x.com"
        )
        assert isinstance(provider.created_at, datetime)
        assert isinstance(provider.updated_at, datetime)


class TestLLMModel:
    """LLMModel 创建测试"""

    def test_creation_with_required_fields(self):
        model = LLMModel(
            id="m1",
            provider_id="p1",
            name="deepseek-chat",
            model_id="deepseek-chat",
        )
        assert model.id == "m1"
        assert model.provider_id == "p1"
        assert model.name == "deepseek-chat"
        assert model.model_id == "deepseek-chat"

    def test_default_temperature(self):
        model = LLMModel(id="m1", provider_id="p1", name="x", model_id="x")
        assert model.default_temperature == pytest.approx(0.7)

    def test_default_max_tokens_none(self):
        model = LLMModel(id="m1", provider_id="p1", name="x", model_id="x")
        assert model.default_max_tokens is None

    def test_default_timeout(self):
        model = LLMModel(id="m1", provider_id="p1", name="x", model_id="x")
        assert model.default_timeout == 60

    def test_default_max_retries(self):
        model = LLMModel(id="m1", provider_id="p1", name="x", model_id="x")
        assert model.default_max_retries == 3

    def test_is_active_default_true(self):
        model = LLMModel(id="m1", provider_id="p1", name="x", model_id="x")
        assert model.is_active is True

    def test_is_default_default_false(self):
        model = LLMModel(id="m1", provider_id="p1", name="x", model_id="x")
        assert model.is_default is False

    def test_capabilities_default_empty_dict(self):
        model = LLMModel(id="m1", provider_id="p1", name="x", model_id="x")
        assert model.capabilities == {}

    def test_provider_fields_default_none(self):
        model = LLMModel(id="m1", provider_id="p1", name="x", model_id="x")
        assert model.provider_name is None
        assert model.provider_code is None
        assert model.provider_base_url is None


class TestAgentModelConfig:
    """AgentModelConfig 创建测试"""

    def test_creation_with_required_field(self):
        config = AgentModelConfig(id="ac1", agent_type="math_solver")
        assert config.id == "ac1"
        assert config.agent_type == "math_solver"

    def test_optional_overrides_default_none(self):
        config = AgentModelConfig(id="ac1", agent_type="tutor")
        assert config.model_id is None
        assert config.temperature_override is None
        assert config.max_tokens_override is None
        assert config.top_p_override is None
        assert config.timeout_override is None
        assert config.max_retries_override is None

    def test_extra_config_default_empty(self):
        config = AgentModelConfig(id="ac1", agent_type="tutor")
        assert config.extra_config == {}

    def test_is_active_default_true(self):
        config = AgentModelConfig(id="ac1", agent_type="tutor")
        assert config.is_active is True

    def test_creation_with_overrides(self):
        config = AgentModelConfig(
            id="ac2",
            agent_type="diagnostician",
            model_id="m1",
            temperature_override=0.3,
            max_tokens_override=2048,
            timeout_override=120,
        )
        assert config.model_id == "m1"
        assert config.temperature_override == pytest.approx(0.3)
        assert config.max_tokens_override == 2048
        assert config.timeout_override == 120


class TestResolvedAgentConfig:
    """ResolvedAgentConfig 创建测试"""

    def _make(self, **kwargs):
        defaults = {
            "agent_type": "math_solver",
            "api_base": "https://api.deepseek.com/v1",
            "api_key": "test-key-placeholder",
            "model_name": "deepseek-chat",
            "temperature": 0.7,
            "timeout": 60,
            "max_retries": 3,
        }
        defaults.update(kwargs)
        return ResolvedAgentConfig(**defaults)

    def test_creation_with_required_fields(self):
        config = self._make()
        assert config.agent_type == "math_solver"
        assert config.api_base == "https://api.deepseek.com/v1"
        assert config.api_key == "test-key-placeholder"
        assert config.model_name == "deepseek-chat"
        assert config.temperature == pytest.approx(0.7)
        assert config.timeout == 60
        assert config.max_retries == 3

    def test_max_tokens_default_none(self):
        config = self._make()
        assert config.max_tokens is None

    def test_top_p_default_none(self):
        config = self._make()
        assert config.top_p is None

    def test_extra_config_default_empty(self):
        config = self._make()
        assert config.extra_config == {}

    def test_source_fields_default_none(self):
        """来源信息字段默认为 None"""
        config = self._make()
        assert config.provider_id is None
        assert config.provider_name is None
        assert config.model_id is None

    def test_creation_with_all_fields(self):
        config = self._make(
            max_tokens=4096,
            top_p=0.9,
            extra_config={"stream": True},
            provider_id="p1",
            provider_name="DeepSeek",
            model_id="m1",
        )
        assert config.max_tokens == 4096
        assert config.top_p == pytest.approx(0.9)
        assert config.extra_config == {"stream": True}
        assert config.provider_id == "p1"
        assert config.provider_name == "DeepSeek"
        assert config.model_id == "m1"
