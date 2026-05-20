from typing import TypedDict, Dict
from langchain_core.messages import (
    HumanMessage,
    SystemMessage
)
from model.ChatGroq import llm_model as model
from database.pg import db

from .prompts import (
    generate_query_system_prompt,
    generate_query_human_prompt,
    user_query_intent_system_prompt,
    check_query_human_prompt,
    check_query_system_prompt,
    augment_query_result_human_prompt,
    augment_query_result_system_prompt
)

import json
import re
import traceback

from .utils import validate_sql_security
from logging import getLogger

logger = getLogger(__name__)

class GraphState(TypedDict, total=False):
    messages: list
    available_tables: list[str]
    table_metadata: Dict[str, str]

    intent_query_tables: list[str]
    intent_query_tables_schemas: str

    generated_query: str
    query_error: str

    query_result: list

    retry_count: int
    execution_success: bool

    sql_validation_passed: bool
    sql_validation_error: str

    augmented_result: str  

def _parse_json_response(content: str) -> dict:
    """Safely parse JSON from model response, stripping markdown fences if present."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", content.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())
    return json.loads(cleaned)


def list_tables(state: GraphState):
    try:
        with db.cursor() as cur:
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """)
            tables = cur.fetchall()

        return {
            "available_tables": [
                table["table_name"]
                for table in tables
            ]
        }

    except Exception as e:
        print("ERROR IN list_tables")
        traceback.print_exc()
        return {
            "query_error": str(e),
            "available_tables": []
        }


def user_query_intent(state: GraphState):
    try:
        user_query = state["messages"][-1]["content"]

        response = model.invoke([
            HumanMessage(
                content=user_query_intent_system_prompt(
                    user_query,
                    state["table_metadata"]
                )
            )
        ])

        json_response = _parse_json_response(response.content)

        return {
            "intent_query_tables": json_response.get("tables", [])
        }

    except Exception as e:
        print("ERROR IN user_query_intent")
        traceback.print_exc()
        return {
            "query_error": str(e),
            "intent_query_tables": []
        }


def call_get_schema(state: GraphState):
    try:
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

        intent_tables = state.get("intent_query_tables", [])

        with db.cursor() as cursor:
            for table in intent_tables:
                if table not in ALLOWED_TABLES:
                    continue

                cursor.execute("""
                    SELECT
                        column_name,
                        data_type
                    FROM information_schema.columns
                    WHERE table_name = %s
                    ORDER BY ordinal_position;
                """, (table,))

                columns = cursor.fetchall()

                if not columns:
                    continue

                table_schemas += f"\n{table} (\n"
                for column in columns:
                    table_schemas += (
                        f"    {column['column_name']} "
                        f"{column['data_type']},\n"
                    )
                table_schemas += ")\n"

        return {
            "intent_query_tables_schemas": table_schemas
        }

    except Exception as e:
        print("ERROR IN call_get_schema")
        traceback.print_exc()
        return {
            "query_error": str(e),
            "intent_query_tables_schemas": ""
        }


def generate_query(state: GraphState):
    try:
        schemas = state.get("intent_query_tables_schemas", "")

        if not schemas:
            return {
                "query_error": "No table schemas available; cannot generate query.",
                "generated_query": ""
            }

        user_query = state["messages"][-1]["content"]

        response = model.invoke([
            SystemMessage(
                content=generate_query_system_prompt(schemas)
            ),
            HumanMessage(
                content=generate_query_human_prompt(user_query)
            )
        ])

        generated_sql = response.content.strip()


        
        return {
            "generated_query": generated_sql,
            "retry_count": 0 # reset the count after new query generation
        }
    
    except Exception as e:
        print("ERROR IN generate_query")
        traceback.print_exc()
        return {
            "query_error": str(e),
            "generated_query": ""
        }


def check_query(state: GraphState):
    try:
        generated_query = state.get("generated_query", "")

        if not generated_query:
            return {
                "query_error": "No generated query to check."
            }

        user_query = state["messages"][-1]["content"]

        query_error = (
            state.get("sql_validation_error")
            or state.get("query_error")
            or "No Errors"
        )

        table_metadata = state["table_metadata"]

        response = model.invoke([
            SystemMessage(
                content=check_query_system_prompt(
                    table_metadata,
                    user_query,
                    generated_query,
                    query_error
                )
            ),
            HumanMessage(
                content=check_query_human_prompt(generated_query)
            )
        ])

        corrected_query = response.content.strip()

        print("\nCORRECTED QUERY\n")
        print(corrected_query)

        return {
            "generated_query": corrected_query,
            "sql_validation_passed": False,  # force re-validation
            "sql_validation_error": ""
        }

    except Exception as e:
        print("ERROR IN check_query")
        traceback.print_exc()
        return {
            "query_error": str(e)
        }


def execute_query(state: GraphState):
    try:
        generated_query = state.get("generated_query", "")

        if not generated_query:
            raise ValueError("No query to execute.")

        print("\nEXECUTING QUERY\n")
        print(generated_query)

        with db.cursor() as cursor:
            cursor.execute(generated_query)
            results = cursor.fetchall()

        print("\nQUERY EXECUTED SUCCESSFULLY\n")

        return {
            "query_result": [dict(row) for row in results],
            "execution_success": True,
            "query_error": ""
        }

    except Exception as e:
        retry_count = state.get("retry_count", 0) + 1

        print(f"\nQUERY EXECUTION FAILED (Attempt {retry_count})\n")
        traceback.print_exc()

        return {
            "retry_count": retry_count,
            "execution_success": False,
            "query_error": str(e)
        }

def augment_query_result(state: GraphState):
    try:
        query_result = state.get("query_result", [])
        user_query = state["messages"][-1]["content"]
        
        response = model.invoke([
            SystemMessage(
                content=augment_query_result_system_prompt()
            ),
            HumanMessage(
                content=augment_query_result_human_prompt(user_query, query_result)
            )
        ])
        
        augmented_result = response.content.strip()
        
        print("\nAUGMENTED RESULT\n")
        print(augmented_result)
        
        return {
            "augmented_result": augmented_result
        }
        
    except Exception as e:
        print("ERROR IN augment_query_result")
        traceback.print_exc()
        return {
            "augmented_result": "Error augmenting result: " + str(e)
        }


def validate_query(state: GraphState):
    logger.info("STARTING validate_query NODE")

    try:
        query = state.get("generated_query", "")
        allowed_tables = state.get("available_tables", [])

        is_valid, error = validate_sql_security(
            query=query,
            allowed_tables=allowed_tables
        )

        if is_valid:
            logger.info("SQL VALIDATION PASSED")
        else:
            logger.warning(f"SQL VALIDATION FAILED:\n{error}")

        return {
            "sql_validation_passed": is_valid,
            "sql_validation_error": error or "",
            "query_error": error if not is_valid else ""
            # removed retry_count — validation no longer retries
        }

    except Exception as e:
        logger.exception("ERROR IN validate_query NODE")
        return {
            "sql_validation_passed": False,
            "sql_validation_error": str(e),
            "query_error": str(e)
        }


def handle_failure(state: GraphState):
    """Immediately returns a user-facing message on validation or execution failure."""

    validation_error = state.get("sql_validation_error", "")
    query_error = state.get("query_error", "")
    retry_count = state.get("retry_count", 0)

    if validation_error:
        message = (
            f"Your request could not be processed because the generated SQL "
            f"failed security validation.\n\nReason: {validation_error}\n\n"
            f"DML operations (INSERT, UPDATE, DELETE, DROP, etc.) and "
            f"SELECT * are not allowed."
        )
    else:
        message = (
            f"Your request could not be processed after {retry_count} attempts.\n\n"
            f"Reason: {query_error or 'Unknown error'}"
        )

    logger.warning(f"HANDLE FAILURE: {message}")

    return {
        "augmented_result": message
    }