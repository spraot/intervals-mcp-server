"""Manual live check of add_or_update_event against the real Intervals.icu API.

This is NOT part of the pytest suite (pytest only collects ``test_*.py``): it makes
real API calls using the API_KEY and ATHLETE_ID from your .env, and it creates one
throwaway event on far-future dates, exercises every create/update/clear path, and
deletes it again. It touches no other event.

Run it from the repository root, where .env lives:

    .venv/bin/python tests/manual/live_event_check.py

It prints a PASS/FAIL line per check. The dates below are deliberately far in the
future so the test event never lands in real training; change them if they collide.

Known Intervals.icu behavior this check pins down, so the output is not surprising:
  - An update merges: a field left out of the body keeps its stored value, and an
    explicit null is ignored, which is why clearing sends "" / 0 instead.
  - moving_time and distance are computed from the workout steps whenever the event
    has a description, so a value sent alongside workout_doc does not stick, and
    distance stays 0 once an event has ever had a description (an empty one included).
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from intervals_mcp_server.server import (  # noqa: E402
    ATHLETE_ID,
    add_or_update_event,
    delete_event,
    httpx_client,
    make_intervals_request,
)
from intervals_mcp_server.utils.types import WorkoutDoc  # noqa: E402

DATE, MOVED = "2027-04-12", "2027-04-15"
NAME = "MCP live check - safe to delete"
results = []


def check(label, ok, detail=""):
    results.append((label, ok))
    print(f"  {'PASS' if ok else 'FAIL'}  {label}{(' -- ' + detail) if detail else ''}")


async def fetch(eid):
    return await make_intervals_request(url=f"/athlete/{ATHLETE_ID}/events/{eid}")


async def main():
    doc = WorkoutDoc.from_dict({
        "description": "MCP regression test",
        "steps": [{"duration": 600, "power": {"value": 60, "units": "%ftp"}, "warmup": True},
                  {"duration": 300, "power": {"value": 90, "units": "%ftp"}}],
    })

    print("[1] create")
    msg = await add_or_update_event(
        start_date=DATE, name=NAME, workout_type="Ride", workout_doc=doc
    )
    if "Successfully created event: " not in msg:
        print("  create failed: " + msg[:300])
        return
    eid = str(json.loads(msg.split("Successfully created event: ", 1)[1])["id"])
    print(f"  event id {eid}")
    base = await fetch(eid)
    check("created on requested date", base.get("start_date_local", "").startswith(DATE),
          str(base.get("start_date_local")))
    check("description stored", bool(base.get("description")))
    check("type stored", base.get("type") == "Ride", str(base.get("type")))
    check("category WORKOUT", base.get("category") == "WORKOUT", str(base.get("category")))
    print(f"  computed moving_time={base.get('moving_time')} distance={base.get('distance')}")

    try:
        print("\n[2] update name only")
        await add_or_update_event(event_id=eid, name=NAME + " (renamed)")
        e = await fetch(eid)
        check("name changed", e.get("name") == NAME + " (renamed)", str(e.get("name")))
        check("date unchanged", e.get("start_date_local") == base.get("start_date_local"),
              str(e.get("start_date_local")))
        check("description unchanged", e.get("description") == base.get("description"))
        check("type unchanged", e.get("type") == base.get("type"), str(e.get("type")))
        check("category unchanged", e.get("category") == base.get("category"),
              str(e.get("category")))
        check("moving_time unchanged", e.get("moving_time") == base.get("moving_time"),
              str(e.get("moving_time")))

        print("\n[3] update start_date only")
        await add_or_update_event(event_id=eid, start_date=MOVED)
        e = await fetch(eid)
        check("date moved", e.get("start_date_local", "").startswith(MOVED),
              str(e.get("start_date_local")))
        check("name kept while moving", e.get("name") == NAME + " (renamed)", str(e.get("name")))
        check("description kept while moving", e.get("description") == base.get("description"))

        print("\n[4] update workout_type only")
        await add_or_update_event(event_id=eid, workout_type="Run")
        e = await fetch(eid)
        check("type changed", e.get("type") == "Run", str(e.get("type")))
        check("name kept", e.get("name") == NAME + " (renamed)", str(e.get("name")))

        print("\n[5] clear sentinels")
        await add_or_update_event(
            event_id=eid, workout_doc=WorkoutDoc(), moving_time=0, distance=0
        )
        e = await fetch(eid)
        check("description CLEARED", not e.get("description"), repr(e.get("description"))[:40])
        check("moving_time CLEARED", not e.get("moving_time"), str(e.get("moving_time")))
        check("distance CLEARED", not e.get("distance"), str(e.get("distance")))
        check("date survived clearing", e.get("start_date_local", "").startswith(MOVED),
              str(e.get("start_date_local")))
        check("name survived clearing", e.get("name") == NAME + " (renamed)", str(e.get("name")))

        print("\n[6] set moving_time on an event whose steps were cleared")
        await add_or_update_event(event_id=eid, moving_time=3600, distance=20000)
        e = await fetch(eid)
        check("moving_time set", e.get("moving_time") == 3600, str(e.get("moving_time")))
        # Intervals.icu pins distance to the (now empty) step total, so 20000 is dropped.
        check("distance stays computed from steps", not e.get("distance"),
              str(e.get("distance")))

        print("\n[7] empty update is refused without an API call")
        out = await add_or_update_event(event_id=eid)
        check("empty update refused", "Nothing to update" in out, out[:80])
        e = await fetch(eid)
        check("event untouched by refusal", e.get("moving_time") == 3600, str(e.get("moving_time")))
    finally:
        print("\n[8] cleanup")
        await delete_event(event_id=eid)
        gone = await fetch(eid)
        check("test event deleted", isinstance(gone, dict) and bool(gone.get("error")))

    failed = [r[0] for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        print("failed: " + ", ".join(failed))


async def run():
    try:
        await main()
    finally:
        await httpx_client.aclose()


asyncio.run(run())
