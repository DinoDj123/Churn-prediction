from pathlib import Path
import pandas as pd
import numpy as np
import xgboost as xgb
import shap
import json

DATA_PATH = Path("data/telco_churn.csv")
OUT_PATH = Path("data/model_results.json")

FEATURES = ["tenure", "MonthlyCharges", "TotalCharges", "Contract",
            "InternetService", "TechSupport", "OnlineSecurity", "PaymentMethod"]


def load_and_prep(path=DATA_PATH, sample_size=1000):
    df = pd.read_csv(path)

    if len(df) > sample_size:
        df = df.sample(sample_size, random_state=42).reset_index(drop=True)

    df["Churn"] = df["Churn"].map({"Yes": 1, "No": 0}).fillna(0).astype(int)
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce").fillna(0)

    df["charge_ratio"] = df["MonthlyCharges"] / (df["TotalCharges"] + 1)

    features = ["tenure", "MonthlyCharges", "TotalCharges", "charge_ratio",
                "Contract", "InternetService", "TechSupport", "OnlineSecurity", "PaymentMethod"]

    X = pd.get_dummies(df[features])
    y = df["Churn"]

    return X, y, df


def train(X, y):
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.1,
        eval_metric="logloss",
        random_state=42
    )
    model.fit(X, y)
    return model


def get_shap(model, X):
    explainer = shap.TreeExplainer(model)
    vals = explainer.shap_values(X)
    return vals


def retention_actions(model, row, prob, monthly):
    results = {}

    r = row.copy()
    r["MonthlyCharges"] *= 0.8
    results["discount_20"] = {
        "new_prob": float(model.predict_proba(r)[0, 1]),
        "cost": monthly * 0.2 * 12,
        "label": "20% popust"
    }

    r2 = row.copy()
    if "Contract_One year" in r2.columns:
        r2["Contract_One year"] = 1
        r2["Contract_Month-to-month"] = 0
    results["contract_1yr"] = {
        "new_prob": float(model.predict_proba(r2)[0, 1]),
        "cost": 50,
        "label": "Godišnji ugovor"
    }

    for k, v in results.items():
        clv = monthly * 12
        v["roi"] = round((prob - v["new_prob"]) * clv - v["cost"], 2)

    return results


def main():
    X, y, df = load_and_prep()

    model = train(X, y)

    shap_vals = get_shap(model, X)

    output = []

    for i in range(len(df)):
        row = X.iloc[[i]]
        prob = float(model.predict_proba(row)[0, 1])
        monthly = float(df.iloc[i]["MonthlyCharges"])
        clv = monthly * 12
        expected_loss = round(prob * clv, 2)

        actions = retention_actions(model, row, prob, monthly)
        best = max(actions.values(), key=lambda x: x["roi"])

        top_idx = np.argsort(np.abs(shap_vals[i]))[-3:][::-1]
        top_factors = [X.columns[j] for j in top_idx]

        output.append({
            "customerID": df.iloc[i].get("customerID", f"C{i}"),
            "risk": round(prob, 3),
            "expected_loss": expected_loss,
            "best_action": best["label"],
            "best_roi": best["roi"],
            "top_factors": top_factors,
            "actions": actions,
            "monthly": monthly,
            "tenure": int(df.iloc[i]["tenure"]),
            "contract": df.iloc[i].get("Contract", "N/A")
        })

    output.sort(key=lambda x: x["expected_loss"], reverse=True)

    OUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(output, f)

    print("Model saved to", OUT_PATH)


if __name__ == "__main__":
    main()
