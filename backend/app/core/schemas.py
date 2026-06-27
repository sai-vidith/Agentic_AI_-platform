from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum


def utc_now() -> datetime:
    """Timezone-aware UTC now (replaces deprecated datetime.utcnow())."""
    return datetime.now(timezone.utc)

class LeadStatus(str, Enum):
    NEW = "new"
    QUALIFIED = "qualified"
    DISQUALIFIED = "disqualified"
    APPROVAL_REQUIRED = "approval_required"
    APPROVED = "approved"
    REJECTED = "rejected"

class Contact(BaseModel):
    name: str
    title: str
    email: str
    phone: str
    linkedin: str
    joined_date: Optional[str] = None
    pii_fields_redacted: List[str] = Field(default_factory=list)
    raw_email: Optional[str] = None  # Store encrypted email here
    raw_phone: Optional[str] = None  # Store encrypted phone here

class CompanyDetails(BaseModel):
    name: str
    industry: str
    employees: int
    founded: int
    hq: str
    tech_stack: List[str] = Field(default_factory=list)
    current_hr_tool: Optional[str] = None
    recent_funding: Optional[Dict[str, Any]] = None
    growth_rate: Optional[str] = None

class TriggerEvent(BaseModel):
    id: Optional[str] = None
    source: str
    event_type: str
    company: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)

class ShadowVerdict(BaseModel):
    status: str  # "CONFIRMED" or "DIVERGENCE_WARNING"
    reason: str
    confidence: int  # 0 to 100
    force_human_review: bool = False

class ProspectSummary(BaseModel):
    id: Optional[str] = None
    company_name: str
    company_details: Optional[CompanyDetails] = None
    contacts: List[Contact] = Field(default_factory=list)
    icp_score: int = 0
    evidence_chain: List[str] = Field(default_factory=list)
    shadow_verdict: Optional[ShadowVerdict] = None
    outreach_template: Optional[str] = None
    status: LeadStatus = LeadStatus.NEW
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

class AgentState(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    RECOVERED = "recovered"

class WSEventTypes(str, Enum):
    WORKFLOW_STARTED = "workflow_started"
    AGENT_THINKING = "agent_thinking"
    AGENT_REASONING = "agent_reasoning"
    AGENT_TOOL_CALL = "agent_tool_call"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    AGENT_RETRYING = "agent_retrying"
    AGENT_RECOVERED = "agent_recovered"
    SHADOW_DIVERGENCE = "shadow_divergence"
    DAG_HANDOFF = "dag_handoff"
    APPROVAL_REQUIRED = "approval_required"
    WORKFLOW_COMPLETED = "workflow_completed"

class WSEvent(BaseModel):
    type: WSEventTypes
    agent: str
    target: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trace_id: Optional[str] = None

class AgentTask(BaseModel):
    id: str
    name: str
    dependencies: List[str] = Field(default_factory=list)
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[Dict[str, Any]] = None
    status: AgentState = AgentState.IDLE
    error_message: Optional[str] = None

class DAG(BaseModel):
    tasks: Dict[str, AgentTask]
    edges: List[List[str]]  # [["parent", "child"]]
    plan_reasoning: str = "Default sequential pipeline"

class WorkflowRun(BaseModel):
    id: str
    domain: str
    goal: str
    dag: DAG
    status: str  # "running", "completed", "failed", "pending"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
