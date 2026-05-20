import sqlglot
from sqlglot import expressions as exp
from typing import Tuple


FORBIDDEN_EXPRESSIONS = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.TruncateTable,
    exp.Command,
    exp.Merge,
)

def validate_sql_security(query: str, allowed_tables: list[str]) -> Tuple[bool, str]:
    try:
        parsed = sqlglot.parse_one(
            query,
            dialect="postgres"
        )

    except Exception as e:
        return False, f"Invalid SQL syntax: {str(e)}"

    # BLOCK DML / DDL
    for expression in FORBIDDEN_EXPRESSIONS:
        if parsed.find(expression):
            return False, f"Forbidden SQL operation detected: {expression.__name__}"

    # ONLY SELECT / WITH ALLOWED

    if not isinstance(parsed, (exp.Select, exp.With)):
        return (False, "Only SELECT queries are allowed")

    # BLOCK MULTIPLE STATEMENTS

    statements = sqlglot.parse(query,dialect="postgres")

    if len(statements) > 1:
        return (False,"Multiple SQL statements are not allowed")

    
    # VALIDATE TABLES
    query_tables = [
        table.name
        for table in parsed.find_all(exp.Table)
    ]

    invalid_tables = [table for table in query_tables if table not in allowed_tables]

    if invalid_tables:
        return (False, f"Unauthorized or hallucinated tables detected: {invalid_tables}")

    # BLOCK SELECT *

    if parsed.find(exp.Star):
        return (
            False,
            "SELECT * is not allowed"
        )

    return (True,"")