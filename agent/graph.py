from langgraph.graph import (
    END,
    START,
    StateGraph
)

from .tools import (
    GraphState,
    list_tables,
    user_query_intent,
    call_get_schema,
    generate_query,
    check_query,
    execute_query
)

MAX_QUERY_RETRY = 5

builder = StateGraph(GraphState)

builder.add_node("list_tables",list_tables)
builder.add_node("user_query_intent",user_query_intent)
builder.add_node("call_get_schema", call_get_schema)
builder.add_node("generate_query",generate_query)
builder.add_node("check_query",check_query)
builder.add_node("execute_query",execute_query)

builder.add_edge(START,"list_tables")
builder.add_edge("list_tables","user_query_intent")
builder.add_edge("user_query_intent","call_get_schema")
builder.add_edge("call_get_schema","generate_query")
builder.add_edge("generate_query","check_query")
builder.add_edge("check_query","execute_query")

def route_after_execution(state: GraphState):

    execution_success = state.get(
        "execution_success",
        False
    )

    retry_count = state.get(
        "retry_count",
        0
    )

    if execution_success:
        return END

    if retry_count >= MAX_QUERY_RETRY:
        return END

    return "check_query"


builder.add_conditional_edges(
    "execute_query",
    route_after_execution,
    {
        "check_query": "check_query",
        END: END
    }
)

agent = builder.compile()