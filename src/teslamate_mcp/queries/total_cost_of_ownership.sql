SELECT CASE %(group_by)s::text
        WHEN 'month' THEN TO_CHAR(DATE_TRUNC('month', v.bangkok_time), 'YYYY-MM')
        ELSE v.category
    END AS group_key,
    v.category,
    COUNT(*)::int AS tx_count,
    ROUND(SUM(v.cost)::numeric, 2) AS total_cost
FROM ledger.v_all_car_costs v
    LEFT JOIN cars c ON v.car_id = c.id
WHERE (%(car_name)s::text IS NULL OR c.name ILIKE '%%' || %(car_name)s || '%%')
    AND (%(start_date)s::date IS NULL OR v.bangkok_time::date >= %(start_date)s::date)
    AND (%(end_date)s::date IS NULL OR v.bangkok_time::date <= %(end_date)s::date)
GROUP BY 1, v.category
ORDER BY 1 DESC, total_cost DESC;
