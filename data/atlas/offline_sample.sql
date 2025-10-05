-- Offline atlas schema and seed data for testing and demos.
-- Generated from authoritative geocoding sources; values mirror those in tests.

BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS places (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    country TEXT,
    search_name TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    tzid TEXT NOT NULL,
    population INTEGER DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_places_search ON places(search_name);

INSERT OR REPLACE INTO places (name, country, search_name, latitude, longitude, tzid, population)
VALUES (
    'London, United Kingdom',
    'GB',
    'london united kingdom',
    51.5074,
    -0.1278,
    'Europe/London',
    8908081
);
COMMIT;
