# ♻ WasteLoop — MVP Web Application

A Django-based platform that transforms waste into economic opportunity for refugee
communities. Collectors log waste, admins verify and pay, recyclers buy in bulk.

---

## Tech Stack

| Layer    | Technology                       |
|----------|----------------------------------|
| Backend  | Django 4.x (Python 3.12)         |
| Frontend | HTML + Bootstrap 5.3 + CSS       |
| Database | SQLite (ready to migrate to PostgreSQL) |
| Fonts    | Space Grotesk + DM Sans (Google) |
| Icons    | Bootstrap Icons                  |

---

## Requirements

- Python 3.10+
- pip

---

## Quick Start (Local)

### 1. Clone / download the project

```bash
git clone <your-repo-url>
cd wasteloop_project
```

### 2. Create and activate a virtual environment

```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install django python-dotenv
```

### 4. Configure environment variables

The `.env` file is already included with safe dev defaults.
For production, update these values:

```
SECRET_KEY=your-strong-random-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
```

### 5. Run database migrations

```bash
python manage.py migrate
```

### 6. Create a superuser (admin account)

```bash
python manage.py createsuperuser
```

When prompted, choose role = `admin` (or set it via the Django admin panel).

### 7. (Optional) Load demo seed data

```bash
python manage.py shell < seed.py
```

Or run the server and add data manually through the admin panel.

### 8. Start the development server

```bash
python manage.py runserver
```

Visit: **http://127.0.0.1:8000**

---

## Demo Accounts

The following accounts are pre-loaded if you ran the seed data:

| Role      | Username | Password  | Access                        |
|-----------|----------|-----------|-------------------------------|
| Admin     | admin    | admin1234 | Full platform access          |
| Collector | aisha    | pass1234  | Own dashboard + entries only  |
| Collector | john     | pass1234  | Own dashboard + entries only  |

> ⚠️ Change all passwords before any real deployment.

---

## Page Map

| URL               | Page                  | Access          |
|-------------------|-----------------------|-----------------|
| `/`               | Home                  | Public          |
| `/about/`         | About WasteLoop       | Public          |
| `/impact/`        | Impact Stats          | Public          |
| `/recyclers/`     | Recycling Partners    | Public          |
| `/contact/`       | Contact               | Public          |
| `/register/`      | Register              | Public          |
| `/login/`         | Login                 | Public          |
| `/dashboard/`     | Dashboard (role-based)| Login required  |
| `/waste/`         | Waste Entry List      | Login required  |
| `/waste/add/`     | Add Waste Entry       | Admin only      |
| `/waste/verify/<id>/` | Toggle Verify    | Admin only      |
| `/payments/`      | Payments Manager      | Admin only      |
| `/payments/mark-paid/<id>/` | Mark Paid | Admin only    |
| `/admin/`         | Django Admin Panel    | Superuser only  |

---

## Project Structure

```
wasteloop_project/
├── .env                          # Environment variables (dev defaults)
├── manage.py
├── db.sqlite3                    # SQLite database (auto-created)
├── templates/
│   └── base.html                 # Shared layout (navbar + footer)
├── static/
│   ├── css/wasteloop.css         # Full design system (566 lines)
│   └── js/wasteloop.js           # Lightweight UX enhancements
└── core/                         # Main application
    ├── models.py                 # User, WasteEntry, Payment, Recycler, ImpactStat
    ├── views.py                  # 14 views with role-based access
    ├── urls.py                   # 14 URL patterns (namespaced: core:)
    ├── forms.py                  # 6 forms with full validation
    ├── admin.py                  # 5 model registrations with bulk actions
    └── templates/core/
        ├── public/               # home, about, impact, contact
        ├── auth/                 # login, register
        ├── dashboard/            # admin, collector
        ├── waste/                # list, add
        ├── payments/             # payments
        └── recycler/             # recyclers
```

---

## Database Models

```
User          — role (collector/admin), phone_number, location
WasteEntry    — collector, waste_type, weight_kg, date_collected, verified_by_admin
Payment       — collector, waste_entry (1:1), amount, is_paid, date_paid
Recycler      — name, materials_accepted, price_per_kg, phone_number, email
ImpactStat    — singleton: total_waste_kg, total_income_generated, active_collectors
```

ImpactStat updates **automatically** via Django signals whenever a WasteEntry
or Payment is saved or deleted — no cron jobs needed.

---

## Key Business Rules

- Collectors see **only their own** waste entries and earnings
- Admins see **everything** and can verify waste / mark payments
- Adding a waste entry **auto-creates** a pending payment at the best recycler price
- Weight must be `> 0` — validated at form level and database level
- Duplicate entries (same collector + type + date + weight) are blocked

---

## Migrating to PostgreSQL

1. Install the adapter: `pip install psycopg2-binary`
2. In `.env`, add:
   ```
   DB_NAME=wasteloop_db
   DB_USER=postgres
   DB_PASSWORD=yourpassword
   DB_HOST=localhost
   DB_PORT=5432
   ```
3. In `settings.py`, swap the `DATABASES` block (the PostgreSQL config is
   already written there as a comment — just uncomment it and comment out SQLite).
4. Run: `python manage.py migrate`

---

## Features NOT built (by design — pre-seed MVP)

- ❌ M-Pesa / mobile money integration
- ❌ Real-time chat
- ❌ QR code waste tagging
- ❌ Geolocation tracking
- ❌ AI sorting systems
- ❌ Complex mobile apps

These can be added in future sprints once the core model is validated.

---

## Running in Production (checklist)

- [ ] Set `DEBUG=False` in `.env`
- [ ] Set a strong `SECRET_KEY`
- [ ] Set `ALLOWED_HOSTS` to your domain
- [ ] Run `python manage.py collectstatic`
- [ ] Use **gunicorn** + **nginx** (or Railway / Render for easy deploy)
- [ ] Switch to PostgreSQL
- [ ] Set up daily database backups

---

Built with ♻ for WasteLoop — April 2026
