SELECT c.name AS car_name,
    s.state,
    COUNT(*) AS occurrences,
    ROUND((SUM(EXTRACT(EPOCH FROM (COALESCE(s.end_date, CURRENT_TIMESTAMP) - s.start_date))) / 3600)::numeric, 1) AS total_hours
FROM states s
    JOIN cars c ON s.car_id = c.id
WHERE s.state IN ('sentry', 'sentry_mode', 'online', 'asleep', 'suspended')
    AND s.start_date >= CURRENT_DATE - make_interval(days => %(days)s::int)
    AND (%(car_name)s::text IS NULL OR c.name ILIKE '%%' || %(car_name)s || '%%')
GROUP BY c.name, s.state
ORDER BY c.name, total_hours DESC;
