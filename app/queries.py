# app/queries.py

from datetime import date
from typing import List, Optional, Tuple

from db import get_connection


# ---------- Helpers ----------
def list_users() -> List[Tuple[int, str]]:
    """
    Return all users as (user_id, username) sorted by username.
    Useful for a simple 'login' selector in the app.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_id, username FROM Users ORDER BY username;"
                )
                return cur.fetchall()
    finally:
        conn.close()

def get_user_id_by_username(username: str) -> Optional[int]:
    """
    Look up a user_id given a username.
    Returns None if not found.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_id FROM Users WHERE username = %s;",
                    (username,)
                )
                row = cur.fetchone()
                if row:
                    return row[0]
                return None
    finally:
        conn.close()


def get_workout_type_id_by_name(name: str) -> Optional[int]:
    """
    Map a workout type name like 'swim', 'bike', 'run' to its ID.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT workout_type_id FROM Workout_Types WHERE name = %s;",
                    (name,)
                )
                row = cur.fetchone()
                if row:
                    return row[0]
                return None
    finally:
        conn.close()


def list_workout_types() -> List[Tuple[int, str]]:
    """
    Return all workout types as (workout_type_id, name).
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT workout_type_id, name FROM Workout_Types ORDER BY workout_type_id;"
                )
                return cur.fetchall()
    finally:
        conn.close()


# ---------- Core operations ----------

def insert_workout(
    user_id: int,
    workout_type_name: str,
    workout_date: date,
    duration_seconds: int,
    distance_km: float,
    effort_level: int,
    location_id: Optional[int] = None,
    start_time: Optional[str] = None,  # 'HH:MM' or None
    elevation_gain_m: Optional[float] = None,
    calories_kcal: Optional[int] = None,
    avg_heart_rate_bpm: Optional[int] = None,
    avg_cadence: Optional[float] = None,
    avg_power_w: Optional[float] = None,
    gear_id: Optional[int] = None,
    notes: Optional[str] = None,
) -> int:
    """
    Insert a new workout row and return its workout_id.

    Python code still works in km; we convert to meters for the DB.
    """
    workout_type_id = get_workout_type_id_by_name(workout_type_name)
    if workout_type_id is None:
        raise ValueError(f"Unknown workout type: {workout_type_name}")

    # Convert km -> m for canonical storage
    distance_m = None
    if distance_km is not None:
        distance_m = distance_km * 1000.0

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO Workouts (
                        user_id, workout_type_id, location_id,
                        workout_date, start_time,
                        duration_seconds, distance_m,
                        elevation_gain_m, calories_kcal,
                        avg_heart_rate_bpm, avg_cadence, avg_power_w,
                        effort_level, gear_id, notes
                    ) VALUES (
                        %s, %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s, %s,
                        %s, %s, %s
                    )
                    RETURNING workout_id;
                    """,
                    (
                        user_id,
                        workout_type_id,
                        location_id,
                        workout_date,
                        start_time,
                        duration_seconds,
                        distance_m,
                        elevation_gain_m,
                        calories_kcal,
                        avg_heart_rate_bpm,
                        avg_cadence,
                        avg_power_w,
                        effort_level,
                        gear_id,
                        notes,
                    ),
                )
                workout_id = cur.fetchone()[0]
                return workout_id
    finally:
        conn.close()


def get_recent_workouts(
    user_id: int,
    limit: int = 10
) -> List[Tuple]:
    """
    Return recent workouts for a user, ordered by date + start_time desc.
    Each row:
      (workout_date, start_time, workout_type, distance_km, duration_seconds, effort_level, notes)
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        w.workout_date,
                        COALESCE(w.start_time::text, '') AS start_time,
                        wt.name AS workout_type,
                        -- meters -> km
                        (w.distance_m / 1000.0) AS distance_km,
                        w.duration_seconds,
                        w.effort_level,
                        w.notes
                    FROM Workouts w
                    JOIN Workout_Types wt
                      ON w.workout_type_id = wt.workout_type_id
                    WHERE w.user_id = %s
                    ORDER BY w.workout_date DESC, w.start_time DESC NULLS LAST
                    LIMIT %s;
                    """,
                    (user_id, limit),
                )
                return cur.fetchall()
    finally:
        conn.close()


def get_weekly_volume_by_sport(
    user_id: int,
    start_date: date,
    end_date: date
) -> List[Tuple]:
    """
    Return weekly total distance (km) and duration (sec) per sport between given dates.
    Each row: (week_start, workout_type, total_distance_km, total_duration_sec)
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        date_trunc('week', w.workout_date)::date AS week_start,
                        wt.name AS workout_type,
                        -- meters -> km
                        COALESCE(SUM(w.distance_m) / 1000.0, 0) AS total_distance_km,
                        COALESCE(SUM(w.duration_seconds), 0) AS total_duration_sec
                    FROM Workouts w
                    JOIN Workout_Types wt
                      ON w.workout_type_id = wt.workout_type_id
                    WHERE w.user_id = %s
                      AND w.workout_date BETWEEN %s AND %s
                    GROUP BY week_start, wt.name
                    ORDER BY week_start ASC, wt.name;
                    """,
                    (user_id, start_date, end_date),
                )
                return cur.fetchall()
    finally:
        conn.close()


def get_total_distance_per_gear(user_id: int) -> List[Tuple]:
    """
    Sum distance for each piece of gear for this user.

    Uses the gear_distance VIEW, which already joins Gear + Workout_Gear + Workouts
    and stores total_distance_m (meters). We convert to km.
    Returns each row as:
      (gear_id, gear_type, brand, model, total_distance_km)
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        gear_id,
                        gear_type,
                        brand,
                        model,
                        (total_distance_m / 1000.0) AS total_distance_km
                    FROM gear_distance
                    WHERE user_id = %s
                    ORDER BY total_distance_m DESC, gear_id;
                    """,
                    (user_id,),
                )
                return cur.fetchall()
    finally:
        conn.close()


def fetch_workouts(
    user_id: int,
    workout_type_name: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[Tuple]:
    """
    Fetch workouts for a user with optional filters on type and date range.

    Each row:
      (workout_id, workout_date, start_time, workout_type,
       distance_km, duration_seconds, effort_level, notes)
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                base_query = """
                    SELECT
                        w.workout_id,
                        w.workout_date,
                        w.start_time,
                        wt.name AS workout_type,
                        (w.distance_m / 1000.0) AS distance_km,
                        w.duration_seconds,
                        w.effort_level,
                        w.notes
                    FROM Workouts w
                    JOIN Workout_Types wt
                      ON w.workout_type_id = wt.workout_type_id
                    WHERE w.user_id = %s
                """
                params = [user_id]

                if workout_type_name and workout_type_name != "All":
                    base_query += " AND wt.name = %s"
                    params.append(workout_type_name)

                if start_date:
                    base_query += " AND w.workout_date >= %s"
                    params.append(start_date)
                if end_date:
                    base_query += " AND w.workout_date <= %s"
                    params.append(end_date)

                base_query += " ORDER BY w.workout_date DESC, w.start_time DESC NULLS LAST;"

                cur.execute(base_query, tuple(params))
                return cur.fetchall()
    finally:
        conn.close()
def fetch_run_workouts_view(
    user_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[Tuple]:
    """
    Fetch run workouts from the run_workouts VIEW.

    Each row:
      (workout_id, workout_date, start_time,
       distance_miles, duration_seconds,
       pace_seconds_per_mile, elevation_gain_m,
       calories_kcal, avg_heart_rate_bpm,
       avg_cadence_spm, effort_level, notes)
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                base_query = """
                    SELECT
                        workout_id,
                        workout_date,
                        start_time,
                        distance_miles,
                        duration_seconds,
                        pace_seconds_per_mile,
                        elevation_gain_m,
                        calories_kcal,
                        avg_heart_rate_bpm,
                        avg_cadence_spm,
                        effort_level,
                        notes
                    FROM run_workouts
                    WHERE user_id = %s
                """
                params = [user_id]

                if start_date:
                    base_query += " AND workout_date >= %s"
                    params.append(start_date)
                if end_date:
                    base_query += " AND workout_date <= %s"
                    params.append(end_date)

                base_query += " ORDER BY workout_date DESC, start_time DESC NULLS LAST;"

                cur.execute(base_query, tuple(params))
                return cur.fetchall()
    finally:
        conn.close()


def fetch_bike_workouts_view(
    user_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[Tuple]:
    """
    Fetch bike workouts from the bike_workouts VIEW.

    Each row:
      (workout_id, workout_date, start_time,
       distance_miles, duration_seconds,
       speed_mph, elevation_gain_m,
       calories_kcal, avg_heart_rate_bpm,
       avg_cadence_rpm, avg_power_w,
       effort_level, notes)
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                base_query = """
                    SELECT
                        workout_id,
                        workout_date,
                        start_time,
                        distance_miles,
                        duration_seconds,
                        speed_mph,
                        elevation_gain_m,
                        calories_kcal,
                        avg_heart_rate_bpm,
                        avg_cadence_rpm,
                        avg_power_w,
                        effort_level,
                        notes
                    FROM bike_workouts
                    WHERE user_id = %s
                """
                params = [user_id]

                if start_date:
                    base_query += " AND workout_date >= %s"
                    params.append(start_date)
                if end_date:
                    base_query += " AND workout_date <= %s"
                    params.append(end_date)

                base_query += " ORDER BY workout_date DESC, start_time DESC NULLS LAST;"

                cur.execute(base_query, tuple(params))
                return cur.fetchall()
    finally:
        conn.close()


def fetch_swim_workouts_view(
    user_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[Tuple]:
    """
    Fetch swim workouts from the swim_workouts VIEW.

    Each row:
      (workout_id, workout_date, start_time,
       distance_yards, duration_seconds,
       pace_seconds_per_100yd,
       calories_kcal, avg_heart_rate_bpm,
       effort_level, notes)
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                base_query = """
                    SELECT
                        workout_id,
                        workout_date,
                        start_time,
                        distance_yards,
                        duration_seconds,
                        pace_seconds_per_100yd,
                        calories_kcal,
                        avg_heart_rate_bpm,
                        effort_level,
                        notes
                    FROM swim_workouts
                    WHERE user_id = %s
                """
                params = [user_id]

                if start_date:
                    base_query += " AND workout_date >= %s"
                    params.append(start_date)
                if end_date:
                    base_query += " AND workout_date <= %s"
                    params.append(end_date)

                base_query += " ORDER BY workout_date DESC, start_time DESC NULLS LAST;"

                cur.execute(base_query, tuple(params))
                return cur.fetchall()
    finally:
        conn.close()

# ---------- Gear operations ----------

def insert_gear(
    user_id: int,
    gear_type: str,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    purchase_date: Optional[date] = None,
    retired: bool = False,
) -> int:
    """
    Insert a new gear item for this user and return its gear_id.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO Gear (
                        user_id,
                        gear_type,
                        brand,
                        model,
                        purchase_date,
                        retired
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING gear_id;
                    """,
                    (user_id, gear_type, brand, model, purchase_date, retired),
                )
                gear_id = cur.fetchone()[0]
                return gear_id
    finally:
        conn.close()


def attach_gear_to_workout(workout_id: int, gear_ids: list[int]) -> None:
    """
    Attach one or more gear items to a workout by inserting into Workout_Gear.
    Also supports calling multiple times safely via ON CONFLICT DO NOTHING.
    """
    if not gear_ids:
        return

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                for gid in set(gear_ids):
                    cur.execute(
                        """
                        INSERT INTO Workout_Gear (workout_id, gear_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING;
                        """,
                        (workout_id, gid),
                    )
    finally:
        conn.close()
