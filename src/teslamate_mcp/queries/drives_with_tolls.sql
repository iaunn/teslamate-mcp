SELECT v.drive_id,
    c.name AS car_name,
    TO_CHAR(v.start_bangkok_time, 'YYYY-MM-DD HH24:MI:SS') AS start_bangkok_time,
    TO_CHAR(v.end_bangkok_time, 'YYYY-MM-DD HH24:MI:SS') AS end_bangkok_time,
    v.start_location,
    v.end_location,
    ROUND(v.distance_km::numeric, 2) AS distance_km,
    v.duration_min,
    ROUND(v.energy_kwh::numeric, 2) AS energy_kwh,
    ROUND(v.kwh_rate::numeric, 2) AS kwh_rate,
    ROUND(v.electric_cost::numeric, 2) AS electric_cost,
    v.toll_count::int AS toll_count,
    ROUND(v.toll_cost::numeric, 2) AS toll_cost,
    ROUND(v.total_trip_cost::numeric, 2) AS total_trip_cost,
    ROUND(v.cost_per_km::numeric, 2) AS cost_per_km,
    v.plazas
FROM ledger.v_drives_with_tolls v
    JOIN cars c ON v.car_id = c.id
WHERE (NOT %(only_with_tolls)s::boolean OR v.toll_count > 0)
    AND (%(car_name)s::text IS NULL OR c.name ILIKE '%%' || %(car_name)s || '%%')
    AND (%(start_date)s::date IS NULL OR v.start_bangkok_time::date >= %(start_date)s::date)
    AND (%(end_date)s::date IS NULL OR v.start_bangkok_time::date <= %(end_date)s::date)
ORDER BY v.start_bangkok_time DESC
LIMIT %(limit)s::int;
