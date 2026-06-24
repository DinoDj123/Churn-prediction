CREATE TABLE IF NOT EXISTS customers (
    customer_id       VARCHAR(32) PRIMARY KEY,
    gender            VARCHAR(10),
    senior_citizen    SMALLINT,
    partner           VARCHAR(5),
    dependents        VARCHAR(5),
    tenure            INTEGER,
    phone_service     VARCHAR(20),
    internet_service  VARCHAR(30),
    contract          VARCHAR(20),
    payment_method    VARCHAR(40),
    monthly_charges   NUMERIC(10, 2),
    total_charges     NUMERIC(12, 2),
    actual_churn      SMALLINT,
    updated_at        TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS churn_predictions (
    customer_id       VARCHAR(32) PRIMARY KEY REFERENCES customers(customer_id),
    risk              NUMERIC(6, 4),
    expected_loss     NUMERIC(12, 2),
    best_action       VARCHAR(100),
    best_roi          NUMERIC(12, 2),
    updated_at        TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS retention_actions (
    id                SERIAL PRIMARY KEY,
    customer_id       VARCHAR(32) REFERENCES customers(customer_id),
    action_key        VARCHAR(50),
    action_label      VARCHAR(100),
    new_prob          NUMERIC(6, 4),
    cost              NUMERIC(10, 2),
    roi               NUMERIC(12, 2),
    updated_at        TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dashboard_kpis (
    id                    SERIAL PRIMARY KEY,
    total_customers       INTEGER,
    total_monthly_revenue NUMERIC(14, 2),
    total_annual_revenue  NUMERIC(14, 2),
    churn_rate            NUMERIC(6, 2),
    at_risk_customers     INTEGER,
    predicted_loss        NUMERIC(14, 2),
    avg_risk              NUMERIC(6, 4),
    run_at                TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS churn_by_contract (
    id                 SERIAL PRIMARY KEY,
    contract           VARCHAR(20),
    customers          INTEGER,
    churn_rate         NUMERIC(6, 2),
    avg_predicted_risk NUMERIC(6, 2),
    run_at             TIMESTAMP DEFAULT NOW()
);

CREATE OR REPLACE VIEW v_dashboard AS
SELECT
    k.total_customers,
    k.total_monthly_revenue,
    k.total_annual_revenue,
    k.churn_rate,
    k.at_risk_customers,
    k.predicted_loss,
    k.avg_risk,
    k.run_at
FROM dashboard_kpis k
ORDER BY k.run_at DESC
LIMIT 1;

CREATE OR REPLACE VIEW v_customer_risk AS
SELECT
    c.customer_id,
    c.contract,
    c.tenure,
    c.monthly_charges,
    c.total_charges,
    c.actual_churn,
    p.risk,
    p.expected_loss,
    p.best_action,
    p.best_roi
FROM customers c
JOIN churn_predictions p ON c.customer_id = p.customer_id;

CREATE OR REPLACE VIEW v_churn_contract AS
SELECT contract, customers, churn_rate, avg_predicted_risk, run_at
FROM churn_by_contract
WHERE run_at = (SELECT MAX(run_at) FROM churn_by_contract);
