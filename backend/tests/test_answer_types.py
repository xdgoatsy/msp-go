"""测试 NUMERIC 和 TEXT 答案类型"""
import asyncio

from app.agents.core.math_equivalence import check_equivalence, detect_answer_type


async def test_numeric():
    """测试数值答案"""
    print("=== 测试数值答案 ===")

    # 测试 1: 精确匹配
    result = await check_equivalence("42", "42", "numeric")
    print(f"42 vs 42: {result.is_equivalent} (置信度: {result.confidence}, 原因: {result.reason})")

    # 测试 2: 小数匹配
    result = await check_equivalence("3.14", "3.14", "numeric")
    print(f"3.14 vs 3.14: {result.is_equivalent} (置信度: {result.confidence}, 原因: {result.reason})")

    # 测试 3: 容差内匹配
    result = await check_equivalence("3.14159", "3.14159265", "numeric")
    print(f"3.14159 vs 3.14159265: {result.is_equivalent} (置信度: {result.confidence}, 原因: {result.reason})")

    # 测试 4: 不匹配
    result = await check_equivalence("100", "99", "numeric")
    print(f"100 vs 99: {result.is_equivalent} (置信度: {result.confidence}, 原因: {result.reason})")

    # 测试 5: 负数
    result = await check_equivalence("-5", "-5", "numeric")
    print(f"-5 vs -5: {result.is_equivalent} (置信度: {result.confidence}, 原因: {result.reason})")

    print()


async def test_text():
    """测试文本答案"""
    print("=== 测试文本答案 ===")

    # 测试 1: 精确匹配
    result = await check_equivalence("连续", "连续", "text")
    print(f"'连续' vs '连续': {result.is_equivalent} (置信度: {result.confidence}, 原因: {result.reason})")

    # 测试 2: 带空格匹配
    result = await check_equivalence("  连续  ", "连续", "text")
    print(f"'  连续  ' vs '连续': {result.is_equivalent} (置信度: {result.confidence}, 原因: {result.reason})")

    # 测试 3: 大小写不敏感
    result = await check_equivalence("Continuous", "continuous", "text")
    print(f"'Continuous' vs 'continuous': {result.is_equivalent} (置信度: {result.confidence}, 原因: {result.reason})")

    # 测试 4: 不匹配
    result = await check_equivalence("连续", "不连续", "text")
    print(f"'连续' vs '不连续': {result.is_equivalent} (置信度: {result.confidence}, 原因: {result.reason})")

    # 测试 5: 多词文本
    result = await check_equivalence("函数  连续", "函数 连续", "text")
    print(f"'函数  连续' vs '函数 连续': {result.is_equivalent} (置信度: {result.confidence}, 原因: {result.reason})")

    print()


async def test_auto_detect():
    """测试自动检测"""
    print("=== 测试自动检测 ===")

    test_cases = [
        ("42", "数值"),
        ("3.14", "数值"),
        ("-100", "数值"),
        ("连续", "文本"),
        ("不连续", "文本"),
        ("x^2 + 1", "表达式"),
        ("{1, 2, 3}", "集合"),
        ("[0, 1)", "区间"),
        ("x = 5", "方程"),
    ]

    for answer, expected in test_cases:
        detected = detect_answer_type(answer)
        print(f"'{answer}' -> {detected.value} (期望: {expected})")

    print()


async def main():
    await test_numeric()
    await test_text()
    await test_auto_detect()
    print("✅ 所有测试完成")


if __name__ == "__main__":
    asyncio.run(main())
