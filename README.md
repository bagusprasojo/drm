# DRM Backend API

## Scope
- Django + DRF API backend
- JWT auth (access + refresh)
- Device registration + revoke
- PDF upload + async processing with Celery
- `.bookpkg` generation (zip container)
- AES-256-GCM per page + RSA-2048 manifest signature
- License verify/issue/revoke
- Resumable download (`Range` header)

## Quick Start
1. Create and activate venv.
2. Install deps:
   - `pip install -r requirements.txt`
3. Copy env:
   - `copy .env.example .env`
4. Configure MySQL + Redis and keys in `.env`.
5. Run migrations:
   - `python manage.py makemigrations`
   - `python manage.py migrate`
6. Create admin user:
   - `python manage.py createsuperuser`
7. Run API:
   - `python manage.py runserver`
8. Run worker:
   <!-- - `celery -A config worker -l info` -->
   - 'celery -A config worker -l info -P solo --concurrency 1'

## Main Endpoints
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `POST /api/auth/refresh`
- `POST /api/device/register`
- `POST /api/device/revoke`
- `GET /api/books`
- `GET /api/book/{id}`
- `POST /api/book/upload`
- `POST /api/book/download`
- `POST /api/license/verify`
- `POST /api/license/issue` (admin)
- `POST /api/license/revoke` (admin)
"# drm" 
