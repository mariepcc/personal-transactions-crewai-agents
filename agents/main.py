from crewai.flow.flow import Flow, start, listen, router
from pydantic import BaseModel
from crews.analysis_crew import AnalysisCrew
from crews.transactions_crew import TransactionCrew


class RoutingState(BaseModel):
    query: str = ""
    route_to: str = ""


class RoutingFlow(Flow[RoutingState]):
    @start()
    def receive_query(self, query: str):
        self.state.query = query

    def classify_intent(self, query: str) -> str:
        manager = TransactionCrew().manager_agent()
        prompt = (
            "Classify the intent of this user query. Reply only with 'add_transaction' or 'query_expenses'.\n"
            f"User: {query}"
        )
        response = manager.run(prompt)
        intent = response.strip().lower()
        if intent not in ["add_transaction", "query_expenses"]:
            intent = "query_expenses"
        return intent

    @router(classify_intent)
    def route(self):
        intent = self.classify_intent(self.state.query)
        self.state.route_to = intent
        return intent

    @listen("transaction_crew")
    def run_transaction_crew(self):
        crew = TransactionCrew()
        return crew.crew().kickoff(inputs={"query": self.state.query})

    @listen("analysis_crew")
    def run_analysis_crew(self):
        crew = AnalysisCrew()
        return crew.crew().kickoff(inputs={"query": self.state.query})


if __name__ == "__main__":
    flow = RoutingFlow()
    flow.kickoff(inputs={"query": "I spent 250 on a doctor appointment"})
    result = flow.execute_route()
    print(result)
