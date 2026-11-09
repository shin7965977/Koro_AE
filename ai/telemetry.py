"""
Langfuse Telemetry & AI Observability Module for KoRo Lakehouse.
Instruments Socratic Copilot, Requirement Memo Generation, and Dynamic dbt SQL Synthesis.
Complies with Langfuse Best Practices and Zero-Facade Lakehouse Governance.
"""

from __future__ import annotations

import os
from typing import Any, Optional
from dotenv import load_dotenv

# Load .env before accessing credentials
load_dotenv()


class LakehouseTelemetry:
    """Manages Langfuse tracing and observability for Socratic Copilot workflows."""

    _instance: Optional[LakehouseTelemetry] = None

    def __init__(self) -> None:
        self.public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
        self.secret_key = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
        self.host = (
            os.getenv("LANGFUSE_BASE_URL")
            or os.getenv("LANGFUSE_HOST")
            or "https://cloud.langfuse.com"
        ).strip()
        self.client: Any = None
        self.is_active = False

        if self.public_key and self.secret_key:
            try:
                from langfuse import Langfuse

                self.client = Langfuse(
                    public_key=self.public_key,
                    secret_key=self.secret_key,
                    host=self.host,
                )
                self.is_active = True
                print(f"🔭 [Langfuse Telemetry] Connected to Langfuse host: {self.host}")
            except Exception as e:
                print(f"⚠️ [Langfuse Telemetry] Failed to initialize client: {e}")
                self.is_active = False
        else:
            print("ℹ️ [Langfuse Telemetry] Keys not detected. Running in passive local observability mode.")

    @classmethod
    def get_instance(cls) -> LakehouseTelemetry:
        if cls._instance is None:
            cls._instance = LakehouseTelemetry()
        return cls._instance

    def create_trace(
        self,
        name: str,
        user_id: Optional[str] = "lakehouse_analyst",
        session_id: Optional[str] = "default_session",
        metadata: Optional[dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
        input_data: Optional[Any] = None,
    ) -> Any:
        """Create a top-level execution trace observation following Langfuse best practices."""
        if not self.is_active or not self.client:
            return None
        try:
            meta = dict(metadata or {})
            if user_id:
                meta["user_id"] = user_id
            if session_id:
                meta["session_id"] = session_id
            if tags:
                meta["tags"] = tags
            return self.client.start_observation(
                name=name,
                as_type="agent",
                input=input_data,
                metadata=meta,
            )
        except Exception as e:
            print(f"⚠️ [Langfuse Telemetry] Failed to create trace: {e}")
            return None

    def log_span(
        self,
        trace: Any,
        name: str,
        input_data: Optional[Any] = None,
        output_data: Optional[Any] = None,
        metadata: Optional[dict[str, Any]] = None,
        level: str = "DEFAULT",
        status_message: Optional[str] = None,
    ) -> Any:
        """Log a child span within an existing trace."""
        if not trace:
            return None
        try:
            return trace.span(
                name=name,
                input=input_data,
                output=output_data,
                metadata=metadata or {},
                level=level,
                status_message=status_message,
            )
        except Exception as e:
            print(f"⚠️ [Langfuse Telemetry] Failed to log span: {e}")
            return None

    def log_generation(
        self,
        trace: Any,
        name: str,
        model: str,
        input_prompt: Any,
        output_completion: Any,
        usage: Optional[dict[str, int]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Log an LLM generation observation with model and token metrics."""
        if not trace:
            return None
        try:
            return trace.generation(
                name=name,
                model=model,
                input=input_prompt,
                output=output_completion,
                usage=usage or {},
                metadata=metadata or {},
            )
        except Exception as e:
            print(f"⚠️ [Langfuse Telemetry] Failed to log generation: {e}")
            return None

    def evaluate_grounding(
        self,
        trace: Any,
        name: str = "semantic_grounding",
        expected_filters: Optional[list[str]] = None,
        generated_sql: Optional[str] = None,
        observation: Optional[Any] = None,
    ) -> float:
        """Evaluate whether generated SQL adheres to expected filters (Grounding Score: 0.0 or 1.0)."""
        if not expected_filters or not generated_sql:
            score = 1.0
            missing: list[str] = []
        else:
            sql_upper = generated_sql.upper()
            missing = [f for f in expected_filters if f.upper() not in sql_upper]
            score = 0.0 if missing else 1.0

        if trace and self.is_active and self.client:
            try:
                trace_id = getattr(trace, "id", None) or getattr(trace, "trace_id", None)
                obs_id = getattr(observation, "id", None) if observation else None
                if trace_id:
                    score_args = {
                        "name": name,
                        "value": score,
                        "trace_id": trace_id,
                        "comment": "All business filters grounded" if score == 1.0 else f"Dropped filters: {missing}",
                    }
                    if obs_id:
                        score_args["observation_id"] = obs_id
                    self.client.create_score(**score_args)
            except Exception as e:
                print(f"⚠️ [Langfuse Telemetry] Failed to log score: {e}")

        return score

    def flush(self) -> None:
        """Flush telemetry buffer to server."""
        if self.is_active and self.client:
            try:
                self.client.flush()
            except Exception as e:
                print(f"⚠️ [Langfuse Telemetry] Flush error: {e}")


# Global singleton helper
telemetry = LakehouseTelemetry.get_instance()
