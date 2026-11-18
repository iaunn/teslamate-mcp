-- Current balance per Easy Pass card: the newest ledger row of each card.
-- easypass-mqtt-golang writes a row on every balance change (TOLL / TOPUP),
-- so balance_after of the latest row is the balance as of that change.
SELECT car_name,
    card_name,
    card_number,
    license_plate,
    balance,
    as_of,
    days_since_update,
    last_tx_type,
    last_amount,
    last_plaza,
    is_low
FROM (
    SELECT DISTINCT ON (t.card_number)
        c.name AS car_name,
        t.card_name,
        t.card_number,
        t.license_plate,
        ROUND(t.balance_after::numeric, 2) AS balance,
        TO_CHAR(t.transaction_time AT TIME ZONE %(tz)s::text, 'YYYY-MM-DD HH24:MI:SS') AS as_of,
        ROUND((EXTRACT(EPOCH FROM (now() - t.transaction_time)) / 86400)::numeric, 1) AS days_since_update,
        t.tx_type AS last_tx_type,
        ROUND(t.amount::numeric, 2) AS last_amount,
        t.plaza_name AS last_plaza,
        t.balance_after < %(low_balance)s::numeric AS is_low
    FROM ledger.toll_transactions t
        LEFT JOIN cars c ON t.car_id = c.id
    WHERE (%(car_name)s::text IS NULL OR c.name ILIKE '%%' || %(car_name)s || '%%')
        AND (%(card_name)s::text IS NULL OR t.card_name ILIKE '%%' || %(card_name)s || '%%')
    ORDER BY t.card_number, t.transaction_time DESC, t.id DESC
) latest
ORDER BY days_since_update ASC, card_name;
