# SurplusReach

SurplusReach is a full-stack platform for coordinating surplus food donations, NGO pickups, volunteers, and food-safety guidance.

## Stack

- React, Vite, Tailwind CSS
- FastAPI, Pydantic v2, SQLAlchemy 2
- MySQL
- Google Maps JavaScript, Places, Geocoding and Directions APIs
- xAI Grok chat completions

## Run locally

### Prerequisites

Install Python 3.11+, Node.js 20+, and MySQL 8+. Enable the Google Maps JavaScript API, Places API, Geocoding API and Directions API for your Google key. Create a MySQL account with access to the `surplusreach` database before starting the API.

### Backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Set DATABASE_URL and JWT_SECRET, plus optional API keys, in .env
mysql -u root -p < schema.sql
uvicorn app.main:app --reload
```

Create the first platform administrator in a separate backend terminal with `python -m app.create_admin` (after setting up `.env`). The script prompts for credentials and does not install a default password.

API docs: http://localhost:8000/docs

### Frontend

In another terminal:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open http://localhost:5173. Choose **Explore a preview workspace** to explore the interface without backend credentials. Preview changes are held in the current browser session; authentication and persistence require the backend.

## Configuration

Copy `backend/.env.example` and `frontend/.env.example` to `.env` in each directory. Never commit real credentials. Configure the Google key with HTTP referrer restrictions for production and restrict enabled APIs. Configure CORS origins and a strong random `JWT_SECRET` before deployment.

## Product flows

- Donors and NGOs register as separate accounts with their own email login and password. Sign-in identifies the account and opens its role-specific dashboard; NGO accounts require administrator verification before they can claim food.
- Donors publish food listings and reveal a pickup code for handover.
- NGOs browse, filter and claim donations, then assign volunteers.
- Volunteers see assigned pickups and can confirm collection using the donor code, then confirm delivery.
- Admins verify NGO accounts and inspect platform metrics and audit events.
- The Grok assistant offers operational and food-safety guidance. It is advisory and prompts users to follow local food-safety rules.

## Production notes

This is a deployable foundation, not a substitute for operational security review. Use HTTPS, a managed MySQL service, secret management, backups, rate limiting, monitoring and email verification/password reset before public launch. Set `GOOGLE_MAPS_API_KEY` to enable maps and `GROK_API_KEY` to enable the assistant. Listing creation, claiming, volunteer assignment, OTP handover and drop-off are enforced by role-protected backend endpoints.
