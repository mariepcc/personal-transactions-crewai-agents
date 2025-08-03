import asyncio
from crewai import Agent
from crewai.flow.flow import Flow, start, listen, router
from pydantic import BaseModel
from agents.crews.analysis_crew import AnalysisCrew
from agents.crews.transactions_crew import TransactionsCrew
from langchain_openai import AzureChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

llm = AzureChatOpenAI(
    azure_deployment="gpt-4o",
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version="2024-12-01-preview",
)


class RoutingState(BaseModel):
    query: str = ""
    route_to: str = ""


class RoutingFlow(Flow[RoutingState]):
    @start()
    def receive_query(self):
        return {"query": self.state.query}

    async def classify_intent(self) -> str:
        classifier = Agent(
            role="Intent Classifier",
            goal="Classify user queries as 'add_transaction' or 'query_expenses'.",
            backstory=(
                "You are a precise classifier. You ONLY reply with one of: 'add_transaction' or 'query_expenses'."
            ),
            tools=[],
            verbose=True,
            llm=llm,
        )

        prompt = (
            "Classify the intent of this user query. Reply ONLY with 'add_transaction' or 'query_expenses'.\n"
            f"User: {self.state.query}"
        )

        result = await classifier.kickoff_async(prompt)

        intent = str(result).strip().lower()
        print("Intent classified as:", intent)

        return intent

    @router(receive_query)
    async def route(self):
        result = await self.classify_intent()
        print("🔍 classify_intent result:", result)

        intent = result
        self.state.route_to = intent
        print("Routing to:", intent)
        return intent

    @listen("add_transaction")
    def run_transaction_crew(self):
        crew = TransactionsCrew()
        return crew.crew().kickoff(inputs={"query": self.state.query})

    @listen("query_expenses")
    def run_analysis_crew(self):
        crew = AnalysisCrew()
        return crew.crew().kickoff(inputs={"query": self.state.query})


async def run_flow():
    flow = RoutingFlow()
    result = await flow.kickoff_async(inputs={"query": "Do I have any income?"})
    print(result)


if __name__ == "__main__":
    asyncio.run(run_flow())
