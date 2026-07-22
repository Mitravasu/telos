import asyncio

from langchain_core.messages import AIMessageChunk

from telos.agents.orchestrator.graph import build_graph


def test_graph_streams_chunks_and_persists_one_ai_message():
    class Model:
        async def astream(self, messages):
            yield AIMessageChunk(content="res")
            yield AIMessageChunk(content="ponse")

    async def exercise():
        graph = build_graph(Model(), None)
        chunks = [
            chunk
            async for chunk in graph.astream(
                {"messages": [("user", "hello")]}, stream_mode="custom"
            )
        ]
        result = await graph.ainvoke({"messages": [("user", "again")]})
        return chunks, result

    chunks, result = asyncio.run(exercise())

    assert [chunk.content for chunk in chunks] == ["res", "ponse"]
    assert result["messages"][-1].content == "response"
