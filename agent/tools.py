from model.ChatGroq import llm_model as model
from langchain.messages import AIMessage
from typing import TypedDict, Dict
from database.pg import db


class GraphState(TypedDict):
    messages: list
    available_tables: list[str]
    table_metadata: Dict[str, str]
    intent_query_tables: list[str]
    intent_query_tables_schemas: str
    generated_query: str


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
        "olist_orders_dataset",
        "olist_customers_dataset",
        "olist_order_items_dataset",
        "olist_order_payments_dataset",
        "olist_order_reviews_dataset",
        "olist_products_dataset",
        "olist_sellers_dataset",
        "olist_geolocation_dataset",
        "product_category_name_translation"
    }

    with db.cursor() as cursor:
        for table in state["intent_query_tables"]:
            if table not in ALLOWED_TABLES:
                continue

            query = """
            SELECT
                column_name,
                data_type
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position;
            """

            cursor.execute(query, (table,))
            columns = cursor.fetchall()

            if not columns:
                continue

            table_schemas += f"\n{table} (\n"

            for column in columns:
                table_schemas += f"    {column['column_name']} {column['data_type']},\n"

            table_schemas += ")\n"

    # for table_name in state['intent_query_tables']:
    #     for table in state['fake_table_schemas']:
    #         if table['table_name'] == table_name:
    #             table_schemas += table['schema']
    #             break

    state["intent_query_tables_schemas"] = table_schemas
    return state

from langchain_core.messages import (
    HumanMessage,
    SystemMessage
)

def generate_query(state: GraphState):

    user_query = state["messages"][-1]["content"]

    system_prompt = f"""
    You are a PostgreSQL SQL generation engine.

    Your only task is to generate a valid PostgreSQL SELECT query
    that correctly answers the user's question.

    ==================================================
    DATABASE SCHEMA
    ==================================================

    {state["intent_query_tables_schemas"]}

    ==================================================
    DATABASE UNDERSTANDING
    ==================================================

    The database contains e-commerce marketplace data.

    Important table relationships:

    1. olist_orders_dataset
    - Core orders table
    - Connects customers, payments, reviews, and order items
    - Join with customers using customer_id
    - Join with order items using order_id
    - Join with payments using order_id
    - Join with reviews using order_id

    2. olist_customers_dataset
    - Contains customer information
    - customer_unique_id identifies repeat customers
    - customer_id is unique per order

    3. olist_order_items_dataset
    - Contains product-level order items
    - One order can contain multiple items
    - Contains seller_id and product_id
    - price represents item price
    - freight_value represents shipping cost

    4. olist_products_dataset
    - Contains product metadata
    - product_category_name stores category

    5. olist_order_payments_dataset
    - Contains payment transactions
    - payment_value represents paid amount

    6. olist_order_reviews_dataset
    - Contains review scores from 1 to 5

    7. olist_sellers_dataset
    - Contains seller information

    ==================================================
    SQL GENERATION RULES
    ==================================================

    1. Generate ONLY PostgreSQL SQL.
    2. Generate ONLY SELECT queries.
    3. NEVER generate:
    - DELETE
    - UPDATE
    - INSERT
    - DROP
    - ALTER
    - CREATE
    - TRUNCATE

    4. Use ONLY tables and columns from provided schema.
    5. NEVER hallucinate columns or tables.
    6. Use explicit JOIN conditions.
    7. Prefer readable aliases:
    - o = orders
    - oi = order_items
    - p = products
    - c = customers
    - op = payments
    - r = reviews
    - s = sellers

    8. NEVER use SELECT *
    9. Always select only necessary columns.
    10. Add LIMIT 100 unless user asks for all records.
    11. Use GROUP BY for aggregations.
    12. Use ORDER BY when ranking or sorting is implied.
    13. Use aggregate functions properly:
    - SUM for revenue
    - COUNT for totals
    - AVG for averages

    14. Revenue calculations:
    - Use payment_value from payments table
    - OR use price from order items table

    15. Repeat customers:
    - Use customer_unique_id
    - NOT customer_id

    16. Delivery analysis:
    - Use:
        order_delivered_customer_date
        order_estimated_delivery_date

    17. Product analysis:
    - Join order_items with products using product_id

    18. Seller analysis:
    - Join order_items with sellers using seller_id

    19. Time analysis:
    - Use DATE_TRUNC for month/quarter/year grouping

    20. NULL safety:
    - Use NULLIF where division may occur

    ==================================================
    OUTPUT RULES
    ==================================================

    1. Return ONLY raw SQL.
    2. No markdown.
    3. No explanations.
    4. No comments.
    5. No code blocks.
    6. No extra text.
    7. Output must start with:
    SELECT
    OR
    WITH

    ==================================================
    EXAMPLE PATTERNS
    ==================================================

    Example 1:

    User:
    Top selling product categories

    SQL:
    SELECT
        p.product_category_name,
        SUM(oi.price) AS total_revenue
    FROM olist_order_items_dataset oi
    JOIN olist_products_dataset p
        ON oi.product_id = p.product_id
    GROUP BY p.product_category_name
    ORDER BY total_revenue DESC
    LIMIT 100;

    --------------------------------------------------

    Example 2:

    User:
    Top customers by spending

    SQL:
    SELECT
        c.customer_unique_id,
        SUM(op.payment_value) AS total_spent
    FROM olist_orders_dataset o
    JOIN olist_customers_dataset c
        ON o.customer_id = c.customer_id
    JOIN olist_order_payments_dataset op
        ON o.order_id = op.order_id
    GROUP BY c.customer_unique_id
    ORDER BY total_spent DESC
    LIMIT 100;

    --------------------------------------------------

    Example 3:

    User:
    Average review score by seller

    SQL:
    SELECT
        oi.seller_id,
        AVG(r.review_score) AS avg_review_score
    FROM olist_order_items_dataset oi
    JOIN olist_orders_dataset o
        ON oi.order_id = o.order_id
    JOIN olist_order_reviews_dataset r
        ON o.order_id = r.order_id
    GROUP BY oi.seller_id
    ORDER BY avg_review_score DESC
    LIMIT 100;

    ==================================================
    FINAL INSTRUCTION
    ==================================================

    Generate ONLY valid PostgreSQL SQL query.
    """

    human_prompt = f"""
Generate PostgreSQL query for:

{user_query}
"""

    response = model.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ])

    generated_sql = response.content.strip()

    state["generated_query"] = generated_sql

    print("Generated Query:", generated_sql)

    return state

def check_query(state: GraphState):
    pass

def execute_query(state: GraphState):
    print("Going to Execture Query", state['generated_query'])
    
    with db.cursor() as cursor:
        cursor.execute(state['generated_query'])
        results = cursor.fetchall()
        print("Results: ", results)
    
    return state