SELECT c.name AS car_name,
    s.state,
    COUNT(*) AS occurrences,
    ROUND(
        (SUM(EXTRACT(EPOCH FROM (COALESCE(s.end_date, s.start_date) - s.start_date))) / 3600)::numeric,
        1
    ) AS total_hours
FROM states s
    JOIN cars c ON c.id = s.car_id
WHERE (%(car_name)s::text IS NULL OR c.name ILIKE '%%' || %(car_name)s || '%%')
    AND s.start_date >= CURRENT_DATE - make_interval(days => %(days)s::int)
GROUP BY c.id,
    c.name,
    s.state
ORDER BY car_name,
    total_hours DESC;
