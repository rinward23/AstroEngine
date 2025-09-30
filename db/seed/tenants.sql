INSERT INTO tenants (id, name, quota_scans_per_day, quota_concurrent_jobs)
VALUES
  ('00000000-0000-0000-0000-000000000001', 'AstroEngine Demo', 1000, 5)
ON CONFLICT (id) DO UPDATE
SET name = EXCLUDED.name,
    quota_scans_per_day = EXCLUDED.quota_scans_per_day,
    quota_concurrent_jobs = EXCLUDED.quota_concurrent_jobs;
