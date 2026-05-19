from model.ChatGroq import llm_model as model
from langchain.messages import AIMessage
from typing import TypedDict, Dict
from database.pg import db


class GraphState(TypedDict):
    messages: list
    available_tables: list[str]
    table_metadata: Dict[str, str]
    intent_query_tables: list[str]
    fake_table_schemas: list[dict]
    intent_query_tables_schemas: str


def list_tables(state: GraphState):
    with db.cursor() as cur:
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """)

        tables = cur.fetchall()

    all_tables = [table['table_name'] for table in tables]
    state["available_tables"] = all_tables
    return state


def user_query_intent(state: GraphState):
    user_query = state["messages"][-1]["content"]
    user_query_intent_system_prompt = """
You are an expert Database Query Intent Classifier.
Your task is to identify which database tables are relevant to answering the user's query.
You MUST ONLY select tables that are directly useful for generating the SQL query.

-----------------------------------
USER QUERY
-----------------------------------
{user_query}

-----------------------------------
AVAILABLE TABLES
-----------------------------------
{table_metadata}

-----------------------------------
INSTRUCTIONS
-----------------------------------

1. Read the user query carefully.
2. Analyze the meaning of the query.
3. Select ONLY the tables that are necessary to answer the query.
4. Do NOT include unrelated tables.
5. If multiple tables may be needed for joins, include all relevant tables.
6. If no tables are relevant, return an empty list.
7. Return ONLY valid table names from the provided metadata.
8. Do NOT hallucinate or invent table names.
9. Output MUST be valid JSON.

-----------------------------------
OUTPUT FORMAT
-----------------------------------

Return ONLY this JSON format:

{{
    "tables": ["table1", "table2"]
}}

-----------------------------------
EXAMPLES
-----------------------------------

Example 1:
User Query:
"Show all recent customer orders"

Output:
{{
    "tables": ["customers", "orders"]
}}

Example 2:
User Query:
"List products with low inventory"

Output:
{{
    "tables": ["products", "inventory"]
}}

Example 3:
User Query:
"Show failed payment transactions"

Output:
{{
    "tables": ["payments"]
}}

Example 4:
User Query:
"What are the top selling products?"

Output:
{{
    "tables": ["products", "orders"]
}}

Example 5:
User Query:
"Delete all users"

Output:
{{
    "tables": ["users"]
}}

-----------------------------------
IMPORTANT
-----------------------------------

- Return ONLY JSON
- No explanation
- No markdown
- No extra text

""".format(
    table_metadata=state["table_metadata"],
    user_query=user_query
)
    response = model.invoke([AIMessage(content=user_query_intent_system_prompt)])
    # print("Inside call_get_intent - Response: ", response)

    import json    
    json_response = json.loads(response.content)

    state['intent_query_tables'] = json_response.get('tables', [])
    return state

def call_get_schema(state: GraphState):
    table_schemas = ""
    
    ALLOWED_TABLES = {
        "users",
        "orders",
        "products",
        "payments",
        "customers",
        "employees",
        "inventory",
        "support_tickets",
        "shipments",
        "audit_logs"
    }

    # with db.cursor() as cursor:
        # for table in state["intent_query_tables"]:
        #     if table not in ALLOWED_TABLES:
        #         continue

        #     query = """
        #     SELECT
        #         column_name,
        #         data_type
        #     FROM information_schema.columns
        #     WHERE table_name = %s
        #     ORDER BY ordinal_position;
        #     """

        #     cursor.execute(query, (table,))
        #     columns = cursor.fetchall()

        #     if not columns:
        #         continue

        #     table_schemas += f"\n{table} (\n"

        #     for column_name, data_type in columns:
        #         table_schemas += f"    {column_name} {data_type},\n"

        #     table_schemas += ")\n"

    for table_name in state['intent_query_tables']:
        for table in state['fake_table_schemas']:
            if table['table_name'] == table_name:
                table_schemas += table['schema']
                break

    state["intent_query_tables_schemas"] = table_schemas
    return state


def generate_query(state: GraphState):
    user_query = state["messages"][-1]["content"]

    user_generated_query = """
You are an expert PostgreSQL SQL query generator.

Your task is to generate a syntactically correct and safe SQL query
that answers the user's request using ONLY the provided database schema.

--------------------------------------------------
DATABASE SCHEMA
--------------------------------------------------

{table_schemas}

--------------------------------------------------
USER REQUEST
--------------------------------------------------

{user_query}

--------------------------------------------------
INSTRUCTIONS
--------------------------------------------------

1. Generate ONLY a valid PostgreSQL SQL query.
2. Use ONLY tables and columns present in the provided schema.
3. Do NOT hallucinate table names or column names.
4. Use proper SQL JOINs when multiple tables are needed.
5. Prefer explicit column names instead of SELECT *.
6. Add LIMIT 100 unless the user explicitly requests all records.
7. If aggregation is needed, use appropriate GROUP BY clauses.
8. If sorting is implied, use ORDER BY.
9. If the user query is ambiguous, generate the most reasonable SQL query.
10. Do NOT generate destructive queries.

--------------------------------------------------
STRICT SECURITY RULES
--------------------------------------------------

NEVER generate:
- DELETE
- DROP
- UPDATE
- INSERT
- ALTER
- TRUNCATE
- CREATE

Generate ONLY SELECT queries.

--------------------------------------------------
OUTPUT RULES
--------------------------------------------------

- Return ONLY raw SQL.
- No markdown.
- No explanation.
- No comments.
- No extra text.
- No ```sql blocks.

--------------------------------------------------
EXAMPLES
--------------------------------------------------

Example 1:
User Request:
"Show recent customer orders"

SQL:
SELECT
    orders.id,
    orders.order_date,
    customers.name
FROM orders
JOIN customers
    ON orders.customer_id = customers.id
ORDER BY orders.order_date DESC
LIMIT 100;

--------------------------------------------------

Example 2:
User Request:
"Show products with low inventory"

SQL:
SELECT
    products.product_name,
    inventory.stock_quantity
FROM products
JOIN inventory
    ON products.id = inventory.product_id
WHERE inventory.stock_quantity < 10
LIMIT 100;

--------------------------------------------------

Example 3:
User Request:
"Total revenue this month"

SQL:
SELECT
    SUM(total_amount) AS total_revenue
FROM orders
WHERE DATE_TRUNC('month', order_date) = DATE_TRUNC('month', CURRENT_DATE);

--------------------------------------------------

IMPORTANT:
Return ONLY executable PostgreSQL SQL.
""".format(table_schemas=state["intent_query_tables_schemas"], user_query=user_query)
    
    response = model.invoke([AIMessage(content=user_generated_query)])
    state['generated_query'] = response.content

    print("FULL Prompt: ", user_generated_query)


    print("Generated Query: ", state['generated_query'])
    
    return state


def check_query(state: GraphState):
    pass