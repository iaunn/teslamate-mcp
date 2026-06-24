SELECT c.name AS car_name,
    s.state,
    COUNT(*) AS occurrences,
    ROUND(
        (SUM(EXTRACT(EPOCH FROM (COALESCE(s.end_date, s.start_date) - s.start_date))) / 3600)::numeric,
        1
    ) AS total_hours
FROM states s
    JOIN cars c ON c.id = s.car_id
WHERE true /* FILTERS */
GROUP BY c.id,
    c.name,
    s.state
ORDER BY car_name,
    total_hours DESC;
