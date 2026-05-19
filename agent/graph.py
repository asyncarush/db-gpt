from langgraph.graph import END, START, StateGraph
from .tools import list_tables, user_query_intent, call_get_schema, generate_query, execute_query

from .tools import GraphState


builder = StateGraph(GraphState)
builder.add_node("user_query_intent", user_query_intent)
builder.add_node("list_tables", list_tables)
builder.add_node("call_get_schema", call_get_schema)
builder.add_node("generate_query", generate_query)
builder.add_node("execute_query", execute_query)

builder.add_edge(START, "list_tables")
builder.add_edge("list_tables", "user_query_intent")
builder.add_edge("user_query_intent", "call_get_schema")
builder.add_edge("call_get_schema", "generate_query")
builder.add_edge("generate_query", "execute_query")
builder.add_edge("execute_query", END)


agent = builder.compile()