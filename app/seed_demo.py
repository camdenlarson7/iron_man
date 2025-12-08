from db import get_connection


def seed_demo_user_and_workout():
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO Users (username, email, password_hash)
                    VALUES ('cam', 'cam@example.com', 'fake_hash')
                    ON CONFLICT (username) DO NOTHING
                    RETURNING user_id;
                    """
                )
                row = cur.fetchone()
                if row:
                    user_id = row[0]
                    print(f"Inserted new user 'cam' with user_id={user_id}")
                else:
                    cur.execute(
                        "SELECT user_id FROM Users WHERE username = 'cam';"
                    )
                    user_id = cur.fetchone()[0]
                    print(f"User 'cam' already exists with user_id={user_id}")

                cur.execute(
                    """
                    SELECT location_id
                    FROM Locations
                    WHERE name = 'Case Track' AND location_type = 'track'
                    LIMIT 1;
                    """
                )
                loc_row = cur.fetchone()
                if loc_row:
                    location_id = loc_row[0]
                    print(
                        f"Location 'Case Track' already exists with location_id={location_id}"
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO Locations (name, location_type, city, state)
                        VALUES ('Case Track', 'track', 'Cleveland', 'OH')
                        RETURNING location_id;
                        """
                    )
                    location_id = cur.fetchone()[0]
                    print(
                        f"Inserted location 'Case Track' with location_id={location_id}"
                    )

                
                cur.execute(
                    "SELECT workout_type_id FROM Workout_Types WHERE name = 'run';"
                )
                workout_type_id = cur.fetchone()[0]

                
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
                        CURRENT_DATE, '07:30',
                        3600, 10000.0,              -- 10 km run in meters
                        50.0, 600,                  -- 50 m climb, 600 kcal (example)
                        140, 170.0, NULL,           -- avg HR, cadence, no power
                        7, NULL, 'Easy morning run from Python'
                    )
                    RETURNING workout_id;
                    """,
                    (user_id, workout_type_id, location_id),
                )

                workout_id = cur.fetchone()[0]
                print(f"Inserted workout {workout_id} for user {user_id}")
    finally:
        conn.close()


if __name__ == "__main__":
    seed_demo_user_and_workout()
