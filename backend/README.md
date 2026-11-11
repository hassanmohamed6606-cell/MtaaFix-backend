# MtaaFix Backend

Flask REST API for MtaaFix community reports. It provides SQLAlchemy persistence, JWT authentication, report CRUD, filtering/pagination, owner/admin authorization, optional SendGrid email notifications and Cloudinary image uploads.

## Run locally

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python run.py
```

Health check: `http://127.0.0.1:5000/api/health`.

## Tests

```powershell
pytest -q
```

## Database migrations

Set `AUTO_CREATE_DB=false` in `.env`, then apply the included initial migration:

```powershell
flask --app run db upgrade
```

See `../docs/API.md` for endpoint contracts and `../README.md` for full-stack setup.
