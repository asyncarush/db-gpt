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
    validate_query,
    check_query,
    execute_query,
    augment_query_result,
    handle_failure
)


MAX_QUERY_RETRY = 4


builder = StateGraph(GraphState)

builder.add_node(
    "list_tables",
    list_tables
)

builder.add_node(
    "user_query_intent",
    user_query_intent
)

builder.add_node(
    "call_get_schema",
    call_get_schema
)

builder.add_node(
    "generate_query",
    generate_query
)

builder.add_node(
    "validate_query",
    validate_query
)

builder.add_node(
    "check_query",
    check_query
)

builder.add_node(
    "execute_query",
    execute_query
)

builder.add_node(
    "augment_query_result",
    augment_query_result
)

builder.add_node(
    "handle_failure",
    handle_failure
)


# Define the flow of Graph
builder.add_edge(
    START,
    "list_tables"
)

builder.add_edge(
    "list_tables",
    "user_query_intent"
)

builder.add_edge(
    "user_query_intent",
    "call_get_schema"
)

builder.add_edge(
    "call_get_schema",
    "generate_query"
)

builder.add_edge(
    "generate_query",
    "validate_query"
)


# VALIDATION ROUTING

def route_after_validation(state: GraphState):
    if state.get(
        "sql_validation_passed",
        False
    ):
        return "check_query"

    return "handle_failure"


builder.add_conditional_edges(
    "validate_query",
    route_after_validation,
    {
        "check_query": "check_query",
        "handle_failure": "handle_failure"
    }
)


# CHECK QUERY → EXECUTE

builder.add_edge(
    "check_query",
    "execute_query"
)



# EXECUTION ROUTING
def route_after_execution(state: GraphState):

    if state.get(
        "execution_success",
        False
    ):
        return "augment_query_result"

    retry_count = state.get(
        "retry_count",
        0
    )

    if retry_count >= MAX_QUERY_RETRY:
        return "handle_failure"

    return "check_query"


builder.add_conditional_edges(
    "execute_query",
    route_after_execution,
    {
        "augment_query_result":
            "augment_query_result",

        "check_query":
            "check_query",

        "handle_failure":
            "handle_failure"
    }
)

# FINAL EDGES
builder.add_edge(
    "augment_query_result",
    END
)

builder.add_edge(
    "handle_failure",
    END
)


agent = builder.compile()