import os
import json
import datetime
import uuid
import shutil

class SessionManager:
    """
    Manages production pipeline sessions, checkpoints, resumption, and audit logging.
    Sessions are stored in: data/sessions/<session_id>/
    """
    def __init__(self, base_dir=None):
        if base_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            base_dir = os.path.join(project_root, "data", "sessions")
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def create_session(self, topic: str, profile_id: str = "default_psychology", profile_name: str = "Default Psychology") -> dict:
        """
        Creates a new unique production session directory and session.json metadata.
        """
        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        unique_suffix = str(uuid.uuid4())[:4].upper()
        session_id = f"SESS_{timestamp_str}_{unique_suffix}"
        
        session_dir = os.path.join(self.base_dir, session_id)
        os.makedirs(session_dir, exist_ok=True)
        os.makedirs(os.path.join(session_dir, "audio_assets"), exist_ok=True)
        os.makedirs(os.path.join(session_dir, "video_assets"), exist_ok=True)
        
        session_meta = {
            "session_id": session_id,
            "topic": topic,
            "profile_id": profile_id,
            "profile_name": profile_name,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "status": "CREATED",
            "current_step": "SCRIPT_GENERATION",
            "completed_steps": [],
            "audio_count": 0,
            "video_count": 0,
            "final_video_path": None,
            "package_path": None,
            "error": None
        }
        
        meta_file = os.path.join(session_dir, "session.json")
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(session_meta, f, indent=2)
            
        # Initialize empty audit trail
        audit_file = os.path.join(session_dir, "audit_trail.json")
        with open(audit_file, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
            
        print(f"[+] Created new production session: {session_id} for topic '{topic}'")
        return session_meta

    def list_sessions(self) -> list[dict]:
        """
        Returns all sessions ordered by creation date (newest first).
        """
        sessions = []
        if not os.path.exists(self.base_dir):
            return sessions
            
        for name in os.listdir(self.base_dir):
            sess_dir = os.path.join(self.base_dir, name)
            meta_file = os.path.join(sess_dir, "session.json")
            if os.path.isdir(sess_dir) and os.path.exists(meta_file):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        sessions.append(meta)
                except Exception as e:
                    print(f"[-] Could not read session {name}: {e}")
                    
        sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return sessions

    def get_session(self, session_id: str) -> dict:
        """
        Returns session metadata for session_id.
        """
        sess_dir = os.path.join(self.base_dir, session_id)
        meta_file = os.path.join(sess_dir, "session.json")
        if os.path.exists(meta_file):
            with open(meta_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def update_status(self, session_id: str, status: str, current_step: str = None, error: str = None) -> dict:
        """
        Updates session status and step state.
        """
        sess_dir = os.path.join(self.base_dir, session_id)
        meta_file = os.path.join(sess_dir, "session.json")
        meta = self.get_session(session_id)
        if not meta:
            return None
            
        meta["status"] = status
        meta["updated_at"] = datetime.datetime.now().isoformat()
        if current_step:
            meta["current_step"] = current_step
        if status not in meta["completed_steps"] and status in ["SCRIPT_GENERATED", "ASSETS_GENERATED", "ASSEMBLED", "PACKAGED"]:
            meta["completed_steps"].append(status)
        if error:
            meta["error"] = error
            meta["status"] = "FAILED"
            
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        return meta

    def save_checkpoint(self, session_id: str, checkpoint_name: str, data: dict) -> None:
        """
        Saves step checkpoint data (script_data, audio_assets, video_assets, package_info).
        """
        sess_dir = os.path.join(self.base_dir, session_id)
        if not os.path.exists(sess_dir):
            return
            
        cp_file = os.path.join(sess_dir, f"{checkpoint_name}.json")
        with open(cp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
        print(f"[+] Saved checkpoint '{checkpoint_name}' for session {session_id}")

    def load_checkpoint(self, session_id: str, checkpoint_name: str):
        """
        Loads checkpoint data for session_id.
        """
        sess_dir = os.path.join(self.base_dir, session_id)
        cp_file = os.path.join(sess_dir, f"{checkpoint_name}.json")
        if os.path.exists(cp_file):
            with open(cp_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def log_api_call(self, session_id: str, step: str, service: str, request_data: dict, response_data: dict, status: str = "SUCCESS", duration_sec: float = 0.0) -> dict:
        """
        Appends an API request & response audit entry to the session's audit_trail.json.
        """
        if not session_id:
            return None
            
        sess_dir = os.path.join(self.base_dir, session_id)
        if not os.path.exists(sess_dir):
            os.makedirs(sess_dir, exist_ok=True)
            
        audit_file = os.path.join(sess_dir, "audit_trail.json")
        entries = []
        if os.path.exists(audit_file):
            try:
                with open(audit_file, "r", encoding="utf-8") as f:
                    entries = json.load(f)
            except Exception:
                entries = []
                
        entry = {
            "id": str(uuid.uuid4())[:8],
            "timestamp": datetime.datetime.now().isoformat(),
            "step": step,
            "service": service,
            "request": request_data,
            "response": response_data,
            "status": status,
            "duration_sec": round(duration_sec, 2)
        }
        entries.append(entry)
        
        with open(audit_file, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
            
        print(f"  [audit] Logged {service} [{status}] ({duration_sec:.2f}s) for session {session_id}")
        return entry

    def get_audit_trail(self, session_id: str) -> list[dict]:
        """
        Returns all logged API requests and responses for a session.
        """
        sess_dir = os.path.join(self.base_dir, session_id)
        audit_file = os.path.join(sess_dir, "audit_trail.json")
        if os.path.exists(audit_file):
            try:
                with open(audit_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def get_session_dir(self, session_id: str) -> str:
        """
        Returns directory path for session_id.
        """
        return os.path.join(self.base_dir, session_id)

    def delete_session(self, session_id: str) -> bool:
        """
        Deletes session folder and all associated checkpoints & logs.
        """
        sess_dir = os.path.join(self.base_dir, session_id)
        if os.path.exists(sess_dir):
            try:
                shutil.rmtree(sess_dir)
                print(f"[+] Deleted session: {session_id}")
                return True
            except Exception as e:
                print(f"[-] Could not delete session {session_id}: {e}")
        return False
