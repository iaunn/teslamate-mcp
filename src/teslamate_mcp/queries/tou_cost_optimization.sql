SELECT c.name AS car_name,
    COUNT(*) AS charging_sessions,
    ROUND(SUM(cp.charge_energy_added)::numeric, 2) AS total_energy_kwh,
    ROUND(SUM(COALESCE(cp.cost, 0))::numeric, 2) AS actual_cost,
    ROUND((SUM(cp.charge_energy_added) * %(off_peak_rate)s)::numeric, 2) AS optimal_cost,
    ROUND((SUM(COALESCE(cp.cost, 0)) - (SUM(cp.charge_energy_added) * %(off_peak_rate)s))::numeric, 2) AS potential_savings
FROM charging_processes cp
    JOIN cars c ON cp.car_id = c.id
    LEFT JOIN addresses a ON cp.address_id = a.id
WHERE (%(car_name)s::text IS NULL OR c.name ILIKE '%%' || %(car_name)s || '%%')
    AND cp.start_date >= CURRENT_DATE - make_interval(days => %(days)s::int)
    AND (a.display_name ILIKE '%%home%%' OR a.display_name ILIKE '%%บ้าน%%')
GROUP BY c.name
ORDER BY c.name;
