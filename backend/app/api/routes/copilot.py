"""AI Copilot Chat API endpoints.

Provides a conversational AI interface for internal users (counsel/agents)
to ask case-specific questions and get RAG-grounded answers with citations.

Features:
- Real-time streaming responses via SSE
- Case-scoped context retrieval
- Citation tracking
- Conversation memory with Redis persistence
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Any, AsyncGenerator
import json
import logging
import asyncio
from datetime import datetime
from uuid import uuid4
import redis

from app.core.config import get_settings
from app.services.ai_pipeline import get_gemini_model, retrieve_rag_context
from app.services.rag_service import search_for_context, format_context_for_prompt

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/copilot", tags=["AI Copilot"])


# =============================================================================
# Request/Response Models
# =============================================================================

class CopilotMessage(BaseModel):
    """A single message in a copilot conversation."""
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    citations: Optional[list[str]] = Field(None, description="Citations for assistant messages")


class CopilotRequest(BaseModel):
    """Request for copilot assistance."""
    question: str = Field(..., description="User's question")
    case_id: Optional[str] = Field(None, description="Case ID for context")
    parcel_id: Optional[str] = Field(None, description="Parcel ID for context")
    jurisdiction: Optional[str] = Field(None, description="Jurisdiction for filtering")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    conversation_history: Optional[list[dict]] = Field(None, description="Previous messages")
    stream: bool = Field(True, description="Whether to stream the response")


class CopilotResponse(BaseModel):
    """Response from copilot (non-streaming)."""
    conversation_id: str
    answer: str
    citations: list[str]
    confidence: float
    sources: list[dict[str, Any]]
    suggested_actions: list[str]


# =============================================================================
# Copilot System Prompt
# =============================================================================

COPILOT_SYSTEM_PROMPT = """You are an AI legal assistant for an eminent domain law firm. 
You help attorneys and land agents with case-specific questions.

IMPORTANT RULES:
1. NEVER provide final legal advice - always indicate that an attorney should review
2. Ground your answers in the provided legal context and case data
3. Cite specific statutes, cases, or rules when relevant
4. Be concise but thorough
5. Flag any issues that require human attorney review
6. If you don't know something, say so clearly

You have access to:
- State-specific eminent domain rules and procedures
- Case documents and history (when provided)
- Statutory requirements and deadlines

When answering questions:
- Start with a direct answer to the question
- Provide relevant citations from the legal context
- List any action items or next steps
- Note any risks or concerns
"""


# =============================================================================
# Redis-based Conversation Storage
# =============================================================================

CONVERSATION_PREFIX = "copilot:conversation:"
CONVERSATION_TTL = 86400 * 7  # 7 days
CONVERSATION_LIST_PREFIX = "copilot:user_conversations:"
MAX_MESSAGES_PER_CONVERSATION = 20


def _get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client for conversation storage."""
    try:
        return redis.from_url(
            settings.effective_redis_url,
            decode_responses=True,
            socket_timeout=5,
        )
    except Exception as e:
        logger.warning(f"Redis unavailable, using in-memory fallback: {e}")
        return None


# In-memory fallback when Redis is unavailable
_conversations: dict[str, list[CopilotMessage]] = {}


def get_conversation(conversation_id: str) -> list[CopilotMessage]:
    """Get conversation history by ID from Redis or memory."""
    client = _get_redis_client()
    
    if client:
        try:
            key = f"{CONVERSATION_PREFIX}{conversation_id}"
            data = client.get(key)
            if data:
                messages_data = json.loads(data)
                return [
                    CopilotMessage(
                        role=m["role"],
                        content=m["content"],
                        timestamp=datetime.fromisoformat(m["timestamp"]) if isinstance(m["timestamp"], str) else m["timestamp"],
                        citations=m.get("citations"),
                    )
                    for m in messages_data
                ]
            return []
        except Exception as e:
            logger.warning(f"Redis read failed, using memory: {e}")
    
    return _conversations.get(conversation_id, [])


def save_message(conversation_id: str, message: CopilotMessage, user_id: str = "anonymous"):
    """Save a message to conversation history in Redis or memory."""
    client = _get_redis_client()
    
    if client:
        try:
            key = f"{CONVERSATION_PREFIX}{conversation_id}"
            
            # Get existing messages
            existing_data = client.get(key)
            messages = json.loads(existing_data) if existing_data else []
            
            # Add new message
            messages.append({
                "role": message.role,
                "content": message.content,
                "timestamp": message.timestamp.isoformat() if isinstance(message.timestamp, datetime) else message.timestamp,
                "citations": message.citations,
            })
            
            # Limit to last N messages
            if len(messages) > MAX_MESSAGES_PER_CONVERSATION:
                messages = messages[-MAX_MESSAGES_PER_CONVERSATION:]
            
            # Save with TTL
            client.setex(key, CONVERSATION_TTL, json.dumps(messages))
            
            # Track conversation in user's list
            user_key = f"{CONVERSATION_LIST_PREFIX}{user_id}"
            client.zadd(user_key, {conversation_id: datetime.utcnow().timestamp()})
            client.expire(user_key, CONVERSATION_TTL)
            
            return
        except Exception as e:
            logger.warning(f"Redis write failed, using memory: {e}")
    
    # Fallback to memory
    if conversation_id not in _conversations:
        _conversations[conversation_id] = []
    _conversations[conversation_id].append(message)
    
    if len(_conversations[conversation_id]) > MAX_MESSAGES_PER_CONVERSATION:
        _conversations[conversation_id] = _conversations[conversation_id][-MAX_MESSAGES_PER_CONVERSATION:]


def list_user_conversations(user_id: str = "anonymous", limit: int = 20) -> list[dict]:
    """List recent conversations for a user."""
    client = _get_redis_client()
    
    if client:
        try:
            user_key = f"{CONVERSATION_LIST_PREFIX}{user_id}"
            # Get most recent conversations (sorted set, newest first)
            conversation_ids = client.zrevrange(user_key, 0, limit - 1, withscores=True)
            
            result = []
            for conv_id, timestamp in conversation_ids:
                key = f"{CONVERSATION_PREFIX}{conv_id}"
                data = client.get(key)
                if data:
                    messages = json.loads(data)
                    if messages:
                        # Get preview from first user message
                        first_user_msg = next((m for m in messages if m["role"] == "user"), None)
                        result.append({
                            "conversation_id": conv_id,
                            "last_updated": datetime.fromtimestamp(timestamp).isoformat(),
                            "message_count": len(messages),
                            "preview": first_user_msg["content"][:100] if first_user_msg else "",
                        })
            return result
        except Exception as e:
            logger.warning(f"Redis list failed: {e}")
    
    # Memory fallback - limited functionality
    return [
        {
            "conversation_id": conv_id,
            "last_updated": datetime.utcnow().isoformat(),
            "message_count": len(msgs),
            "preview": msgs[0].content[:100] if msgs else "",
        }
        for conv_id, msgs in list(_conversations.items())[:limit]
    ]


def delete_conversation(conversation_id: str, user_id: str = "anonymous") -> bool:
    """Delete a conversation from Redis or memory."""
    client = _get_redis_client()
    
    if client:
        try:
            key = f"{CONVERSATION_PREFIX}{conversation_id}"
            user_key = f"{CONVERSATION_LIST_PREFIX}{user_id}"
            
            client.delete(key)
            client.zrem(user_key, conversation_id)
            return True
        except Exception as e:
            logger.warning(f"Redis delete failed: {e}")
    
    # Memory fallback
    if conversation_id in _conversations:
        del _conversations[conversation_id]
        return True
    return False


# =============================================================================
# Core Copilot Logic
# =============================================================================

async def build_copilot_prompt(
    question: str,
    jurisdiction: str = None,
    case_context: dict = None,
    conversation_history: list[dict] = None,
) -> tuple[str, list[str]]:
    """Build the complete prompt for the copilot with RAG context.
    
    Returns:
        Tuple of (prompt, citations)
    """
    # Retrieve relevant legal context
    search_query = question
    if jurisdiction:
        search_query = f"{jurisdiction} {question}"
    
    rag_results = await search_for_context(search_query, jurisdiction, top_k=5)
    legal_context = format_context_for_prompt(rag_results)
    citations = [r.citation for r in rag_results if r.citation]
    
    # Build prompt parts
    prompt_parts = [COPILOT_SYSTEM_PROMPT]
    
    # Add legal context
    prompt_parts.append(f"\n{legal_context}")
    
    # Add case context if provided
    if case_context:
        prompt_parts.append(f"\nCURRENT CASE CONTEXT:\n{json.dumps(case_context, indent=2)}")
    
    # Add conversation history
    if conversation_history:
        prompt_parts.append("\nCONVERSATION HISTORY:")
        for msg in conversation_history[-5:]:  # Last 5 messages
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt_parts.append(f"{role.upper()}: {content}")
    
    # Add current question
    prompt_parts.append(f"\nUSER QUESTION: {question}")
    prompt_parts.append("\nProvide a helpful, well-cited response:")
    
    return "\n".join(prompt_parts), citations


async def generate_copilot_response(
    request: CopilotRequest,
    case_context: dict = None,
) -> AsyncGenerator[str, None]:
    """Generate streaming copilot response.
    
    Yields SSE-formatted chunks.
    """
    conversation_id = request.conversation_id or str(uuid4())
    
    # Build prompt with RAG context
    prompt, citations = await build_copilot_prompt(
        question=request.question,
        jurisdiction=request.jurisdiction,
        case_context=case_context,
        conversation_history=request.conversation_history,
    )
    
    # Save user message
    user_message = CopilotMessage(role="user", content=request.question)
    save_message(conversation_id, user_message)
    
    # Send conversation ID first
    yield f"data: {json.dumps({'type': 'conversation_id', 'conversation_id': conversation_id})}\n\n"
    
    # Send citations
    if citations:
        yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"
    
    # Get Gemini model
    model = get_gemini_model()
    if model is None:
        error_msg = "AI service is currently unavailable. Please try again later."
        yield f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n"
        return
    
    try:
        # Generate streaming response
        response = await model.generate_content_async(
            prompt,
            stream=True,
        )
        
        full_response = ""
        async for chunk in response:
            if chunk.text:
                full_response += chunk.text
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk.text})}\n\n"
                await asyncio.sleep(0.01)  # Small delay for smoother streaming
        
        # Save assistant message
        assistant_message = CopilotMessage(
            role="assistant",
            content=full_response,
            citations=citations,
        )
        save_message(conversation_id, assistant_message)
        
        # Send completion signal
        yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"
        
    except Exception as e:
        logger.error(f"Copilot generation failed: {e}")
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"


async def generate_copilot_response_sync(
    request: CopilotRequest,
    case_context: dict = None,
) -> CopilotResponse:
    """Generate non-streaming copilot response."""
    conversation_id = request.conversation_id or str(uuid4())
    
    # Build prompt with RAG context
    prompt, citations = await build_copilot_prompt(
        question=request.question,
        jurisdiction=request.jurisdiction,
        case_context=case_context,
        conversation_history=request.conversation_history,
    )
    
    # Save user message
    user_message = CopilotMessage(role="user", content=request.question)
    save_message(conversation_id, user_message)
    
    # Get Gemini model
    model = get_gemini_model()
    if model is None:
        raise HTTPException(status_code=503, detail="AI service unavailable")
    
    try:
        response = await model.generate_content_async(prompt)
        
        if response.candidates and len(response.candidates) > 0:
            answer = response.candidates[0].content.parts[0].text
        else:
            answer = "I was unable to generate a response. Please try rephrasing your question."
        
        # Save assistant message
        assistant_message = CopilotMessage(
            role="assistant",
            content=answer,
            citations=citations,
        )
        save_message(conversation_id, assistant_message)
        
        # Parse suggested actions from response
        suggested_actions = []
        if "next steps" in answer.lower() or "action" in answer.lower():
            # Simple extraction - could be improved with structured output
            lines = answer.split("\n")
            for line in lines:
                if line.strip().startswith(("-", "•", "*")) and len(line.strip()) > 5:
                    suggested_actions.append(line.strip().lstrip("-•* "))
        
        return CopilotResponse(
            conversation_id=conversation_id,
            answer=answer,
            citations=citations,
            confidence=0.85,  # Could be computed from model confidence
            sources=[{"citation": c} for c in citations],
            suggested_actions=suggested_actions[:5],
        )
        
    except Exception as e:
        logger.error(f"Copilot generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/ask")
async def ask_copilot(request: CopilotRequest):
    """Ask the AI copilot a question.
    
    Supports both streaming (SSE) and non-streaming responses.
    Set `stream=true` for real-time streaming.
    """
    # Build case context if IDs provided
    case_context = {}
    if request.case_id:
        case_context["case_id"] = request.case_id
    if request.parcel_id:
        case_context["parcel_id"] = request.parcel_id
    if request.jurisdiction:
        case_context["jurisdiction"] = request.jurisdiction
    
    if request.stream:
        return StreamingResponse(
            generate_copilot_response(request, case_context),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    else:
        return await generate_copilot_response_sync(request, case_context)


@router.get("/conversations")
async def list_conversations(request: Request, limit: int = 20):
    """List recent conversations for the current user.
    
    Returns a list of conversation summaries with preview text.
    """
    # Get user ID from header or use anonymous
    user_id = request.headers.get("X-User-ID", "anonymous")
    conversations = list_user_conversations(user_id, limit)
    
    return {
        "conversations": conversations,
        "count": len(conversations),
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation_history(conversation_id: str):
    """Get conversation history by ID."""
    history = get_conversation(conversation_id)
    if not history:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "conversation_id": conversation_id,
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat() if isinstance(msg.timestamp, datetime) else msg.timestamp,
                "citations": msg.citations,
            }
            for msg in history
        ],
    }


@router.delete("/conversations/{conversation_id}")
async def clear_conversation(conversation_id: str, request: Request):
    """Clear conversation history."""
    user_id = request.headers.get("X-User-ID", "anonymous")
    deleted = delete_conversation(conversation_id, user_id)
    return {"status": "cleared" if deleted else "not_found"}


@router.get("/health")
async def copilot_health():
    """Check copilot service health."""
    model = get_gemini_model()
    
    # Check Redis connectivity
    redis_available = False
    redis_client = _get_redis_client()
    if redis_client:
        try:
            redis_client.ping()
            redis_available = True
        except Exception:
            pass
    
    return {
        "status": "healthy" if model else "degraded",
        "gemini_available": model is not None,
        "redis_available": redis_available,
        "storage_mode": "redis" if redis_available else "memory",
        "active_conversations_in_memory": len(_conversations),
    }


# =============================================================================
# Quick Action Endpoints
# =============================================================================

@router.post("/draft-response")
async def draft_response(
    parcel_id: str,
    response_type: str,  # counter_offer, acceptance, rejection
    jurisdiction: str = None,
    notes: str = None,
):
    """Generate a draft response for a landowner communication.
    
    Uses RAG context to ensure jurisdiction-appropriate language.
    """
    prompt = f"""Draft a professional {response_type} response for an eminent domain case.
    
Parcel ID: {parcel_id}
Jurisdiction: {jurisdiction or 'Unknown'}
Notes: {notes or 'None provided'}

The response should:
1. Be professionally written and legally appropriate
2. Reference relevant jurisdiction requirements
3. Clearly state the position and next steps
4. Include appropriate legal disclaimers

Generate a complete draft suitable for attorney review."""

    request = CopilotRequest(
        question=prompt,
        parcel_id=parcel_id,
        jurisdiction=jurisdiction,
        stream=False,
    )
    
    return await generate_copilot_response_sync(request)


@router.post("/summarize-case")
async def summarize_case(
    case_id: str = None,
    parcel_id: str = None,
    jurisdiction: str = None,
):
    """Generate a summary of a case's current status and next steps."""
    prompt = f"""Provide a comprehensive summary of the eminent domain case status.

Case ID: {case_id or 'N/A'}
Parcel ID: {parcel_id or 'N/A'}
Jurisdiction: {jurisdiction or 'Unknown'}

Please include:
1. Current case stage and status
2. Key dates and deadlines
3. Outstanding issues or risks
4. Recommended next actions
5. Relevant statutory requirements for this jurisdiction"""

    request = CopilotRequest(
        question=prompt,
        case_id=case_id,
        parcel_id=parcel_id,
        jurisdiction=jurisdiction,
        stream=False,
    )
    
    return await generate_copilot_response_sync(request)


@router.post("/explain-requirement")
async def explain_requirement(
    requirement: str,
    jurisdiction: str,
):
    """Explain a specific legal requirement for a jurisdiction.
    
    Uses RAG to ground the explanation in actual statutes.
    """
    prompt = f"""Explain the following eminent domain requirement for {jurisdiction}:

{requirement}

Please include:
1. What the requirement means in practice
2. Specific statutory citations
3. Deadlines or timeframes involved
4. Consequences of non-compliance
5. Best practices for compliance"""

    request = CopilotRequest(
        question=prompt,
        jurisdiction=jurisdiction,
        stream=False,
    )
    
    return await generate_copilot_response_sync(request)
