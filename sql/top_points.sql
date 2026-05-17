-- top_points.sql
--
-- Fatal crashes only, as individual map points. The full 134k+
-- crash dataset is too many points for Tableau Public to render
-- cleanly on a single map sheet, so we ship only fatals (~19k) as
-- the point layer. Counties + heatmaps cover the broader picture.
--
-- Ordering by (year, month) gives Tableau a stable load order for
-- any time-based animation/filtering.
--
-- Expected row count: ~19,105 (fatal crashes 2011-2018).

SELECT
    crash_id,
    year,
    month,
    day_of_week,
    hour,
    county,
    lat,
    lon,
    severity
FROM crashes
WHERE severity = 'Fatal'
ORDER BY year, month;
