"""Print the campus network with real distances, so it can be checked.

The coordinates in ``data/routes/*.json`` are hand-placed. This prints what
they actually mean on the ground - route lengths, stop-to-stop distances, the
network's footprint - so they can be compared against Google Maps and
corrected, rather than being trusted because they look about right.

    python scripts/inspect_network.py
    python scripts/inspect_network.py --stop "PRP Block"

Correcting a coordinate takes about ten seconds:

1. Right-click the building in Google Maps and click the lat/lng to copy it.
2. Paste it into the stop's ``latitude`` and ``longitude`` in the route JSON.
3. Update the matching ``[longitude, latitude]`` entry in ``geometry`` - note
   the order is reversed there, because that is what MapLibre expects.
4. Re-run this script; the map, distances and ETAs all follow the data.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Run from anywhere: make the app package importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.data.repository import JsonRouteRepository  # noqa: E402
from app.geo import haversine_distance  # noqa: E402
from app.geo.route_geometry import RouteGeometry  # noqa: E402
from app.models import Route  # noqa: E402


def describe_route(route: Route) -> None:
    geometry = RouteGeometry.build(route)

    print(f"\n{route.id}  {route.name}")
    print(f"  {'-' * 66}")
    print(
        f"  {len(route.geometry)} geometry points, {len(route.stops)} stops, "
        f"{route.loop_mode.value.lower()}s at the end"
    )
    print(f"  Route length: {geometry.total_distance_m:,.0f} m")

    average_speed = route.average_speed_kmh
    lap_seconds = geometry.total_distance_m / 1000 / average_speed * 3600
    print(f"  One lap at {average_speed:.0f} km/h: {lap_seconds / 60:.1f} min")

    print(f"\n  {'stop':<28}{'along route':>12}{'from previous':>15}")
    previous = None
    for stop, along in zip(route.stops, geometry.stop_distances, strict=True):
        gap = "" if previous is None else f"{haversine_distance(previous, stop.position):>12,.0f} m"
        print(f"  {stop.name:<28}{along:>10,.0f} m{gap:>15}")
        previous = stop.position


def describe_network(routes: tuple[Route, ...]) -> None:
    points = [point for route in routes for point in route.geometry]
    latitudes = [point.latitude for point in points]
    longitudes = [point.longitude for point in points]

    south, north = min(latitudes), max(latitudes)
    west, east = min(longitudes), max(longitudes)

    # A degree of latitude is ~111.2 km; longitude shrinks by cos(latitude).
    height_m = (north - south) * 111_195
    width_m = (east - west) * 111_195 * 0.974

    print("\nNetwork footprint")
    print(f"  {'-' * 66}")
    print(f"  latitude  {south:.5f} .. {north:.5f}   ({height_m:,.0f} m north-south)")
    print(f"  longitude {west:.5f} .. {east:.5f}   ({width_m:,.0f} m east-west)")
    print(f"  centre    {(south + north) / 2:.5f}, {(west + east) / 2:.5f}")
    print(f"  stops     {sum(len(route.stops) for route in routes)}")
    print("\n  Paste the centre into Google Maps to see where this actually is.")


def distances_from(routes: tuple[Route, ...], stop_name: str) -> None:
    """Every stop's straight-line distance from one named stop."""
    stops = {stop.name: stop for route in routes for stop in route.stops}

    origin = stops.get(stop_name)
    if origin is None:
        print(f"\nNo stop named {stop_name!r}. Known stops:")
        for name in sorted(stops):
            print(f"  {name}")
        return

    print(f"\nStraight-line distance from {origin.name}")
    print(f"  {'-' * 66}")

    measured = sorted(
        (haversine_distance(origin.position, stop.position), stop.name) for stop in stops.values()
    )
    for distance, name in measured:
        print(f"  {name:<32}{distance:>10,.0f} m")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stop", help="Show every distance from this stop.")
    arguments = parser.parse_args()

    routes = JsonRouteRepository(get_settings().routes_dir).list_routes()

    for route in routes:
        describe_route(route)

    describe_network(routes)

    if arguments.stop:
        distances_from(routes, arguments.stop)


if __name__ == "__main__":
    main()
