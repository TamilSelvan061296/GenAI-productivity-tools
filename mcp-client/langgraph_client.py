import os
from dotenv import load_dotenv

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition
import asyncio
from langchain_openai import AzureChatOpenAI

from langgraph.prebuilt import create_react_agent

# load the environmental variables
load_dotenv()

llm = AzureChatOpenAI(model_name=os.environ['MODEL_NAME'],
                      openai_api_version=os.environ['API_VERSION'],
                      azure_deployment=os.environ['DEPLOYMENT'],
                      azure_endpoint=os.environ['ENDPOINT'],
                      openai_api_key=os.environ['SUBSCRIPTION_KEY'])



# specify the mcp server

client = MultiServerMCPClient(
    {
        "my_custom_mcp_server": {
            "command": "python",
            "args": ["/home/tamil/work/youtube-summarizer/server.py"],
            "transport": "stdio",
        },
    }
)

async def main():
    tools = await client.get_tools()

    def call_model(state: MessagesState):
        response = llm.bind_tools(tools).invoke(state["messages"])
        return {"messages": response}

    builder = StateGraph(MessagesState)
    builder.add_node(call_model)
    builder.add_node(ToolNode(tools))
    builder.add_edge(START, "call_model")
    builder.add_conditional_edges(
        "call_model",
        tools_condition,
    )
    builder.add_edge("tools", "call_model")
    graph = builder.compile()

    messages = []
    print("Type your question (or STOP to exit):")
    while True:
        user_input = input("> ")
        if user_input.strip().upper() == "STOP":
            break
        messages.append({"role": "user", "content": user_input})
        response = await graph.ainvoke({"messages": messages})
        answer = response["messages"][-1].content
        print(answer)
        messages = response["messages"]  # keep conversation context

if __name__ == "__main__":
    asyncio.run(main())
