SELECT
    COALESCE(a1.display_name, 'Unknown') AS start_location,
    COALESCE(a2.display_name, 'Unknown') AS end_location,
    COUNT(*) AS trip_count,
    ROUND(AVG(d.distance)::numeric, 1) AS avg_distance_km,
    ROUND(AVG(d.start_rated_range_km - d.end_rated_range_km)::numeric, 1) AS avg_range_used_km,
    ROUND(AVG(d.distance / NULLIF(d.start_rated_range_km - d.end_rated_range_km, 0))::numeric, 2) AS efficiency_factor,
    ROUND(AVG(d.duration_min)::numeric, 0) AS avg_duration_min
FROM drives d
    JOIN addresses a1 ON d.start_address_id = a1.id
    JOIN addresses a2 ON d.end_address_id = a2.id
    JOIN cars c ON d.car_id = c.id
WHERE (%(car_name)s::text IS NULL OR c.name ILIKE '%%' || %(car_name)s || '%%')
    AND d.start_address_id IS NOT NULL
    AND d.end_address_id IS NOT NULL
    AND d.distance > 5
    AND d.start_rated_range_km > d.end_rated_range_km
    AND (%(start_location)s::text IS NULL OR a1.display_name ILIKE '%%' || %(start_location)s || '%%')
    AND (%(end_location)s::text IS NULL OR a2.display_name ILIKE '%%' || %(end_location)s || '%%')
GROUP BY start_location, end_location
HAVING COUNT(*) >= %(min_trips)s::int
ORDER BY trip_count DESC
LIMIT %(limit)s::int;
