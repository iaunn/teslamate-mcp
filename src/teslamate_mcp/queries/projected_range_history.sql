SELECT c.name AS car_name,
    DATE_TRUNC('month', p.date) AS month,
    ROUND(
        AVG(
            p.rated_battery_range_km / NULLIF(COALESCE(p.usable_battery_level, p.battery_level), 0) * 100
        )::numeric,
        1
    ) AS projected_range_at_100pct_km,
    COUNT(*) AS data_points
FROM positions p
    JOIN cars c ON p.car_id = c.id
WHERE p.rated_battery_range_km IS NOT NULL
    AND COALESCE(p.usable_battery_level, p.battery_level) > 0 /* FILTERS */
GROUP BY c.id,
    c.name,
    DATE_TRUNC('month', p.date)
ORDER BY car_name,
    month;
