import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import threading
from app.config import settings

# Database paths
DB_FILE = Path(__file__).resolve().parent.parent / "mock_data" / "leads_db.json"

try:
    from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Text
    from sqlalchemy.orm import declarative_base, sessionmaker
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

if SQLALCHEMY_AVAILABLE:
    Base = declarative_base()
    
    class LeadModel(Base):
        __tablename__ = "leads"
        id = Column(String, primary_key=True)
        company_name = Column(String, nullable=False)
        icp_score = Column(Integer, default=0)
        status = Column(String, default="new")
        evidence_chain = Column(Text, default="[]")
        outreach_template = Column(Text, default="")
        shadow_verdict = Column(Text, default="{}")
        contacts = Column(Text, default="[]")
        company_details = Column(Text, default="{}")
        sources = Column(Text, default="[]")
        debate_transcript = Column(Text, default="[]")
        buying_committee = Column(Text, default="[]")
        domain = Column(String, default="hr_saas")
        pipeline_log = Column(Text, default="[]")
        data_quality_flags = Column(Text, default="[]")
        company = Column(Text, default="{}")
        decision_makers = Column(Text, default="[]")
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow)

    class EventModel(Base):
        __tablename__ = "events"
        id = Column(String, primary_key=True)
        source = Column(String)
        event_type = Column(String)
        company = Column(String)
        data = Column(Text)
        timestamp = Column(DateTime, default=datetime.utcnow)

    class NotificationQueueModel(Base):
        __tablename__ = "notification_queue"
        id = Column(String, primary_key=True)
        subject = Column(String, nullable=False)
        html_content = Column(Text, nullable=False)
        timestamp = Column(DateTime, default=datetime.utcnow)

class EventStore:
    """Manages persistence of Event Logs and Lead Summaries."""
    
    def __init__(self):
        self.session_factory = None
        self.engine = None
        self.use_fallback = not SQLALCHEMY_AVAILABLE
        self.lock = threading.Lock()
        
        if not self.use_fallback:
            try:
                # We use SQLite as the default Database engine
                self.engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30.0} if "sqlite" in settings.DATABASE_URL else {})
                Base.metadata.create_all(self.engine)
                
                # Dynamically alter table to add columns if they don't exist
                try:
                    from sqlalchemy import inspect, text
                    inspector = inspect(self.engine)
                    columns = [col["name"] for col in inspector.get_columns("leads")]
                    
                    with self.engine.begin() as conn:
                        if "company_details" not in columns:
                            conn.execute(text("ALTER TABLE leads ADD COLUMN company_details TEXT DEFAULT '{}'"))
                        if "sources" not in columns:
                            conn.execute(text("ALTER TABLE leads ADD COLUMN sources TEXT DEFAULT '[]'"))
                        if "debate_transcript" not in columns:
                            conn.execute(text("ALTER TABLE leads ADD COLUMN debate_transcript TEXT DEFAULT '[]'"))
                        if "buying_committee" not in columns:
                            conn.execute(text("ALTER TABLE leads ADD COLUMN buying_committee TEXT DEFAULT '[]'"))
                        if "domain" not in columns:
                            conn.execute(text("ALTER TABLE leads ADD COLUMN domain TEXT DEFAULT 'hr_saas'"))
                        if "pipeline_log" not in columns:
                            conn.execute(text("ALTER TABLE leads ADD COLUMN pipeline_log TEXT DEFAULT '[]'"))
                        if "data_quality_flags" not in columns:
                            conn.execute(text("ALTER TABLE leads ADD COLUMN data_quality_flags TEXT DEFAULT '[]'"))
                        if "company" not in columns:
                            conn.execute(text("ALTER TABLE leads ADD COLUMN company TEXT DEFAULT '{}'"))
                        if "decision_makers" not in columns:
                            conn.execute(text("ALTER TABLE leads ADD COLUMN decision_makers TEXT DEFAULT '[]'"))
                except Exception as ex:
                    print(f"Error altering database tables: {ex}")
                
                self.session_factory = sessionmaker(bind=self.engine)
            except Exception as e:
                print(f"Database connection error: {e}. Falling back to file storage.")
                self.use_fallback = True

        self.fallback_data = {"leads": {}, "events": [], "notifications": []}
        if self.use_fallback:
            self._load_fallback_db()

    def _load_fallback_db(self):
        if DB_FILE.exists():
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    self.fallback_data = json.load(f)
            except Exception as e:
                print(f"Error reading fallback database: {e}")
                self.fallback_data = {"leads": {}, "events": [], "notifications": []}

    def _save_fallback_db(self):
        DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(self.fallback_data, f, indent=2)
        except Exception as e:
            print(f"Error saving fallback database: {e}")

    # Leads CRUD
    def save_lead(self, lead_data: Dict[str, Any]):
        lead_id = lead_data["id"]
        
        # Normalize outreach_template to be a string
        template = lead_data.get("outreach_template", "")
        if isinstance(template, dict):
            if "Subject" in template and "Body" in template:
                normalized_template = f"Subject: {template['Subject']}\n\n{template['Body']}"
            elif "subject" in template and "body" in template:
                normalized_template = f"Subject: {template['subject']}\n\n{template['body']}"
            else:
                normalized_template = json.dumps(template)
        else:
            normalized_template = str(template)
            
        lead_data["outreach_template"] = normalized_template

        if self.use_fallback:
            with self.lock:
                self.fallback_data["leads"][lead_id] = lead_data
                self._save_fallback_db()
            return
            
        with self.lock:
            with self.session_factory() as session:
                # Check if exists
                lead = session.query(LeadModel).filter(LeadModel.id == lead_id).first()
                if not lead:
                    lead = LeadModel(id=lead_id)
                    session.add(lead)
                    
                lead.company_name = lead_data.get("company_name", "")
                lead.icp_score = lead_data.get("icp_score", 0)
                lead.status = lead_data.get("status", "new")
                lead.evidence_chain = json.dumps(lead_data.get("evidence_chain", []))
                lead.outreach_template = normalized_template
                lead.shadow_verdict = json.dumps(lead_data.get("shadow_verdict", {}))
                lead.contacts = json.dumps(lead_data.get("contacts", []))
                lead.company_details = json.dumps(lead_data.get("company_details", {}))
                lead.sources = json.dumps(lead_data.get("sources", []))
                lead.debate_transcript = json.dumps(lead_data.get("debate_transcript", []))
                lead.buying_committee = json.dumps(lead_data.get("buying_committee", []))
                lead.domain = lead_data.get("domain", "hr_saas")
                lead.pipeline_log = json.dumps(lead_data.get("pipeline_log", []))
                lead.data_quality_flags = json.dumps(lead_data.get("data_quality_flags", []))
                lead.company = json.dumps(lead_data.get("company", {}))
                lead.decision_makers = json.dumps(lead_data.get("decision_makers", []))
                lead.updated_at = datetime.utcnow()
                session.commit()

    def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        if self.use_fallback:
            with self.lock:
                return self.fallback_data["leads"].get(lead_id)
            
        with self.lock:
            with self.session_factory() as session:
                lead = session.query(LeadModel).filter(LeadModel.id == lead_id).first()
                if lead:
                    return self._parse_lead_model(lead)
        return None

    def get_lead_by_company(self, company_name: str) -> Optional[Dict[str, Any]]:
        name_clean = company_name.strip().lower()
        if self.use_fallback:
            with self.lock:
                for lead in self.fallback_data["leads"].values():
                    if lead.get("company_name", "").strip().lower() == name_clean:
                        return lead
                return None
            
        with self.lock:
            with self.session_factory() as session:
                lead = session.query(LeadModel).filter(LeadModel.company_name.ilike(company_name)).first()
                if lead:
                    return self._parse_lead_model(lead)
        return None

    def get_all_leads(self) -> List[Dict[str, Any]]:
        if self.use_fallback:
            with self.lock:
                return list(self.fallback_data["leads"].values())
                
        with self.lock:
            with self.session_factory() as session:
                leads = session.query(LeadModel).order_by(LeadModel.created_at.desc()).all()
                return [self._parse_lead_model(l) for l in leads]
            
    def delete_lead(self, lead_id: str):
        if self.use_fallback:
            with self.lock:
                if lead_id in self.fallback_data["leads"]:
                    del self.fallback_data["leads"][lead_id]
                    self._save_fallback_db()
            return
            
        with self.lock:
            with self.session_factory() as session:
                lead = session.query(LeadModel).filter(LeadModel.id == lead_id).first()
                if lead:
                    session.delete(lead)
                    session.commit()

    def _parse_lead_model(self, lead: Any) -> Dict[str, Any]:
        return {
            "id": lead.id,
            "company_name": lead.company_name,
            "icp_score": lead.icp_score,
            "status": lead.status,
            "evidence_chain": json.loads(lead.evidence_chain),
            "outreach_template": lead.outreach_template,
            "shadow_verdict": json.loads(lead.shadow_verdict),
            "contacts": json.loads(lead.contacts),
            "company_details": json.loads(lead.company_details) if getattr(lead, 'company_details', None) else {},
            "sources": json.loads(lead.sources) if getattr(lead, 'sources', None) else [],
            "debate_transcript": json.loads(lead.debate_transcript) if getattr(lead, 'debate_transcript', None) else [],
            "buying_committee": json.loads(lead.buying_committee) if getattr(lead, 'buying_committee', None) else [],
            "domain": getattr(lead, 'domain', 'hr_saas') or 'hr_saas',
            "pipeline_log": json.loads(lead.pipeline_log) if getattr(lead, 'pipeline_log', None) else [],
            "data_quality_flags": json.loads(lead.data_quality_flags) if getattr(lead, 'data_quality_flags', None) else [],
            "company": json.loads(lead.company) if getattr(lead, 'company', None) else {},
            "decision_makers": json.loads(lead.decision_makers) if getattr(lead, 'decision_makers', None) else [],
            "created_at": lead.created_at.isoformat(),
            "updated_at": lead.updated_at.isoformat()
        }

    # Events CRUD
    def log_event(self, event_data: Dict[str, Any]):
        import uuid
        event_id = event_data.get("id") or f"evt_{uuid.uuid4().hex[:12]}"
        event_data["id"] = event_id
        
        if self.use_fallback:
            with self.lock:
                self.fallback_data["events"].append(event_data)
                self._save_fallback_db()
            return
            
        with self.lock:
            with self.session_factory() as session:
                event = EventModel(
                    id=event_id,
                    source=event_data.get("source"),
                    event_type=event_data.get("event_type"),
                    company=event_data.get("company"),
                    data=json.dumps(event_data.get("data", {})),
                    timestamp=event_data.get("timestamp", datetime.utcnow())
                )
                session.add(event)
                session.commit()

    def get_all_events(self) -> List[Dict[str, Any]]:
        if self.use_fallback:
            with self.lock:
                return self.fallback_data["events"]
            
        with self.lock:
            with self.session_factory() as session:
                events = session.query(EventModel).order_by(EventModel.timestamp.desc()).all()
                return [
                    {
                        "id": e.id,
                        "source": e.source,
                        "event_type": e.event_type,
                        "company": e.company,
                        "data": json.loads(e.data),
                        "timestamp": e.timestamp.isoformat()
                    } for e in events
                ]

    # Notifications Queue CRUD
    def queue_notification(self, subject: str, html_content: str):
        import uuid
        notif_id = f"notif_{uuid.uuid4().hex[:12]}"
        
        if self.use_fallback:
            with self.lock:
                if "notifications" not in self.fallback_data:
                    self.fallback_data["notifications"] = []
                self.fallback_data["notifications"].append({
                    "id": notif_id,
                    "subject": subject,
                    "html_content": html_content,
                    "timestamp": datetime.utcnow().isoformat()
                })
                self._save_fallback_db()
            return
            
        with self.lock:
            with self.session_factory() as session:
                notif = NotificationQueueModel(
                    id=notif_id,
                    subject=subject,
                    html_content=html_content,
                    timestamp=datetime.utcnow()
                )
                session.add(notif)
                session.commit()

    def get_queued_notifications(self) -> List[Dict[str, Any]]:
        if self.use_fallback:
            with self.lock:
                return self.fallback_data.get("notifications", [])
            
        with self.lock:
            with self.session_factory() as session:
                notifs = session.query(NotificationQueueModel).order_by(NotificationQueueModel.timestamp.asc()).all()
                return [
                    {
                        "id": n.id,
                        "subject": n.subject,
                        "html_content": n.html_content,
                        "timestamp": n.timestamp.isoformat() if n.timestamp else datetime.utcnow().isoformat()
                    } for n in notifs
                ]

    def clear_queued_notifications(self):
        if self.use_fallback:
            with self.lock:
                self.fallback_data["notifications"] = []
                self._save_fallback_db()
            return
            
        with self.lock:
            with self.session_factory() as session:
                session.query(NotificationQueueModel).delete()
                session.commit()

# Shared instance
event_store = EventStore()


