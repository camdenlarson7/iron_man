# app/app.py

import streamlit as st
import pandas as pd
from datetime import date, timedelta
import altair as alt


from queries import (
    get_user_id_by_username,
    insert_workout,
    get_weekly_volume_by_sport,
    get_total_distance_per_gear,
    fetch_workouts,              
    fetch_run_workouts_view,     
    fetch_bike_workouts_view,    
    fetch_swim_workouts_view,
    insert_gear,
    attach_gear_to_workout,    
    get_total_distance_per_gear,
    list_users
)

def format_pace(seconds: float | int | None) -> str:
    if seconds is None:
        return ""
    try:
        s = int(seconds)
    except (TypeError, ValueError):
        return ""
    minutes = s // 60
    sec = s % 60
    return f"{minutes}:{sec:02d}"



def main():
    st.set_page_config(page_title="IronTrack", layout="wide")
    st.title("IronTrack – Ironman Triathlon Training Tracker")

    # Sidebar: choose user from DB
    st.sidebar.header("User")

    users = list_users()
    if not users:
        st.sidebar.error("No users found in the database. Seed or create a user first.")
        st.write("No users in the database. Run seed_demo.py or insert a user manually.")
        return

    # users: list of (user_id, username)
    username_to_id = {u[1]: u[0] for u in users}
    usernames = list(username_to_id.keys())

    selected_username = st.sidebar.selectbox(
        "Username",
        options=usernames,
        index=0,  # default to first user, usually 'cam'
    )
    user_id = username_to_id[selected_username]
    st.sidebar.caption(f"Logged in as {selected_username}")

    # Navigation
    st.sidebar.header("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["Dashboard", "View Workouts", "Add Workout", "Gear"],
    )

    # Page routing
    if page == "Dashboard":
        render_dashboard(user_id)
    elif page == "View Workouts":
        render_view_workouts(user_id)
    elif page == "Add Workout":
        render_add_workout(user_id)
    elif page == "Gear":
        render_gear(user_id)


# Dashboard 

def render_dashboard(user_id: int):
    st.header("Dashboard – Weekly Training Volume")

    # Date range selector (default: last 8 weeks)
    today = date.today()
    default_start = today - timedelta(weeks=8)

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start date", value=default_start)
    with col2:
        end_date = st.date_input("End date", value=today)

    if start_date > end_date:
        st.error("Start date must be before end date.")
        return

    rows = get_weekly_volume_by_sport(user_id, start_date, end_date)
    if not rows:
        st.info("No workouts in this date range.")
        return

    df = pd.DataFrame(
        rows,
        columns=[
            "week_start",
            "workout_type",
            "total_distance_km",
            "total_duration_sec",
        ],
    )

    # Ensure types are correct for Altair
    df["week_start"] = pd.to_datetime(df["week_start"])
    df["total_distance_km"] = pd.to_numeric(df["total_distance_km"], errors="coerce")
    df["total_duration_sec"] = pd.to_numeric(df["total_duration_sec"], errors="coerce")
    df["total_duration_min"] = (df["total_duration_sec"] // 60).astype("Int64")
    df["total_duration_hours"] = df["total_duration_min"] / 60.0

    df = df.dropna(subset=["total_distance_km"])

    # Sport filter
        # Sport filter (checkboxes instead of dropdown)
    all_sports = sorted(df["workout_type"].unique())

    st.markdown("**Sports to show**")
    sport_cols = st.columns(len(all_sports))

    selected_sports = []
    for col, sport in zip(sport_cols, all_sports):
        with col:
            checked = st.checkbox(
                sport.capitalize(),
                value=True,
                key=f"sport_{sport}",
            )
            if checked:
                selected_sports.append(sport)

    if not selected_sports:
        st.info("Select at least one sport to display.")
        return

    df_filtered = df[df["workout_type"].isin(selected_sports)]
    if df_filtered.empty:
        st.info("No workouts for the selected sports in this date range.")
        return


    if not selected_sports:
        st.info("Select at least one sport to display.")
        return

    df_filtered = df[df["workout_type"].isin(selected_sports)]
    if df_filtered.empty:
        st.info("No workouts for the selected sports in this date range.")
        return

    # Summary cards: total distance per selected sport
    summary = (
        df_filtered.groupby("workout_type")["total_distance_km"]
        .sum()
        .reset_index()
        .sort_values("workout_type")
    )
    st.subheader("Total Distance by Sport")
    cols = st.columns(len(summary))
    for col, (_, row) in zip(cols, summary.iterrows()):
        with col:
            st.metric(
                label=row["workout_type"].capitalize(),
                value=f"{row['total_distance_km']:.1f} km",
            )

    # Side-by-side charts 
    left_col, right_col = st.columns(2)

    # Left: Weekly Distance 
    with left_col:
        st.markdown("**Weekly Distance (km)**")

        max_dist = df_filtered["total_distance_km"].max()
        if pd.isna(max_dist) or max_dist <= 0:
            st.info("No positive distance values to plot.")
        else:
            y_max_dist = max(1.0, float(max_dist) * 1.1)

            distance_chart = (
                alt.Chart(df_filtered)
                .mark_line(point=True)
                .encode(
                    x=alt.X("week_start:T", title="Week starting"),
                    y=alt.Y(
                        "total_distance_km:Q",
                        title="Distance (km)",
                        scale=alt.Scale(domain=[0, y_max_dist]),
                    ),
                    color=alt.Color("workout_type:N", title="Sport"),
                    tooltip=[
                        alt.Tooltip("week_start:T", title="Week"),
                        alt.Tooltip("workout_type:N", title="Sport"),
                        alt.Tooltip(
                            "total_distance_km:Q", title="Distance (km)", format=".1f"
                        ),
                        alt.Tooltip(
                            "total_duration_min:Q", title="Duration (min)"
                        ),
                    ],
                )
                .properties(height=350)
            )

            st.altair_chart(distance_chart, width="stretch")

    # Right: Weekly Time 
    with right_col:
        st.markdown("**Weekly Time (hours)**")

        max_hours = df_filtered["total_duration_hours"].max()
        if pd.isna(max_hours) or max_hours <= 0:
            st.info("No positive duration values to plot.")
        else:
            y_max_hours = max(0.5, float(max_hours) * 1.1)

            time_chart = (
                alt.Chart(df_filtered)
                .mark_line(point=True)
                .encode(
                    x=alt.X("week_start:T", title="Week starting"),
                    y=alt.Y(
                        "total_duration_hours:Q",
                        title="Duration (hours)",
                        scale=alt.Scale(domain=[0, y_max_hours]),
                    ),
                    color=alt.Color("workout_type:N", title="Sport"),
                    tooltip=[
                        alt.Tooltip("week_start:T", title="Week"),
                        alt.Tooltip("workout_type:N", title="Sport"),
                        alt.Tooltip(
                            "total_duration_hours:Q", title="Duration (h)", format=".2f"
                        ),
                        alt.Tooltip(
                            "total_duration_min:Q", title="Duration (min)"
                        ),
                    ],
                )
                .properties(height=350)
            )

            st.altair_chart(time_chart, width="stretch")


# View Workouts

def render_view_workouts(user_id: int):
    st.header("View Workouts")

    # Filter controls
    col1, col2 = st.columns(2)
    with col1:
        workout_scope = st.radio(
            "Workout type",
            options=["All", "Run", "Bike", "Swim"],
            horizontal=True,
        )
    with col2:
        # Optional date range filter
        today = date.today()
        start_default = today.replace(month=10, day=1) if today.year == 2025 else today - timedelta(weeks=8)
        start_date = st.date_input("Start date", value=start_default)
        end_date = st.date_input("End date", value=today)

    if start_date > end_date:
        st.error("Start date must be before end date.")
        return

    # Query based on selected scope
    if workout_scope == "All":
        # Base workouts table via existing fetch_workouts()
        rows = fetch_workouts(
            user_id=user_id,
            workout_type_name=None,
            start_date=start_date,
            end_date=end_date,
        )
        if not rows:
            st.info("No workouts found for this range.")
            return

        df = pd.DataFrame(
            rows,
            columns=[
                "workout_id",
                "workout_date",
                "start_time",
                "workout_type",
                "distance_km",
                "duration_seconds",
                "effort_level",
                "notes",
            ],
        )
        df["duration_min"] = (df["duration_seconds"] // 60).astype(int)

        st.subheader("All Workouts (base table)")
        st.dataframe(
            df[
                [
                    "workout_date",
                    "start_time",
                    "workout_type",
                    "distance_km",
                    "duration_min",
                    "effort_level",
                    "notes",
                ]
            ],
            width="stretch",
        )

    elif workout_scope == "Run":
        rows = fetch_run_workouts_view(user_id, start_date, end_date)
        if not rows:
            st.info("No run workouts found for this range.")
            return

        df = pd.DataFrame(
            rows,
            columns=[
                "workout_id",
                "workout_date",
                "start_time",
                "distance_miles",
                "duration_seconds",
                "pace_seconds_per_mile",
                "elevation_gain_m",
                "calories_kcal",
                "avg_heart_rate_bpm",
                "avg_cadence_spm",
                "effort_level",
                "notes",
            ],
        )
        df["duration_min"] = (df["duration_seconds"] // 60).astype(int)
        df["pace_min_per_mile"] = df["pace_seconds_per_mile"].apply(format_pace)

        st.subheader("Run Workouts (run_workouts view)")
        st.dataframe(
            df[
                [
                    "workout_date",
                    "start_time",
                    "distance_miles",
                    "duration_min",
                    "pace_min_per_mile",
                    "elevation_gain_m",
                    "avg_heart_rate_bpm",
                    "avg_cadence_spm",
                    "effort_level",
                    "notes",
                ]
            ],
            width="stretch",
        )

    elif workout_scope == "Bike":
        rows = fetch_bike_workouts_view(user_id, start_date, end_date)
        if not rows:
            st.info("No bike workouts found for this range.")
            return

        df = pd.DataFrame(
            rows,
            columns=[
                "workout_id",
                "workout_date",
                "start_time",
                "distance_miles",
                "duration_seconds",
                "speed_mph",
                "elevation_gain_m",
                "calories_kcal",
                "avg_heart_rate_bpm",
                "avg_cadence_rpm",
                "avg_power_w",
                "effort_level",
                "notes",
            ],
        )
        df["duration_min"] = (df["duration_seconds"] // 60).astype(int)

        st.subheader("Bike Workouts (bike_workouts view)")
        st.dataframe(
            df[
                [
                    "workout_date",
                    "start_time",
                    "distance_miles",
                    "duration_min",
                    "speed_mph",
                    "elevation_gain_m",
                    "avg_heart_rate_bpm",
                    "avg_cadence_rpm",
                    "avg_power_w",
                    "effort_level",
                    "notes",
                ]
            ],
            width="stretch",
        )

    else:  # Swim
        rows = fetch_swim_workouts_view(user_id, start_date, end_date)
        if not rows:
            st.info("No swim workouts found for this range.")
            return

        df = pd.DataFrame(
            rows,
            columns=[
                "workout_id",
                "workout_date",
                "start_time",
                "distance_yards",
                "duration_seconds",
                "pace_seconds_per_100yd",
                "calories_kcal",
                "avg_heart_rate_bpm",
                "effort_level",
                "notes",
            ],
        )
        df["duration_min"] = (df["duration_seconds"] // 60).astype(int)
        df["pace_min_per_100yd"] = df["pace_seconds_per_100yd"].apply(format_pace)

        st.subheader("Swim Workouts (swim_workouts view)")
        st.dataframe(
            df[
                [
                    "workout_date",
                    "start_time",
                    "distance_yards",
                    "duration_min",
                    "pace_min_per_100yd",
                    "avg_heart_rate_bpm",
                    "effort_level",
                    "notes",
                ]
            ],
            width="stretch",
        )


# Add Workout
def render_add_workout(user_id: int):
    st.header("Add Workout")

    # Load gear list for this user (for selection later)
    gear_rows = get_total_distance_per_gear(user_id)
    # gear_rows: (gear_id, gear_type, brand, model, total_distance_km)
    gear_map = {row[0]: row for row in gear_rows}

    with st.form("add_workout_form"):
        col_left, col_right = st.columns(2)

        with col_left:
            workout_type = st.radio(
                "Workout type",
                options=["swim", "bike", "run"],
                horizontal=True,
            )

            workout_date = st.date_input(
                "Workout date",
                value=date.today(),
            )

            start_time_str = st.text_input(
                "Start time (HH:MM)",
                value="07:00",
                help="Optional; leave blank if unknown.",
            )

            duration_minutes = st.number_input(
                "Duration (minutes)",
                min_value=1,
                max_value=600,
                value=60,
                step=5,
            )

            distance_km = st.number_input(
                "Distance (km)",
                min_value=0.0,
                max_value=500.0,
                value=5.0,
                step=0.1,
            )

        with col_right:
            effort_level = st.slider(
                "Effort level (1–10)",
                min_value=1,
                max_value=10,
                value=6,
            )

            elevation_gain_m = st.number_input(
                "Elevation gain (m)",
                min_value=0.0,
                max_value=5000.0,
                value=0.0,
                step=10.0,
                help="Optional; more relevant for bike/run.",
            )

            calories_kcal = st.number_input(
                "Calories (kcal)",
                min_value=0,
                max_value=10000,
                value=0,
                step=10,
                help="Optional; leave 0 if unknown.",
            )

            avg_hr = st.number_input(
                "Avg heart rate (bpm)",
                min_value=0,
                max_value=250,
                value=0,
                step=1,
                help="Optional; leave 0 if you didn’t record HR.",
            )

        st.markdown("#### Advanced metrics (optional)")

        cad_label = {
            "swim": "Avg cadence (strokes / min)",
            "bike": "Avg cadence (rpm)",
            "run": "Avg cadence (steps / min)",
        }[workout_type]

        avg_cadence = st.number_input(
            cad_label,
            min_value=0.0,
            max_value=300.0,
            value=0.0,
            step=1.0,
            help="Optional; leave 0 if unknown.",
        )

        avg_power_w = None
        avg_power_w_val = 0.0
        if workout_type == "bike":
            avg_power_w_val = st.number_input(
                "Avg power (W)",
                min_value=0.0,
                max_value=800.0,
                value=0.0,
                step=5.0,
                help="Optional; leave 0 if unknown.",
            )

        # ---------- Gear selection ----------
        st.markdown("#### Gear used (optional)")

        if gear_map:
            selected_gear_ids = st.multiselect(
                "Select gear used for this workout",
                options=list(gear_map.keys()),
                format_func=lambda gid: (
                    f"{gear_map[gid][1]} - "
                    f"{(gear_map[gid][2] or '').strip()} "
                    f"{(gear_map[gid][3] or '').strip()} "
                    f"({gear_map[gid][4]:.1f} km total)"
                ),
                help="You can select multiple items (e.g., bike + shoes).",
            )
        else:
            st.info("No gear found yet. Add gear in the Gear tab.")
            selected_gear_ids = []

        notes = st.text_area(
            "Notes",
            placeholder="Easy long run, brick off the bike, intervals, etc.",
        )

        submitted = st.form_submit_button("Save workout")

    if submitted:
        duration_seconds = int(duration_minutes * 60)

        # Treat 0 values for optional metrics as None
        elevation_val = elevation_gain_m if elevation_gain_m > 0 else None
        calories_val = calories_kcal if calories_kcal > 0 else None
        hr_val = avg_hr if avg_hr > 0 else None
        cadence_val = avg_cadence if avg_cadence > 0 else None
        power_val = avg_power_w_val if (workout_type == "bike" and avg_power_w_val > 0) else None

        start_time_clean = start_time_str.strip() or None
        notes_clean = notes.strip() or None

        # Use the first selected gear as the "primary" gear_id in Workouts
        primary_gear_id = selected_gear_ids[0] if selected_gear_ids else None

        try:
            workout_id = insert_workout(
                user_id=user_id,
                workout_type_name=workout_type,
                workout_date=workout_date,
                duration_seconds=duration_seconds,
                distance_km=distance_km,
                effort_level=effort_level,
                location_id=None,
                start_time=start_time_clean,
                elevation_gain_m=elevation_val,
                calories_kcal=calories_val,
                avg_heart_rate_bpm=hr_val,
                avg_cadence=cadence_val,
                avg_power_w=power_val,
                gear_id=primary_gear_id,
                notes=notes_clean,
            )

            # Attach all selected gear via the Workout_Gear table (for gear_distance view)
            attach_gear_to_workout(workout_id, selected_gear_ids)

        except Exception as e:
            st.error(f"Error inserting workout: {e}")
        else:
            st.success(f"Workout saved (id={workout_id})")


# Gear

def render_gear(user_id: int):
    st.header("Gear")

    # Add new gear form
    with st.form("add_gear_form"):
        st.subheader("Add new gear")

        gear_type = st.selectbox(
            "Gear type",
            options=["shoe", "bike", "wetsuit", "goggles", "other"],
        )

        brand = st.text_input("Brand", placeholder="Nike, Trek, Speedo, etc.")
        model = st.text_input("Model", placeholder="Pegasus 41, Domane SL6, etc.")
        purchase_date = st.date_input("Purchase date", value=date.today())
        retired = st.checkbox("Retired", value=False)

        submit_gear = st.form_submit_button("Add gear")

    if submit_gear:
        try:
            gear_id = insert_gear(
                user_id=user_id,
                gear_type=gear_type,
                brand=brand.strip() or None,
                model=model.strip() or None,
                purchase_date=purchase_date,
                retired=retired,
            )
        except Exception as e:
            st.error(f"Error inserting gear: {e}")
        else:
            st.success(f"Gear added (id={gear_id})")

    st.markdown("---")

    # --------- Gear distance view ---------
    st.subheader("Gear usage (from gear_distance view)")

    rows = get_total_distance_per_gear(user_id)
    if not rows:
        st.info("No gear found yet.")
        return

    df = pd.DataFrame(
        rows,
        columns=["gear_id", "gear_type", "brand", "model", "total_distance_km"],
    )
    df["label"] = (
        df["gear_type"]
        + " - "
        + df["brand"].fillna("")
        + " "
        + df["model"].fillna("")
    ).str.strip()

    st.dataframe(
        df[
            ["gear_id", "label", "total_distance_km"]
        ].rename(columns={"label": "gear", "total_distance_km": "total_distance_km"}),
        use_container_width=True,
    )

if __name__ == "__main__":
    main()
