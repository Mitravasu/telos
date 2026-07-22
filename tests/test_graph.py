from langchain_core.messages import AIMessage

from telos.agents.orchestrator.graph import build_graph


def test_graph_runs_one_llm_turn_and_returns_an_ai_message():
    class Model:
        def __init__(self):
            self.calls = 0

        def invoke(self, messages):
            self.calls += 1
            assert messages[-1].content == "hello"
            return AIMessage(content="response")

    model = Model()
    result = build_graph(model, None).invoke({"messages": [("user", "hello")]})

    assert model.calls == 1
    assert result["messages"][-1].content == "response"
