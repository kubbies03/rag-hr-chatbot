# Tutorial

This tutorial is the shortest path to a working local demo.

## 1. Install

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install langchain-text-splitters
copy .env.example .env
```

Set `GOOGLE_API_KEY` in `.env`.

## 2. Seed local demo data

```bash
python -m app.db.seed
```

## 3. Start the backend

```bash
uvicorn app.main:app --reload --port 8000
```

## 4. Open the built-in tools

- Swagger: `http://localhost:8000/docs`
- Admin UI: `http://localhost:8000/admin`
- Health: `http://localhost:8000/health`

## 5. Try an employee question

```bash
curl -X POST http://localhost:8000/api/chat ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: demo_hr_001" ^
  -d "{\"message\":\"Ai dang nghi phep hom nay?\",\"session_id\":\"tutorial-employee\"}"
```

## 6. Ingest documents

Put files into `data/docs/`, then run:

```bash
curl -X POST http://localhost:8000/api/documents/ingest-all ^
  -H "X-API-Key: demo_admin_001"
```

## 7. Try a policy question

```bash
curl -X POST http://localhost:8000/api/chat ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: demo_employee_001" ^
  -d "{\"message\":\"Quy dinh remote work la gi?\",\"session_id\":\"tutorial-docs\"}"
```

## 8. Switch to Firebase mode later

When you are ready:

- Set `FIREBASE_PROJECT_ID`
- Provide `firebase-service-account.json`
- Send `Authorization: Bearer <firebase_id_token>` instead of `X-API-Key`

The backend will then resolve user roles from Firestore.
