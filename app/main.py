import asyncio
import chainlit as cl
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from agents.main import TransactionsCrew


@cl.on_chat_start
async def on_chat_start():
    crew_instance = TransactionsCrew()
    crew = crew_instance.crew()

    await cl.Message(
        content="👋 Welcome! Please describe your expense to get started. For example: `I spent 55 zł on groceries.`"
    ).send()

    cl.user_session.set("crew", crew)


@cl.on_message
async def on_message(message: cl.Message):
    crew = cl.user_session.get("crew")
    user_input = message.content

    # Run in background thread to avoid blocking
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, crew.kickoff, {"query": user_input})

    await cl.Message(content=str(result)).send()
