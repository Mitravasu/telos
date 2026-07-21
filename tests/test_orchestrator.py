from langchain_core.messages import AIMessage, HumanMessage

from telos.agents.orchestrator.nodes import invoke_llm, is_retryable_llm_error


class Model:
    def invoke(self, messages):
        return AIMessage(content="hello")


def test_llm_node_returns_ai_message():
    result = invoke_llm(Model())({"messages": [HumanMessage(content="hi")]})
    assert result["messages"][0].content == "hello"


def test_retry_classification():
    assert is_retryable_llm_error(ConnectionError())
    assert not is_retryable_llm_error(ValueError())
