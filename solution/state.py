from typing import Annotated,TypedDict,Any
from langgraph.graph.message import add_messages

class TicketState(TypedDict,total=False):
    # total=False makes all keys optional by default
    messages: Annotated[list,add_messages]

    # identity/routing context
    ticket_id: str # used as thread_id in checkpointer
    customer_id: str # external Cultpass userid
    
    # classifer output
    category: str # technical-support, refund, etc
    priority: str # low|medium|high
    confidence: float # clf confidence
    route: str # which route the classifier takes

     # Retrieval / memory context
    retrieved_docs: list[dict[str, Any]]   # KB snippets used by the resolver
    memory_context: list[str]              # long-term memories about the user
    tool_results: list[dict[str, Any]]     # DB tool calls/results observed by the tool agent

    # Outcome
    resolution: str             # the drafted customer-facing answer
    escalation_required: bool   # True -> hand off to a human
    escalation_reason: str      # machine-readable reason when escalation is required
