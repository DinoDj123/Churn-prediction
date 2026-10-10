# Churn Analytics: prijava korisnika

Dashboard i API sada vidi svako ko zna adresu. Cilj: samo registrovan i prijavljen korisnik
vidi podatke o klijentima, da bi aplikacija mogla da se objavi na internetu.

## Zahtjevi

1. **Registracija:** korisnik se registruje emailom i lozinkom. Email je jedinstven
   (bez obzira na velika i mala slova), lozinka ima najmanje 8 znakova.
2. **Prijava:** ispravan email i lozinka daju sesiju u HttpOnly kolačiću. Pogrešni podaci daju 401
   i ne postavljaju sesiju. Poruka greške ne otkriva da li email postoji.
3. **Zaštita:** bez prijave `/dashboard/*` i `/customers*` vraćaju 401. Stranica `/` šalje
   neprijavljenog korisnika na `/login.html`.
4. **Odjava:** `POST /auth/logout` briše sesiju.
5. **Lozinke:** čuvaju se samo kao hash sa solju, nikad u čistom obliku.

## Scenariji

### Nova korisnica
- `POST /auth/register` sa `{"email": "ana@test.me", "password": "Lozinka123"}` → 201
- Ista registracija ponovo → 409
- `{"email": "ANA@test.me", "password": "Lozinka123"}` → 409
- `{"email": "marko@test.me", "password": "abc"}` → 422, korisnik se ne pravi

### Prijava i dashboard
- Bez prijave `GET /dashboard/kpis` → 401
- `POST /auth/login` sa `{"email": "ana@test.me", "password": "Lozinka123"}` → 200
- Zatim `GET /dashboard/kpis` → 200 i `total_customers` je 7043
- Zatim `GET /auth/me` → 200 i `{"email": "ana@test.me"}`
- `POST /auth/login` sa `{"email": "ana@test.me", "password": "pogresna1"}` → 401, sesija nije postavljena
- `POST /auth/login` sa `{"email": "niko@test.me", "password": "Lozinka123"}` → 401, ista poruka kao za pogrešnu lozinku

### Odjava
- Prijavljena Ana: `POST /auth/logout` → 200, zatim `GET /dashboard/kpis` → 401

### Hash lozinke
- Poslije registracije Ane, u bazi korisnika sačuvana lozinka nije `Lozinka123` i ne sadrži taj tekst

### Stranica za prijavu
- Neprijavljen `GET /` → preusmjerenje na `/login.html`
- `GET /login.html` → 200 bez prijave
- Na `/login.html` vidljiva je samo forma za prijavu; link "Registruj se" je zamjenjuje formom
  za registraciju, a link "Prijavi se" vraća prijavu. Obje forme nikad nisu vidljive istovremeno.

### Paginacija liste korisnika
- Prijavljen korisnik na dashboardu vidi listu korisnika po 10 na strani, sa dugmadima
  "Prethodna" i "Sljedeća" i natpisom "Strana 1 od 10" (za 100 korisnika iz `/customers`)
- Promjena strane ne mijenja URL i ne šalje novi zahtjev; filter vraća na prvu stranu
- Klik na korisnika i dalje otvara njegov detalj

## Odluke

- Korisnici u SQLite (`sqlite3` iz standardne biblioteke), putanja iz `USERS_DB_PATH`
  (podrazumijevano `data/users.db`)
- Hash: `hashlib.pbkdf2_hmac` (sha256, nasumična so po korisniku)
- Sesija: Starlette `SessionMiddleware`, ključ iz `SECRET_KEY`

## Šta nije obuhvaćeno

- Reset lozinke, potvrda emaila, uloge i admin, Google/OAuth prijava
- Ograničavanje broja pokušaja prijave
- Trajni korisnici na besplatnom hostingu (SQLite na Renderu se briše pri redeployu);
  sljedeći korak je PostgreSQL za korisnike
- Ispravka preporuke za dvogodišnje ugovore u `churn/model.py`
