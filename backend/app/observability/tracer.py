"""Observability tracer — lightweight span-based tracing for agent execution pipelines."""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class TraceSpan:
    """A single unit of work within a distributed trace."""
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    trace_id: str = ""
    parent_span_id: Optional[str] = None
    operation: str = ""
    agent_name: str = ""
    status: str = "in_progress"  # in_progress, completed, failed, recovered
    start_time: str = ""
    end_time: Optional[str] = None
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    
    def finish(self, status: str = "completed"):
        self.end_time = datetime.now(timezone.utc).isoformat()
        self.status = status
        if self.start_time:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            self.duration_ms = int((end - start).total_seconds() * 1000)
    
    def add_event(self, name: str, data: Dict[str, Any] = None):
        self.events.append({
            "name": name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
        })
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WorkflowTracer:
    """Manages traces across workflow executions.
    
    Each workflow run creates a trace (identified by trace_id).
    Each agent execution within the workflow creates a span.
    Spans can be nested (e.g., LLM call within an agent).
    """
    
    def __init__(self):
        self.traces: Dict[str, List[TraceSpan]] = {}  # trace_id -> spans
        self.active_spans: Dict[str, TraceSpan] = {}  # span_id -> span
    
    def start_trace(self, workflow_id: str = None) -> str:
        """Start a new trace for a workflow execution."""
        trace_id = workflow_id or uuid.uuid4().hex[:16]
        self.traces[trace_id] = []
        return trace_id
    
    def start_span(
        self,
        trace_id: str,
        operation: str,
        agent_name: str = "",
        parent_span_id: str = None,
        metadata: Dict[str, Any] = None,
    ) -> TraceSpan:
        """Start a new span within a trace."""
        span = TraceSpan(
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation=operation,
            agent_name=agent_name,
            start_time=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )
        
        if trace_id in self.traces:
            self.traces[trace_id].append(span)
        else:
            self.traces[trace_id] = [span]
        
        self.active_spans[span.span_id] = span
        return span
    
    def finish_span(self, span_id: str, status: str = "completed"):
        """Finish a span."""
        if span_id in self.active_spans:
            span = self.active_spans[span_id]
            span.finish(status)
            del self.active_spans[span_id]
    
    def get_trace(self, trace_id: str) -> List[Dict[str, Any]]:
        """Get all spans for a trace."""
        if trace_id not in self.traces:
            return []
        return [span.to_dict() for span in self.traces[trace_id]]
    
    def get_all_traces(self) -> Dict[str, Any]:
        """Get summary of all traces."""
        summaries = []
        for trace_id, spans in self.traces.items():
            total_duration = sum(s.duration_ms for s in spans)
            failed_count = sum(1 for s in spans if s.status == "failed")
            
            # Extract company name from spans metadata
            company_name = "Event pipeline run"
            for s in spans:
                if s.metadata and s.metadata.get("company_name"):
                    company_name = s.metadata.get("company_name")
                    break
                    
            summaries.append({
                "trace_id": trace_id,
                "span_count": len(spans),
                "total_duration_ms": total_duration,
                "failed_spans": failed_count,
                "status": "failed" if failed_count > 0 else "completed",
                "metadata": {"company_name": company_name}
            })
        return {"traces": summaries}
    
    def get_waterfall(self, trace_id: str) -> List[Dict[str, Any]]:
        """Get spans formatted for waterfall visualization."""
        if trace_id not in self.traces:
            return []
        
        spans = sorted(self.traces[trace_id], key=lambda s: str(s.start_time))
        if not spans:
            return []
        
        trace_start = spans[0].start_time
        waterfall = []
        for span in spans:
            if isinstance(span.start_time, datetime):
                start_dt = span.start_time
            else:
                try:
                    start_dt = datetime.fromisoformat(str(span.start_time).replace('Z', '+00:00'))
                except Exception:
                    start_dt = datetime.now(timezone.utc)
                    
            start_epoch = start_dt.timestamp()
            
            if span.end_time:
                if isinstance(span.end_time, datetime):
                    end_dt = span.end_time
                else:
                    try:
                        end_dt = datetime.fromisoformat(str(span.end_time).replace('Z', '+00:00'))
                    except Exception:
                        end_dt = start_dt
                end_epoch = end_dt.timestamp()
            else:
                end_epoch = start_epoch
                
            waterfall.append({
                "id": span.span_id,
                "name": span.operation or span.agent_name,
                "start_time": start_epoch,
                "end_time": end_epoch,
                "duration_ms": span.duration_ms,
                "offset_ms": self._time_diff_ms(trace_start, span.start_time),
                "metadata": {**span.metadata, "state": span.status}
            })
        return waterfall
    
    @staticmethod
    def _time_diff_ms(start_iso: Any, end_iso: Any) -> int:
        try:
            start = start_iso if isinstance(start_iso, datetime) else datetime.fromisoformat(str(start_iso).replace('Z', '+00:00'))
            end = end_iso if isinstance(end_iso, datetime) else datetime.fromisoformat(str(end_iso).replace('Z', '+00:00'))
            return int((end - start).total_seconds() * 1000)
        except Exception:
            return 0


# Shared singleton
workflow_tracer = WorkflowTracer()
