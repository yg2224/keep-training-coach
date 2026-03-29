from datetime import datetime


ACTIVE_PLAN_JOB_STATUSES = {"queued", "running"}
TERMINAL_PLAN_JOB_STATUSES = {"succeeded", "failed"}


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def create_plan_job(conn, job_type, language):
    cursor = conn.execute(
        """
        INSERT INTO plan_jobs (
            job_type,
            status,
            language,
            created_at
        ) VALUES (?, ?, ?, ?)
        """,
        (job_type, "queued", language, now_text()),
    )
    conn.commit()
    return cursor.lastrowid


def mark_plan_job_running(conn, job_id):
    conn.execute(
        """
        UPDATE plan_jobs
        SET status = ?,
            started_at = ?,
            error_message = NULL
        WHERE id = ?
        """,
        ("running", now_text(), job_id),
    )
    conn.commit()


def mark_plan_job_succeeded(conn, job_id, result_plan_id):
    conn.execute(
        """
        UPDATE plan_jobs
        SET status = ?,
            result_plan_id = ?,
            finished_at = ?,
            error_message = NULL
        WHERE id = ?
        """,
        ("succeeded", result_plan_id, now_text(), job_id),
    )
    conn.commit()


def mark_plan_job_failed(conn, job_id, error_message):
    conn.execute(
        """
        UPDATE plan_jobs
        SET status = ?,
            error_message = ?,
            finished_at = ?
        WHERE id = ?
        """,
        ("failed", error_message, now_text(), job_id),
    )
    conn.commit()


def get_plan_job(conn, job_id):
    row = conn.execute(
        """
        SELECT *
        FROM plan_jobs
        WHERE id = ?
        """,
        (job_id,),
    ).fetchone()
    return dict(row) if row else None


def get_active_plan_job(conn):
    row = conn.execute(
        """
        SELECT *
        FROM plan_jobs
        WHERE status IN ('queued', 'running')
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    return dict(row) if row else None


def get_latest_plan_job(conn):
    active_job = get_active_plan_job(conn)
    if active_job:
        return active_job
    row = conn.execute(
        """
        SELECT *
        FROM plan_jobs
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    return dict(row) if row else None


def serialize_plan_job(job):
    if not job:
        return None
    status = job["status"]
    return {
        "id": job["id"],
        "job_type": job["job_type"],
        "status": status,
        "language": job["language"],
        "result_plan_id": job["result_plan_id"],
        "error_message": job["error_message"],
        "created_at": job["created_at"],
        "started_at": job["started_at"],
        "finished_at": job["finished_at"],
        "is_terminal": status in TERMINAL_PLAN_JOB_STATUSES,
    }
