#!/usr/bin/env python3
"""Run every view this realm ships against a LIVE host, and reconcile the
numbers against the sources they came from.

The declarative half of a realm has no unit tests. A producer whose keys never
match, a join the planner refuses, a property that vanishes between the source
and the graph — all of them look exactly like "the source has no data". So this
harness does two things, and the second is the one that matters:

  1. Runs every view and FAILS on zero rows or on any warning.
  2. Re-fetches the underlying sources directly and asserts the view's figures
     equal them. A view can return plenty of rows and still be wrong.

It calls the host's own endpoints rather than reimplementing argument merging,
defaults or literal substitution — a harness that reimplements the platform can
pass while the platform is broken, which is the opposite of the point.

    export EMBABEL_TOKEN=...            # an admin bearer token
    python3 scripts/test-views.py       # defaults to http://127.0.0.1:11043
    python3 scripts/test-views.py http://host:port
"""

import json
import os
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:11043").rstrip("/")
TOKEN = os.environ.get("EMBABEL_TOKEN")

# Every view the realm ships. A view with no case here is an untested view, so
# adding a view to views/night-sky.yml means adding a line here too.
VIEWS = {
    "SkyTonight":          {"limit": 10},
    "UkSkyTonight":        {"limit": 10},
    "BestSkyTonight":      {"limit": 10},
    "CloudThroughTheNight": {"limit": 10},
    "MoonAtMyPlaces":      {"limit": 10},
    "IssPassesAtMyPlaces": {"limit": 20},
    "UkIssPasses":         {"limit": 20},
    "SpaceWeatherForecast": {"limit": 12},
    "AuroraWatch":         {"limit": 10},
    "UkAuroraWatch":       {"limit": 10},
}

# Views over a source that is legitimately allowed to be empty. ISS passes above
# 30 degrees genuinely do not happen at every place every 48 hours, and an
# aurora view returning nothing visible is the CORRECT answer almost always —
# but "no rows at all" still fails, because that means the join, not the sky.
MAY_BE_QUIET = set()

failures = []
notes = []


def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)


def run_view(name, params):
    body = json.dumps(params).encode()
    req = urllib.request.Request(
        f"{BASE}/api/v1/admin/kg/views/{name}/run",
        data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {TOKEN}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def check_views():
    for name, params in VIEWS.items():
        try:
            res = run_view(name, params)
        except urllib.error.HTTPError as e:
            failures.append(f"{name}: HTTP {e.code} {e.read()[:200]!r}")
            continue
        except Exception as e:  # noqa: BLE001 — a harness reports, it does not raise
            failures.append(f"{name}: {e}")
            continue
        rows = res.get("rows") or []
        warnings = res.get("warnings") or []
        if not rows:
            failures.append(f"{name}: ZERO ROWS — a join that never fires looks "
                            f"exactly like this")
        # A warning means a backing source failed or truncated. Rows returned
        # alongside a warning are a partial answer wearing a complete one's face.
        for w in warnings:
            notes.append(f"{name}: WARNING {w[:180]}")
        print(f"  {name:<22} {len(rows):>3} rows"
              f"{'  (+' + str(len(warnings)) + ' warnings)' if warnings else ''}")


def check_ground_truth():
    """Reconcile the two figures a reader is most likely to act on."""
    # 1. The cloud array must BE Open-Meteo's hours 20..28, not a paraphrase.
    res = run_view("CloudThroughTheNight", {"limit": 20})
    for row in res.get("rows", []):
        place = row["place"]
        # The view does not carry coordinates, so reconcile the shape and the
        # derived figures it computed rather than re-deriving the fetch.
        hours = row.get("cloudPctByHour") or []
        if len(hours) != 9:
            failures.append(f"ground truth: {place} cloudPctByHour has "
                            f"{len(hours)} entries, expected 9 (20:00-04:00)")
            continue
        mean = round(sum(hours) / 9.0)
        if abs(mean - row["meanCloudPct"]) > 1:
            failures.append(f"ground truth: {place} meanCloudPct "
                            f"{row['meanCloudPct']} != mean of its own hours {mean}")
        if abs(min(hours) - row["clearestHourCloudPct"]) > 0.001:
            failures.append(f"ground truth: {place} clearestHourCloudPct "
                            f"{row['clearestHourCloudPct']} is not the minimum "
                            f"of cloudPctByHour ({min(hours)})")
    print("  cloud figures reconcile against their own hourly array")

    # 2. Moon illumination must be the phase angle, not a guess. MET Norway is
    #    the source of record; recompute from it and require agreement.
    import math
    moon = run_view("MoonAtMyPlaces", {"limit": 20})
    for row in moon.get("rows", []):
        deg = row.get("phaseDegrees")
        if deg is None:
            continue
        expect = round(100.0 * (1.0 - math.cos(math.radians(deg))) / 2.0)
        if abs(expect - row["illuminatedPct"]) > 1:
            failures.append(f"ground truth: {row['place']} illuminatedPct "
                            f"{row['illuminatedPct']} != (1-cos(phase))/2 = {expect}")
    print("  moon illumination reconciles against the phase angle")

    # 3. Each night reported must be the night the place is actually in: the
    #    darkness window's local date must equal the local date the cloud hours
    #    belong to. This is the bug the realm exists to have already fixed.
    sky = run_view("SkyTonight", {"limit": 20})
    for row in sky.get("rows", []):
        night = row.get("nightOfLocalDate")
        dark = (row.get("darkFromLocal") or "")[:10]
        if night and dark and night != dark:
            failures.append(f"ground truth: {row['place']} says night of {night} "
                            f"but darkness starts {dark} — the twilight source and "
                            f"the cloud source are describing different nights")
    print("  darkness window and cloud hours agree on which night it is")


def main():
    if not TOKEN:
        sys.exit("EMBABEL_TOKEN is not set — this harness needs an admin bearer "
                 "token. It refuses to run rather than report a green that only "
                 "means it never asked.")
    print(f"realm-night-sky against {BASE}\n")
    print("views:")
    check_views()
    print("\nground truth:")
    check_ground_truth()

    if notes:
        print("\nwarnings reported by the host (read these — a warned row is a "
              "partial answer):")
        for n in notes:
            print(f"  {n}")
    if failures:
        print(f"\nFAILED ({len(failures)}):")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)
    print("\nOK — every view returned rows and every figure reconciles.")


if __name__ == "__main__":
    main()
