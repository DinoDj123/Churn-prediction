from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from churn.model import (
    churn_by_contract,
    compute_kpis,
    load_and_clean,
    predict_customers,
    prepare_features,
    train_model,
)

DATA_PATH = Path("data/raw/telco_churn.csv")
OUT_PATH = Path("data/processed/model_results.json")


def main():
    df = load_and_clean(DATA_PATH, sample_size=1000)
    X, y = prepare_features(df)
    model = train_model(X, y)
    predictions = predict_customers(df, model, X)
    kpis = compute_kpis(df, predictions)
    contract_stats = churn_by_contract(df, predictions)

    output = {
        "kpis": kpis,
        "churn_by_contract": contract_stats,
        "customers": [
            {
                "customerID": p["customer_id"],
                "risk": p["risk"],
                "expected_loss": p["expected_loss"],
                "best_action": p["best_action"],
                "best_roi": p["best_roi"],
                "top_factors": [],
                "actions": p["actions"],
                "monthly": p["monthly_charges"],
                "tenure": p["tenure"],
                "contract": p["contract"],
            }
            for p in predictions
        ],
    }

    OUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f)

    print("Model saved to", OUT_PATH)


if __name__ == "__main__":
    main()
