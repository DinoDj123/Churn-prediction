import json
import logging
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from auth.routes import require_user
from auth.routes import router as auth_router

load_dotenv()

app = FastAPI(title="Churn Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_urlsafe(32)
    logging.getLogger(__name__).warning(
        "SECRET_KEY nije postavljen; koristi se nasumičan ključ i sesije neće preživjeti restart"
    )

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",
    https_only=os.getenv("SESSION_HTTPS_ONLY", "false").lower() == "true",
)

app.include_router(auth_router)

DATA_PATH = Path("data/processed/model_results.json")
USE_DB = os.getenv("USE_DB", "auto").lower()

customers = []
kpis = {}
churn_by_contract_data = []


def _use_database():
    if USE_DB == "true":
        return True
    if USE_DB == "false":
        return False
    try:
        from etl.database import fetch_kpis
        fetch_kpis()
        return True
    except Exception:
        return False


def _load_json():
    global customers, kpis, churn_by_contract_data
    if not DATA_PATH.exists():
        customers, kpis, churn_by_contract_data = [], {}, []
        return
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        customers = data
        kpis = {}
        churn_by_contract_data = []
    else:
        customers = data.get("customers", [])
        kpis = data.get("kpis", {})
        churn_by_contract_data = data.get("churn_by_contract", [])


@app.on_event("startup")
def load():
    if _use_database():
        return
    _load_json()


@app.get("/")
def index(request: Request):
    if not request.session.get("email"):
        return RedirectResponse("/login.html", status_code=303)
    return FileResponse("frontend/index.html")


@app.get("/dashboard/kpis", dependencies=[Depends(require_user)])
def dashboard_kpis():
    if _use_database():
        from etl.database import fetch_kpis
        result = fetch_kpis()
        if result:
            return result
    if kpis:
        return kpis
    return _fallback_kpis()


@app.get("/dashboard/churn-by-contract", dependencies=[Depends(require_user)])
def dashboard_churn_contract():
    if _use_database():
        from etl.database import fetch_churn_by_contract
        return fetch_churn_by_contract()
    if churn_by_contract_data:
        return churn_by_contract_data
    return _fallback_churn_by_contract()


@app.get("/dashboard/top-risk", dependencies=[Depends(require_user)])
def dashboard_top_risk(limit: int = 10):
    if _use_database():
        from etl.database import fetch_top_risk
        return fetch_top_risk(limit)
    sorted_c = sorted(customers, key=lambda x: x.get("expected_loss", 0), reverse=True)
    return sorted_c[:limit]


@app.get("/customers", dependencies=[Depends(require_user)])
def get_customers(min_risk: float = 0.0, contract: str = ""):
    if _use_database():
        from etl.database import fetch_customers
        return fetch_customers(min_risk, contract)
    result = customers
    if min_risk > 0:
        result = [c for c in result if c["risk"] >= min_risk]
    if contract:
        result = [c for c in result if c.get("contract", "") == contract]
    return result[:100]


@app.get("/customers/{customer_id}", dependencies=[Depends(require_user)])
def get_customer(customer_id: str):
    if _use_database():
        from etl.database import fetch_customer_detail
        detail = fetch_customer_detail(customer_id)
        if detail:
            return detail
        return {"error": "not found"}
    for c in customers:
        if c["customerID"] == customer_id:
            return c
    return {"error": "not found"}


def _fallback_kpis():
    if not customers:
        return {}
    high = [c for c in customers if c["risk"] > 0.7]
    return {
        "total_customers": len(customers),
        "total_monthly_revenue": round(sum(c.get("monthly", 0) for c in customers), 2),
        "total_annual_revenue": round(sum(c.get("monthly", 0) for c in customers) * 12, 2),
        "churn_rate": 0,
        "at_risk_customers": len(high),
        "predicted_loss": round(sum(c["expected_loss"] for c in customers), 2),
        "avg_risk": round(sum(c["risk"] for c in customers) / len(customers), 4),
    }


def _fallback_churn_by_contract():
    contracts = {}
    for c in customers:
        ct = c.get("contract", "N/A")
        if ct not in contracts:
            contracts[ct] = {"contract": ct, "customers": 0, "churn_rate": 0, "avg_predicted_risk": 0, "_risks": []}
        contracts[ct]["customers"] += 1
        contracts[ct]["_risks"].append(c["risk"])
    result = []
    for v in contracts.values():
        risks = v.pop("_risks")
        v["avg_predicted_risk"] = round(sum(risks) / len(risks) * 100, 2) if risks else 0
        result.append(v)
    return result


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
