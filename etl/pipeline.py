import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from churn.model import (
    churn_by_contract,
    compute_kpis,
    load_and_clean,
    predict_customers,
    prepare_features,
    train_model,
)
from etl.database import (
    clear_tables,
    init_schema,
    insert_churn_by_contract,
    insert_customers,
    insert_kpis,
    insert_predictions,
)


def run_pipeline(sample_size=None, skip_db=False):
    data_path = os.getenv("DATA_PATH", "data/raw/telco_churn.csv")
    json_out = Path("data/processed/model_results.json")

    print("[1/6] Loading CSV...")
    df = load_and_clean(data_path, sample_size=sample_size)

    print("[2/6] Preparing features...")
    X, y = prepare_features(df)

    print("[3/6] Training model...")
    model = train_model(X, y)

    print("[4/6] Running predictions...")
    predictions = predict_customers(df, model, X)

    print("[5/6] Computing KPIs...")
    kpis = compute_kpis(df, predictions)
    contract_stats = churn_by_contract(df, predictions)

    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_data = [
        {
            "customerID": p["customer_id"],
            "risk": p["risk"],
            "expected_loss": p["expected_loss"],
            "best_action": p["best_action"],
            "best_roi": p["best_roi"],
            "monthly": p["monthly_charges"],
            "tenure": p["tenure"],
            "contract": p["contract"],
            "actions": p["actions"],
        }
        for p in predictions
    ]
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump({"kpis": kpis, "churn_by_contract": contract_stats, "customers": json_data}, f)

    if skip_db:
        print("[6/6] Skipping database (SKIP_DB=true)")
        return kpis

    print("[6/6] Writing to PostgreSQL...")
    init_schema()
    clear_tables()
    insert_customers(df)
    insert_predictions(predictions)
    insert_kpis(kpis)
    insert_churn_by_contract(contract_stats)

    print("Done.")
    print(f"  Customers: {kpis['total_customers']}")
    print(f"  Monthly revenue: ${kpis['total_monthly_revenue']:,.2f}")
    print(f"  Churn rate: {kpis['churn_rate']}%")
    print(f"  At-risk customers: {kpis['at_risk_customers']}")
    print(f"  Predicted loss: ${kpis['predicted_loss']:,.2f}")
    return kpis


if __name__ == "__main__":
    sample = int(os.getenv("SAMPLE_SIZE", "0")) or None
    skip = os.getenv("SKIP_DB", "").lower() in ("1", "true", "yes")
    run_pipeline(sample_size=sample, skip_db=skip)
