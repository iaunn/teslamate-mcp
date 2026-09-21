WITH current_odo AS (
    SELECT c.id, c.name, MAX(p.odometer) AS current_odometer
    FROM positions p
    JOIN cars c ON p.car_id = c.id
    GROUP BY c.id, c.name
)
SELECT name AS car_name,
    ROUND(current_odometer::numeric, 0) AS current_odometer_km,
    ROUND((10000 - MOD(current_odometer::numeric, 10000)), 0) AS km_until_next_tire_rotation,
    ROUND((40000 - MOD(current_odometer::numeric, 40000)), 0) AS km_until_next_cabin_filter,
    ROUND((current_odometer / 10000 - 0.5)::numeric, 0) AS total_tire_rotations_due,
    ROUND((current_odometer / 40000 - 0.5)::numeric, 0) AS total_cabin_filters_due
FROM current_odo
WHERE (%(car_name)s::text IS NULL OR name ILIKE '%%' || %(car_name)s || '%%')
ORDER BY name;
