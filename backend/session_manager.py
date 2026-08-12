import os
import json
import datetime
import uuid
import shutil
from backend.database import PipelineDB


class SessionManager:
    """
    Manages production pipeline sessions with SQLite database as primary store
    and file-based session directories for binary assets + offline access.
    Sessions stored in: data/sessions/<session_id>/
    Database at: data/pipeline.db
    """
    def __init__(self, base_dir=None):
        if base_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            base_dir = os.path.join(project_root, "data", "sessions")
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.db = PipelineDB()
        self._run_migration()

    def _run_migration(self):
        marker = os.path.join(os.path.dirname(self.base_dir), ".db_migrated")
        if not os.path.exists(marker):
            count = self.db.migrate_json_sessions(self.base_dir)
            if count > 0:
                print(f"[+] Migrated {count} existing JSON sessions into database")
            with open(marker, "w") as f:
                f.write(datetime.datetime.now().isoformat())

    def create_session(self, topic: str, profile_id: str = "default_psychology", profile_name: str = "Default Psychology") -> dict:
        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        unique_suffix = str(uuid.uuid4())[:4].upper()
        session_id = f"SESS_{timestamp_str}_{unique_suffix}"

        session_dir = os.path.join(self.base_dir, session_id)
        os.makedirs(session_dir, exist_ok=True)
        os.makedirs(os.path.join(session_dir, "audio_assets"), exist_ok=True)
        os.makedirs(os.path.join(session_dir, "video_assets"), exist_ok=True)

        created_at = now.isoformat()
        self.db.create_session(session_id, topic, profile_id, profile_name, created_at)

        session_meta = {
            "session_id": session_id,
            "topic": topic,
            "profile_id": profile_id,
            "profile_name": profile_name,
            "created_at": created_at,
            "updated_at": created_at,
            "status": "CREATED",
            "current_step": "SCRIPT_GENERATION",
            "completed_steps": [],
            "audio_count": 0,
            "video_count": 0,
            "final_video_path": None,
            "package_path": None,
            "error": None
        }

        self._write_session_json(session_dir, session_meta)
        self._write_audit_json(session_dir, [])

        print(f"[+] Created new production session: {session_id} for topic '{topic}'")
        return session_meta

    def list_sessions(self) -> list:
        return self.db.list_sessions()

    def get_session(self, session_id: str) -> dict:
        return self.db.get_session(session_id)

    def update_status(self, session_id: str, status: str, current_step: str = None, error: str = None) -> dict:
        meta = self.db.get_session(session_id)
        if not meta:
            return None

        updates = {"status": status}
        if current_step:
            updates["current_step"] = current_step
        completed = meta.get("completed_steps", [])
        if status in ["SCRIPT_GENERATED", "ASSETS_GENERATED", "ASSEMBLED", "PACKAGED"] and status not in completed:
            completed.append(status)
            updates["completed_steps"] = completed
        if error:
            updates["error"] = error
            updates["status"] = "FAILED"

        self.db.update_session(session_id, **updates)
        updated = self.db.get_session(session_id)

        sess_dir = os.path.join(self.base_dir, session_id)
        if os.path.exists(sess_dir):
            self._write_session_json(sess_dir, updated)
            self.db.export_session_bundle(session_id, sess_dir)

        return updated

    def save_checkpoint(self, session_id: str, checkpoint_name: str, data) -> None:
        sess_dir = os.path.join(self.base_dir, session_id)
        if not os.path.exists(sess_dir):
            return

        cp_file = os.path.join(sess_dir, f"{checkpoint_name}.json")
        with open(cp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        if checkpoint_name == "script_data" and isinstance(data, dict):
            self.db.save_script(session_id, data)
        elif checkpoint_name == "audio_assets" and isinstance(data, list):
            for a in data:
                ap = a.get("audio_path", "")
                if ap:
                    self.db.register_asset(
                        session_id=session_id,
                        scene_number=a.get("scene_number", 0),
                        asset_type="audio",
                        file_path=ap,
                        status=a.get("status", "GENERATED"),
                        engine_used=a.get("engine_used", ""),
                        duration_sec=a.get("duration_sec", 0.0),
                        api_duration_sec=a.get("api_duration_sec", 0.0)
                    )
        elif checkpoint_name == "video_assets" and isinstance(data, list):
            for v in data:
                vp = v.get("video_path", "")
                if vp:
                    self.db.register_asset(
                        session_id=session_id,
                        scene_number=v.get("scene_number", 0),
                        asset_type="video",
                        file_path=vp,
                        status=v.get("status", "GENERATED"),
                        model_used=v.get("image_model", ""),
                        duration_sec=v.get("duration_sec", 0.0),
                        api_duration_sec=v.get("total_api_duration_sec", 0.0)
                    )
                ip = v.get("image_path", "")
                if ip:
                    self.db.register_asset(
                        session_id=session_id,
                        scene_number=v.get("scene_number", 0),
                        asset_type="image",
                        file_path=ip,
                        status="GENERATED",
                        model_used=v.get("image_model", "")
                    )

        self.db.export_session_bundle(session_id, sess_dir)
        print(f"[+] Saved checkpoint '{checkpoint_name}' for session {session_id}")

    def load_checkpoint(self, session_id: str, checkpoint_name: str):
        if checkpoint_name == "script_data":
            db_data = self.db.get_script(session_id)
            if db_data:
                return db_data

        sess_dir = os.path.join(self.base_dir, session_id)
        cp_file = os.path.join(sess_dir, f"{checkpoint_name}.json")
        if os.path.exists(cp_file):
            with open(cp_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def log_api_call(self, session_id: str, step: str, service: str, request_data: dict,
                     response_data: dict, status: str = "SUCCESS", duration_sec: float = 0.0) -> dict:
        if not session_id:
            return None

        result = self.db.log_api_call(session_id, step, service, request_data, response_data, status, duration_sec)

        sess_dir = os.path.join(self.base_dir, session_id)
        if os.path.exists(sess_dir):
            audit_file = os.path.join(sess_dir, "audit_trail.json")
            entries = []
            if os.path.exists(audit_file):
                try:
                    with open(audit_file, "r", encoding="utf-8") as f:
                        entries = json.load(f)
                except Exception:
                    entries = []

            entry = {
                "id": result["id"],
                "timestamp": datetime.datetime.now().isoformat(),
                "step": step,
                "service": service,
                "request": request_data,
                "response": response_data,
                "status": status,
                "duration_sec": round(duration_sec, 2)
            }
            entries.append(entry)
            self._write_audit_json(sess_dir, entries)

        print(f"  [audit] Logged {service} [{status}] ({duration_sec:.2f}s) for session {session_id}")
        return result

    def get_audit_trail(self, session_id: str) -> list:
        return self.db.get_audit_logs(session_id)

    def get_session_dir(self, session_id: str) -> str:
        return os.path.join(self.base_dir, session_id)

    def increment_counter(self, session_id: str, counter_name: str) -> int:
        meta = self.db.get_session(session_id)
        if not meta:
            return 0
        new_val = meta.get(counter_name, 0) + 1
        self.db.update_session(session_id, **{counter_name: new_val})

        sess_dir = os.path.join(self.base_dir, session_id)
        if os.path.exists(sess_dir):
            updated = self.db.get_session(session_id)
            self._write_session_json(sess_dir, updated)

        return new_val

    def register_asset(self, session_id, scene_number, asset_type, file_path,
                       status="GENERATED", engine_used="", model_used="",
                       duration_sec=0.0, api_duration_sec=0.0, metadata=None):
        self.db.register_asset(session_id, scene_number, asset_type, file_path,
                               status, engine_used, model_used,
                               duration_sec, api_duration_sec, metadata)

    def get_assets(self, session_id, asset_type=None):
        return self.db.get_assets(session_id, asset_type)

    def get_asset_summary(self, session_id):
        return self.db.get_asset_summary(session_id)

    def save_research(self, session_id, seed_topic, data):
        self.db.save_research(session_id, seed_topic, data)
        sess_dir = os.path.join(self.base_dir, session_id)
        if os.path.exists(sess_dir):
            research_file = os.path.join(sess_dir, "competitor_research.json")
            with open(research_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

    def get_research(self, session_id):
        return self.db.get_research(session_id)

    def get_api_cost_summary(self, session_id):
        return self.db.get_api_cost_summary(session_id)

    def export_bundle(self, session_id):
        sess_dir = os.path.join(self.base_dir, session_id)
        return self.db.export_session_bundle(session_id, sess_dir)

    def delete_session(self, session_id: str) -> bool:
        self.db.delete_session(session_id)
        sess_dir = os.path.join(self.base_dir, session_id)
        if os.path.exists(sess_dir):
            try:
                shutil.rmtree(sess_dir)
                print(f"[+] Deleted session: {session_id}")
                return True
            except Exception as e:
                print(f"[-] Could not delete session directory {session_id}: {e}")
        return True

    def _write_session_json(self, sess_dir, meta):
        meta_file = os.path.join(sess_dir, "session.json")
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, default=str)

    def _write_audit_json(self, sess_dir, entries):
        audit_file = os.path.join(sess_dir, "audit_trail.json")
        with open(audit_file, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, default=str)
