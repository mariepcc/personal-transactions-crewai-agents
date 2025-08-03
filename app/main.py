import chainlit as cl
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from agents.main import RoutingFlow


@cl.on_chat_start
async def on_chat_start():
    await cl.Message(
        content="👋 Welcome! Please describe your expense or question. For example: `I spent 55 zł on groceries.`"
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    user_input = message.content
    flow = RoutingFlow()
    result = await flow.kickoff_async(inputs={"query": user_input})
    await cl.Message(content=str(result)).send()
