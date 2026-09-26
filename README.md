# Kawa Network MVP

A Django REST API for tracking coffee cherry deliveries from farmer plots
to washing stations, built for the Kawa Network pilot at Nyaruguru. This
is Formative 1 of a cumulative project spanning F1, F2, and the Summative.

See ADR.md for the architecture decisions and stakeholder trade-offs
behind this design.

## Requirements

- Python 3.13+
- pip

## Setup

1. Clone the repository and enter it:

   git clone <your-repo-url>
   cd advanced-python-programming-kawa

2. Create and activate a virtual environment:

   python -m venv venv
   .\venv\Scripts\Activate.ps1        # Windows PowerShell
   source venv/bin/activate           # macOS/Linux

3. Install dependencies:

   pip install -r requirements.txt

4. Create a .env file in the project root with the following variables:

   SECRET_KEY=<any string - Django uses this for cryptographic signing>
   DEBUG=True

   Note: .env is gitignored and must be created locally. There is no
   .env.example committed at this time.

5. Apply migrations:

   python manage.py migrate

6. (Optional) Create a superuser to access Django admin:

   python manage.py createsuperuser

7. Run the development server:

   python manage.py runserver

The API is now available at http://127.0.0.1:8000/api/
Django admin is available at http://127.0.0.1:8000/admin/

## Async Risk Check (Background Worker)

When a Plot is registered via POST /api/plots/, the API queues a
background risk check against a simulated external risk registry
(deliveries/risk_registry.py). This check runs in a separate Python
thread and does NOT block the HTTP response - the client receives a
201 Created response immediately, typically in well under a second,
regardless of how long the risk check takes.

### How it works

1. POST /api/plots/ saves the Plot with risk_status="pending" and
   returns the response right away.
2. A background thread is started (see perform_create in
   deliveries/views.py) which calls the simulated registry.
3. The simulated registry (deliveries/risk_registry.py) sleeps for
   2-6 seconds (compressed from the brief's stated 2-40 seconds for
   faster local testing) and either returns a result ("cleared" or
   "flagged") or raises a simulated outage error (~20% of calls).
4. On success, the Plot's risk_status and risk_checked_at fields are
   updated directly in the database.
5. On simulated registry failure, risk_status remains "pending" and
   risk_checked_at remains null - see ADR.md for why deliveries are
   still accepted from such a plot.

### Starting the background worker

No separate process or command is required. The background worker is
just a Python thread spawned automatically inside the same Django
process when a Plot is created - as long as `python manage.py runserver`
is running, plot registrations will trigger risk checks automatically.

There is no Celery, Redis, or other external broker/queue in this MVP.
See ADR.md, Decision 3, for why this choice was made and what it
trades off.

### Evidence / how to see it working

Every risk check attempt is logged to the console via Django's logging
framework. While the server is running, registering a Plot will print
lines similar to:

    Queued async risk check for plot 3
    Risk check started for plot 3
    Risk check completed for plot 3: cleared

or, if the simulated registry is "down" for that attempt:

    Risk check failed for plot 3: Registry unavailable for plot 3

You can verify the update took effect by fetching the same plot again
a few seconds later - GET /api/plots/{id}/ - and observing risk_status
has changed from "pending" to "cleared" or "flagged", with
risk_checked_at populated.

## API Endpoints

All endpoints are under /api/. The full browsable API is available at
http://127.0.0.1:8000/api/ when the server is running.

### Sectors

    GET  /api/sectors/
    POST /api/sectors/

Example request (POST):

    {
      "name": "Nyaruguru"
    }

Example response (201 Created):

    {
      "id": 1,
      "name": "Nyaruguru"
    }

### Washing Stations

    GET  /api/washing-stations/
    POST /api/washing-stations/

Example request (POST):

    {
      "name": "Nyaruguru Station",
      "location": "Nyaruguru, Southern Province"
    }

### Farmers

    GET  /api/farmers/
    POST /api/farmers/

Example request (POST):

    {
      "name": "Emmanuel Habimana",
      "phone_number": "+250788123456"
    }

Example response (201 Created):

    {
      "id": 1,
      "name": "Emmanuel Habimana",
      "phone_number": "+250788123456",
      "registered_at": "2026-09-22T11:53:35.405857Z"
    }

Example error (400 Bad Request) - missing required field:

    {
      "phone_number": ["This field is required."]
    }

### Plots

    GET  /api/plots/
    POST /api/plots/
    GET  /api/plots/{id}/

Registering a Plot also queues an async risk check - see the Async
Risk Check section above.

Example request (POST):

    {
      "farmer": 1,
      "sector": 1,
      "washing_station": 1
    }

Example response (201 Created):

    {
      "id": 1,
      "farmer": 1,
      "sector": 1,
      "sector_name": "Nyaruguru",
      "washing_station": 1,
      "washing_station_name": "Nyaruguru Station",
      "risk_status": "pending",
      "risk_checked_at": null,
      "registered_at": "2026-09-22T11:55:05.367571Z"
    }

risk_status and risk_checked_at are read-only - they are only ever
updated by the background risk check, never directly by a client.

Example error (400 Bad Request) - non-existent farmer:

    {
      "farmer": ["Invalid pk \"9999\" - object does not exist."]
    }

Filtering: /api/plots/?search=Nyaruguru searches by sector name or
washing station name.

### Deliveries (station-facing delivery feed)

    GET  /api/deliveries/
    POST /api/deliveries/

Deliveries can be recorded against a Plot regardless of its
risk_status - see ADR.md, Decision 2, for why.

Example request (POST):

    {
      "plot": 1,
      "weight_kg": 45.50
    }

Example response (201 Created):

    {
      "id": 1,
      "plot": 1,
      "plot_sector": "Nyaruguru",
      "plot_washing_station": "Nyaruguru Station",
      "plot_risk_status": "pending",
      "weight_kg": "45.50",
      "recorded_at": "2026-09-22T11:56:41.664260Z"
    }

Example error (400 Bad Request) - invalid weight:

    {
      "weight_kg": ["Delivery weight must be greater than zero."]
    }

GET /api/deliveries/ is paginated (see Performance section below) and
ordered most-recent-first. Example paginated response shape:

    {
      "count": 26,
      "next": "http://127.0.0.1:8000/api/deliveries/?page=2",
      "previous": null,
      "results": [ ... up to 20 deliveries ... ]
    }

### Price Schedule (Task 4 mandatory endpoint)

    GET /api/price-schedule/

Read-only. Price management (who sets prices, approval flow) is out
of scope for this MVP - see ADR.md.

Example response (200 OK):

    [
      {
        "id": 1,
        "season_label": "2026 Main Harvest",
        "price_per_kg": "350.00",
        "effective_from": "2026-09-22T18:07:34.421801Z",
        "is_active": true
      }
    ]

## Performance Foundation (Task 4)

This project implements pagination (not caching) as its assessed
performance feature, applied to GET /api/deliveries/.

### Why pagination over caching

Emmanuel records deliveries on a phone on 2G during harvest peak
(~400 deliveries/day at one station), with farmers queuing at the
scale. An unpaginated delivery feed becomes a large, slow-to-download
JSON payload as deliveries accumulate over a harvest season - this is
a payload-size problem that directly affects Emmanuel's environment.

GET /api/price-schedule/ (the pricing path) is a small, low-traffic,
low-volume endpoint by contrast - it does not have the volume or
payload-size problem that caching solves well, so caching it would
not have addressed the constraint the brief actually describes.

### How it works

- Page size defaults to 20 deliveries per page.
- Callers can request a different page size with ?page_size=N (up to
  a max of 100), and a specific page with ?page=N.
- Responses include count, next, previous, and results fields (DRF's
  standard PageNumberPagination shape).

Tested manually: with 26 deliveries in the database, GET
/api/deliveries/ returns page 1 (20 results, next populated, previous
null), and GET /api/deliveries/?page=2 returns the remaining 6
results (next null, previous populated). An empty delivery table
returns results: [] with count: 0 rather than an error.

Since pagination (not caching) was chosen, cache invalidation does
not apply to this MVP - see ADR.md, Decision 4.

## AI-Use Disclosure

AI assistance (Claude, via Anthropic) was used during this project for:

- Scaffolding Django/DRF boilerplate (project structure, serializer
  and viewset patterns, URL routing).
- Explaining DRF conventions and Django ORM behavior while building.
- Drafting this README and initial structure for ADR.md.
- Debugging file-save and PowerShell encoding issues during
  development.

The architecture decisions themselves - what to build, which
trade-offs to accept, and the reasoning in ADR.md - reflect my own
analysis of the Kawa Network brief and stakeholder constraints, and
were reviewed and written in my own words prior to submission.
