SELECT c.name AS car_name,
    d.start_date,
    d.end_date,
    d.duration_min,
    ROUND(d.distance::numeric, 2) AS distance_km,
    COALESCE(sg.name, sa.display_name) AS start_location,
    COALESCE(eg.name, ea.display_name) AS end_location,
    sp.battery_level AS start_battery_level,
    ep.battery_level AS end_battery_level,
    ROUND((d.start_rated_range_km - d.end_rated_range_km)::numeric, 1) AS rated_range_used_km,
    ROUND(((d.start_rated_range_km - d.end_rated_range_km) * c.efficiency)::numeric, 2) AS consumption_kwh,
    d.speed_max,
    d.power_max,
    ROUND(d.outside_temp_avg::numeric, 1) AS outside_temp_avg
FROM drives d
    JOIN cars c ON d.car_id = c.id
    LEFT JOIN addresses sa ON d.start_address_id = sa.id
    LEFT JOIN addresses ea ON d.end_address_id = ea.id
    LEFT JOIN geofences sg ON d.start_geofence_id = sg.id
    LEFT JOIN geofences eg ON d.end_geofence_id = eg.id
    LEFT JOIN positions sp ON d.start_position_id = sp.id
    LEFT JOIN positions ep ON d.end_position_id = ep.id
WHERE true /* FILTERS */
ORDER BY d.start_date DESC
LIMIT 100;
