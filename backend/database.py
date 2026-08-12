import os
import json
import sqlite3
import datetime
import uuid


class PipelineDB:
    def __init__(self, db_path=None):
        if db_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(project_root, "data", "pipeline.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    profile_id TEXT NOT NULL DEFAULT 'default_psychology',
                    profile_name TEXT,
                    status TEXT NOT NULL DEFAULT 'CREATED',
                    current_step TEXT DEFAULT 'SCRIPT_GENERATION',
                    completed_steps TEXT DEFAULT '[]',
                    audio_count INTEGER DEFAULT 0,
                    video_count INTEGER DEFAULT 0,
                    final_video_path TEXT,
                    package_path TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS competitor_research (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    seed_topic TEXT,
                    data_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS scripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    title TEXT,
                    hook_statement TEXT,
                    scene_count INTEGER DEFAULT 0,
                    total_words INTEGER DEFAULT 0,
                    target_minutes INTEGER DEFAULT 10,
                    data_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    scene_number INTEGER NOT NULL,
                    asset_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_name TEXT,
                    file_size_bytes INTEGER DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'GENERATED',
                    engine_used TEXT,
                    model_used TEXT,
                    duration_sec REAL DEFAULT 0.0,
                    api_duration_sec REAL DEFAULT 0.0,
                    metadata_json TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    step TEXT,
                    service TEXT,
                    request_json TEXT DEFAULT '{}',
                    response_json TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'SUCCESS',
                    duration_sec REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS research_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_key TEXT NOT NULL UNIQUE,
                    seed_topic TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_research_cache_topic ON research_cache(topic_key);
                CREATE INDEX IF NOT EXISTS idx_assets_session ON assets(session_id);
                CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(session_id, asset_type);
                CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_logs(session_id);
                CREATE INDEX IF NOT EXISTS idx_scripts_session ON scripts(session_id);
                CREATE INDEX IF NOT EXISTS idx_research_session ON competitor_research(session_id);
            """)
            conn.commit()
        finally:
            conn.close()

    # --- SESSION OPERATIONS ---

    def create_session(self, session_id, topic, profile_id, profile_name, created_at):
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT OR IGNORE INTO sessions
                   (session_id, topic, profile_id, profile_name, status, current_step,
                    completed_steps, audio_count, video_count, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 'CREATED', 'SCRIPT_GENERATION', '[]', 0, 0, ?, ?)""",
                (session_id, topic, profile_id, profile_name, created_at, created_at)
            )
            conn.commit()
        finally:
            conn.close()

    def get_session(self, session_id):
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
            if row:
                return self._row_to_session_dict(row)
            return None
        finally:
            conn.close()

    def list_sessions(self):
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM sessions ORDER BY created_at DESC").fetchall()
            return [self._row_to_session_dict(r) for r in rows]
        finally:
            conn.close()

    def update_session(self, session_id, **kwargs):
        conn = self._get_conn()
        try:
            kwargs["updated_at"] = datetime.datetime.now().isoformat()
            if "completed_steps" in kwargs and isinstance(kwargs["completed_steps"], list):
                kwargs["completed_steps"] = json.dumps(kwargs["completed_steps"])
            set_clause = ", ".join(f"{k} = ?" for k in kwargs)
            values = list(kwargs.values()) + [session_id]
            conn.execute(f"UPDATE sessions SET {set_clause} WHERE session_id = ?", values)
            conn.commit()
        finally:
            conn.close()

    def delete_session(self, session_id):
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
        finally:
            conn.close()

    def _row_to_session_dict(self, row):
        d = dict(row)
        try:
            d["completed_steps"] = json.loads(d.get("completed_steps", "[]"))
        except (json.JSONDecodeError, TypeError):
            d["completed_steps"] = []
        return d

    # --- COMPETITOR RESEARCH ---

    def save_research(self, session_id, seed_topic, data):
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM competitor_research WHERE session_id = ?", (session_id,))
            conn.execute(
                """INSERT INTO competitor_research (session_id, seed_topic, data_json, created_at)
                   VALUES (?, ?, ?, ?)""",
                (session_id, seed_topic, json.dumps(data, default=str), datetime.datetime.now().isoformat())
            )
            conn.commit()
        finally:
            conn.close()

    def get_research(self, session_id):
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT data_json FROM competitor_research WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
                (session_id,)
            ).fetchone()
            if row:
                return json.loads(row["data_json"])
            return None
        finally:
            conn.close()

    # --- RESEARCH CACHE (topic-keyed, cross-session) ---

    @staticmethod
    def _topic_key(seed_topic):
        return "".join(c.lower() if c.isalnum() else "_" for c in str(seed_topic).strip()).strip("_")

    def save_research_cache(self, seed_topic, data):
        key = self._topic_key(seed_topic)
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO research_cache (topic_key, seed_topic, data_json, created_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(topic_key) DO UPDATE SET
                     data_json = excluded.data_json,
                     created_at = excluded.created_at""",
                (key, seed_topic, json.dumps(data, default=str), datetime.datetime.now().isoformat())
            )
            conn.commit()
        finally:
            conn.close()

    def get_research_cache(self, seed_topic, max_age_hours=None):
        key = self._topic_key(seed_topic)
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT data_json, created_at FROM research_cache WHERE topic_key = ?", (key,)
            ).fetchone()
            if not row:
                return None
            if max_age_hours is not None:
                try:
                    created = datetime.datetime.fromisoformat(row["created_at"])
                    age_hours = (datetime.datetime.now() - created).total_seconds() / 3600.0
                    if age_hours > max_age_hours:
                        return None
                except Exception:
                    pass
            data = json.loads(row["data_json"])
            data["_cached_at"] = row["created_at"]
            return data
        finally:
            conn.close()

    def list_research_cache(self):
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT seed_topic, created_at, LENGTH(data_json) as size_bytes FROM research_cache ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def delete_research_cache(self, seed_topic):
        key = self._topic_key(seed_topic)
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM research_cache WHERE topic_key = ?", (key,))
            conn.commit()
        finally:
            conn.close()

    # --- SCRIPT DATA ---

    def save_script(self, session_id, script_data, target_minutes=10):
        conn = self._get_conn()
        try:
            scenes = script_data.get("scenes", [])
            total_words = sum(len(s.get("spoken_text", "").split()) for s in scenes)
            conn.execute("DELETE FROM scripts WHERE session_id = ?", (session_id,))
            conn.execute(
                """INSERT INTO scripts (session_id, title, hook_statement, scene_count, total_words,
                   target_minutes, data_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (session_id, script_data.get("title", ""), script_data.get("hook_statement", ""),
                 len(scenes), total_words, target_minutes,
                 json.dumps(script_data, default=str), datetime.datetime.now().isoformat())
            )
            conn.commit()
        finally:
            conn.close()

    def get_script(self, session_id):
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT data_json FROM scripts WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
                (session_id,)
            ).fetchone()
            if row:
                return json.loads(row["data_json"])
            return None
        finally:
            conn.close()

    def get_script_meta(self, session_id):
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT title, hook_statement, scene_count, total_words, target_minutes, created_at FROM scripts WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
                (session_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # --- ASSET REGISTRY ---

    def register_asset(self, session_id, scene_number, asset_type, file_path,
                       status="GENERATED", engine_used="", model_used="",
                       duration_sec=0.0, api_duration_sec=0.0, metadata=None):
        file_size = 0
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM assets WHERE session_id = ? AND scene_number = ? AND asset_type = ?",
                         (session_id, scene_number, asset_type))
            conn.execute(
                """INSERT INTO assets (session_id, scene_number, asset_type, file_path, file_name,
                   file_size_bytes, status, engine_used, model_used, duration_sec, api_duration_sec,
                   metadata_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (session_id, scene_number, asset_type, file_path, os.path.basename(file_path),
                 file_size, status, engine_used, model_used, duration_sec, api_duration_sec,
                 json.dumps(metadata or {}, default=str), datetime.datetime.now().isoformat())
            )
            conn.commit()
        finally:
            conn.close()

    def get_assets(self, session_id, asset_type=None):
        conn = self._get_conn()
        try:
            if asset_type:
                rows = conn.execute(
                    "SELECT * FROM assets WHERE session_id = ? AND asset_type = ? ORDER BY scene_number",
                    (session_id, asset_type)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM assets WHERE session_id = ? ORDER BY scene_number, asset_type",
                    (session_id,)
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_asset_summary(self, session_id):
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """SELECT asset_type, COUNT(*) as count, SUM(file_size_bytes) as total_bytes,
                   SUM(duration_sec) as total_duration
                   FROM assets WHERE session_id = ? GROUP BY asset_type""",
                (session_id,)
            ).fetchall()
            return {r["asset_type"]: {"count": r["count"], "total_bytes": r["total_bytes"] or 0,
                                      "total_duration": r["total_duration"] or 0.0} for r in rows}
        finally:
            conn.close()

    # --- AUDIT LOGS ---

    def log_api_call(self, session_id, step, service, request_data, response_data,
                     status="SUCCESS", duration_sec=0.0):
        entry_id = str(uuid.uuid4())[:8]
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO audit_logs (entry_id, session_id, step, service, request_json, response_json,
                   status, duration_sec, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (entry_id, session_id, step, service,
                 json.dumps(request_data, default=str), json.dumps(response_data, default=str),
                 status, round(duration_sec, 2), datetime.datetime.now().isoformat())
            )
            conn.commit()
        finally:
            conn.close()
        return {"id": entry_id, "step": step, "service": service, "status": status}

    def get_audit_logs(self, session_id, limit=500):
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM audit_logs WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
                (session_id, limit)
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                try:
                    d["request"] = json.loads(d.pop("request_json", "{}"))
                except (json.JSONDecodeError, TypeError):
                    d["request"] = {}
                try:
                    d["response"] = json.loads(d.pop("response_json", "{}"))
                except (json.JSONDecodeError, TypeError):
                    d["response"] = {}
                d["timestamp"] = d.get("created_at", "")
                result.append(d)
            return result
        finally:
            conn.close()

    def get_api_cost_summary(self, session_id):
        conn = self._get_conn()
        try:
            row = conn.execute(
                """SELECT COUNT(*) as total_calls, SUM(duration_sec) as total_api_time,
                   SUM(CASE WHEN status='SUCCESS' THEN 1 ELSE 0 END) as success_count,
                   SUM(CASE WHEN status='FAILED' THEN 1 ELSE 0 END) as failed_count
                   FROM audit_logs WHERE session_id = ?""",
                (session_id,)
            ).fetchone()
            return dict(row) if row else {"total_calls": 0, "total_api_time": 0, "success_count": 0, "failed_count": 0}
        finally:
            conn.close()

    # --- EXPORT SESSION BUNDLE (offline-readable JSON) ---

    def export_session_bundle(self, session_id, session_dir):
        session = self.get_session(session_id)
        if not session:
            return None

        bundle = {
            "session": session,
            "script_meta": self.get_script_meta(session_id),
            "script_data": self.get_script(session_id),
            "competitor_research": self.get_research(session_id),
            "assets": self.get_assets(session_id),
            "asset_summary": self.get_asset_summary(session_id),
            "audit_logs": self.get_audit_logs(session_id),
            "api_cost_summary": self.get_api_cost_summary(session_id),
            "exported_at": datetime.datetime.now().isoformat()
        }

        os.makedirs(session_dir, exist_ok=True)
        bundle_path = os.path.join(session_dir, "session_bundle.json")
        with open(bundle_path, "w", encoding="utf-8") as f:
            json.dump(bundle, f, indent=2, default=str)
        return bundle_path

    # --- MIGRATION: import existing JSON sessions ---

    def migrate_json_sessions(self, sessions_base_dir):
        if not os.path.exists(sessions_base_dir):
            return 0

        migrated = 0
        for name in os.listdir(sessions_base_dir):
            sess_dir = os.path.join(sessions_base_dir, name)
            meta_file = os.path.join(sess_dir, "session.json")
            if not os.path.isdir(sess_dir) or not os.path.exists(meta_file):
                continue

            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                continue

            sid = meta.get("session_id", name)
            if self.get_session(sid):
                continue

            self.create_session(
                session_id=sid,
                topic=meta.get("topic", "Unknown"),
                profile_id=meta.get("profile_id", "default_psychology"),
                profile_name=meta.get("profile_name", ""),
                created_at=meta.get("created_at", datetime.datetime.now().isoformat())
            )

            completed = meta.get("completed_steps", [])
            self.update_session(sid,
                status=meta.get("status", "CREATED"),
                current_step=meta.get("current_step", "SCRIPT_GENERATION"),
                completed_steps=completed,
                audio_count=meta.get("audio_count", 0),
                video_count=meta.get("video_count", 0),
                final_video_path=meta.get("final_video_path"),
                package_path=meta.get("package_path"),
                error=meta.get("error")
            )

            audit_file = os.path.join(sess_dir, "audit_trail.json")
            if os.path.exists(audit_file):
                try:
                    with open(audit_file, "r", encoding="utf-8") as f:
                        entries = json.load(f)
                    for entry in entries:
                        self.log_api_call(
                            session_id=sid,
                            step=entry.get("step", ""),
                            service=entry.get("service", ""),
                            request_data=entry.get("request", {}),
                            response_data=entry.get("response", {}),
                            status=entry.get("status", "SUCCESS"),
                            duration_sec=entry.get("duration_sec", 0.0)
                        )
                except Exception:
                    pass

            script_file = os.path.join(sess_dir, "script_data.json")
            if os.path.exists(script_file):
                try:
                    with open(script_file, "r", encoding="utf-8") as f:
                        script_data = json.load(f)
                    self.save_script(sid, script_data)
                except Exception:
                    pass

            audio_file = os.path.join(sess_dir, "audio_assets.json")
            if os.path.exists(audio_file):
                try:
                    with open(audio_file, "r", encoding="utf-8") as f:
                        audio_list = json.load(f)
                    for a in audio_list:
                        ap = a.get("audio_path", "")
                        if ap and os.path.exists(ap):
                            self.register_asset(
                                session_id=sid,
                                scene_number=a.get("scene_number", 0),
                                asset_type="audio",
                                file_path=ap,
                                status=a.get("status", "GENERATED"),
                                engine_used=a.get("engine_used", ""),
                                duration_sec=a.get("duration_sec", 0.0),
                                api_duration_sec=a.get("api_duration_sec", 0.0)
                            )
                except Exception:
                    pass

            video_file = os.path.join(sess_dir, "video_assets.json")
            if os.path.exists(video_file):
                try:
                    with open(video_file, "r", encoding="utf-8") as f:
                        video_list = json.load(f)
                    for v in video_list:
                        vp = v.get("video_path", "")
                        if vp and os.path.exists(vp):
                            self.register_asset(
                                session_id=sid,
                                scene_number=v.get("scene_number", 0),
                                asset_type="video",
                                file_path=vp,
                                status=v.get("status", "GENERATED"),
                                model_used=v.get("image_model", ""),
                                duration_sec=v.get("duration_sec", 0.0),
                                api_duration_sec=v.get("total_api_duration_sec", 0.0)
                            )
                        ip = v.get("image_path", "")
                        if ip and os.path.exists(ip):
                            self.register_asset(
                                session_id=sid,
                                scene_number=v.get("scene_number", 0),
                                asset_type="image",
                                file_path=ip,
                                status="GENERATED",
                                model_used=v.get("image_model", "")
                            )
                except Exception:
                    pass

            self.export_session_bundle(sid, sess_dir)
            migrated += 1

        return migrated
