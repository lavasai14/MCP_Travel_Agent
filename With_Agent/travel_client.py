
# #!/usr/bin/env python3
# """
# MCP Client with Gemini Agent (Live Queries)
# - Connects to `demo_adv/travel_server.py`
# - Uses Gemini LLM via Semantic Kernel (GoogleAI)
# - Dynamically lists tools from the MCP server
# - Lets Gemini decide which tool to call for each live query
# - Outputs clean text only (no JSON blobs)
# """

# import asyncio
# import os
# import json
# from dotenv import load_dotenv
# from mcp.client.stdio import stdio_client, StdioServerParameters
# from mcp.client.session import ClientSession

# from semantic_kernel import Kernel
# from semantic_kernel.connectors.ai.google.google_ai.services.google_ai_chat_completion import (
#     GoogleAIChatCompletion,
#     ChatHistory,
# )
# from semantic_kernel.connectors.ai.google.google_ai.google_ai_prompt_execution_settings import (
#     GoogleAIChatPromptExecutionSettings,
# )

# # ---------- Load Env ----------
# load_dotenv()
# GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

# # ---------- Setup LLM ----------
# kernel = Kernel()
# kernel.add_service(
#     GoogleAIChatCompletion(
#         service_id="gemini",
#         api_key=GEMINI_KEY or None,
#         gemini_model_id="gemini-1.5-flash",
#     )
# )


# # ---------- Agent Decision Logic ----------
# async def agent_decision(session: ClientSession, query: str):
#     """
#     Use Gemini to decide which tool to call and execute it.
#     Dynamically lists tools from the server instead of hardcoding.
#     """
#     if not GEMINI_KEY:
#         return "❌ GEMINI_API_KEY is not set in .env. Please add GEMINI_API_KEY to use the Gemini agent."

#     llm = kernel.get_service(service_id="gemini")

#     # 🔹 1. Ask server what tools exist
#     tools = await session.list_tools()
#     if not tools.tools:
#         return "❌ No tools available from the server."

#     # 🔹 2. Build system prompt dynamically
#     tool_descriptions = []
#     for t in tools.tools:
#         tool_descriptions.append(
#             f"- {t.name}({t.inputSchema}) → {t.description}"
#         )

#     system_prompt = (
#         "You are a travel assistant. The user will ask questions.\n"
#         "You have the following tools available:\n"
#         f"{chr(10).join(tool_descriptions)}\n\n"
#         "Based on the user query, decide which tool to call.\n"
#         "Respond in JSON with exactly this shape (no extra text):\n"
#         "{\n  \"tool\": \"<tool_name>\",\n  \"arguments\": { ... }\n}"
#     )

#     # 🔹 3. Build chat history
#     chat = ChatHistory()
#     chat.add_system_message(system_prompt)
#     chat.add_user_message(f"User query: {query}")

#     settings = GoogleAIChatPromptExecutionSettings(max_output_tokens=300)

#     # 🔹 4. Get model response
#     response = await llm.get_chat_message_content(chat, settings)

#     # Helper: Extract text
#     def extract_text(msg):
#         if msg is None:
#             return ""
#         text = getattr(msg, "text", None)
#         if text:
#             return text
#         content = getattr(msg, "content", None)
#         if isinstance(content, list) and content:
#             first = content[0]
#             return getattr(first, "text", None) or str(first)
#         return str(msg)

#     raw = extract_text(response)
#     print("\n🤖 Gemini Decision:", raw)

#     # 🔹 5. Clean and parse JSON
#     s = raw.strip()
#     if s.startswith("```"):
#         first_newline = s.find("\n")
#         if first_newline != -1:
#             s = s[first_newline + 1 :]
#         if s.endswith("```"):
#             s = s[:-3]
#         raw_clean = s.strip()
#     else:
#         raw_clean = raw

#     try:
#         decision = json.loads(raw_clean)
#     except Exception as e:
#         return f"❌ Failed to parse decision: {e}\nRaw: {raw}"

#     tool_name = decision.get("tool")
#     args = decision.get("arguments", {})

#     # 🔹 6. Call the selected tool
#     try:
#         result = await session.call_tool(tool_name, args)

#         # ✅ Extract clean text output only
#         if hasattr(result, "content") and result.content:
#             texts = []
#             for c in result.content:
#                 if hasattr(c, "text"):
#                     texts.append(c.text)
#             if texts:
#                 return "\n".join(texts)

#         return str(result)  # fallback if no clean text found

#     except Exception as e:
#         return f"❌ Tool call failed: {e}"


# # ---------- Client Main ----------
# async def main():
#     params = StdioServerParameters(
#         command="python",
#         args=["travel_server.py"],   # adjust path if needed
#     )

#     async with stdio_client(params) as streams:
#         async with ClientSession(streams[0], streams[1]) as session:
#             await session.initialize()
#             print("✅ Connected to Travel MCP Server")
            
#             # Show available tools
#             tools = await session.list_tools()
#             print("\n🔧 Available tools from server:")
#             for t in tools.tools:
#                 print(f"- {t.name} → {t.description}")

#             print("\n💬 Type your query (or 'exit' to quit):")

#             # 🔹 Live query loop
#             while True:
#                 user_query = input("\nUser: ")
#                 if user_query.lower() in ["exit", "quit"]:
#                     print("👋 Exiting client.")
#                     break

#                 result = await agent_decision(session, user_query)
#                 print("📌 Result:\n", result)


# if __name__ == "__main__":
#     asyncio.run(main())



#!/usr/bin/env python3
"""
Travel Agent using MCP + Gemini (Autonomous)
- Connects to Travel MCP Server
- Uses Semantic Kernel + Gemini for reasoning
- Maintains memory of past actions
- Plans multi-step actions autonomously
"""

import asyncio
import os
import json
from dotenv import load_dotenv
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.google.google_ai.services.google_ai_chat_completion import GoogleAIChatCompletion, ChatHistory
from semantic_kernel.connectors.ai.google.google_ai.google_ai_prompt_execution_settings import GoogleAIChatPromptExecutionSettings

# ---------- Load Env ----------
load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

# ---------- Setup Semantic Kernel + Gemini ----------
kernel = Kernel()
kernel.add_service(
    GoogleAIChatCompletion(
        service_id="gemini",
        api_key=GEMINI_KEY or None,
        gemini_model_id="gemini-1.5-flash",
    )
)

# ---------- Autonomous Agent Logic ----------
async def agent(query: str, session: ClientSession, memory: dict):
    """
    The agent:
    - Keeps memory of past actions
    - Decides which MCP tool(s) to call
    - Executes tools and updates memory
    """
    if not GEMINI_KEY:
        return "❌ GEMINI_API_KEY is not set."

    llm = kernel.get_service("gemini")

    # Step 1: List available tools once
    tools_list = await session.list_tools()
    tool_descriptions = [
        f"- {t.name}({t.inputSchema}) → {t.description}" for t in tools_list.tools
    ]

    # Step 2: Build system prompt with memory
    memory_text = json.dumps(memory) if memory else "No past memory."
    system_prompt = (
        "You are an autonomous travel assistant. The user will ask questions.\n"
        "Here is your memory of past actions:\n"
        f"{memory_text}\n\n"
        "You have the following tools available:\n"
        f"{chr(10).join(tool_descriptions)}\n\n"
        "Decide which tool(s) to call and in what order. "
        "Provide tool name(s) and arguments. Respond ONLY in JSON:"
        "{ 'plan': [ {'tool': '<tool_name>', 'arguments': {...}} ] }"
    )

    # Step 3: Prepare chat
    chat = ChatHistory()
    chat.add_system_message(system_prompt)
    chat.add_user_message(f"User query: {query}")

    settings = GoogleAIChatPromptExecutionSettings(max_output_tokens=500)
    response = await llm.get_chat_message_content(chat, settings)

    # Step 4: Extract JSON plan
    raw = getattr(response, "text", str(response))
    try:
        # Clean and parse
        s = raw.strip()
        if s.startswith("```"):
            s = s.split("\n", 1)[1].rsplit("```", 1)[0]
        plan = json.loads(s).get("plan", [])
    except Exception as e:
        return f"❌ Failed to parse plan: {e}\nRaw: {raw}"

    results = []
    # Step 5: Execute each tool in plan
    for step in plan:
        tool_name = step.get("tool")
        args = step.get("arguments", {})
        try:
            result = await session.call_tool(tool_name, args)
            # Extract clean text
            if hasattr(result, "content"):
                texts = [c.text for c in result.content if hasattr(c, "text")]
                results.append("\n".join(texts) if texts else str(result))
            else:
                results.append(str(result))
            # Update memory
            memory[tool_name] = args
        except Exception as e:
            results.append(f"❌ Tool call failed: {e}")

    return "\n".join(results)


# ---------- Main ----------
async def main():
    params = StdioServerParameters(
        command="python",
        args=["travel_server.py"],  # path to your MCP server
    )

    memory = {}  # Agent memory

    async with stdio_client(params) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            print("✅ Connected to Travel MCP Server")

            tools = await session.list_tools()
            print("\n🔧 Available tools:")
            for t in tools.tools:
                print(f"- {t.name} → {t.description}")

            print("\n💬 Type your query (or 'exit' to quit):")
            while True:
                user_query = input("\nUser: ")
                if user_query.lower() in ["exit", "quit"]:
                    print("👋 Exiting agent.")
                    break

                result = await agent(user_query, session, memory)
                print("\n📌 Agent Result:\n", result)


if __name__ == "__main__":
    asyncio.run(main())
