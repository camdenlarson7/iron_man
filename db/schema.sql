-- db/schema.sql

DROP TABLE IF EXISTS Workout_Gear;
DROP TABLE IF EXISTS Workouts;
DROP TABLE IF EXISTS Gear;
DROP TABLE IF EXISTS Locations;
DROP TABLE IF EXISTS Workout_Types;
DROP TABLE IF EXISTS Users;

CREATE TABLE Users (
    user_id         SERIAL PRIMARY KEY,
    username        VARCHAR(50) UNIQUE NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE Workout_Types (
    workout_type_id SERIAL PRIMARY KEY,
    name            VARCHAR(20) UNIQUE NOT NULL
);

CREATE TABLE Locations (
    location_id   SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    location_type VARCHAR(20) NOT NULL
        CHECK (location_type IN ('pool', 'road', 'trail', 'track', 'indoor', 'other')),
    city          VARCHAR(100),
    state         VARCHAR(100)
);

CREATE TABLE Gear (
    gear_id       SERIAL PRIMARY KEY,
    user_id       INT NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    gear_type     VARCHAR(20) NOT NULL
        CHECK (gear_type IN ('shoe', 'bike', 'wetsuit', 'other')),
    brand         VARCHAR(100) NOT NULL,
    model         VARCHAR(100) NOT NULL,
    purchase_date DATE,
    retired       BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE Workouts (
    workout_id              SERIAL PRIMARY KEY,
    user_id                 INT NOT NULL REFERENCES Users(user_id) ON DELETE CASCADE,
    workout_type_id         INT NOT NULL REFERENCES Workout_Types(workout_type_id),
    location_id             INT REFERENCES Locations(location_id),
    workout_date            DATE NOT NULL,
    start_time              TIME,
    duration_seconds        INT NOT NULL CHECK (duration_seconds > 0),
    distance_km             NUMERIC(6,2) CHECK (distance_km >= 0),
    avg_pace_seconds_per_km INT,
    effort_level            INT CHECK (effort_level BETWEEN 1 AND 10),
    notes                   TEXT
);

CREATE TABLE Workout_Gear (
    workout_id INT NOT NULL REFERENCES Workouts(workout_id) ON DELETE CASCADE,
    gear_id    INT NOT NULL REFERENCES Gear(gear_id) ON DELETE CASCADE,
    PRIMARY KEY (workout_id, gear_id)
);

-- Seed the three sports
INSERT INTO Workout_Types (name) VALUES ('swim'), ('bike'), ('run')
ON CONFLICT (name) DO NOTHING;
