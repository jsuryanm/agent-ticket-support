# reset_udahub.py
import asyncio
import os
import re
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager
from langchain_core.messages import (
    SystemMessage,
    HumanMessage, 
)
from langgraph.graph.state import CompiledStateGraph

from solution.config import settings
from solution.data.models import udahub

EXIT_WORDS = {"quit", "exit", "q"}
CHAT_TURN_TIMEOUT_SECONDS = 12
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "can",
    "do",
    "for",
    "how",
    "i",
    "is",
    "it",
    "me",
    "my",
    "of",
    "the",
    "to",
    "what",
}


Base = declarative_base()

def reset_db(db_path: str, echo: bool = True):
    """Drops the existing udahub.db file and recreates all tables."""

    # Remove the file if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"✅ Removed existing {db_path}")

    # Create a new engine and recreate tables
    engine = create_engine(f"sqlite:///{db_path}", echo=echo)
    Base.metadata.create_all(engine)
    print(f"✅ Recreated {db_path} with fresh schema")


@contextmanager
def get_session(engine: Engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def model_to_dict(instance):
    """Convert a SQLAlchemy model instance to a dictionary."""
    return {
        column.name: getattr(instance, column.name)
        for column in instance.__table__.columns
    }

def _query_terms(text: str) -> list[str]:
    return [
        term
        for term in re.findall(r"[a-z0-9]+", text.lower())
        if len(term) > 2 and term not in _STOP_WORDS
    ]

def _local_knowledge_fallback(user_input: str) -> str:
    """Return a local KB answer when remote LLM/RAG services are unavailable."""
    config = settings()
    if not config.UDAHUB_DB.exists():
        return "I could not reach the agent services, and the local knowledge database is missing."

    terms = _query_terms(user_input)
    engine = create_engine(f"sqlite:///{config.UDAHUB_DB}", echo=False)
    session = sessionmaker(bind=engine)()
    try:
        articles = session.query(udahub.Knowledge).all()
    finally:
        session.close()

    if not articles:
        return "I could not reach the agent services, and the local knowledge base is empty."

    def score(article) -> int:
        haystack = f"{article.title} {article.tags or ''} {article.content}".lower()
        return sum(1 for term in terms if term in haystack)

    best = max(articles, key=score)
    if score(best) == 0:
        return (
            "I could not reach the agent services. Locally, I can help with CultPass "
            "reservations, subscriptions, refunds, login issues, payments, profiles, "
            "waitlists, notifications, and contacting support."
        )

    excerpt = " ".join((best.content or "").split())
    if len(excerpt) > 500:
        excerpt = excerpt[:497].rstrip() + "..."
    return f"{best.title}: {excerpt}"

def chat_interface(agent:CompiledStateGraph, ticket_id:str):
    is_first_iteration = False
    messages = [SystemMessage(content = f"ThreadId: {ticket_id}")]
    while True:
        user_input = input("User: ")
        print("User:", user_input)
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Assistant: Goodbye!")
            break
        messages = [HumanMessage(content=user_input)]
        if is_first_iteration:
            messages.append(HumanMessage(content=user_input))
        trigger = {
            "messages": messages
        }
        config = {
            "configurable": {
                "thread_id": ticket_id,
            }
        }
        
        result = agent.invoke(input=trigger, config=config)
        print("Assistant:", result["messages"][-1].content)
        is_first_iteration = False

async def async_chat_interface(agent: CompiledStateGraph, ticket_id: str) -> None:
    """Simple REPL. `ticket_id` is the thread_id -> short-term memory per session."""
    config = {"configurable": {"thread_id": ticket_id}}
    print("UDA-Hub ready. Type 'q' to quit.")
    while True:
        user_input = input("User: ")
        print("User:", user_input)
        user_input = user_input.strip()
        if user_input.lower() in EXIT_WORDS:
            print("Assistant: Goodbye!")
            break
        if not user_input:
            print("Assistant: Please type a question, or 'q' to quit.")
            continue
        try:
            result = await asyncio.wait_for(
                agent.ainvoke(
                    {"messages": [HumanMessage(content=user_input)], "ticket_id": ticket_id},
                    config=config,
                ),
                timeout=CHAT_TURN_TIMEOUT_SECONDS,
            )
            print("Assistant:", result["messages"][-1].content)
        except asyncio.TimeoutError:
            print("Assistant:", _local_knowledge_fallback(user_input))
        except Exception as exc:
            print(f"Assistant: {_local_knowledge_fallback(user_input)}")
