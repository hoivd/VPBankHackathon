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
            "MDB_MCP_CONNECTION_STRING": os.getenv("MONGO_URI")
        }
        }
      }
    }

    # Create MCPClient from configuration dictionary
    client = MCPClient.from_dict(config)

    # Create LLM
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", api_key=os.getenv("GEMINI_API_KEY"))
    
    # Create agent with the client
    # Add parent directory to Python path for imports
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from prompts.data_prompt.dynamodb_origin import DYNAMODB_SCHEMA, RELATION_TABLES, COLLECTION_STRUCTURE
    
    instructions = f"""
    You are a helpful assistant that can answer questions about the data in the database.
    You can access the MongoDB database.
    You can use the MONGO_SCHEMA to understand the data in the database vp_bank_hackathon.
    {DYNAMODB_SCHEMA}
    You can use the RELATION_TABLES to understand the relationships between the tables in the database.
    {RELATION_TABLES}
    You can use the COLLECTION_STRUCTURE to understand the data in the database. Remember use EXACTLY the collection name (dont uppercase it)
    {COLLECTION_STRUCTURE}
    
    """
    agent = MCPAgent(llm=llm, client=client, max_steps=30)
    # Run the query
    # try:
    #     async for step in agent.stream(
    #         final_prompt
    #     ):
    #         if isinstance(step, str):
    #             print("Result:", step)
    #         else:
    #             action, observation = step
    #             print("Observation:", observation[:20])
    #             print("Calling:", action.tool)
    #             print("Input:", action.tool_input)
    query = """
    hãy truy cập vào MongoDB và giúp tôi tìm kiếm thông tin về bà Trương Mỹ Lan, 
    trả về tất cả thông tin vi phạm pháp lý và nguồn bài báo mà bạn có được, 
    nếu bạn không tìm thấy thông tin về bà Trương Mỹ Lan, hãy trả về 'không tìm thấy thông tin'
    """
    query_en = """
    Please access MongoDB and help me search for information about Mrs. Trương Mỹ Lan. 
    Return all legal violation information and the source of the news articles you found. 
    If you cannot find any information about Mrs. Trương Mỹ Lan, return 'no information found'.
    """

    final_prompt = f"""
    {instructions}
    {query_en}
    """
    result = await agent.run(
        final_prompt
    )
    print(f"\nResult: {result}")
    # finally:
    #     # Clean up all sessions
    #     await client.close_all_sessions()

if __name__ == "__main__":
    asyncio.run(main())