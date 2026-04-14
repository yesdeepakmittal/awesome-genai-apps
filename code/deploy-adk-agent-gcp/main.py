from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from agent import root_agent
import uuid

app = FastAPI()

APP_NAME = "simple_agent_app"
session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)


class QueryRequest(BaseModel):
    query: str
    user_id: str = "user_1"
    session_id: str | None = None


@app.get("/")
def health():
    return {"status": "running"}


@app.post("/chat")
async def chat(req: QueryRequest):
    session_id = req.session_id or str(uuid.uuid4())

    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=req.user_id,
        session_id=session_id,
    )
    if not session:
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=req.user_id,
            session_id=session_id,
        )

    message = types.Content(
        role="user",
        parts=[types.Part(text=req.query)],
    )

    response_text = ""

    async for event in runner.run_async(
        user_id=req.user_id,
        session_id=session_id,
        new_message=message,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    response_text += part.text

    return {
        "session_id": session_id,
        "response": response_text.strip(),
    }