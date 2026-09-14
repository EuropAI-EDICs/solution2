-- nLDT CDC source init (runs once on empty Postgres volume)
-- Logical replication enabled via compose command; publication for future slot consumers.
-- Outbox triggers generate CDC events for the lake capture script (DuckDB/Iceberg path).

CREATE TABLE IF NOT EXISTS peilen_measurements (
  id BIGSERIAL PRIMARY KEY,
  peilgebied_id TEXT NOT NULL UNIQUE,
  waterstand_m DOUBLE PRECISION NOT NULL,
  measured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  source TEXT NOT NULL DEFAULT 'seed',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS peilen_cdc_outbox (
  cdc_lsn BIGSERIAL PRIMARY KEY,
  op CHAR(1) NOT NULL CHECK (op IN ('I', 'U', 'D')),
  peilgebied_id TEXT NOT NULL,
  waterstand_m DOUBLE PRECISION,
  measured_at TIMESTAMPTZ,
  source TEXT,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION peilen_cdc_outbox_fn() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    INSERT INTO peilen_cdc_outbox (op, peilgebied_id, waterstand_m, measured_at, source)
    VALUES ('I', NEW.peilgebied_id, NEW.waterstand_m, NEW.measured_at, NEW.source);
    RETURN NEW;
  ELSIF TG_OP = 'UPDATE' THEN
    INSERT INTO peilen_cdc_outbox (op, peilgebied_id, waterstand_m, measured_at, source)
    VALUES ('U', NEW.peilgebied_id, NEW.waterstand_m, NEW.measured_at, NEW.source);
    RETURN NEW;
  ELSIF TG_OP = 'DELETE' THEN
    INSERT INTO peilen_cdc_outbox (op, peilgebied_id, waterstand_m, measured_at, source)
    VALUES ('D', OLD.peilgebied_id, OLD.waterstand_m, OLD.measured_at, OLD.source);
    RETURN OLD;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS peilen_cdc_outbox_trg ON peilen_measurements;
CREATE TRIGGER peilen_cdc_outbox_trg
  AFTER INSERT OR UPDATE OR DELETE ON peilen_measurements
  FOR EACH ROW EXECUTE PROCEDURE peilen_cdc_outbox_fn();

CREATE PUBLICATION nldt_peilen_pub FOR TABLE peilen_measurements;

-- Replication role hint (same user ok for local compose)
-- ALTER ROLE nldt WITH REPLICATION;
