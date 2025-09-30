-- Enable row level security for tenants
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE charts ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON charts
USING (tenant_id = current_setting('app.current_tenant')::uuid);

GRANT USAGE ON SCHEMA public TO tenant_viewer;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO tenant_viewer;
