import asyncio
import os
from dotenv import load_dotenv
# from google import genai
from langchain_google_genai import ChatGoogleGenerativeAI
from mcp_use import MCPAgent, MCPClient
import mcp_use
mcp_use.set_debug(2)  # DEBUG level (full verbose output)

async def main():
    # Load environment variables
    load_dotenv()

    # Create configuration dictionary
    config = {
      "mcpServers": {
        "MongoDB": {
        "command": "npx",
        "args": ["-y", "mongodb-mcp-server"],
        "env": {
            "MDB_MCP_CONNECTION_STRING": "mongodb+srv://hoivd:vinhhoi@cluster0.amxct9l.mongodb.net/"
        }
        },
        "dynamodb": {
      "command": "docker",
      "args": [ "run", "-i", "--rm", "-e", "AWS_ACCESS_KEY_ID", "-e", "AWS_SECRET_ACCESS_KEY", "-e", "AWS_REGION", "-e", "AWS_SESSION_TOKEN", "mcp/dynamodb-mcp-server" ],
      "env": {
        "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
        "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "AWS_REGION": os.getenv("AWS_REGION"),
        "AWS_SESSION_TOKEN": os.getenv("AWS_SESSION_TOKEN")  
      }
    }
      }
    }

    # Create MCPClient from configuration dictionary
    client = MCPClient.from_dict(config)

    # Create LLM
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", api_key=os.getenv("GEMINI_API_KEY"))

    # Create agent with the client
    agent = MCPAgent(llm=llm, client=client, max_steps=30)
    
    query = """
    hãy truy cập vào mongodb và giúp tôi tìm kiếm thông tin về bà Trương Mỹ Lan, 
    trả về tất cả thông tin vi phạm pháp lý và nguồn bài báo mà bạn có được, 
    đừng truy cập vào những collection khác ngoài collection customer2media, customer_info
    nếu bạn không tìm thấy thông tin về bà Trương Mỹ Lan, hãy trả về 'không tìm thấy thông tin'
    """
    query_eng = """
    Please access MongoDB and help me search for information about Ms. Truong My Lan.
    Return all legal violation information and the source of the articles you found.
    Do not access any collections other than customer2media and customer_info.
    If you cannot find any information about Ms. Truong My Lan, return 'no information found'.
    """
    # test = "cho tôi xem toàn bộ tables bạn có trong database blacklist, collection là adverse_media "
    connect_prompt = "database : blacklist, collection : customer2media, customer_info"
    final_prompt = f""" 
    {query}
    {connect_prompt}
    """
    # Run the query
    try:
        async for step in agent.stream(
            final_prompt
        ):
            if isinstance(step, str):
                print("Result:", step)
            else:
                action, observation = step
                print("Observation:", observation[:20])
                print("Calling:", action.tool)
                print("Input:", action.tool_input)

        # result = await agent.run(
        #     query,
        #     connect_prompt
        # )
        # print(f"\nResult: {result}")
    finally:
        # Clean up all sessions
        await client.close_all_sessions()

if __name__ == "__main__":
    asyncio.run(main())