SELECT e.id AS expense_id,
    c.name AS car_name,
    TO_CHAR(e.expense_date, 'YYYY-MM-DD') AS expense_date,
    e.category,
    e.title,
    e.details,
    ROUND(e.cost::numeric, 2) AS cost,
    ROUND(e.odometer_km::numeric, 2) AS odometer_km,
    ROUND(e.latitude::numeric, 6) AS latitude,
    ROUND(e.longitude::numeric, 6) AS longitude,
    e.maps_url
FROM ledger.car_expenses e
    LEFT JOIN cars c ON e.car_id = c.id
WHERE (%(car_name)s::text IS NULL OR c.name ILIKE '%%' || %(car_name)s || '%%')
    AND (%(category)s::text IS NULL OR e.category ILIKE %(category)s)
    AND (%(start_date)s::date IS NULL OR e.expense_date >= %(start_date)s::date)
    AND (%(end_date)s::date IS NULL OR e.expense_date <= %(end_date)s::date)
ORDER BY e.expense_date DESC, e.id DESC
LIMIT %(limit)s::int;
