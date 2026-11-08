"""Verifica migración de SQLite de laboratorio sin perder tareas anteriores."""
import sqlite3
import tempfile
from pathlib import Path
from ac_storage import SCHEMA
from ac_bridge import ACBridge


def test_old_task_table_is_migrated_without_losing_rows():
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/"propuesta_ac.sqlite3"
        legacy=SCHEMA.replace(
            "source_capture_id TEXT REFERENCES ac_captures(id)",
            "source_capture_id TEXT NOT NULL REFERENCES ac_captures(id)"
        )
        with sqlite3.connect(path) as db:
            db.executescript(legacy)
            db.execute("""INSERT INTO ac_sessions
                (id,store,employee_id,flow,stage,area,started_at)
                VALUES('sess','Iztapalapa','worker','Surtido','Separar','Colgado','2026-01-01')""")
            db.execute("""INSERT INTO ac_captures
                (id,event_key,store,model_id,color,flow,stage,area,session_id,
                 recorded_at,created_by)
                VALUES('capture','original','Iztapalapa','914629','','Surtido',
                 'Separar','Colgado','sess','2026-01-01','worker')""")
            db.execute("""INSERT INTO ac_tasks
                (id,source_capture_id,store,model_id,color,flow,stage,area,created_at)
                VALUES('old_task','capture','Iztapalapa','914629','','Surtido',
                'Acondicionar','Colgado','2026-01-01')""")
            db.execute("""INSERT INTO ac_task_sizes(task_id,size,total)
                VALUES('old_task','M',5)""")
        bridge=ACBridge(temp);bridge.initialize()
        with bridge.operation.transaction() as db:
            row=db.execute("SELECT * FROM ac_tasks WHERE id='old_task'").fetchone()
            assert row["source_capture_id"]=="capture"
            assert db.execute("SELECT total FROM ac_task_sizes WHERE task_id='old_task'").fetchone()[0]==5
            assert db.execute("PRAGMA foreign_key_check").fetchall()==[]
            meta={r["name"]:r for r in db.execute("PRAGMA table_info(ac_tasks)")}
            assert meta["source_capture_id"]["notnull"]==0
        bridge.initialize()
