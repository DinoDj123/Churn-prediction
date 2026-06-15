# Churn Retention Tool

Alat za predviđanje odlaska korisnika telekom kompanije. Koristi XGBoost model i SHAP objašnjenja za identifikaciju rizičnih korisnika i preporuku retention akcija.

---

## Instalacija

### 1. Klonirajte projekat

```bash
git clone <https://github.com/DinoDj123/Churn-prediction>
cd PythonProject
```

### 2. Napravite virtualno okruženje

```bash
python -m venv venv
```

Aktivirajte ga:

```bash
venv\Scripts\activate
```

### 3. Instalirajte zavisnosti

```bash
pip install -r requirements.txt
```

### 4. Dodajte dataset (*ukoliko vec ne postoji*)

Skini [Telco Customer Churn](https://www.kaggle.com/datasets/blastchar/telco-customer-churn) dataset i stavite ga u:

```data/telco_churn.csv```
> Ako ste klonirali git repozitorijum, dataset i model vec postoje.

---

## Pokretanje

### Korak 1 — Trenirajte model (*ukoliko vec ne postoji*)

```bash
python train_model.py
```

Generiše `data/model_results.json` sa predikcijama za sve korisnike.

### Korak 2 — Pokrenite server

```bash
uvicorn app:app --reload
```

### Korak 3 — Otvorite aplikaciju

Idi na [http://127.0.0.1:8000](http://127.0.0.1:8000)
