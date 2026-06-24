WITH drive_seq AS (
    SELECT d.car_id,
        d.start_date,
        d.end_date,
        d.start_rated_range_km,
        d.end_rated_range_km,
        d.start_km,
        d.end_km
    FROM drives d
    WHERE true /* FILTERS */
),
parked AS (
    SELECT car_id,
        LAG(end_date) OVER w AS park_start,
        start_date AS park_end,
        LAG(end_rated_range_km) OVER w AS start_range,
        start_rated_range_km AS end_range,
        LAG(end_km) OVER w AS start_km,
        start_km AS end_km
    FROM drive_seq
    WINDOW w AS (PARTITION BY car_id ORDER BY start_date)
)
SELECT c.name AS car_name,
    p.park_start,
    p.park_end,
    ROUND((EXTRACT(EPOCH FROM (p.park_end - p.park_start)) / 3600)::numeric, 2) AS parked_hours,
    ROUND((p.start_range - p.end_range)::numeric, 1) AS rated_range_lost_km,
    ROUND(((p.start_range - p.end_range) * c.efficiency)::numeric, 2) AS energy_lost_kwh,
    ROUND(
        (
            (p.start_range - p.end_range) / NULLIF(EXTRACT(EPOCH FROM (p.park_end - p.park_start)) / 3600, 0)
        )::numeric,
        3
    ) AS range_lost_per_hour_km
FROM parked p
    JOIN cars c ON c.id = p.car_id
WHERE p.park_start IS NOT NULL
    AND EXTRACT(EPOCH FROM (p.park_end - p.park_start)) > 3600 -- parked at least an hour
    AND (p.start_range - p.end_range) >= 0 -- excludes intervals where charging happened
    AND (p.end_km - p.start_km) < 1 -- excludes any driving between the two records
ORDER BY p.park_start DESC;
