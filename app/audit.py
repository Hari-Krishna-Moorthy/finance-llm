from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import get_history
from .models import AuditLog, Account, Category, Transaction, AppSetting
import json
from decimal import Decimal
from datetime import date, datetime

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)

def _get_changes(obj):
    changes = {}
    for attr in obj.__mapper__.attrs:
        if attr.key.startswith("_"):
            continue
        
        history = get_history(obj, attr.key)
        
        if history.has_changes():
            old_value = history.deleted[0] if history.deleted else None
            new_value = history.added[0] if history.added else None
            
            # Simple conversion to avoid json serialization errors
            changes[attr.key] = {"old": old_value, "new": new_value}
            
    return changes

def _create_audit_log(session, obj, action):
    table_name = obj.__tablename__
    record_id = getattr(obj, "id", None)
    
    if not record_id:
        return
        
    changes = _get_changes(obj) if action == "UPDATE" else None
    
    if action == "UPDATE" and not changes:
        return # No actual fields changed

    # If it's a delete, maybe store the whole object as old?
    if action == "DELETE":
        changes = {attr.key: {"old": getattr(obj, attr.key), "new": None} for attr in obj.__mapper__.attrs if not attr.key.startswith("_")}
        
    if action == "INSERT":
        changes = {attr.key: {"old": None, "new": getattr(obj, attr.key)} for attr in obj.__mapper__.attrs if not attr.key.startswith("_")}

    # Serialize to JSON safely
    try:
        changes_json = json.loads(json.dumps(changes, cls=CustomEncoder))
    except Exception:
        changes_json = {"error": "Could not serialize changes"}

    audit = AuditLog(
        table_name=table_name,
        record_id=record_id,
        action=action,
        changes=changes_json
    )
    session.add(audit)


# We use before_flush so the new AuditLog objects get included in the same transaction
@event.listens_for(Session, 'before_flush')
def receive_before_flush(session, flush_context, instances):
    AUDITED_MODELS = (Account, Category, Transaction, AppSetting)
    
    for obj in session.new:
        if isinstance(obj, AUDITED_MODELS):
            _create_audit_log(session, obj, "INSERT")
            
    for obj in session.dirty:
        if isinstance(obj, AUDITED_MODELS):
            if session.is_modified(obj):
                _create_audit_log(session, obj, "UPDATE")
                
    for obj in session.deleted:
        if isinstance(obj, AUDITED_MODELS):
            _create_audit_log(session, obj, "DELETE")

