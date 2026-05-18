"""AI Telemetry Service.

Provides comprehensive telemetry for AI operations:
- Full input/output logging persisted to the ``ai_events`` table
- Reproducible run capability (hashes, prompt version, retrieval set)
- Cost tracking per model/action
- PII redaction before persistence
- Audit trail generation

Every AI action should flow through this service so that auditability, cost
controls, and replay work across process restarts.  The service falls back to
an in-memory store when no SQLAlchemy session is provided (e.g. tests or
decorators invoked outside request scope), but production code paths are
expected to inject ``db`` from ``app.api.deps.get_db``.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable, Optional

from sqlalchemy.orm import Session

from app.services.hashing import sha256_hex

logger = logging.getLogger(__name__)


# Cost estimates per 1K tokens (as of 2026).  The ``-001`` / version suffixes
# resolve to the base model name for costing so callers can pass the exact
# Vertex model identifier without losing lookups.
MODEL_COSTS: dict[str, dict[str, Decimal]] = {
    "gemini-1.5-pro": {"input": Decimal("0.00125"), "output": Decimal("0.005")},
    "gemini-1.5-flash": {"input": Decimal("0.000075"), "output": Decimal("0.0003")},
    "gemini-2.0-pro": {"input": Decimal("0.0015"), "output": Decimal("0.006")},
    "gemini-2.0-flash": {"input": Decimal("0.000075"), "output": Decimal("0.0003")},
}


# Field names that almost always contain PII or privileged content.  These are
# recursively redacted before the payload hits ``inputs_json`` / ``outputs_json``
# on ``ai_events``.  Callers that need richer control pass ``redact=False``.
REDACT_FIELDS: frozenset[str] = frozenset(
    {
        "ssn",
        "social_security",
        "social_security_number",
        "tax_id",
        "ein",
        "dob",
        "date_of_birth",
        "driver_license",
        "drivers_license",
        "passport",
        "password",
        "api_key",
        "authorization",
        "credit_card",
        "card_number",
        "bank_account",
        "routing_number",
    }
)

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")


def _redact_scalar(value: str) -> str:
    value = _SSN_RE.sub("[REDACTED-SSN]", value)
    value = _EMAIL_RE.sub("[REDACTED-EMAIL]", value)
    value = _PHONE_RE.sub("[REDACTED-PHONE]", value)
    return value


def redact(payload: Any) -> Any:
    """Return a deep-copied payload with PII redacted.

    - Keys in :data:`REDACT_FIELDS` are replaced with ``"[REDACTED]"``.
    - String leaves are scanned for SSN / email / phone patterns.
    - ``bytes`` are converted to ``"<bytes len=...>"``.
    """

    if isinstance(payload, dict):
        return {
            k: ("[REDACTED]" if k.lower() in REDACT_FIELDS else redact(v))
            for k, v in payload.items()
        }
    if isinstance(payload, list):
        return [redact(v) for v in payload]
    if isinstance(payload, tuple):
        return tuple(redact(v) for v in payload)
    if isinstance(payload, str):
        return _redact_scalar(payload)
    if isinstance(payload, bytes):
        return f"<bytes len={len(payload)}>"
    return payload


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
    model_version: Optional[str] = None
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

    # Outcome
    confidence: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None

    # Link back to an orchestration decision, if any
    ai_decision_id: Optional[str] = None


@dataclass
class AIEvent:
    """A logged AI event."""

    id: str
    action: str
    model: str

    prompt_hash: str
    inputs_hash: str
    outputs_hash: str

    inputs_json: dict[str, Any]
    outputs_json: dict[str, Any]

    actor_persona: Optional[str] = None
    actor_user_id: Optional[str] = None
    project_id: Optional[str] = None
    parcel_id: Optional[str] = None

    prompt_template_id: Optional[str] = None
    prompt_version: Optional[str] = None
    model_version: Optional[str] = None
    temperature: Optional[float] = None

    latency_ms: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_estimate_usd: Optional[Decimal] = None

    retrieval_set_ids: list[str] = field(default_factory=list)
    retrieval_query: Optional[str] = None

    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    citation_ids: list[str] = field(default_factory=list)

    confidence: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None

    ai_decision_id: Optional[str] = None

    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
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
            "temperature": (
                float(self.temperature) if self.temperature is not None else None
            ),
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost_estimate_usd": (
                str(self.cost_estimate_usd) if self.cost_estimate_usd else None
            ),
            "retrieval_set_ids": self.retrieval_set_ids,
            "retrieval_query": self.retrieval_query,
            "tool_calls": self.tool_calls,
            "citation_ids": self.citation_ids,
            "confidence": float(self.confidence) if self.confidence is not None else None,
            "success": self.success,
            "error_message": self.error_message,
            "ai_decision_id": self.ai_decision_id,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class PromptTemplate:
    """A versioned prompt template (in-memory projection)."""

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


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)


def _base_model_for_cost(model: str) -> Optional[str]:
    """Map a possibly-versioned model id to a base costing key."""

    if model in MODEL_COSTS:
        return model
    for base in MODEL_COSTS:
        if model.startswith(base):
            return base
    return None


def estimate_cost(
    model: str, input_tokens: int, output_tokens: int
) -> Optional[Decimal]:
    base = _base_model_for_cost(model)
    if not base:
        return None
    costs = MODEL_COSTS[base]
    return (Decimal(input_tokens) / 1000) * costs["input"] + (
        Decimal(output_tokens) / 1000
    ) * costs["output"]


def extract_usage_from_vertex(response: Any) -> dict[str, Optional[int]]:
    """Best-effort extraction of Vertex Gemini ``usage_metadata``.

    Different vertexai SDK versions expose usage in slightly different shapes;
    we try several before giving up.  Returns a dict with optional
    ``input_tokens`` / ``output_tokens`` / ``total_tokens``.
    """

    usage = getattr(response, "usage_metadata", None) or getattr(
        response, "usage", None
    )
    if usage is None:
        return {"input_tokens": None, "output_tokens": None, "total_tokens": None}

    def _read(attr_candidates: Iterable[str]) -> Optional[int]:
        for name in attr_candidates:
            val = getattr(usage, name, None)
            if val is None and isinstance(usage, dict):
                val = usage.get(name)
            if val is not None:
                try:
                    return int(val)
                except (TypeError, ValueError):
                    return None
        return None

    return {
        "input_tokens": _read(("prompt_token_count", "input_tokens", "prompt_tokens")),
        "output_tokens": _read(
            ("candidates_token_count", "output_tokens", "completion_tokens")
        ),
        "total_tokens": _read(("total_token_count", "total_tokens")),
    }


class AITelemetryService:
    """Persistent-first telemetry service.

    Pass ``db`` to persist events on ``ai_events``.  Without a session, the
    service falls back to a process-local dict so unit tests still work, but
    those events are lost across processes.
    """

    # Class-level in-memory store so log_ai_call decorator (which has no DI)
    # doesn't produce disjoint caches for each instantiation.
    _shared_mem_events: dict[str, AIEvent] = {}
    _shared_mem_templates: dict[str, PromptTemplate] = {}

    def __init__(self, db: Optional[Session] = None, redact_payloads: bool = True):
        self.db = db
        self.redact_payloads = redact_payloads
        self._events = AITelemetryService._shared_mem_events
        self._templates = AITelemetryService._shared_mem_templates

    # ------------------------------------------------------------------
    # Event logging
    # ------------------------------------------------------------------

    def log_event(self, payload: AIEventInput) -> AIEvent:
        event_id = f"aievt_{uuid.uuid4().hex[:12]}"

        inputs = redact(payload.inputs) if self.redact_payloads else payload.inputs
        outputs = redact(payload.outputs) if self.redact_payloads else payload.outputs

        inputs_hash = sha256_hex(_canonical_json(inputs).encode())
        outputs_hash = sha256_hex(_canonical_json(outputs).encode())
        prompt_content = inputs.get("prompt") or inputs.get("messages") or ""
        prompt_hash = sha256_hex(_canonical_json(prompt_content).encode())

        input_tokens = payload.input_tokens or 0
        output_tokens = payload.output_tokens or 0
        total_tokens = (
            (input_tokens + output_tokens)
            if payload.input_tokens is not None or payload.output_tokens is not None
            else None
        )

        cost_estimate = estimate_cost(payload.model, input_tokens, output_tokens)

        event = AIEvent(
            id=event_id,
            action=payload.action,
            model=payload.model,
            prompt_hash=prompt_hash,
            inputs_hash=inputs_hash,
            outputs_hash=outputs_hash,
            inputs_json=inputs,
            outputs_json=outputs,
            actor_persona=payload.actor_persona,
            actor_user_id=payload.actor_user_id,
            project_id=payload.project_id,
            parcel_id=payload.parcel_id,
            prompt_template_id=payload.prompt_template_id,
            prompt_version=payload.prompt_version,
            model_version=payload.model_version,
            temperature=payload.temperature,
            latency_ms=payload.latency_ms,
            input_tokens=payload.input_tokens,
            output_tokens=payload.output_tokens,
            total_tokens=total_tokens,
            cost_estimate_usd=cost_estimate,
            retrieval_set_ids=payload.retrieval_set_ids or [],
            retrieval_query=payload.retrieval_query,
            tool_calls=payload.tool_calls or [],
            citation_ids=payload.citation_ids or [],
            confidence=payload.confidence,
            success=payload.success,
            error_message=payload.error_message,
            ai_decision_id=payload.ai_decision_id,
        )

        if self.db is not None:
            try:
                self._persist(event)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("ai_telemetry: persist failed: %s", exc)
                self._events[event_id] = event
        else:
            self._events[event_id] = event

        return event

    def _persist(self, event: AIEvent) -> None:
        assert self.db is not None
        from app.db import models

        row = models.AIEvent(
            id=event.id,
            actor_persona=(
                models.Persona(event.actor_persona) if event.actor_persona else None
            ),
            actor_user_id=event.actor_user_id,
            action=event.action,
            prompt_template_id=event.prompt_template_id,
            prompt_version=event.prompt_version,
            prompt_hash=event.prompt_hash,
            model=event.model,
            model_version=event.model_version,
            temperature=event.temperature,
            inputs_hash=event.inputs_hash,
            outputs_hash=event.outputs_hash,
            inputs_json=event.inputs_json,
            outputs_json=event.outputs_json,
            tool_calls=event.tool_calls,
            retrieval_set_ids=event.retrieval_set_ids,
            retrieval_query=event.retrieval_query,
            latency_ms=event.latency_ms,
            input_tokens=event.input_tokens,
            output_tokens=event.output_tokens,
            total_tokens=event.total_tokens,
            cost_estimate_usd=event.cost_estimate_usd,
            confidence=event.confidence,
            success=event.success,
            error_message=event.error_message,
            citation_ids=event.citation_ids,
            project_id=event.project_id,
            parcel_id=event.parcel_id,
            ai_decision_id=event.ai_decision_id,
            created_at=event.created_at,
        )
        self.db.add(row)
        self.db.commit()

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def _row_to_event(self, row: Any) -> AIEvent:
        return AIEvent(
            id=row.id,
            action=row.action,
            model=row.model,
            prompt_hash=row.prompt_hash,
            inputs_hash=row.inputs_hash,
            outputs_hash=row.outputs_hash,
            inputs_json=row.inputs_json or {},
            outputs_json=row.outputs_json or {},
            actor_persona=row.actor_persona.value if row.actor_persona else None,
            actor_user_id=row.actor_user_id,
            project_id=row.project_id,
            parcel_id=row.parcel_id,
            prompt_template_id=row.prompt_template_id,
            prompt_version=row.prompt_version,
            model_version=row.model_version,
            temperature=float(row.temperature) if row.temperature is not None else None,
            latency_ms=row.latency_ms,
            input_tokens=row.input_tokens,
            output_tokens=row.output_tokens,
            total_tokens=row.total_tokens,
            cost_estimate_usd=row.cost_estimate_usd,
            retrieval_set_ids=row.retrieval_set_ids or [],
            retrieval_query=row.retrieval_query,
            tool_calls=row.tool_calls or [],
            citation_ids=row.citation_ids or [],
            confidence=(float(row.confidence) if row.confidence is not None else None),
            success=bool(row.success),
            error_message=row.error_message,
            ai_decision_id=row.ai_decision_id,
            created_at=row.created_at or datetime.utcnow(),
        )

    def get_event(self, event_id: str) -> Optional[AIEvent]:
        if self.db is not None:
            from app.db import models

            row = self.db.get(models.AIEvent, event_id)
            return self._row_to_event(row) if row else None
        return self._events.get(event_id)

    def list_events(
        self,
        project_id: Optional[str] = None,
        parcel_id: Optional[str] = None,
        action: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[AIEvent]:
        if self.db is not None:
            from app.db import models

            q = self.db.query(models.AIEvent)
            if project_id:
                q = q.filter(models.AIEvent.project_id == project_id)
            if parcel_id:
                q = q.filter(models.AIEvent.parcel_id == parcel_id)
            if action:
                q = q.filter(models.AIEvent.action == action)
            if since:
                q = q.filter(models.AIEvent.created_at >= since)
            rows = q.order_by(models.AIEvent.created_at.desc()).limit(limit).all()
            return [self._row_to_event(r) for r in rows]

        events = list(self._events.values())
        if project_id:
            events = [e for e in events if e.project_id == project_id]
        if parcel_id:
            events = [e for e in events if e.parcel_id == parcel_id]
        if action:
            events = [e for e in events if e.action == action]
        if since:
            events = [e for e in events if e.created_at >= since]
        events.sort(key=lambda e: e.created_at, reverse=True)
        return events[:limit]

    def get_event_trace(self, event_id: str) -> dict[str, Any]:
        event = self.get_event(event_id)
        if not event:
            return {"error": "Event not found"}

        return {
            "event": event.to_dict(),
            "inputs": event.inputs_json,
            "outputs": event.outputs_json,
            "verification": {
                "inputs_hash_valid": sha256_hex(
                    _canonical_json(event.inputs_json).encode()
                )
                == event.inputs_hash,
                "outputs_hash_valid": sha256_hex(
                    _canonical_json(event.outputs_json).encode()
                )
                == event.outputs_hash,
            },
        }

    def get_replay_config(self, event_id: str) -> dict[str, Any]:
        event = self.get_event(event_id)
        if not event:
            return {"error": "Event not found"}

        return {
            "event_id": event_id,
            "original_timestamp": event.created_at.isoformat(),
            "model": event.model,
            "temperature": (
                float(event.temperature) if event.temperature is not None else None
            ),
            "prompt_template_id": event.prompt_template_id,
            "prompt_version": event.prompt_version,
            "inputs": event.inputs_json,
            "retrieval_set_ids": event.retrieval_set_ids,
            "retrieval_query": event.retrieval_query,
            "expected_outputs_hash": event.outputs_hash,
        }

    # ------------------------------------------------------------------
    # Prompt templates
    # ------------------------------------------------------------------

    def register_template(self, template: PromptTemplate) -> None:
        key = f"{template.id}:{template.version}"
        self._templates[key] = template

    def get_template(
        self, template_id: str, version: Optional[str] = None
    ) -> Optional[PromptTemplate]:
        if version:
            return self._templates.get(f"{template_id}:{version}")
        matching = [
            t for k, t in self._templates.items() if k.startswith(f"{template_id}:")
        ]
        if not matching:
            return None
        matching.sort(key=lambda t: t.version, reverse=True)
        return matching[0]

    # ------------------------------------------------------------------
    # Cost reporting
    # ------------------------------------------------------------------

    def get_cost_summary(
        self,
        project_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> dict[str, Any]:
        events = self.list_events(project_id=project_id, since=since, limit=10_000)
        total_cost = Decimal("0")
        total_input_tokens = 0
        total_output_tokens = 0
        by_model: dict[str, Decimal] = {}
        by_action: dict[str, Decimal] = {}

        for event in events:
            if event.cost_estimate_usd:
                total_cost += event.cost_estimate_usd
                by_model[event.model] = (
                    by_model.get(event.model, Decimal("0")) + event.cost_estimate_usd
                )
                by_action[event.action] = (
                    by_action.get(event.action, Decimal("0")) + event.cost_estimate_usd
                )
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


# ----------------------------------------------------------------------
# Decorator helpers
# ----------------------------------------------------------------------


def log_ai_call(action: str, template_id: Optional[str] = None):
    """Decorator to automatically log AI calls via the shared in-memory store.

    For request-scoped persistence, prefer constructing ``AITelemetryService``
    with a DB session inside the route handler instead of relying on this
    decorator.
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            import time

            telemetry = AITelemetryService()
            start_time = time.time()
            outputs: dict[str, Any] = {}
            error: Optional[str] = None

            try:
                outputs = await func(*args, **kwargs)
                return outputs
            except Exception as exc:
                error = str(exc)
                raise
            finally:
                latency_ms = int((time.time() - start_time) * 1000)
                inputs = kwargs.get("inputs", kwargs.get("payload", {}))
                if args:
                    inputs = args[0] if isinstance(args[0], dict) else inputs

                telemetry.log_event(
                    AIEventInput(
                        action=action,
                        model=kwargs.get("model", "gemini-1.5-pro"),
                        inputs=inputs if isinstance(inputs, dict) else {"args": repr(inputs)},
                        outputs=outputs if isinstance(outputs, dict) else {"value": outputs},
                        prompt_template_id=template_id,
                        latency_ms=latency_ms,
                        success=error is None,
                        error_message=error,
                    )
                )

        return wrapper

    return decorator


class AICallContext:
    """Context manager for tracking AI calls.

    Usage::

        with AICallContext(telemetry, action="generate_draft", project_id=pid) as ctx:
            ctx.set_inputs({"prompt": prompt, "variables": vars})
            result = await call_ai(...)
            ctx.set_outputs(result)
    """

    def __init__(
        self,
        telemetry: AITelemetryService,
        action: str,
        **metadata: Any,
    ):
        self.telemetry = telemetry
        self.action = action
        self.metadata = metadata
        self.inputs: dict[str, Any] = {}
        self.outputs: dict[str, Any] = {}
        self.start_time: Optional[float] = None
        self.error: Optional[str] = None
        self.tool_calls: list[dict[str, Any]] = []

    def __enter__(self) -> "AICallContext":
        import time

        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        import time

        latency_ms = int((time.time() - (self.start_time or time.time())) * 1000)
        if exc_val:
            self.error = str(exc_val)

        self.telemetry.log_event(
            AIEventInput(
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
                prompt_version=self.metadata.get("prompt_version"),
                model_version=self.metadata.get("model_version"),
                temperature=self.metadata.get("temperature"),
                input_tokens=self.metadata.get("input_tokens"),
                output_tokens=self.metadata.get("output_tokens"),
                retrieval_set_ids=self.metadata.get("retrieval_set_ids"),
                retrieval_query=self.metadata.get("retrieval_query"),
                tool_calls=self.tool_calls or None,
                citation_ids=self.metadata.get("citation_ids"),
                confidence=self.metadata.get("confidence"),
                success=self.error is None,
                error_message=self.error,
                ai_decision_id=self.metadata.get("ai_decision_id"),
            )
        )

    def set_inputs(self, inputs: dict[str, Any]) -> None:
        self.inputs = inputs

    def set_outputs(self, outputs: dict[str, Any]) -> None:
        self.outputs = outputs

    def set_usage(self, input_tokens: Optional[int], output_tokens: Optional[int]) -> None:
        self.metadata["input_tokens"] = input_tokens
        self.metadata["output_tokens"] = output_tokens

    def add_tool_call(
        self, tool_name: str, args: dict[str, Any], result: Any
    ) -> None:
        self.tool_calls.append({"tool": tool_name, "args": args, "result": result})
