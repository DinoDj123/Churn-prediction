import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import execute_values

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://churn_user:churn_pass@localhost:5433/churn_db",
)


def get_connection():
    return psycopg2.connect(DATABASE_URL)


@contextmanager
def db_cursor():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema():
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, encoding="utf-8") as f:
        sql = f.read()
    with db_cursor() as cur:
        cur.execute(sql)


def clear_tables():
    with db_cursor() as cur:
        cur.execute("TRUNCATE retention_actions, churn_predictions, customers, dashboard_kpis, churn_by_contract RESTART IDENTITY CASCADE")


def insert_customers(df):
    rows = [
        (
            str(r["customerID"]),
            str(r.get("gender", "")),
            int(r.get("SeniorCitizen", 0)),
            str(r.get("Partner", "")),
            str(r.get("Dependents", "")),
            int(r["tenure"]),
            str(r.get("PhoneService", "")),
            str(r.get("InternetService", "")),
            str(r.get("Contract", "")),
            str(r.get("PaymentMethod", "")),
            float(r["MonthlyCharges"]),
            float(r["TotalCharges"]),
            int(r["Churn"]),
        )
        for _, r in df.iterrows()
    ]
    with db_cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO customers (
                customer_id, gender, senior_citizen, partner, dependents,
                tenure, phone_service, internet_service, contract,
                payment_method, monthly_charges, total_charges, actual_churn
            ) VALUES %s
            ON CONFLICT (customer_id) DO UPDATE SET
                tenure = EXCLUDED.tenure,
                monthly_charges = EXCLUDED.monthly_charges,
                total_charges = EXCLUDED.total_charges,
                actual_churn = EXCLUDED.actual_churn,
                updated_at = NOW()
            """,
            rows,
        )


def insert_predictions(predictions):
    pred_rows = [
        (p["customer_id"], p["risk"], p["expected_loss"], p["best_action"], p["best_roi"])
        for p in predictions
    ]
    action_rows = []
    for p in predictions:
        for key, action in p["actions"].items():
            action_rows.append((
                p["customer_id"], key, action["label"],
                action["new_prob"], action["cost"], action["roi"],
            ))

    with db_cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO churn_predictions (customer_id, risk, expected_loss, best_action, best_roi)
            VALUES %s
            ON CONFLICT (customer_id) DO UPDATE SET
                risk = EXCLUDED.risk,
                expected_loss = EXCLUDED.expected_loss,
                best_action = EXCLUDED.best_action,
                best_roi = EXCLUDED.best_roi,
                updated_at = NOW()
            """,
            pred_rows,
        )
        if action_rows:
            cur.execute("DELETE FROM retention_actions")
            execute_values(
                cur,
                """
                INSERT INTO retention_actions
                    (customer_id, action_key, action_label, new_prob, cost, roi)
                VALUES %s
                """,
                action_rows,
            )


def insert_kpis(kpis):
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO dashboard_kpis (
                total_customers, total_monthly_revenue, total_annual_revenue,
                churn_rate, at_risk_customers, predicted_loss, avg_risk
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                kpis["total_customers"],
                kpis["total_monthly_revenue"],
                kpis["total_annual_revenue"],
                kpis["churn_rate"],
                kpis["at_risk_customers"],
                kpis["predicted_loss"],
                kpis["avg_risk"],
            ),
        )


def insert_churn_by_contract(rows):
    with db_cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO churn_by_contract (contract, customers, churn_rate, avg_predicted_risk)
            VALUES %s
            """,
            [(r["contract"], r["customers"], r["churn_rate"], r["avg_predicted_risk"]) for r in rows],
        )


def fetch_kpis():
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT total_customers, total_monthly_revenue, total_annual_revenue,
                   churn_rate, at_risk_customers, predicted_loss, avg_risk, run_at
            FROM dashboard_kpis ORDER BY run_at DESC LIMIT 1
            """
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "total_customers": row[0],
            "total_monthly_revenue": float(row[1]),
            "total_annual_revenue": float(row[2]),
            "churn_rate": float(row[3]),
            "at_risk_customers": row[4],
            "predicted_loss": float(row[5]),
            "avg_risk": float(row[6]),
            "run_at": row[7].isoformat() if row[7] else None,
        }


def fetch_churn_by_contract():
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT contract, customers, churn_rate, avg_predicted_risk
            FROM churn_by_contract
            WHERE run_at = (SELECT MAX(run_at) FROM churn_by_contract)
            ORDER BY churn_rate DESC
            """
        )
        return [
            {
                "contract": r[0],
                "customers": r[1],
                "churn_rate": float(r[2]),
                "avg_predicted_risk": float(r[3]),
            }
            for r in cur.fetchall()
        ]


def fetch_top_risk(limit=10):
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT c.customer_id, c.contract, c.tenure, c.monthly_charges,
                   p.risk, p.expected_loss, p.best_action, p.best_roi
            FROM customers c
            JOIN churn_predictions p ON c.customer_id = p.customer_id
            ORDER BY p.expected_loss DESC
            LIMIT %s
            """,
            (limit,),
        )
        return [
            {
                "customerID": r[0],
                "contract": r[1],
                "tenure": r[2],
                "monthly": float(r[3]),
                "risk": float(r[4]),
                "expected_loss": float(r[5]),
                "best_action": r[6],
                "best_roi": float(r[7]),
            }
            for r in cur.fetchall()
        ]


def fetch_customers(min_risk=0.0, contract="", limit=100):
    query = """
        SELECT c.customer_id, c.contract, c.tenure, c.monthly_charges,
               p.risk, p.expected_loss, p.best_action, p.best_roi
        FROM customers c
        JOIN churn_predictions p ON c.customer_id = p.customer_id
        WHERE p.risk >= %s
    """
    params = [min_risk]
    if contract:
        query += " AND c.contract = %s"
        params.append(contract)
    query += " ORDER BY p.expected_loss DESC LIMIT %s"
    params.append(limit)

    with db_cursor() as cur:
        cur.execute(query, params)
        return [
            {
                "customerID": r[0],
                "contract": r[1],
                "tenure": r[2],
                "monthly": float(r[3]),
                "risk": float(r[4]),
                "expected_loss": float(r[5]),
                "best_action": r[6],
                "best_roi": float(r[7]),
            }
            for r in cur.fetchall()
        ]


def fetch_customer_detail(customer_id):
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT c.customer_id, c.contract, c.tenure, c.monthly_charges,
                   p.risk, p.expected_loss, p.best_action, p.best_roi
            FROM customers c
            JOIN churn_predictions p ON c.customer_id = p.customer_id
            WHERE c.customer_id = %s
            """,
            (customer_id,),
        )
        row = cur.fetchone()
        if not row:
            return None

        cur.execute(
            """
            SELECT action_key, action_label, new_prob, cost, roi
            FROM retention_actions WHERE customer_id = %s
            """,
            (customer_id,),
        )
        actions = {
            r[0]: {"label": r[1], "new_prob": float(r[2]), "cost": float(r[3]), "roi": float(r[4])}
            for r in cur.fetchall()
        }

        return {
            "customerID": row[0],
            "contract": row[1],
            "tenure": row[2],
            "monthly": float(row[3]),
            "risk": float(row[4]),
            "expected_loss": float(row[5]),
            "best_action": row[6],
            "best_roi": float(row[7]),
            "actions": actions,
            "top_factors": [],
        }
