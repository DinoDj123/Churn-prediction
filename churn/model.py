from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
DATA_PATH = Path("data/raw/telco_churn.csv")

FEATURE_COLS = [
    "tenure", "MonthlyCharges", "TotalCharges", "charge_ratio",
    "Contract", "InternetService", "TechSupport", "OnlineSecurity", "PaymentMethod",
]

RISK_THRESHOLD = 0.7


def load_and_clean(path=DATA_PATH, sample_size=None):
    df = pd.read_csv(path)

    if sample_size and len(df) > sample_size:
        df = df.sample(sample_size, random_state=42).reset_index(drop=True)

    df["Churn"] = df["Churn"].map({"Yes": 1, "No": 0}).fillna(0).astype(int)
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce").fillna(0)
    df["charge_ratio"] = df["MonthlyCharges"] / (df["TotalCharges"] + 1)

    return df


def prepare_features(df):
    X = pd.get_dummies(df[FEATURE_COLS])
    y = df["Churn"]
    return X, y


def train_model(X, y):
    model = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.1,
        random_state=42,
    )
    model.fit(X, y)
    return model


def retention_actions(model, row, prob, monthly):
    results = {}

    r = row.copy()
    r["MonthlyCharges"] *= 0.8
    results["discount_20"] = {
        "new_prob": float(model.predict_proba(r)[0, 1]),
        "cost": monthly * 0.2 * 12,
        "label": "20% popust",
    }

    r2 = row.copy()
    if "Contract_One year" in r2.columns:
        r2["Contract_One year"] = 1
        r2["Contract_Month-to-month"] = 0
    results["contract_1yr"] = {
        "new_prob": float(model.predict_proba(r2)[0, 1]),
        "cost": 50,
        "label": "Godišnji ugovor",
    }

    for v in results.values():
        clv = monthly * 12
        v["roi"] = round((prob - v["new_prob"]) * clv - v["cost"], 2)

    return results


def predict_customers(df, model, X):
    output = []

    for i in range(len(df)):
        row = X.iloc[[i]]
        prob = float(model.predict_proba(row)[0, 1])
        monthly = float(df.iloc[i]["MonthlyCharges"])
        clv = monthly * 12
        expected_loss = round(prob * clv, 2)

        actions = retention_actions(model, row, prob, monthly)
        best = max(actions.values(), key=lambda x: x["roi"])

        output.append({
            "customer_id": str(df.iloc[i].get("customerID", f"C{i}")),
            "risk": round(prob, 4),
            "expected_loss": expected_loss,
            "best_action": best["label"],
            "best_roi": best["roi"],
            "monthly_charges": monthly,
            "total_charges": float(df.iloc[i]["TotalCharges"]),
            "tenure": int(df.iloc[i]["tenure"]),
            "contract": str(df.iloc[i].get("Contract", "N/A")),
            "internet_service": str(df.iloc[i].get("InternetService", "")),
            "payment_method": str(df.iloc[i].get("PaymentMethod", "")),
            "actual_churn": int(df.iloc[i]["Churn"]),
            "actions": actions,
        })

    output.sort(key=lambda x: x["expected_loss"], reverse=True)
    return output


def compute_kpis(df, predictions):
    total_revenue = round(float(df["MonthlyCharges"].sum()), 2)
    annual_revenue = round(total_revenue * 12, 2)
    churn_rate = round(float(df["Churn"].mean()) * 100, 2)
    at_risk = sum(1 for p in predictions if p["risk"] >= RISK_THRESHOLD)
    predicted_loss = round(sum(p["expected_loss"] for p in predictions), 2)
    avg_risk = round(float(np.mean([p["risk"] for p in predictions])), 4)

    return {
        "total_customers": len(df),
        "total_monthly_revenue": total_revenue,
        "total_annual_revenue": annual_revenue,
        "churn_rate": churn_rate,
        "at_risk_customers": at_risk,
        "predicted_loss": predicted_loss,
        "avg_risk": avg_risk,
    }


def churn_by_contract(df, predictions):
    pred_map = {p["customer_id"]: p["risk"] for p in predictions}
    df = df.copy()
    df["predicted_risk"] = df["customerID"].map(pred_map)

    rows = []
    for contract, group in df.groupby("Contract"):
        rows.append({
            "contract": contract,
            "customers": len(group),
            "churn_rate": round(float(group["Churn"].mean()) * 100, 2),
            "avg_predicted_risk": round(float(group["predicted_risk"].mean()) * 100, 2),
        })

    return sorted(rows, key=lambda x: x["churn_rate"], reverse=True)
