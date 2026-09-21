SELECT c.name AS car_name,
    COUNT(*) AS total_drives,
    ROUND(AVG(d.distance)::numeric, 1) AS avg_drive_distance_km,
    ROUND(MAX(d.speed_max)::numeric, 0) AS max_speed_recorded_kmh,
    COUNT(*) FILTER (WHERE d.speed_max > 120) AS drives_over_120_kmh,
    COUNT(*) FILTER (WHERE d.speed_max > 140) AS drives_over_140_kmh,
    ROUND(AVG(d.distance / NULLIF(d.start_rated_range_km - d.end_rated_range_km, 0))::numeric, 2) AS avg_efficiency
FROM drives d
    JOIN cars c ON d.car_id = c.id
WHERE (%(car_name)s::text IS NULL OR c.name ILIKE '%%' || %(car_name)s || '%%')
    AND d.start_date >= CURRENT_DATE - make_interval(days => %(days)s::int)
    AND d.distance > 2
GROUP BY c.name
ORDER BY c.name;
