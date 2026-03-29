from datetime import datetime, timezone

import requests

KEEP_SPORT_TYPES = ["running", "hiking", "cycling"]
KEEP2STRAVA = {
    "outdoorWalking": "Walk",
    "outdoorRunning": "Run",
    "outdoorCycling": "Ride",
    "indoorRunning": "VirtualRun",
    "mountaineering": "Hiking",
}

LOGIN_API = "https://api.gotokeep.com/v1.1/users/login"
RUN_DATA_API = (
    "https://api.gotokeep.com/pd/v3/stats/detail?dateUnit=all&type={sport_type}&lastDate={last_date}"
)
RUN_LOG_API = "https://api.gotokeep.com/pd/v3/{sport_type}log/{run_id}"


def login(session, mobile, password):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
    }
    response = session.post(
        LOGIN_API,
        headers=headers,
        data={"mobile": mobile, "password": password},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("data", {}).get("token")
    if not token:
        raise RuntimeError("Keep login failed: token missing")
    headers["Authorization"] = f"Bearer {token}"
    return headers


def get_to_download_run_ids(session, headers, sport_type):
    last_date = 0
    result = []
    while True:
        response = session.get(
            RUN_DATA_API.format(sport_type=sport_type, last_date=last_date),
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json().get("data", {})
        records = payload.get("records", [])
        for record in records:
            logs = [item["stats"] for item in record.get("logs", []) if "stats" in item]
            result.extend(item["id"] for item in logs if not item.get("isDoubtful"))
        last_date = payload.get("lastTimestamp", 0)
        if not last_date:
            break
    return result


def get_single_run_data(session, headers, run_id, sport_type):
    response = session.get(
        RUN_LOG_API.format(run_id=run_id, sport_type=sport_type),
        headers=headers,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def parse_keep_activity(run_data):
    payload = run_data["data"]
    keep_id = payload["id"].split("_")[1]
    start_time = payload["startTime"]
    start_date = datetime.fromtimestamp(start_time / 1000, tz=timezone.utc)
    data_type = payload["dataType"]
    activity_type = KEEP2STRAVA.get(data_type, data_type)
    heart_rate = payload.get("heartRate", {}).get("averageHeartRate")
    duration = payload.get("duration") or 0
    distance = float(payload.get("distance") or 0)

    return {
        "run_id": str(keep_id),
        "name": f"{activity_type} from Keep",
        "type": activity_type,
        "subtype": activity_type,
        "distance": distance,
        "moving_time": str(duration),
        "elapsed_time": str(max(int((payload.get("endTime", start_time) - start_time) / 1000), 0)),
        "start_date": start_date.strftime("%Y-%m-%d %H:%M:%S"),
        "start_date_local": start_date.strftime("%Y-%m-%d %H:%M:%S"),
        "average_heartrate": heart_rate if heart_rate and heart_rate > 0 else None,
        "average_speed": distance / duration if duration else 0,
        "elevation_gain": None,
        "summary_polyline": "",
    }


def upsert_activity(conn, activity):
    conn.execute(
        """
        INSERT INTO activities (
            run_id,
            name,
            type,
            subtype,
            distance,
            moving_time,
            elapsed_time,
            start_date,
            start_date_local,
            average_heartrate,
            average_speed,
            elevation_gain,
            summary_polyline
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
            name = excluded.name,
            type = excluded.type,
            subtype = excluded.subtype,
            distance = excluded.distance,
            moving_time = excluded.moving_time,
            elapsed_time = excluded.elapsed_time,
            start_date = excluded.start_date,
            start_date_local = excluded.start_date_local,
            average_heartrate = excluded.average_heartrate,
            average_speed = excluded.average_speed,
            elevation_gain = excluded.elevation_gain,
            summary_polyline = excluded.summary_polyline
        """,
        (
            activity["run_id"],
            activity["name"],
            activity["type"],
            activity["subtype"],
            activity["distance"],
            activity["moving_time"],
            activity["elapsed_time"],
            activity["start_date"],
            activity["start_date_local"],
            activity["average_heartrate"],
            activity["average_speed"],
            activity["elevation_gain"],
            activity["summary_polyline"],
        ),
    )
    conn.commit()


def sync_keep_activities(db_path, phone_number, password, sync_types=None):
    from services.storage import get_connection, init_db

    if not phone_number or not password:
        raise RuntimeError("Keep credentials are required")

    init_db(db_path)
    sync_types = sync_types or KEEP_SPORT_TYPES
    session = requests.Session()
    headers = login(session, phone_number, password)
    conn = get_connection(db_path)
    synced = 0
    errors = []
    try:
        existing_ids = {
            row["run_id"] for row in conn.execute("SELECT run_id FROM activities").fetchall()
        }
        for sport_type in sync_types:
            for run_id in get_to_download_run_ids(session, headers, sport_type):
                try:
                    keep_id = run_id.split("_")[1]
                    if keep_id in existing_ids:
                        continue
                    raw_run = get_single_run_data(session, headers, run_id, sport_type)
                    upsert_activity(conn, parse_keep_activity(raw_run))
                    synced += 1
                except Exception as exc:
                    errors.append(str(exc))
    finally:
        conn.close()
    return {"synced": synced, "errors": errors}
