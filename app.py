from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from pathlib import Path

app = FastAPI(title="Churn API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = Path("data/model_results.json")
customers = []


@app.on_event("startup")
def load():
    global customers
    if DATA_PATH.exists():
        with open(DATA_PATH, "rb") as f:
            customers = json.load(f)
    else:
        customers = []

@app.get("/")
def index():
    return FileResponse("frontend/index.html")


@app.get("/customers")
def get_customers(min_risk: float = 0.0, contract: str = ""):
    result = customers
    if min_risk > 0:
        result = [c for c in result if c["risk"] >= min_risk]
    if contract:
        result = [c for c in result if c.get("contract", "") == contract]
    return result[:100]  # max 100


@app.get("/customers/{customer_id}")
def get_customer(customer_id: str):
    for c in customers:
        if c["customerID"] == customer_id:
            return c
    return {"error": "nije pronađen"}


@app.get("/stats")
def stats():
    if not customers:
        return {}
    high_risk = [c for c in customers if c["risk"] > 0.7]
    return {
        "total": len(customers),
        "high_risk": len(high_risk),
        "avg_risk": round(sum(c["risk"] for c in customers) / len(customers), 3),
        "total_expected_loss": round(sum(c["expected_loss"] for c in customers), 2)
    }

app.mount("/", StaticFiles(directory="frontend",html=True), name="frontend")