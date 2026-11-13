SELECT t.id AS transaction_id,
    c.name AS car_name,
    t.card_name,
    t.card_number,
    TO_CHAR(t.transaction_time AT TIME ZONE %(tz)s::text, 'YYYY-MM-DD HH24:MI:SS') AS transaction_time,
    t.tx_type,
    t.plaza_name,
    t.lane,
    ROUND(t.amount::numeric, 2) AS amount,
    ROUND(t.balance_before::numeric, 2) AS balance_before,
    ROUND(t.balance_after::numeric, 2) AS balance_after,
    t.drive_id,
    ROUND(t.odometer_km::numeric, 2) AS odometer_km,
    t.location_hint
FROM ledger.toll_transactions t
    LEFT JOIN cars c ON t.car_id = c.id
WHERE (%(car_name)s::text IS NULL OR c.name ILIKE '%%' || %(car_name)s || '%%')
    AND (%(card_name)s::text IS NULL OR t.card_name ILIKE '%%' || %(card_name)s || '%%')
    AND (%(tx_type)s::text IS NULL OR t.tx_type = %(tx_type)s::text)
    AND (%(plaza)s::text IS NULL OR t.plaza_name ILIKE '%%' || %(plaza)s || '%%')
    AND (%(start_date)s::date IS NULL
        OR (t.transaction_time AT TIME ZONE %(tz)s::text)::date >= %(start_date)s::date)
    AND (%(end_date)s::date IS NULL
        OR (t.transaction_time AT TIME ZONE %(tz)s::text)::date <= %(end_date)s::date)
ORDER BY t.transaction_time DESC, t.id DESC
LIMIT %(limit)s::int;
