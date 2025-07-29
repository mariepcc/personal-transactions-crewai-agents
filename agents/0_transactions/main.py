from crewai.tools import BaseTool
from crewai import Agent, Task, Crew
import os
import requests
import pyodbc
from dotenv import load_dotenv

load_dotenv()


class CategoryLookupTool(BaseTool):
    name: str = "CategoryLookup"
    description: str = (
        "Fetches CategoryId, Name and Description by transaction type from SQL database"
    )

    def _run(self, category_type: str):
        print(f"[CategoryLookupTool] Searching for category of type '{category_type}'")
        try:
            conn_str = os.getenv("AZURE_SQL_CONNECTION_STRING")
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT Id, Name, Description FROM Categories WHERE Type=?",
                (category_type),
            )
            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            if rows:
                categories = [
                    {"id": row[0], "name": row[1], "description": row[2]}
                    for row in rows
                ]
                return {"categories": categories}
            else:
                return {"error": f"Category of type '{category_type}' not found"}

        except Exception as e:
            return {"error": str(e)}


class AddExpenseTool(BaseTool):
    name: str = "AddExpense"
    description: str = (
        "Adds an expense transaction by calling Azure Logic App HTTP trigger"
    )

    def _run(
        self,
        amount: float,
        category_id: int,
        date: str,
        type: str,
        description: str = None,
        user_id: int = 1,
    ):
        print(
            f"[AddExpenseTool] Submitting expense: {amount}, cat_id={category_id}, date={date}, type={type}"
        )
        logic_app_url = os.getenv("LOGIC_APP_URL")
        if not logic_app_url:
            return "Missing Logic App URL in environment variables."

        payload = {
            "Amount": amount,
            "CategoryId": category_id,
            "Date": date,
            "Description": description,
            "Type": type,
            "UserId": user_id,
        }

        response = requests.post(logic_app_url, json=payload)
        if response.status_code == 202:
            return "Expense added successfully!"
        else:
            return f"Failed to add expense: {response.status_code} - {response.text}"


# Agent definition
expense_agent = Agent(
    role="Expense Processor",
    goal="Understand user's expenses and insert them into the database",
    backstory="""
    You are an agent that helps users register financial transactions and activities within the context of a personal finance management app. Your main objective is to collect information from the user and then register it in a database using the available functions.

    To register a transaction, you require the following data:

    - Type: A transaction can be either "Expense" or "Income." Expense transactions refer to movements that involve an outflow of money from the user. Income transactions represent the opposite. You must infer the type based on the information provided; do not ask the user directly for this information.

    - Category ID: A category represents a way to classify income and expense transactions. For example, income categories may include salary, fees, or dividends. Expense categories may include food, fuel, mortgage, health, entertainment, among others. To obtain the category ID, you must first query the categories registered by the user in the database using the {CategoryLookupTool} tool. Something that can help you infer the category is the transaction description. Do not ask the user for the category ID; only request the category name.

    - User ID: It is a number that identifies the user you are interacting with. You will find it in the conversation context. Never ask the user for it.

    - Date: This is the date when the transaction or financial movement occurred. You must identify it from the information provided by the user or from the conversation context. If you cannot determine it by any means, use today’s date, which is available in the conversation context.

    - Amount: Represents the monetary value of the transaction. You must obtain this either from the user or from the conversation context.

    - Description: Refers to a description of the transaction. You can obtain it from the user or the conversation context. If none is provided, generate a short description based on the available information.

    Once you have gathered all the required information, you must proceed to register the transaction using the available tool functions.
""",
    tools=[CategoryLookupTool(), AddExpenseTool()],
    verbose=True,
)


user_expense_input = "I got today my salary. It was 1500 zł."

add_expense_task = Task(
    description=(
        f"You will receive a user message about a recent transaction: '{user_expense_input}'. "
        "Extract the following fields: amount, type, category name, date, description, and user_id (default is 1). "
        "A transaction type can be either 'Expense' or 'Income.' Expense transactions refer to movements that involve an outflow of money from the user. Income transactions represent the opposite. You must infer the type based on the information provided; do not ask the user directly for this information."
        "Use the CategoryLookup tool with type 'expense' or 'income' based on the input context to retrieve all relevant categories. "
        "Choose the most appropriate and matching category name from the list and use its ID. "
        "If the category is not found, ask the user to provide a valid one. "
        "If the date is not provided or unclear, use today's date from the conversation context. "
        "Then use the AddExpense tool to save the transaction."
    ),
    expected_output="Confirmation that the expense has been saved successfully.",
    agent=expense_agent,
)

crew = Crew(agents=[expense_agent], tasks=[add_expense_task])

result = crew.kickoff()
print(result)
