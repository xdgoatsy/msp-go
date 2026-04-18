import pytest

from app.agents.roles.math_solver import SymPySolver


class FakeLLM:
    def __init__(self):
        self.prompts: list[str] = []

    async def generate(self, prompt: str, temperature: float = 0.3) -> str:
        self.prompts.append(prompt)
        return "1. Integrate."


@pytest.mark.asyncio
async def test_generate_steps_handles_latex_bounds_and_literal_prompt_braces():
    llm = FakeLLM()
    solver = SymPySolver(llm_client=llm)

    problem = r"$\int_{0}^{2} (x+1)\,dx$"
    steps = await solver.generate_steps(problem, "4")

    assert steps == ["Integrate."]
    assert problem in llm.prompts[0]
    assert r"\begin{...}" in llm.prompts[0]


@pytest.mark.asyncio
async def test_execute_code_accepts_bare_final_expression():
    solver = SymPySolver(llm_client=FakeLLM())

    success, output = await solver.execute_code(
        "from sympy import *\n"
        "x = Symbol('x')\n"
        "integrate(x, (x, 0, 1))"
    )

    assert success is True
    assert output == r"\frac{1}{2}"


@pytest.mark.asyncio
async def test_execute_code_accepts_printed_final_expression():
    solver = SymPySolver(llm_client=FakeLLM())

    success, output = await solver.execute_code(
        "from sympy import *\n"
        "x = Symbol('x')\n"
        "print(integrate(x, (x, 0, 1)))"
    )

    assert success is True
    assert output == r"\frac{1}{2}"


@pytest.mark.asyncio
async def test_execute_code_accepts_common_answer_variable():
    solver = SymPySolver(llm_client=FakeLLM())

    success, output = await solver.execute_code(
        "from sympy import *\n"
        "x = Symbol('x')\n"
        "answer = integrate(x, (x, 0, 1))"
    )

    assert success is True
    assert output == r"\frac{1}{2}"


@pytest.mark.asyncio
async def test_execute_code_infers_computed_assignment_variable():
    solver = SymPySolver(llm_client=FakeLLM())

    success, output = await solver.execute_code(
        "from sympy import *\n"
        "x = Symbol('x')\n"
        "integral_value = integrate(x, (x, 0, 1))"
    )

    assert success is True
    assert output == r"\frac{1}{2}"
