# AGENTS.md

## Projekat
Churn Analytics: predviđanje odlaska korisnika i preporuke za zadržavanje (retention).
Zahtjevi za tekuću funkcionalnost su u SPEC.md.

## Stack i struktura
- Python 3.11, FastAPI (`app.py`), scikit-learn (`churn/model.py`), ETL u `etl/`
- Frontend: čisti HTML/CSS/JS u `frontend/`, bez build koraka
- Bez baze: `USE_DB=false`, podaci se čitaju iz `data/processed/model_results.json`
- Sa bazom: PostgreSQL preko `docker compose up --build` (vidi README)

## Komande
- Instalacija: `pip install -r requirements.txt -r requirements-dev.txt`
- Testovi: `python -m pytest -q`
- Lint: `ruff check .`
- Lokalno pokretanje (PowerShell): `$env:USE_DB="false"; uvicorn app:app --reload`

## Pravila
- Pokreni `python -m pytest -q` i `ruff check .` prije svakog commita
- Testovi rade sa `USE_DB=false` i ne traže PostgreSQL
- Svaki scenarij iz SPEC.md ima svoj test
- Jedna funkcionalnost = jedan commit, poruke u obliku `feat:`, `fix:`, `test:`, `docs:`, `chore:`
- Lozinke se nikad ne čuvaju niti loguju u čistom obliku
- Tajne (`SECRET_KEY`, `DATABASE_URL`) se čitaju samo iz env varijabli, nikad hardkodovane

## Ne diraj
- `.env` i sve tajne
- `data/raw/telco_churn.csv` i `data/processed/model_results.json` (hosting ih koristi; JSON je namjerno commitovan iako je `data/processed/` u .gitignore)
- `etl/` i `churn/model.py`, osim kad zadatak to izričito traži
