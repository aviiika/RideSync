"""Data access layer.

Routes and stops are static seed data, so the MVP reads them from JSON on the
filesystem. Everything above this package depends on the
:class:`~app.data.repository.RouteRepository` protocol rather than on JSON, so
a PostgreSQL/PostGIS implementation can be introduced later without touching
the services, API or simulation engine.
"""
