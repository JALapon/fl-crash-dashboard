-- crashes_by_hour_dow.sql
--
-- Powers the "when do bad crashes happen?" heatmap (day-of-week x hour).
--
-- EDA finding: rows where CRASH_TIME = '0000' are a mix of genuine
-- midnight crashes and "time unknown" sentinels (~1.92x the volume of
-- hours 1-4). We exclude them here so the hour=0 bucket isn't poisoned.
-- The dashboard footnote should disclose this trim.
--
-- Expected row count: 7 days x 24 hours = 168 rows.

SELECT
    day_of_week,
    hour,
    COUNT(*) AS total
FROM crashes
WHERE NOT hour_is_ambiguous
GROUP BY day_of_week, hour
ORDER BY
    CASE day_of_week
        WHEN 'Monday'    THEN 1
        WHEN 'Tuesday'   THEN 2
        WHEN 'Wednesday' THEN 3
        WHEN 'Thursday'  THEN 4
        WHEN 'Friday'    THEN 5
        WHEN 'Saturday'  THEN 6
        WHEN 'Sunday'    THEN 7
    END,
    hour;
