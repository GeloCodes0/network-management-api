# Network Management REST API

A Python REST API for managing network-device inventory, built with FastAPI, SQLAlchemy, and SQLite. The project demonstrates RESTful API development, data validation, database integration, API-key authentication, rate limiting, and automated testing.

## Features

* **Device inventory:** Create, list, retrieve, update, and delete network-device records.
* **Data validation:** Validate IPv4 addresses, required fields, device types, and device statuses.
* **Database persistence:** Store device records with SQLAlchemy and SQLite.
* **API-key authentication:** Protect device-management endpoints using the `X-API-Key` header.
* **Rate limiting:** Limit device-endpoint requests by client IP using configurable request and time-window settings.
* **Duplicate prevention:** Reject duplicate hostnames and IP addresses.
* **Pagination:** Support `skip` and `limit` query parameters when listing devices.
* **Health monitoring:** Check API and database connectivity.
* **Automated tests:** Test core API functionality and security controls using pytest.

## Technology Stack

* Python
* FastAPI
* SQLAlchemy
* SQLite
* Pydantic
* pytest
* HTTPX

## Project Structure

```text
08-network-management-api/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── database.py
│   ├── schemas.py
│   └── devices.py
├── tests/
│   ├── __init__.py
│   └── test_api.py
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/GeloCodes0/network-management-api.git
cd network-management-api
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create your local `.env` file by copying the example:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and replace the placeholder API key with a strong, randomly generated secret. Never commit the real `.env` file or share the secret publicly.

Example configuration:

```env
DATABASE_URL=sqlite:///./network_management.db
API_KEY=replace-with-a-strong-random-secret
AUTHORIZED_NETWORKS=127.0.0.1/32,192.168.1.0/24
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60
```

The `AUTHORIZED_NETWORKS` variable is included in the example configuration, but network allowlisting must not be considered active unless it is explicitly implemented and enforced by the application.

### 5. Start the API

```powershell
uvicorn app.main:app --reload
```

Open the interactive API documentation:

* Swagger UI: `http://127.0.0.1:8000/docs`
* Health endpoint: `http://127.0.0.1:8000/health`

## API Endpoints

| Method | Endpoint               | Description               |
| ------ | ---------------------- | ------------------------- |
| GET    | `/`                    | API information           |
| GET    | `/health`              | API and database health   |
| POST   | `/devices/`            | Register a device         |
| GET    | `/devices/`            | List devices              |
| GET    | `/devices/{device_id}` | Retrieve one device       |
| PATCH  | `/devices/{device_id}` | Partially update a device |
| DELETE | `/devices/{device_id}` | Delete a device           |

Device-management endpoints require the `X-API-Key` header. The root and health endpoints are publicly accessible.

## Example Request

Register a network switch:

```json
{
  "hostname": "SW-CORE-01",
  "ip_address": "192.168.1.10",
  "device_type": "switch",
  "vendor": "Cisco",
  "model": "Catalyst 2960",
  "operating_system": "Cisco IOS",
  "location": "Test Lab",
  "status": "unknown"
}
```

Send this JSON to `POST /devices/` with the `X-API-Key` header and a valid configured key.

Supported device types: `router`, `switch`, `firewall`, `server`, `access_point`, and `other`.

Supported statuses: `online`, `offline`, and `unknown`.

## Security Controls

* API-key authentication for device-management operations.
* Timing-safe comparison of supplied and configured API keys.
* Rejection of missing or documented placeholder API-key values.
* Input validation using Pydantic schemas.
* Duplicate hostname and IP-address prevention.
* Request rate limiting with HTTP `429 Too Many Requests` and a `Retry-After` response header.
* Environment-based configuration and exclusion of local secrets from version control.

### Rate-Limiting Scope

The current rate limiter stores request timestamps in application memory and applies limits per client IP to `/devices` endpoints. Its counters reset when the application restarts and are not shared between multiple worker processes. A production deployment should use a shared rate-limit store and trusted proxy configuration where appropriate.

## Testing

Run the automated test suite:

```powershell
python -m pytest -v
```

The current test suite contains nine tests covering health checks, authentication, device CRUD operations, duplicate prevention, IPv4 validation, and rate limiting.

**Latest local test result:** 9 passed.

## Limitations and Future Improvements

* Add persistent, distributed rate limiting using Redis.
* Add database migrations using Alembic.
* Implement and test network allowlisting if required.
* Add structured audit logging for device changes and authentication failures.
* Add deployment configuration, monitoring, and integration tests.
* Consider stronger production authentication and secret-management practices.

## Disclaimer

This project is intended for educational and portfolio demonstration purposes. It has not been independently security-audited and should not be considered production-ready without further hardening and testing.
