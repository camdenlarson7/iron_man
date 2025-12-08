# app/populate_workouts.py

import random
from datetime import date, timedelta

from db import get_connection
from queries import (
    get_user_id_by_username,
    insert_workout,
    insert_gear,
    attach_gear_to_workout,
)

USERNAME = "John"  # change this if your username is different


def clear_user_data(user_id: int):
    """
    Delete all workouts (and related Workout_Gear rows via ON DELETE CASCADE)
    and all Gear for the given user. Leaves other users' data alone.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                # Delete Workout_Gear for this user's workouts
                cur.execute(
                    """
                    DELETE FROM Workout_Gear
                    WHERE workout_id IN (
                        SELECT workout_id FROM Workouts WHERE user_id = %s
                    );
                    """,
                    (user_id,),
                )
                print(f"Deleted {cur.rowcount} Workout_Gear rows for user_id={user_id}.")

                # Delete workouts themselves
                cur.execute(
                    "DELETE FROM Workouts WHERE user_id = %s;",
                    (user_id,),
                )
                print(f"Deleted {cur.rowcount} workouts for user_id={user_id}.")

                # Delete gear for this user (will also cascade any remaining Workout_Gear)
                cur.execute(
                    "DELETE FROM Gear WHERE user_id = %s;",
                    (user_id,),
                )
                print(f"Deleted {cur.rowcount} gear items for user_id={user_id}.")
    finally:
        conn.close()


def create_demo_gear(user_id: int) -> dict[str, list[int]]:
    shoes_train = insert_gear(
        user_id=user_id,
        gear_type="shoe",
        brand="Nike",
        model="Pegasus 41",
        purchase_date=date(2025, 7, 1),
        retired=False,
    )
    shoes_race = insert_gear(
        user_id=user_id,
        gear_type="shoe",
        brand="Nike",
        model="Alphafly 3",
        purchase_date=date(2025, 8, 15),
        retired=False,
    )
    road_bike = insert_gear(
        user_id=user_id,
        gear_type="bike",
        brand="Trek",
        model="Emonda SL6",
        purchase_date=date(2025, 4, 10),
        retired=False,
    )
    tt_bike = insert_gear(
        user_id=user_id,
        gear_type="bike",
        brand="Canyon",
        model="Speedmax CF",
        purchase_date=date(2025, 6, 5),
        retired=False,
    )
    pool_goggles = insert_gear(
        user_id=user_id,
        gear_type="goggles",
        brand="Speedo",
        model="Vanquisher 2.0",
        purchase_date=date(2025, 3, 1),
        retired=False,
    )
    wetsuit = insert_gear(
        user_id=user_id,
        gear_type="wetsuit",
        brand="Orca",
        model="Athlex",
        purchase_date=date(2025, 5, 20),
        retired=False,
    )

    gear_by_sport = {
        "run": [shoes_train, shoes_race],
        "bike": [road_bike, tt_bike],
        "swim": [pool_goggles, wetsuit],
    }

    print("Created demo gear:")
    for sport, gids in gear_by_sport.items():
        print(f"  {sport}: {gids}")

    return gear_by_sport


def random_time() -> str:
    """Return a random time string HH:MM (morning or afternoon)."""
    if random.random() < 0.5:
        hour = random.randint(6, 9)   # morning
    else:
        hour = random.randint(16, 19) # evening
    minute = random.choice([0, 15, 30, 45])
    return f"{hour:02d}:{minute:02d}"


def trending_workout_for_type(workout_type: str, week_index: int):
    # Growth factor: starts at ~1.0 and grows with weeks
    growth_factor = 1.0 + week_index * 0.10  # +10% per week

    if workout_type == "swim":
        # Base: 1–3 km, 20–60 minutes
        base_dist = random.uniform(1.0, 3.0)
        base_dur = random.randint(20, 60)

        distance_km = min(base_dist * growth_factor, 5.0)
        duration_minutes = min(base_dur * growth_factor, 120.0)

        # Swim-specific metrics
        elevation_gain_m = 0.0
        avg_cadence = random.uniform(25, 40)  # strokes per minute
        avg_power_w = None  # not really used for swim

    elif workout_type == "bike":
        # Base: 20–70 km, 60–180 minutes
        base_dist = random.uniform(20.0, 70.0)
        base_dur = random.randint(60, 180)

        distance_km = min(base_dist * growth_factor, 150.0)
        duration_minutes = min(base_dur * growth_factor, 360.0)

        # Bike-specific metrics
        elevation_gain_m = random.uniform(100, 2000)  # more climbing possible
        avg_cadence = random.uniform(75, 95)          # rpm
        # Tie power roughly to effort + growth
        base_power = random.uniform(140, 220)
        avg_power_w = min(base_power * (1.0 + 0.03 * week_index), 350.0)

    else:  # run
        # Base: 5–18 km, 30–100 minutes
        base_dist = random.uniform(5.0, 18.0)
        base_dur = random.randint(30, 100)

        distance_km = min(base_dist * growth_factor, 30.0)
        duration_minutes = min(base_dur * growth_factor, 180.0)

        # Run-specific metrics
        elevation_gain_m = random.uniform(50, 800)
        avg_cadence = random.uniform(155, 180)  # steps per minute
        avg_power_w = None  # you could fill this if you want running power

    duration_seconds = int(duration_minutes * 60)

    # Effort trends mildly up too but stays in a realistic range
    base_effort = random.randint(5, 8)
    effort_level = max(3, min(10, base_effort + week_index // 4))

    # Calories: rough estimate based on duration and effort
    # (not meant to be physiologically accurate, just plausible numbers)
    # Base kcal/min by sport:
    if workout_type == "swim":
        base_kcal_per_min = 9.0
    elif workout_type == "bike":
        base_kcal_per_min = 8.0
    else:  # run
        base_kcal_per_min = 11.0

    calories_kcal = int(duration_minutes * base_kcal_per_min * (0.9 + 0.02 * effort_level))

    # Heart rate: tie to effort level
    if workout_type == "swim":
        hr_base = 120
    elif workout_type == "bike":
        hr_base = 125
    else:  # run
        hr_base = 130

    avg_heart_rate_bpm = int(
        hr_base + 5 * (effort_level - 5) + random.uniform(-5, 5)
    )
    avg_heart_rate_bpm = max(100, min(avg_heart_rate_bpm, 190))

    return (
        duration_seconds,
        round(distance_km, 1),
        effort_level,
        round(elevation_gain_m, 1),
        calories_kcal,
        avg_heart_rate_bpm,
        round(avg_cadence, 1),
        avg_power_w,
    )


def choose_gear_for_workout(workout_type: str, gear_by_sport: dict[str, list[int]]) -> list[int]:
    """
    Choose a list of gear_ids appropriate for this workout type.
    We keep it simple but plausible.
    """
    gear_ids: list[int] = []

    sport_gear = gear_by_sport.get(workout_type, [])
    if not sport_gear:
        return gear_ids

    if workout_type == "run":
        # Use one pair of shoes (training or race)
        gear_ids.append(random.choice(sport_gear))
    elif workout_type == "bike":
        # Usually one bike; occasionally use a different bike
        gear_ids.append(random.choice(sport_gear))
    else:  # swim
        # Usually goggles, sometimes goggles + wetsuit
        goggles_id = sport_gear[0]
        gear_ids.append(goggles_id)
        if len(sport_gear) > 1 and random.random() < 0.3:
            gear_ids.append(sport_gear[1])

    return gear_ids


def repopulate_trending_workouts():
    user_id = get_user_id_by_username(USERNAME)
    if user_id is None:
        raise ValueError(
            f"User '{USERNAME}' not found. Make sure you ran seed_demo.py or created this user."
        )

    # 1. Clear existing data (workouts + gear) for this user
    clear_user_data(user_id)

    # 2. Create demo gear for this user
    gear_by_sport = create_demo_gear(user_id)

    # 3. Insert new trending workouts from Oct 1 to Dec 31, 2025
    start = date(2025, 10, 1)
    end = date(2025, 12, 31)

    current = start
    count = 0

    # For consistent experiments
    random.seed(341)

    while current <= end:
        days_from_start = (current - start).days
        week_index = days_from_start // 7  # 0,1,2,... increasing

        # Probability of any workouts on this day increases over time
        base_prob = 0.4 + min(0.02 * week_index, 0.3)  # up to 0.7
        if random.random() > base_prob:
            current += timedelta(days=1)
            continue

        # Number of workouts: mostly 1, sometimes 2 bricks, occasional 3 in heavy weeks
        probs = [0.7, 0.25, 0.05]  # for 1, 2, 3 workouts
        r = random.random()
        if r < probs[0]:
            num_workouts = 1
        elif r < probs[0] + probs[1]:
            num_workouts = 2
        else:
            num_workouts = 3

        # As weeks progress, slightly increase bias toward bike + long run
        swim_w = max(0.15, 0.25 - 0.005 * week_index)
        bike_w = min(0.50, 0.35 + 0.007 * week_index)
        run_w = 1.0 - swim_w - bike_w

        for _ in range(num_workouts):
            workout_type = random.choices(
                population=["swim", "bike", "run"],
                weights=[swim_w, bike_w, run_w],
                k=1,
            )[0]

            (
                duration_seconds,
                distance_km,
                effort_level,
                elevation_gain_m,
                calories_kcal,
                avg_hr,
                avg_cadence,
                avg_power_w,
            ) = trending_workout_for_type(workout_type, week_index)

            start_time_str = random_time()

            notes_options = {
                "swim": [
                    "Pool intervals",
                    "Easy endurance swim",
                    "Drills + technique",
                    "Tempo swim set",
                    "Open water simulation in pool",
                ],
                "bike": [
                    "Endurance ride",
                    "Intervals on trainer",
                    "Long ride outside",
                    "Hill repeats",
                    "Sweet spot workout",
                ],
                "run": [
                    "Easy run",
                    "Tempo run",
                    "Long run",
                    "Track workout",
                    "Brick run off the bike",
                ],
            }

            notes = random.choice(notes_options[workout_type])

            # Choose gear for this workout
            gear_ids = choose_gear_for_workout(workout_type, gear_by_sport)
            primary_gear_id = gear_ids[0] if gear_ids else None

            workout_id = insert_workout(
                user_id=user_id,
                workout_type_name=workout_type,
                workout_date=current,
                duration_seconds=duration_seconds,
                distance_km=distance_km,
                effort_level=effort_level,
                location_id=None,
                start_time=start_time_str,
                elevation_gain_m=elevation_gain_m,
                calories_kcal=calories_kcal,
                avg_heart_rate_bpm=avg_hr,
                avg_cadence=avg_cadence,
                avg_power_w=avg_power_w,
                gear_id=primary_gear_id,
                notes=notes,
            )

            # Attach all gear for this workout -> populates Workout_Gear (driving gear_distance view)
            attach_gear_to_workout(workout_id, gear_ids)

            count += 1
            print(
                f"{current} | {workout_type:4} | {distance_km:5.1f} km | "
                f"{duration_seconds//60:4d} min | eff {effort_level} | "
                f"HR {avg_hr} | gear {gear_ids} | id={workout_id}"
            )

        current += timedelta(days=1)

    print(f"\nDone. Inserted {count} workouts for user '{USERNAME}' with attached gear.")
    

if __name__ == "__main__":
    repopulate_trending_workouts()
