import pytest

from app.agents.roles.tutor import TutorAgent
from app.agents.workflow import nodes


class FakeStreamingAgent:
    async def stream_process(self, state):
        yield {"content": "正在求解中...\n\n"}
        yield {"content": "答案"}

    async def process(self, state):
        raise AssertionError("process should not be called after streaming succeeds")

    def create_message(self, content: str, msg_type: str = "solution", **metadata):
        return {
            "role": "assistant",
            "content": content,
            "metadata": {
                "type": msg_type,
                "agent": "math_solver",
                **metadata,
            },
        }


class FakeFallbackAgent:
    async def stream_process(self, state):
        yield {"content": "partial"}
        raise RuntimeError("stream failed")

    async def process(self, state):
        return {
            **state,
            "message_stream": [
                self.create_message("fallback", msg_type="solution")
            ],
        }

    def create_message(self, content: str, msg_type: str = "solution", **metadata):
        return {
            "role": "assistant",
            "content": content,
            "metadata": {
                "type": msg_type,
                "agent": "math_solver",
                **metadata,
            },
        }


class FakeTutorLLM:
    def __init__(self, chunks):
        self.chunks = chunks
        self.stream_generate_calls = []

    async def stream_generate(self, **kwargs):
        self.stream_generate_calls.append(kwargs)
        for chunk in self.chunks:
            yield chunk

    async def generate_with_history(self, *args, **kwargs):
        raise AssertionError("stream_process should not use generate_with_history")


class FailingTutorLLM:
    async def stream_generate(self, **kwargs):
        raise RuntimeError("boom")
        yield ""  # pragma: no cover

    async def generate_with_history(self, *args, **kwargs):
        raise AssertionError("stream_process should not use generate_with_history")


@pytest.mark.asyncio
async def test_math_solver_node_marks_completed_stream_message(monkeypatch):
    monkeypatch.setattr(
        nodes,
        "_get_agent",
        lambda name, state: FakeStreamingAgent(),
    )
    streamed_events = []

    state = await nodes.math_solver_node({}, streamed_events.append)

    assert [event["content"] for event in streamed_events] == [
        "正在求解中...\n\n",
        "答案",
    ]
    assert state["message_stream"][0]["content"] == "正在求解中...\n\n答案"
    assert state["message_stream"][0]["metadata"]["streaming"] is True


@pytest.mark.asyncio
async def test_math_solver_node_keeps_fallback_message_emit_eligible(monkeypatch):
    monkeypatch.setattr(
        nodes,
        "_get_agent",
        lambda name, state: FakeFallbackAgent(),
    )
    streamed_events = []

    state = await nodes.math_solver_node({}, streamed_events.append)

    assert [event["content"] for event in streamed_events] == ["partial"]
    assert state["message_stream"][0]["content"] == "fallback"
    assert state["message_stream"][0]["metadata"]["streaming"] is False


@pytest.mark.asyncio
async def test_tutor_stream_process_yields_llm_chunks_without_simulated_splitting():
    long_chunk = "这是一个超过二十个字符的流式块，用来确认不会被重新切分。"
    llm = FakeTutorLLM([long_chunk, "第二段"])
    agent = TutorAgent(llm_client=llm)

    events = [
        event
        async for event in agent.stream_process(
            {
                "last_message": "讲讲极限的直观理解",
                "student_context": {},
                "interaction_history": [],
            }
        )
    ]

    assert [event["content"] for event in events] == [long_chunk, "第二段"]
    assert all(event["agent"] == "tutor" for event in events)
    assert all(event["metadata"]["mode"] == "teach" for event in events)
    assert llm.stream_generate_calls[0]["temperature"] == 0.7


@pytest.mark.asyncio
async def test_tutor_stream_process_returns_fallback_on_stream_error():
    agent = TutorAgent(llm_client=FailingTutorLLM())

    events = [
        event
        async for event in agent.stream_process(
            {
                "last_message": "讲讲极限",
                "student_context": {},
                "interaction_history": [],
            }
        )
    ]

    assert len(events) == 1
    assert "抱歉，我暂时无法回答这个问题" in events[0]["content"]
    assert events[0]["agent"] == "tutor"
