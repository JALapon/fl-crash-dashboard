-- severity_breakdown_by_county.sql
--
-- Top 20 FL counties by combined fatal + serious-injury crash volume,
-- with a fatal-share percentage. Powers the dashboard's stacked-bar
-- sheet ("which counties skew most fatal vs serious-injury?").
--
-- fatal_share_pct is useful precisely because it does NOT track raw
-- volume: a small county with a high fatal share is the kind of
-- finding the dashboard is designed to surface.
--
-- Expected row count: 20.

SELECT
    county,
    COUNT(*) FILTER (WHERE severity = 'Fatal')           AS fatal,
    COUNT(*) FILTER (WHERE severity = 'Serious injury')  AS serious_injury,
    COUNT(*)                                             AS total,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE severity = 'Fatal') / COUNT(*),
        1
    ) AS fatal_share_pct
FROM crashes
GROUP BY county
ORDER BY total DESC
LIMIT 20;
