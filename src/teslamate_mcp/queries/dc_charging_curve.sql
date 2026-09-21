SELECT c.name AS car_name,
    ch.battery_level AS soc,
    ROUND(
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ch.charger_power)::numeric,
        0
    ) AS median_power_kw,
    COUNT(*) AS sample_count
FROM charges ch
    JOIN charging_processes cp ON cp.id = ch.charging_process_id
    JOIN cars c ON c.id = cp.car_id
WHERE ch.charger_power > 0
    AND ch.charger_power > 25
    AND (%(car_name)s::text IS NULL OR c.name ILIKE '%%' || %(car_name)s || '%%')
GROUP BY c.id,
    c.name,
    ch.battery_level
ORDER BY car_name,
    soc;
