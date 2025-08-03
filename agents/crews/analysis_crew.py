from crewai.tools import BaseTool
from crewai import Agent, Task, Crew, Process
from crewai.project import CrewBase, agent, task, crew
import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_community.tools.sql_database.tool import (
    InfoSQLDatabaseTool,
    ListSQLDatabaseTool,
    QuerySQLCheckerTool,
    QuerySQLDataBaseTool,
)
from agents.util import DB

load_dotenv()

llm = AzureChatOpenAI(
    azure_deployment="gpt-4o",
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-12-01-preview",
)


class ListTablesTool(BaseTool):
    name: str = "list_tables"
    description: str = "Lists all tables in the connected SQL database."

    def _run(self) -> str:
        """
        List the available tables in the database.
        """
        return ListSQLDatabaseTool(db=DB).invoke("")


class TablesSchemaTool(BaseTool):
    name: str = "tables_schema"
    description: str = "Get the schema and sample rows for the specified tables."

    def _run(self, tables: str) -> str:
        """
        Get the schema and sample rows for the specified tables.

        Args:
            tables (str): A comma-separated list of table names.

        Returns:
            str: A string containing the schema and sample rows for the specified tables.
        """
        tool = InfoSQLDatabaseTool(db=DB)
        return tool.invoke(tables)


class QerySQLDataTool(BaseTool):
    name: str = "execute_sql"
    description: str = "Executes a SQL query against the connected database."

    def _run(self, sql_query: str) -> str:
        """
        Execute a SQL query against the database.

        Args:
            sql_query (str): The SQL query to execute.

        Returns:
            str: The result of the SQL query.
        """
        return QuerySQLDataBaseTool(db=DB).invoke(sql_query)


class CheckSQLTool(BaseTool):
    name: str = "check_sql"
    description: str = "Checks the correctness of a SQL query and returns the corrected query if any issues are found."

    def _run(self, sql_query: str) -> str:
        """
        Check the correctness of a SQL query.

        Args:
            sql_query (str): The SQL query to check.

        Returns:
            str: The corrected SQL query if any issues are found, otherwise the original query.
        """
        return QuerySQLCheckerTool(db=DB).invoke({"query": sql_query})


@CrewBase
class TransactionsCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def sql_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["sql_agent"],
            llm=llm,
            tools=[
                ListTablesTool(),
                TablesSchemaTool(),
                QerySQLDataTool(),
                CheckSQLTool(),
            ],
            allow_delegation=False,
        )

    @agent
    def data_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["data_analyst"],
            llm=llm,
            allow_delegation=False,
        )

    @agent
    def report_writer(self) -> Agent:
        return Agent(
            config=self.agents_config["report_writer"],
            llm=llm,
            allow_delegation=False,
        )

    @task
    def extract_data_task(self) -> Task:
        return Task(
            config=self.tasks_config["extract_data_task"],
            agent=self.sql_agent(),
        )

    @task
    def analyze_data_task(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_data_task"],
            agent=self.data_analyst(),
            context=[self.extract_data_task()],
        )

    @task
    def write_report_task(self) -> Task:
        return Task(
            config=self.tasks_config["write_report_task"],
            agent=self.report_writer(),
            context=[self.analyze_data_task()],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[
                self.sql_agent(),
                self.data_analyst(),
                self.report_writer(),
            ],
            tasks=[
                self.extract_data_task(),
                self.analyze_data_task(),
                self.write_report_task(),
            ],
            process=Process.sequential,
            manager_llm=llm,
        )


if __name__ == "__main__":
    crew_instance = TransactionsCrew()
    result = crew_instance.crew().kickoff(
        inputs={"query": "How much did I spend on groceries so far?"}
    )
    print(result)
