WITH current_odo AS (
    SELECT c.id, c.name, MAX(p.odometer) AS current_odometer
    FROM positions p
    JOIN cars c ON p.car_id = c.id
    GROUP BY c.id, c.name
),
last_rotation AS (
    SELECT car_id, MAX(odometer_km) AS last_rotation_odo
    FROM ledger.car_expenses
    WHERE category = 'TIRE' AND title ILIKE '%%Rotation%%'
    GROUP BY car_id
)
SELECT o.name AS car_name,
    ROUND(o.current_odometer::numeric, 0) AS current_odometer_km,
    ROUND(COALESCE(r.last_rotation_odo, 0)::numeric, 0) AS last_tire_rotation_odometer_km,
    ROUND((o.current_odometer - COALESCE(r.last_rotation_odo, 0))::numeric, 0) AS km_since_last_tire_rotation,
    ROUND((10000 - (o.current_odometer - COALESCE(r.last_rotation_odo, 0)))::numeric, 0) AS km_until_next_tire_rotation,
    ROUND((40000 - MOD(o.current_odometer::numeric, 40000)), 0) AS km_until_next_cabin_filter,
    ROUND((o.current_odometer / 10000 - 0.5)::numeric, 0) AS total_tire_rotations_due,
    ROUND((o.current_odometer / 40000 - 0.5)::numeric, 0) AS total_cabin_filters_due
FROM current_odo o
LEFT JOIN last_rotation r ON r.car_id = o.id
WHERE (%(car_name)s::text IS NULL OR o.name ILIKE '%%' || %(car_name)s || '%%')
ORDER BY o.name;
