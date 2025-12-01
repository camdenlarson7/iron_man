from db import get_connection


def seed_demo_user_and_workout():
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                # 1) Insert demo user (if not exists)
                cur.execute("""
                    INSERT INTO Users (username, email, password_hash)
                    VALUES ('cam', 'cam@example.com', 'fake_hash')
                    ON CONFLICT (username) DO NOTHING
                    RETURNING user_id;
                """)
                row = cur.fetchone()
                if row:
                    user_id = row[0]
                    print(f"Inserted new user 'cam' with user_id={user_id}")
                else:
                    # User already exists; fetch ID
                    cur.execute("SELECT user_id FROM Users WHERE username = 'cam';")
                    user_id = cur.fetchone()[0]
                    print(f"User 'cam' already exists with user_id={user_id}")

                # 2) Insert a demo location
                cur.execute("""
                    INSERT INTO Locations (name, location_type, city, state)
                    VALUES ('Case Track', 'track', 'Cleveland', 'OH')
                    RETURNING location_id;
                """)
                location_id = cur.fetchone()[0]
                print(f"Inserted location 'Case Track' with location_id={location_id}")

                # 3) Get workout_type_id for 'run'
                cur.execute("SELECT workout_type_id FROM Workout_Types WHERE name = 'run';")
                workout_type_id = cur.fetchone()[0]

                # 4) Insert a demo workout
                cur.execute("""
                    INSERT INTO Workouts (
                        user_id, workout_type_id, location_id,
                        workout_date, start_time, duration_seconds,
                        distance_km, avg_pace_seconds_per_km, effort_level, notes
                    ) VALUES (
                        %s, %s, %s,
                        CURRENT_DATE, '07:30',
                        3600, 10.0, 360, 7, 'Easy morning run from Python'
                    )
                    RETURNING workout_id;
                """, (user_id, workout_type_id, location_id))

                workout_id = cur.fetchone()[0]
                print(f"Inserted workout {workout_id} for user {user_id}")
    finally:
        conn.close()


if __name__ == "__main__":
    seed_demo_user_and_workout()
