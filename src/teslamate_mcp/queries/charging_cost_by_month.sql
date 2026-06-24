SELECT c.name AS car_name,
    DATE_TRUNC('month', cp.start_date) AS month,
    COUNT(*) AS sessions,
    ROUND(SUM(cp.charge_energy_added)::numeric, 2) AS energy_added_kwh,
    ROUND(SUM(COALESCE(cp.cost, 0))::numeric, 2) AS total_cost,
    ROUND(
        (
            SUM(cp.cost) / NULLIF(SUM(GREATEST(cp.charge_energy_added, cp.charge_energy_used)), 0)
        )::numeric,
        4
    ) AS avg_cost_per_kwh
FROM charging_processes cp
    JOIN cars c ON cp.car_id = c.id
WHERE cp.charge_energy_added > 0 /* FILTERS */
GROUP BY c.id,
    c.name,
    DATE_TRUNC('month', cp.start_date)
ORDER BY car_name,
    month DESC;
