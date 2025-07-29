import pyodbc
import os
from dotenv import load_dotenv
from typing import Any, Callable, Set

load_dotenv()


def get_db_connection():
    conn_str = os.getenv("AZURE_SQL_CONNECTION_STRING")
    return pyodbc.connect(conn_str)


def get_transaction_categories(type: str = None) -> dict:
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                if type:
                    cursor.execute(
                        "SELECT Id, Name, Description FROM Categories WHERE Type = ?",
                        (type),
                    )
                else:
                    cursor.execute("SELECT Id, Name, Description FROM Categories")

                categories = [
                    {"id": row[0], "name": row[1], "description": row[2]}
                    for row in cursor.fetchall()
                ]
                return {"categories": categories}
    except Exception as e:
        return {"error": str(e)}


print(get_transaction_categories("Expense"))


user_functions: Set[Callable[..., Any]] = {
    get_transaction_categories,
}
