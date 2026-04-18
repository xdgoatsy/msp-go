"""
练习诊断领域模型单元测试
"""

from datetime import datetime

from app.domain.models.exercise import DiagnosisReport, ErrorType


class TestErrorType:
    """ErrorType 枚举测试"""

    def test_conceptual_value(self):
        assert ErrorType.CONCEPTUAL == "conceptual"

    def test_procedural_value(self):
        assert ErrorType.PROCEDURAL == "procedural"

    def test_logical_value(self):
        assert ErrorType.LOGICAL == "logical"

    def test_symbolic_value(self):
        assert ErrorType.SYMBOLIC == "symbolic"

    def test_calculation_value(self):
        assert ErrorType.CALCULATION == "calculation"

    def test_is_str_subclass(self):
        """ErrorType 是 str 的子类，可直接用于字符串比较"""
        assert isinstance(ErrorType.CONCEPTUAL, str)

    def test_string_representation(self):
        """字符串表示与值一致"""
        assert ErrorType.CONCEPTUAL.name == "CONCEPTUAL"
        # 值本身等于字符串
        assert ErrorType.LOGICAL.value == "logical"


class TestDiagnosisReportDefaults:
    """DiagnosisReport 默认值测试"""

    def test_creation_with_required_fields(self):
        """仅提供必填字段时使用默认值"""
        report = DiagnosisReport(id="r1", attempt_id="a1")
        assert report.id == "r1"
        assert report.attempt_id == "a1"

    def test_error_step_index_default(self):
        report = DiagnosisReport(id="r1", attempt_id="a1")
        assert report.error_step_index is None

    def test_bifurcation_point_default(self):
        report = DiagnosisReport(id="r1", attempt_id="a1")
        assert report.bifurcation_point is None

    def test_error_type_default(self):
        report = DiagnosisReport(id="r1", attempt_id="a1")
        assert report.error_type is None

    def test_error_subtype_default(self):
        report = DiagnosisReport(id="r1", attempt_id="a1")
        assert report.error_subtype is None

    def test_severity_default_is_medium(self):
        """严重程度默认值为 medium"""
        report = DiagnosisReport(id="r1", attempt_id="a1")
        assert report.severity == "medium"

    def test_related_concept_ids_default_empty(self):
        report = DiagnosisReport(id="r1", attempt_id="a1")
        assert report.related_concept_ids == []

    def test_related_misconception_ids_default_empty(self):
        report = DiagnosisReport(id="r1", attempt_id="a1")
        assert report.related_misconception_ids == []

    def test_explanation_default_empty_string(self):
        report = DiagnosisReport(id="r1", attempt_id="a1")
        assert report.explanation == ""

    def test_suggestion_default_empty_string(self):
        report = DiagnosisReport(id="r1", attempt_id="a1")
        assert report.suggestion == ""

    def test_recommended_resources_default_empty(self):
        report = DiagnosisReport(id="r1", attempt_id="a1")
        assert report.recommended_resources == []

    def test_created_at_is_datetime(self):
        report = DiagnosisReport(id="r1", attempt_id="a1")
        assert isinstance(report.created_at, datetime)


class TestDiagnosisReportAllFields:
    """DiagnosisReport 全字段创建测试"""

    def test_creation_with_all_fields(self):
        """提供所有字段时正确赋值"""
        now = datetime(2024, 6, 15, 10, 30, 0)
        report = DiagnosisReport(
            id="r2",
            attempt_id="a2",
            error_step_index=3,
            bifurcation_point="步骤3处符号使用错误",
            error_type=ErrorType.SYMBOLIC,
            error_subtype="sign_error",
            severity="high",
            related_concept_ids=["c1", "c2"],
            related_misconception_ids=["m1"],
            explanation="学生在移项时符号处理有误",
            suggestion="复习移项规则",
            recommended_resources=["res_001"],
            created_at=now,
        )
        assert report.id == "r2"
        assert report.attempt_id == "a2"
        assert report.error_step_index == 3
        assert report.bifurcation_point == "步骤3处符号使用错误"
        assert report.error_type == ErrorType.SYMBOLIC
        assert report.error_subtype == "sign_error"
        assert report.severity == "high"
        assert report.related_concept_ids == ["c1", "c2"]
        assert report.related_misconception_ids == ["m1"]
        assert report.explanation == "学生在移项时符号处理有误"
        assert report.suggestion == "复习移项规则"
        assert report.recommended_resources == ["res_001"]
        assert report.created_at == now

    def test_mutable_lists_are_independent(self):
        """不同实例的列表字段相互独立"""
        r1 = DiagnosisReport(id="r1", attempt_id="a1")
        r2 = DiagnosisReport(id="r2", attempt_id="a2")
        r1.related_concept_ids.append("c1")
        assert r2.related_concept_ids == []
