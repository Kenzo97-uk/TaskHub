# PAR 2025Z – Projekt: **TaskHub** (aplikacja rozproszona)

Repozytorium zawiera prostą aplikację rozproszoną składającą się z:
- **serwera** (Python/FastAPI) udostępniającego **REST API (HTTP/JSON)** do operacji CRUD,
- **kanału powiadomień w czasie rzeczywistym** przez **WebSockets**,
- **asynchronicznej komunikacji wewnętrznej** przez **Redis Pub/Sub** (serwer publikuje zdarzenia, a komponenty je subskrybują),
- **workera** (Python) zapisującego zdarzenia do logu (tło),
- **dwóch klientów**:
  - klient **Python** (REST + WebSocket),
  - klient **Node.js** (REST + WebSocket).

Spełnione kryteria: serwer + min. 2 klientów, hybrydowy model komunikacji (synchroniczny + asynchroniczny), konteneryzacja `docker compose`, proste uwierzytelnianie (API Key), obsługa błędów (404/401), dokumentacja z uzasadnieniem i schematem architektury.

---

## Schemat architektury

```mermaid
flowchart LR
  subgraph Clients
    C1[Python Client]
    C2[Node.js Client]
  end

  subgraph Backend
    S[FastAPI Server
REST + WebSocket]
    R[(Redis
Pub/Sub)]
    W[Worker
subscriber]
  end

  C1 -- HTTP/JSON REST --> S
  C2 -- HTTP/JSON REST --> S

  C1 <-- WebSocket events --- S
  C2 <-- WebSocket events --- S

  S -- publish events --> R
  R -- subscribe --> S
  R -- subscribe --> W
```

---

## Protokoły komunikacyjne i biblioteki

### 1) REST API (HTTP/JSON) – komunikacja synchroniczna
- **Kiedy?** CRUD na zasobach (`/tasks`).
- **Dlaczego?** Proste, standardowe, łatwo debugować (curl/Postman), szerokie wsparcie w każdej technologii.
- **Biblioteki:**
  - `FastAPI`, `uvicorn` (serwer),
  - `requests` (klient Python),
  - `axios` (klient Node).

### 2) WebSockets – komunikacja asynchroniczna/push
- **Kiedy?** Powiadomienia do klientów w czasie rzeczywistym o zmianach (create/update/delete).
- **Dlaczego?** Klient nie musi „odpytywać” serwera (polling). Mamy natychmiastowe zdarzenia.

### 3) Redis Pub/Sub – asynchroniczna komunikacja wewnętrzna (messaging)
- **Kiedy?** Serwer publikuje zdarzenia domenowe do kanału `par:events`.
- **Dlaczego?** Rozdziela komponenty (server/worker), łatwiej skalować i dodawać nowych subskrybentów.
- **Biblioteka:** `redis` (async).

---

## Bezpieczeństwo (proste uwierzytelnianie)
Wszystkie endpointy REST wymagają nagłówka:
- `X-API-Key: <sekretny_klucz>`

WebSocket jest otwarty w tej wersji demo (łatwiejszy test). W razie potrzeby można dodać API key jako query param i weryfikować w `websocket_endpoint`.

---

## Uruchomienie (Docker)

1. Zainstaluj Docker + Docker Compose.
2. W katalogu projektu uruchom:
```bash
docker compose up --build
```
Serwer: `http://localhost:8000`  
Healthcheck: `http://localhost:8000/health`

Logi zdarzeń workera zapisują się w `./data/events.log`.

---

## Uruchomienie klientów

### Klient Python
W osobnym terminalu (lokalnie, poza Dockerem):
```bash
cd clients/python_client
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt

export API_KEY=changeme-super-secret
python client.py
```

### Klient Node.js
```bash
cd clients/node_client
npm install

export API_KEY=changeme-super-secret
npm start
```

---

## Przykładowe użycie (curl)
```bash
curl -H "X-API-Key: changeme-super-secret" http://localhost:8000/tasks
```

---

## Obsługa błędów (przykłady)
- `401` – brak/nieprawidłowy `X-API-Key`
- `404` – zasób `/tasks/{id}` nie istnieje

---

## Problemy napotkane i rozwiązania
1) **Synchronizacja powiadomień WebSocket**  
Zamiast emitować zdarzenia tylko lokalnie w serwerze, użyto **Redis Pub/Sub**. Dzięki temu:
- worker i serwer odbierają te same zdarzenia,
- w przyszłości można uruchomić wiele instancji serwera, a powiadomienia nadal będą „globalne”.

2) **Proste bezpieczeństwo**  
Zastosowano API key (nagłówek `X-API-Key`) – minimalna, czytelna forma autoryzacji na potrzeby projektu.

---

## Struktura katalogów
- `server/` – FastAPI (REST + WebSocket) + Redis Pub/Sub
- `worker/` – subscriber zdarzeń zapisujący log
- `clients/python_client/` – klient Python (REST + WS)
- `clients/node_client/` – klient Node.js (REST + WS)
- `docker-compose.yml` – uruchomienie całości jednym poleceniem
