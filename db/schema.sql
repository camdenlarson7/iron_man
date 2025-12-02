-- ---------- Drop in dependency order ----------
DROP VIEW IF EXISTS gear_distance;
DROP VIEW IF EXISTS swim_workouts;
DROP VIEW IF EXISTS bike_workouts;
DROP VIEW IF EXISTS run_workouts;

DROP TABLE IF EXISTS Workout_Gear;
DROP TABLE IF EXISTS Workouts;
DROP TABLE IF EXISTS Gear;
DROP TABLE IF EXISTS Locations;
DROP TABLE IF EXISTS Workout_Types;
DROP TABLE IF EXISTS Users;

-- ---------- Users ----------
CREATE TABLE Users (
    user_id       SERIAL PRIMARY KEY,
    username      VARCHAR(50) UNIQUE NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------- Workout types (swim / bike / run) ----------
CREATE TABLE Workout_Types (
    workout_type_id SERIAL PRIMARY KEY,
    name            VARCHAR(20) UNIQUE NOT NULL
);

-- ---------- Locations ----------
-- location_type expanded to: pool, fresh water, salt water, road, trail, track, indoor, other
CREATE TABLE Locations (
    location_id   SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    location_type VARCHAR(20) NOT NULL
        CHECK (location_type IN (
            'pool',
            'fresh_water',
            'salt_water',
            'road',
            'trail',
            'track',
            'indoor',
            'other'
        )),
    city          VARCHAR(100),
    state         VARCHAR(100)
);

-- ---------- Gear ----------
-- brand/model can be NULL
CREATE TABLE Gear (
    gear_id       SERIAL PRIMARY KEY,
    user_id       INT NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    gear_type     VARCHAR(20) NOT NULL
        CHECK (gear_type IN ('shoe', 'bike', 'wetsuit', 'goggles', 'other')),
    brand         VARCHAR(100),
    model         VARCHAR(100),
    purchase_date DATE,
    retired       BOOLEAN NOT NULL DEFAULT FALSE
);

-- ---------- Workouts ----------
-- Canonical units:
--   distance_m           -> meters
--   duration_seconds     -> seconds
--   elevation_gain_m     -> meters
--   calories_kcal        -> kcal
--   avg_heart_rate_bpm   -> beats per minute
CREATE TABLE Workouts (
    workout_id            SERIAL PRIMARY KEY,
    user_id               INT NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    workout_type_id       INT NOT NULL REFERENCES Workout_Types(workout_type_id),
    location_id           INT REFERENCES Locations(location_id),

    workout_date          DATE NOT NULL,
    start_time            TIME,

    duration_seconds      INT NOT NULL CHECK (duration_seconds > 0),
    distance_m            NUMERIC(8,2) CHECK (distance_m >= 0),
    elevation_gain_m      NUMERIC(6,2) CHECK (elevation_gain_m >= 0),
    calories_kcal         INT CHECK (calories_kcal >= 0),

    avg_heart_rate_bpm    INT CHECK (avg_heart_rate_bpm BETWEEN 30 AND 250),

    -- cadence: steps/min (run) or rev/min (bike); NULL for swim if you want
    avg_cadence           NUMERIC(6,2) CHECK (avg_cadence >= 0),

    -- power: only really used for bike; NULL for others
    avg_power_w           NUMERIC(6,2) CHECK (avg_power_w >= 0),

    effort_level          INT CHECK (effort_level BETWEEN 1 AND 10),

    -- Optional primary gear item for quick lookups
    gear_id               INT REFERENCES Gear(gear_id),

    notes                 TEXT
);

-- ---------- Workout_Gear ----------
-- Many-to-many mapping between workouts and gear
CREATE TABLE Workout_Gear (
    workout_id INT NOT NULL REFERENCES Workouts(workout_id) ON DELETE CASCADE,
    gear_id    INT NOT NULL REFERENCES Gear(gear_id) ON DELETE CASCADE,
    PRIMARY KEY (workout_id, gear_id)
);

-- ---------- Seed base workout types ----------
INSERT INTO Workout_Types (name) VALUES ('swim'), ('bike'), ('run')
ON CONFLICT (name) DO NOTHING;

-- ===========================================================
--   Sport-specific views with sport-specific units & metrics
-- ===========================================================

-- ---------- Run workouts view ----------
-- Distance: miles
-- Pace: seconds per mile
CREATE VIEW run_workouts AS
SELECT
    w.workout_id,
    w.user_id,
    w.workout_date,
    w.start_time,
    w.duration_seconds,
    (w.distance_m / 1609.34) AS distance_miles,
    CASE
        WHEN w.distance_m IS NOT NULL AND w.distance_m > 0
            THEN w.duration_seconds / (w.distance_m / 1609.34)
        ELSE NULL
    END AS pace_seconds_per_mile,
    w.elevation_gain_m,
    w.calories_kcal,
    w.avg_heart_rate_bpm,
    w.avg_cadence       AS avg_cadence_spm,
    w.effort_level,
    w.location_id,
    w.gear_id,
    w.notes
FROM Workouts w
JOIN Workout_Types t
  ON w.workout_type_id = t.workout_type_id
WHERE t.name = 'run';

-- ---------- Bike workouts view ----------
-- Distance: miles
-- Pace: mph
CREATE VIEW bike_workouts AS
SELECT
    w.workout_id,
    w.user_id,
    w.workout_date,
    w.start_time,
    w.duration_seconds,
    (w.distance_m / 1609.34) AS distance_miles,
    CASE
        WHEN w.duration_seconds IS NOT NULL AND w.duration_seconds > 0
            THEN (w.distance_m / 1609.34) / (w.duration_seconds / 3600.0)
        ELSE NULL
    END AS speed_mph,
    w.elevation_gain_m,
    w.calories_kcal,
    w.avg_heart_rate_bpm,
    w.avg_cadence       AS avg_cadence_rpm,
    w.avg_power_w,
    w.effort_level,
    w.location_id,
    w.gear_id,
    w.notes
FROM Workouts w
JOIN Workout_Types t
  ON w.workout_type_id = t.workout_type_id
WHERE t.name = 'bike';

-- ---------- Swim workouts view ----------
-- Distance: yards
-- Pace: seconds per 100 yd
CREATE VIEW swim_workouts AS
SELECT
    w.workout_id,
    w.user_id,
    w.workout_date,
    w.start_time,
    w.duration_seconds,
    (w.distance_m / 0.9144) AS distance_yards,
    CASE
        WHEN w.distance_m IS NOT NULL AND w.distance_m > 0
        THEN w.duration_seconds / ((w.distance_m / 0.9144) / 100.0)
        ELSE NULL
    END AS pace_seconds_per_100yd,
    w.calories_kcal,
    w.avg_heart_rate_bpm,
    w.effort_level,
    w.location_id,
    w.gear_id,
    w.notes
FROM Workouts w
JOIN Workout_Types t
  ON w.workout_type_id = t.workout_type_id
WHERE t.name = 'swim';

-- ===========================================================
--   Gear distance view
-- ===========================================================
CREATE VIEW gear_distance AS
SELECT
    g.gear_id,
    g.user_id,
    g.gear_type,
    g.brand,
    g.model,
    COALESCE(SUM(w.distance_m), 0) AS total_distance_m
FROM Gear g
LEFT JOIN Workout_Gear wg
    ON wg.gear_id = g.gear_id
LEFT JOIN Workouts w
    ON w.workout_id = wg.workout_id
GROUP BY
    g.gear_id, g.user_id, g.gear_type, g.brand, g.model;
