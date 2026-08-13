from pydantic import BaseModel

from tools.contracts import ToolRiskLevel, ToolSpec
from tools.executor import ToolExecutor
from tools.mcp_adapter import MCPServerIdentity, MCPToolAdapter
from tools.registry import ToolRegistry


class Input(BaseModel):
    query: str


class Output(BaseModel):
    items: list[str]


class FakeMCPClient:
    def __init__(self): self.calls=[]
    def call_tool(self,name,arguments):
        self.calls.append((name,arguments))
        return {"structuredContent":{"items":["paper-a"]}}


def test_readonly_mcp_tool_uses_existing_registry_policy_and_executor():
    client=FakeMCPClient()
    adapter=MCPToolAdapter(client,"search_papers",ToolSpec(name="paper.search.mcp_demo",version="1.0",description="只读 MCP 论文搜索",input_model=Input,output_model=Output,provider="mcp_demo",capabilities=("paper.search",),risk_level=ToolRiskLevel.READ_ONLY),MCPServerIdentity("demo-paper-server","0.1","stdio"))
    registry=ToolRegistry();registry.register(adapter)

    result=ToolExecutor(registry).execute("paper.search.mcp_demo",{"query":"agent"})

    assert result.success is True
    assert result.data == {"items":["paper-a"]}
    assert client.calls == [("search_papers",{"query":"agent"})]
    assert result.metadata["tool_origin"] == "mcp"
    assert result.metadata["mcp_server"] == "demo-paper-server"


def test_mcp_adapter_preserves_validation_and_rejects_remote_errors():
    class ErrorClient:
        def call_tool(self,_name,_arguments): return {"isError":True,"error":"remote unavailable"}
    adapter=MCPToolAdapter(ErrorClient(),"search_papers",ToolSpec(name="paper.search.mcp_error",version="1.0",description="error",input_model=Input,output_model=Output,provider="mcp_demo",risk_level=ToolRiskLevel.READ_ONLY),MCPServerIdentity("demo"))
    registry=ToolRegistry();registry.register(adapter);executor=ToolExecutor(registry)
    assert executor.execute("paper.search.mcp_error",{}).error_code == "INVALID_INPUT"
    failed=executor.execute("paper.search.mcp_error",{"query":"agent"})
    assert failed.error_code == "EXECUTION_ERROR"
    assert "remote unavailable" in failed.error_message
