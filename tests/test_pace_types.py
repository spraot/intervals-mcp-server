import json
from src.intervals_mcp_server.utils.types import Value, ValueUnits, PaceUnits


def test_value_pace_km_single():
    v = Value(value=435, units=ValueUnits.PACE, pace_units=PaceUnits.MINS_KM)
    # 435s = 7:15 per km
    assert str(v) == "7:15/km Pace"


def test_value_pace_km_range():
    v = Value(start=435, end=420, units=ValueUnits.PACE, pace_units=PaceUnits.MINS_KM)
    assert str(v) == "7:15-7:00/km Pace"


def test_value_pace_100m_single():
    v = Value(value=90, units=ValueUnits.PACE, pace_units=PaceUnits.SECS_100M)
    # 1:30 per 100m
    assert str(v) == "1:30/100m Pace"


def test_value_pace_400m_single():
    v = Value(value=75, units=ValueUnits.PACE, pace_units=PaceUnits.SECS_400M)
    # 1:15 per 400m
    assert str(v) == "1:15/400m Pace"


def test_value_pace_500m_single():
    v = Value(value=120, units=ValueUnits.PACE, pace_units=PaceUnits.SECS_500M)
    assert str(v) == "2:00/500m Pace"


def test_value_pace_100y_single():
    v = Value(value=85, units=ValueUnits.PACE, pace_units=PaceUnits.SECS_100Y)
    assert str(v) == "1:25/100y Pace"


def test_value_pace_250m_single():
    v = Value(value=60, units=ValueUnits.PACE, pace_units=PaceUnits.SECS_250M)
    assert str(v) == "1:00/250m Pace"


def test_value_pace_mile_single():
    v = Value(value=480, units=ValueUnits.PACE, pace_units=PaceUnits.MINS_MILE)
    assert str(v) == "8:00/mi Pace"


def test_value_pace_default_suffix_is_km():
    v = Value(value=300, units=ValueUnits.PACE)
    # defaults to /km when no pace_units provided
    assert str(v) == "5:00/km Pace"


def test_value_pace_serialization_roundtrip():
    v = Value(start=435, end=420, units=ValueUnits.PACE, pace_units=PaceUnits.MINS_KM)
    d = v.to_dict()
    assert d["units"] == ValueUnits.PACE.value
    assert d["pace_units"] == PaceUnits.MINS_KM.value
    j = v.to_json()
    d2 = json.loads(j)
    assert d2["pace_units"] == PaceUnits.MINS_KM.value
    v2 = Value.from_json(j)
    assert v2.pace_units == PaceUnits.MINS_KM


def test_pace_units_enum_has_track_units():
    # ensure the new units exist
    assert hasattr(PaceUnits, "SECS_400M")
    assert hasattr(PaceUnits, "SECS_250M")
