from datetime import datetime

from queries import (
    get_user_id_by_username,
    list_workout_types,
    insert_workout,
    get_recent_workouts,
    get_weekly_volume_by_sport,
    get_total_distance_per_gear,
)


def prompt_username() -> int:
    while True:
        username = input("Enter your username (e.g., 'cam'): ").strip()
        user_id = get_user_id_by_username(username)
        if user_id is not None:
            print(f"Hello, {username}! (user_id={user_id})")
            return user_id
        else:
            print(f"User '{username}' not found. Please run seed_demo.py or create this user first.")


def add_workout(user_id: int):
    print("\n=== Add Workout ===")
    print("Available workout types:")
    for wt_id, wt_name in list_workout_types():
        print(f"  - {wt_name}")

    workout_type_name = input("Workout type (swim/bike/run): ").strip().lower()
    date_str = input("Workout date (YYYY-MM-DD): ").strip()
    start_time_str = input("Start time (HH:MM, optional - blank for none): ").strip()
    duration_minutes = input("Duration (minutes): ").strip()
    distance_str = input("Distance (km): ").strip()
    effort_str = input("Effort level (1–10): ").strip()
    notes = input("Notes (optional): ").strip()

    # basic parsing
    workout_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    start_time = start_time_str if start_time_str else None
    duration_seconds = int(float(duration_minutes) * 60)
    distance_km = float(distance_str)
    effort_level = int(effort_str)

    workout_id = insert_workout(
        user_id=user_id,
        workout_type_name=workout_type_name,
        workout_date=workout_date,
        duration_seconds=duration_seconds,
        distance_km=distance_km,
        effort_level=effort_level,
        location_id=None,
        start_time=start_time,
        elevation_gain_m=None,
        calories_kcal=None,
        avg_heart_rate_bpm=None,
        avg_cadence=None,
        avg_power_w=None,
        gear_id=None,
        notes=notes or None,
    )

    print(f"\n✅ Workout {workout_id} added.\n")


def show_recent_workouts(user_id: int):
    print("\n=== Recent Workouts ===")
    try:
        limit = int(input("How many workouts to show? (default 10): ") or "10")
    except ValueError:
        limit = 10

    rows = get_recent_workouts(user_id, limit=limit)
    if not rows:
        print("No workouts found.")
        return

    print("\nDate       | Start | Type | Dist (km) | Duration (min) | Effort | Notes")
    print("-" * 80)
    for r in rows:
        workout_date, start_time, workout_type, distance_km, duration_sec, effort_level, notes = r
        minutes = duration_sec // 60
        start_str = start_time if start_time else "--:--"
        note_snippet = (notes or "")[:30]
        print(
            f"{workout_date} | {start_str:5} | {workout_type:4} | "
            f"{distance_km:9.2f} | {minutes:13d} | {effort_level:6d} | {note_snippet}"
        )


def show_weekly_volume(user_id: int):
    print("\n=== Weekly Volume by Sport ===")
    start_str = input("Start date (YYYY-MM-DD): ").strip()
    end_str = input("End date (YYYY-MM-DD): ").strip()

    start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_str, "%Y-%m-%d").date()

    rows = get_weekly_volume_by_sport(user_id, start_date, end_date)
    if not rows:
        print("No workouts in this range.")
        return

    print("\nWeek Start | Type | Total Dist (km) | Total Dur (min)")
    print("-" * 60)
    for week_start, workout_type, total_dist_km, total_dur_sec in rows:
        minutes = total_dur_sec // 60
        print(f"{week_start} | {workout_type:4} | {total_dist_km:15.2f} | {minutes:15d}")


def show_gear_totals(user_id: int):
    print("\n=== Total Distance per Gear ===")
    rows = get_total_distance_per_gear(user_id)
    if not rows:
        print("No gear found.")
        return

    print("\nID | Type  | Brand       | Model        | Total Dist (km)")
    print("-" * 70)
    for gear_id, gear_type, brand, model, total_dist_km in rows:
        brand_disp = (brand or "")[:11]
        model_disp = (model or "")[:12]
        print(
            f"{gear_id:2d} | {gear_type:5} | {brand_disp:11s} | {model_disp:12s} | {total_dist_km:15.2f}"
        )


def main():
    print("=== IronTrack CLI ===")
    user_id = prompt_username()

    while True:
        print("\nMenu:")
        print("1) Add a workout")
        print("2) Show recent workouts")
        print("3) Show weekly volume by sport")
        print("4) Show total distance per gear")
        print("0) Exit")

        choice = input("Choose an option: ").strip()
        if choice == "1":
            add_workout(user_id)
        elif choice == "2":
            show_recent_workouts(user_id)
        elif choice == "3":
            show_weekly_volume(user_id)
        elif choice == "4":
            show_gear_totals(user_id)
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid choice, please try again.")


if __name__ == "__main__":
    main()
