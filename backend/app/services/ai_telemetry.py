"""AI Telemetry Service.

Provides comprehensive telemetry for AI operations:
- Full input/output logging
- Reproducible run capability
- Cost tracking
- Audit trail generation

Every AI action is logged for compliance, debugging, and improvement.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from app.services.hashing import sha256_hex


# Cost estimates per 1K tokens (as of 2026)
MODEL_COSTS = {
    "gemini-1.5-pro": {"input": Decimal("0.00125"), "output": Decimal("0.005")},
    "gemini-1.5-flash": {"input": Decimal("0.000075"), "output": Decimal("0.0003")},
    "gemini-2.0-pro": {"input": Decimal("0.0015"), "output": Decimal("0.006")},
}


@dataclass
class AIEventInput:
    """Input for logging an AI event."""
    action: str
    model: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    
    # Optional context
    actor_persona: Optional[str] = None
    actor_user_id: Optional[str] = None
    project_id: Optional[str] = None
    parcel_id: Optional[str] = None
    
    # Prompt info
    prompt_template_id: Optional[str] = None
    prompt_version: Optional[str] = None
    temperature: Optional[float] = None
    
    # Performance
    latency_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    
    # Retrieval
    retrieval_set_ids: Optional[list[str]] = None
    retrieval_query: Optional[str] = None
    
    # Tool calls
    tool_calls: Optional[list[dict[str, Any]]] = None
    
    # Citations
    citation_ids: Optional[list[str]] = None


@dataclass
class AIEvent:
    """A logged AI event."""
    id: str
    action: str
    model: str
    
    # Hashes for verification
    prompt_hash: str
    inputs_hash: str
    outputs_hash: str
    
    # Content
    inputs_json: dict[str, Any]
    outputs_json: dict[str, Any]
    
    # Metadata
    actor_persona: Optional[str] = None
    actor_user_id: Optional[str] = None
    project_id: Optional[str] = None
    parcel_id: Optional[str] = None
    
    # Prompt
    prompt_template_id: Optional[str] = None
    prompt_version: Optional[str] = None
    model_version: Optional[str] = None
    temperature: Optional[float] = None
    
    # Performance
    latency_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_estimate_usd: Optional[Decimal] = None
    
    # Retrieval
    retrieval_set_ids: list[str] = field(default_factory=list)
    retrieval_query: Optional[str] = None
    
    # Tool calls
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    
    # Citations
    citation_ids: list[str] = field(default_factory=list)
    
    # Outcome
    confidence: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    
    # AI Decision link
    ai_decision_id: Optional[str] = None
    
    # Timestamp
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "action": self.action,
            "model": self.model,
            "prompt_hash": self.prompt_hash,
            "inputs_hash": self.inputs_hash,
            "outputs_hash": self.outputs_hash,
            "actor_persona": self.actor_persona,
            "actor_user_id": self.actor_user_id,
            "project_id": self.project_id,
            "parcel_id": self.parcel_id,
            "prompt_template_id": self.prompt_template_id,
            "prompt_version": self.prompt_version,
            "model_version": self.model_version,
            "temperature": self.temperature,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost_estimate_usd": str(self.cost_estimate_usd) if self.cost_estimate_usd else None,
            "retrieval_set_ids": self.retrieval_set_ids,
            "retrieval_query": self.retrieval_query,
            "tool_calls": self.tool_calls,
            "citation_ids": self.citation_ids,
            "confidence": self.confidence,
            "success": self.success,
            "error_message": self.error_message,
            "ai_decision_id": self.ai_decision_id,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class PromptTemplate:
    """A versioned prompt template."""
    id: str
    name: str
    version: str
    category: str
    system_prompt: Optional[str]
    user_prompt_template: str
    output_schema: Optional[dict[str, Any]]
    default_model: str = "gemini-1.5-pro"
    default_temperature: float = 0.2
    max_tokens: Optional[int] = None
    is_active: bool = True


class AITelemetryService:
    """Service for AI telemetry logging and analysis."""

    def __init__(self):
        """Initialize the service."""
        # In-memory store (would be DB in production)
        self._events: dict[str, AIEvent] = {}
        self._templates: dict[str, PromptTemplate] = {}

    def log_event(self, input: AIEventInput) -> AIEvent:
        """Log an AI event.
        
        Args:
            input: Event input data
            
        Returns:
            Logged event
        """
        event_id = f"aievt_{uuid.uuid4().hex[:12]}"
        
        # Compute hashes
        inputs_json = json.dumps(input.inputs, sort_keys=True, default=str)
        outputs_json = json.dumps(input.outputs, sort_keys=True, default=str)
        
        inputs_hash = sha256_hex(inputs_json.encode())
        outputs_hash = sha256_hex(outputs_json.encode())
        
        # Compute prompt hash from the actual prompt sent
        prompt_content = input.inputs.get("prompt", "") or input.inputs.get("messages", "")
        prompt_hash = sha256_hex(str(prompt_content).encode())
        
        # Estimate cost
        cost_estimate = self._estimate_cost(
            input.model,
            input.input_tokens or 0,
            input.output_tokens or 0,
        )
        
        # Calculate total tokens
        total_tokens = None
        if input.input_tokens is not None or input.output_tokens is not None:
            total_tokens = (input.input_tokens or 0) + (input.output_tokens or 0)
        
        event = AIEvent(
            id=event_id,
            action=input.action,
            model=input.model,
            prompt_hash=prompt_hash,
            inputs_hash=inputs_hash,
            outputs_hash=outputs_hash,
            inputs_json=input.inputs,
            outputs_json=input.outputs,
            actor_persona=input.actor_persona,
            actor_user_id=input.actor_user_id,
            project_id=input.project_id,
            parcel_id=input.parcel_id,
            prompt_template_id=input.prompt_template_id,
            prompt_version=input.prompt_version,
            temperature=input.temperature,
            latency_ms=input.latency_ms,
            input_tokens=input.input_tokens,
            output_tokens=input.output_tokens,
            total_tokens=total_tokens,
            cost_estimate_usd=cost_estimate,
            retrieval_set_ids=input.retrieval_set_ids or [],
            retrieval_query=input.retrieval_query,
            tool_calls=input.tool_calls or [],
            citation_ids=input.citation_ids or [],
        )
        
        self._events[event_id] = event
        return event

    def _estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> Optional[Decimal]:
        """Estimate cost for an AI call.
        
        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Estimated cost in USD
        """
        if model not in MODEL_COSTS:
            return None
        
        costs = MODEL_COSTS[model]
        input_cost = (Decimal(input_tokens) / 1000) * costs["input"]
        output_cost = (Decimal(output_tokens) / 1000) * costs["output"]
        
        return input_cost + output_cost

    def get_event(self, event_id: str) -> Optional[AIEvent]:
        """Get an event by ID.
        
        Args:
            event_id: Event identifier
            
        Returns:
            Event or None
        """
        return self._events.get(event_id)

    def list_events(
        self,
        project_id: Optional[str] = None,
        parcel_id: Optional[str] = None,
        action: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[AIEvent]:
        """List events with optional filters.
        
        Args:
            project_id: Filter by project
            parcel_id: Filter by parcel
            action: Filter by action type
            since: Filter by timestamp
            limit: Maximum events to return
            
        Returns:
            List of matching events
        """
        events = list(self._events.values())
        
        if project_id:
            events = [e for e in events if e.project_id == project_id]
        if parcel_id:
            events = [e for e in events if e.parcel_id == parcel_id]
        if action:
            events = [e for e in events if e.action == action]
        if since:
            events = [e for e in events if e.created_at >= since]
        
        # Sort by timestamp descending
        events.sort(key=lambda e: e.created_at, reverse=True)
        
        return events[:limit]

    def get_event_trace(self, event_id: str) -> dict[str, Any]:
        """Get full trace for an event including inputs/outputs.
        
        Args:
            event_id: Event identifier
            
        Returns:
            Full event trace
        """
        event = self.get_event(event_id)
        if not event:
            return {"error": "Event not found"}
        
        return {
            "event": event.to_dict(),
            "inputs": event.inputs_json,
            "outputs": event.outputs_json,
            "verification": {
                "inputs_hash_valid": sha256_hex(
                    json.dumps(event.inputs_json, sort_keys=True, default=str).encode()
                ) == event.inputs_hash,
                "outputs_hash_valid": sha256_hex(
                    json.dumps(event.outputs_json, sort_keys=True, default=str).encode()
                ) == event.outputs_hash,
            },
        }

    def get_replay_config(self, event_id: str) -> dict[str, Any]:
        """Get configuration to replay an AI event.
        
        Returns prompt template, variables, and retrieval context
        needed to reproduce the exact same call.
        
        Args:
            event_id: Event identifier
            
        Returns:
            Replay configuration
        """
        event = self.get_event(event_id)
        if not event:
            return {"error": "Event not found"}
        
        return {
            "event_id": event_id,
            "original_timestamp": event.created_at.isoformat(),
            "model": event.model,
            "temperature": event.temperature,
            "prompt_template_id": event.prompt_template_id,
            "prompt_version": event.prompt_version,
            "inputs": event.inputs_json,
            "retrieval_set_ids": event.retrieval_set_ids,
            "retrieval_query": event.retrieval_query,
            "expected_outputs_hash": event.outputs_hash,
        }

    def register_template(self, template: PromptTemplate) -> None:
        """Register a prompt template.
        
        Args:
            template: Template to register
        """
        key = f"{template.id}:{template.version}"
        self._templates[key] = template

    def get_template(
        self,
        template_id: str,
        version: Optional[str] = None,
    ) -> Optional[PromptTemplate]:
        """Get a prompt template.
        
        Args:
            template_id: Template identifier
            version: Specific version (None = latest)
            
        Returns:
            Template or None
        """
        if version:
            return self._templates.get(f"{template_id}:{version}")
        
        # Find latest version
        matching = [
            t for k, t in self._templates.items()
            if k.startswith(f"{template_id}:")
        ]
        
        if not matching:
            return None
        
        # Sort by version and return latest
        matching.sort(key=lambda t: t.version, reverse=True)
        return matching[0]

    def get_cost_summary(
        self,
        project_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Get cost summary for AI usage.
        
        Args:
            project_id: Filter by project
            since: Filter by timestamp
            
        Returns:
            Cost summary
        """
        events = self.list_events(
            project_id=project_id,
            since=since,
            limit=10000,
        )
        
        total_cost = Decimal("0")
        total_input_tokens = 0
        total_output_tokens = 0
        by_model: dict[str, Decimal] = {}
        by_action: dict[str, Decimal] = {}
        
        for event in events:
            if event.cost_estimate_usd:
                total_cost += event.cost_estimate_usd
                by_model[event.model] = by_model.get(event.model, Decimal("0")) + event.cost_estimate_usd
                by_action[event.action] = by_action.get(event.action, Decimal("0")) + event.cost_estimate_usd
            
            total_input_tokens += event.input_tokens or 0
            total_output_tokens += event.output_tokens or 0
        
        return {
            "total_cost_usd": str(total_cost),
            "total_events": len(events),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "by_model": {k: str(v) for k, v in by_model.items()},
            "by_action": {k: str(v) for k, v in by_action.items()},
        }


# Decorator for automatic telemetry logging
def log_ai_call(action: str, template_id: Optional[str] = None):
    """Decorator to automatically log AI calls.
    
    Usage:
        @log_ai_call("generate_draft", "draft_v2")
        async def generate_draft(inputs: dict) -> dict:
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            import time
            
            # Get telemetry service (would be injected in production)
            telemetry = AITelemetryService()
            
            start_time = time.time()
            error_message = None
            outputs = {}
            
            try:
                outputs = await func(*args, **kwargs)
                return outputs
            except Exception as e:
                error_message = str(e)
                raise
            finally:
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Attempt to extract inputs from args/kwargs
                inputs = kwargs.get("inputs", kwargs.get("payload", {}))
                if args:
                    inputs = args[0] if isinstance(args[0], dict) else inputs
                
                telemetry.log_event(AIEventInput(
                    action=action,
                    model=kwargs.get("model", "gemini-1.5-pro"),
                    inputs=inputs,
                    outputs=outputs,
                    prompt_template_id=template_id,
                    latency_ms=latency_ms,
                ))
        
        return wrapper
    return decorator


# Context manager for telemetry
class AICallContext:
    """Context manager for tracking AI calls.
    
    Usage:
        with AICallContext(telemetry, "generate_draft") as ctx:
            ctx.set_inputs(inputs)
            result = await call_ai(...)
            ctx.set_outputs(result)
    """

    def __init__(
        self,
        telemetry: AITelemetryService,
        action: str,
        **metadata,
    ):
        """Initialize context.
        
        Args:
            telemetry: Telemetry service
            action: Action name
            **metadata: Additional metadata
        """
        self.telemetry = telemetry
        self.action = action
        self.metadata = metadata
        self.inputs: dict[str, Any] = {}
        self.outputs: dict[str, Any] = {}
        self.start_time: Optional[float] = None
        self.error: Optional[str] = None

    def __enter__(self):
        import time
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        
        latency_ms = int((time.time() - (self.start_time or time.time())) * 1000)
        
        if exc_val:
            self.error = str(exc_val)
        
        self.telemetry.log_event(AIEventInput(
            action=self.action,
            model=self.metadata.get("model", "gemini-1.5-pro"),
            inputs=self.inputs,
            outputs=self.outputs,
            latency_ms=latency_ms,
            actor_persona=self.metadata.get("actor_persona"),
            actor_user_id=self.metadata.get("actor_user_id"),
            project_id=self.metadata.get("project_id"),
            parcel_id=self.metadata.get("parcel_id"),
            prompt_template_id=self.metadata.get("prompt_template_id"),
        ))

    def set_inputs(self, inputs: dict[str, Any]) -> None:
        """Set inputs for the call."""
        self.inputs = inputs

    def set_outputs(self, outputs: dict[str, Any]) -> None:
        """Set outputs from the call."""
        self.outputs = outputs

    def add_tool_call(self, tool_name: str, args: dict[str, Any], result: Any) -> None:
        """Record a tool call."""
        if "tool_calls" not in self.metadata:
            self.metadata["tool_calls"] = []
        self.metadata["tool_calls"].append({
            "tool": tool_name,
            "args": args,
            "result": result,
        })
