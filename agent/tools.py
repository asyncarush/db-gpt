from .prompts import Prompts
from langchain.messages import AIMessage
from langgraph.graph import MessagesState
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from .utils import safe_model_invoke

from database.pg import db
from model.ChatGroq import llm_model as model

from database.redis import redis_client

toolkit = SQLDatabaseToolkit(db=db, llm=model)
tools = toolkit.get_tools()

for tool in tools:
    print(f"{tool.name}: {tool.description}\n")

def get_tool(tools, name):
    for tool in tools:
        if tool.name == name:
            return tool
    raise ValueError(f"Tool '{name}' not found. Available: {[t.name for t in tools]}")

get_schema_tool = get_tool(tools, "sql_db_schema")
run_query_tool = get_tool(tools, "sql_db_query")


def list_tables(state: MessagesState):
    tool_call = {
        "name": "sql_db_list_tables",
        "args": {},
        "id": "abc123",
        "type": "tool_call",
    }
    tool_call_message = AIMessage(content="", tool_calls=[tool_call])


    #check for tables in cache for first time

    if redis_client.exists("tables"):
        print("Cache Hit - Using cached tables")
        tables = redis_client.get("tables")
        response = AIMessage(f"Available tables: {tables}")
        return {"messages": [tool_call_message, response]}


    
    list_tables_tool = get_tool(tools, "sql_db_list_tables")  # fixed
    tool_message = list_tables_tool.invoke(tool_call)
    
    response = AIMessage(f"Available tables: {tool_message.content}")

    print("Cache Miss - Fetching tables from database")
  
    #cache tables
    redis_client.set("tables", tool_message.content, ex=3600) # 1 hour

    return {"messages": [tool_call_message, tool_message, response]}
    

# Example: force a model to create a tool call
def call_get_schema(state: MessagesState):
    
    # as well as `tool_choice=<string name of tool>`.
    llm_with_tools = model.bind_tools([get_schema_tool], tool_choice="any")
    response = llm_with_tools.invoke(state["messages"])

    return {"messages": [response]}


generate_query_system_prompt = Prompts.generate_query_system_prompt

check_query_system_prompt = Prompts.check_query_system_prompt

def generate_query(state: MessagesState):
    system_message = {
        "role": "system",
        "content": generate_query_system_prompt,
    }
    llm_with_tools = model.bind_tools([run_query_tool])
    response = safe_model_invoke(
        llm_with_tools, 
        [system_message] + state["messages"]
    )
    return {"messages": [response]}



def check_query(state: MessagesState):
    system_message = {
        "role": "system",
        "content": check_query_system_prompt,
    }

    tool_call = state["messages"][-1].tool_calls[0]
    query = (
        tool_call["args"].get("query") or 
        tool_call["args"].get("__arg1") or 
        next(iter(tool_call["args"].values()))
    )
    
    user_message = {"role": "user", "content": f"Check and execute this SQL query:\n\n{query}"}
    llm_with_tools = model.bind_tools([run_query_tool])
    
    try:
        response = safe_model_invoke(llm_with_tools, [system_message, user_message])
        response.id = state["messages"][-1].id
        return {"messages": [response]}
    except Exception as e:
        # If check_query completely fails, bypass it and run original query
        print(f"check_query failed, bypassing: {e}")
        return {"messages": [AIMessage(
            content="",
            tool_calls=[{
                "name": "sql_db_query",
                "args": {"query": query},
                "id": tool_call["id"],
                "type": "tool_call"
            }]
        )]}