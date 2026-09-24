# Architecture Decision Record - Kawa Network MVP (Formative 1)

## Context

Kawa Network needs a delivery-tracking API for Emmanuel's washing station pilot at
Nyaruguru. Three constraints shape every decision below:

- The external compliance/risk registry is slow (2-40s) and unreliable
  (down for hours at a time).
- Harvest peak is ~400 deliveries/day at one station, recorded on a phone
  on 2G, with farmers queuing at the scale.
- Three stakeholders pull in different directions: Patrick (buyer
  traceability), Jeanne (same-day accurate pay), Emmanuel (fast recording
  under poor connectivity).

## Decision 1: Provenance modeled as normalized relations, not strings

Sector and WashingStation are separate models with foreign keys from
Plot, rather than free-text fields on Plot.

**What it improves:** Formative 2 explicitly scopes API access against
sector and washing_station. Modeling them as real entities now means
F2's permission logic can filter on a foreign key relationship instead of
string matching, which is more reliable and avoids a painful migration
later.

**What it makes harder:** registering a Plot now requires the Sector and
WashingStation to already exist as rows (two extra setup requests), rather
than accepting arbitrary text.

**Who benefits most:** Patrick - the provenance chain (delivery -> plot ->
sector/station) is the traceability data buyers need, and it's more
trustworthy as a real relation than as free text.

**Trade-off named:** this is more setup cost now for a benefit that only
pays off in F2. It's justified because the brief tells us F2 depends on
it - we are not guessing at future requirements, we are following an
explicit one.

## Decision 2: Async risk checks never block delivery recording

When a Plot is registered, a risk check is queued in a background thread
(Python threading, not Celery - see Decision 3) against a simulated
external registry. Deliveries can be recorded against a Plot regardless
of its risk_status - including while it is still pending, and even
if the risk check never resolves at all.

**What it improves:** this directly satisfies the constraint that Emmanuel
cannot hold a farmer at the scale while a slow or down registry responds.
During a registry outage (simulated at ~20% in our implementation),
deliveries keep flowing and Jeanne can still pay farmers the same day.

**What it makes harder:** a plot's provenance can be "unverified" (pending)
indefinitely if the registry never successfully responds for that plot.
Buyer-facing traceability (Patrick's concern) can therefore include
deliveries whose compliance status was never confirmed.

**Position on a check that never resolves:** the delivery is still
recorded. risk_status simply remains pending, and risk_checked_at
stays null. This is a queryable, honest signal - any consumer of the
API (including a future F2 permission layer or buyer-facing report) can
filter on risk_status to distinguish verified from unverified plots.
We do not retroactively block or hide deliveries from an unresolved plot.

**Who benefits most:** Emmanuel and Jeanne. This is a deliberate trade-off
against Patrick's stricter-compliance interest, named here rather than
hidden - a stricter design would block deliveries until risk_status
resolves, at the cost of exactly the delay the brief says the field
cannot tolerate.

**Evidence of non-blocking behaviour:** verified manually - a POST
/api/plots/ request returns 201 Created with risk_status: "pending"
in well under a second, while the background thread's "risk check
completed" log line appears several seconds later, after the HTTP
response was already sent. Every check attempt (started, completed, or
failed due to simulated registry unavailability) is logged via Django's
logging framework to the console.

## Decision 3: Python threading, not Celery, for background work

**What it improves:** zero additional infrastructure - no message broker
(Redis/RabbitMQ) to install, run, or document. This keeps Task 5's
"another developer can run this independently" trivially true: pip
install -r requirements.txt and python manage.py runserver is the
entire setup.

**What it makes harder:** threads are not durable - if the server process
restarts mid-check, that check is simply lost (no retry queue, no
persistence). Celery would solve this properly.

**Non-functional requirement stressed:** reliability/durability of
background work is weaker than a production system would want.

**Justification:** this is a deliberate MVP-scope simplification, not an
oversight. The brief asks for "non-blocking behaviour and evidence that
attempts are recorded or logged" - both of which threading plus
Django logging satisfy directly - not for a production-grade task queue.
A real deployment would very likely move to Celery; that migration is a
reasonable, explicitly-scoped piece of future work.

## Decision 4: Pagination over caching for the Task 4 performance requirement

GET /api/deliveries/ is paginated (default page size 20, tunable via
?page_size=) rather than cached.

**Whose problem this solves first:** Emmanuel's. The brief states his
phone is on 2G at harvest peak with a queue of farmers watching. A large,
unpaginated delivery feed is a payload-size problem before it is a
compute problem - pagination directly reduces what has to travel over a
slow connection. GET /api/price-schedule/ (the pricing path) is a small,
low-traffic, non-paginated endpoint by contrast; caching it would have
solved a problem the pricing path doesn't really have at MVP scale (low
request volume, small payload already).

**Trade-off named:** we did not implement caching or address cache
invalidation, since it wasn't the problem we chose to solve. If a future
iteration adds caching to /api/price-schedule/, invalidation would need
to fire whenever a new PriceSchedule row is marked is_active=True.

## Summary of stakeholder trade-offs

| Decision | Favors | At the cost of |
|---|---|---|
| Normalized Sector/WashingStation | Patrick (traceability), future F2 access control | Slightly more setup per Plot |
| Non-blocking delivery recording despite unresolved risk | Emmanuel, Jeanne | Patrick (compliance certainty is delayed, not guaranteed) |
| Threading over Celery | Development speed, deployability | Durability of background work |
| Pagination over caching | Emmanuel (2G, harvest peak) | No caching benefit for the pricing path |

No single stakeholder is fully satisfied by every decision above - that
is intentional. The system is designed so risk_status is always visible
and honest, so future work (F2's access scoping, buyer-facing reports)
can layer additional trust decisions on top of accurate data, rather than
this MVP silently making that call for them.
