import os
from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv

load_dotenv()

params = os.getenv("AZURE_SQL_CONNECTION_STRING")

connection_string = f"mssql+pyodbc:///?odbc_connect={params}"

DB = SQLDatabase.from_uri(connection_string)
