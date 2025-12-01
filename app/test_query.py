from db import get_connection


def get_recent_workouts(username: str, limit: int = 10):
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                # Find the user_id for the given username
                cur.execute("""
                    SELECT user_id
                    FROM Users
                    WHERE username = %s;
                """, (username,))
                user_row = cur.fetchone()
                if not user_row:
                    print(f"No such user: {username}")
                    return []

                user_id = user_row[0]

                # Fetch recent workouts
                cur.execute("""
                    SELECT
                        workout_date,
                        wt.name AS workout_type,
                        distance_km,
                        duration_seconds,
                        effort_level,
                        notes
                    FROM Workouts w
                    JOIN Workout_Types wt
                      ON w.workout_type_id = wt.workout_type_id
                    WHERE w.user_id = %s
                    ORDER BY workout_date DESC, start_time DESC
                    LIMIT %s;
                """, (user_id, limit))

                rows = cur.fetchall()
                return rows
    finally:
        conn.close()


if __name__ == "__main__":
    workouts = get_recent_workouts("cam", limit=5)
    if not workouts:
        print("No workouts found.")
    else:
        print("Recent workouts for cam:")
        for w in workouts:
            workout_date, workout_type, distance_km, duration_seconds, effort_level, notes = w
            print(
                f"{workout_date} | {workout_type:4} | "
                f"{distance_km} km | {duration_seconds//60} min | "
                f"effort {effort_level} | {notes}"
            )
