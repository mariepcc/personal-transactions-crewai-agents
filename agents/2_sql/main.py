from crewai.tools import BaseTool
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task, tool


import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()


@tool
class SQLQueryTool(BaseTool):
    name: str = "SQLQuery"
    description: str = (
        "Executes a SQL query against the configured database and returns the results."
    )

    def _run(self, query: str):
        print(f"[SQLQueryTool] Executing query: {query}")
        try:
            conn_str = os.getenv("AZURE_SQL_CONNECTION_STRING")
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            if rows:
                ret = "\n".join(", ".join(map(str, row)) for row in rows)
                return f"Query: {query}\nResult: {ret}"
            else:
                return {"message": "No results found"}

        except Exception as e:
            return {"error": str(e)}
