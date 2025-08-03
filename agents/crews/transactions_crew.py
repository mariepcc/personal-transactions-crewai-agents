from crewai.tools import BaseTool
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew
import os
import requests
import pyodbc
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

load_dotenv()

llm = AzureChatOpenAI(
    azure_deployment="gpt-4o",
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-12-01-preview",
)


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


@CrewBase
class TransactionsCrew:
    agents_config = "../config/agents.yaml"
    tasks_config = "../config/insert_tasks.yaml"

    @agent
    def transaction_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["transaction_agent"],
            tools=[CategoryLookupTool(), AddExpenseTool()],
            verbose=True,
            llm=llm,
        )

    @task
    def add_transaction_task(self) -> Task:
        return Task(
            config=self.tasks_config["add_transaction_task"],
            agent=self.transaction_agent(),
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[
                self.transaction_agent(),
            ],
            tasks=[
                self.add_transaction_task(),
            ],
            process=Process.sequential,
            manager_llm=llm,
        )


if __name__ == "__main__":
    crew_instance = TransactionsCrew()
    result = crew_instance.crew().kickoff(
        inputs={"query": "I spend 250 zł on doctor's appointment."}
    )
    print(result)
