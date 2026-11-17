"""
Tests that WorkoutDoc.from_dict coerces the string-valued numbers that JSON payloads
carry, so a doc built from a dict formats the same way as one built through the MCP
schema (where pydantic does the coercion).
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from intervals_mcp_server.utils.types import (  # pylint: disable=wrong-import-position
    PaceUnits,
    Step,
    Value,
    ValueUnits,
    WorkoutDoc,
    as_float,
    as_int,
)

# The example from the add_or_update_event docstring, which quotes every number.
DOCSTRING_EXAMPLE = {
    "description": "High-intensity workout for increasing VO2 max",
    "steps": [
        {"power": {"value": "80", "units": "%ftp"}, "duration": "900", "warmup": True},
        {
            "reps": "2",
            "text": "High-intensity intervals",
            "steps": [
                {"power": {"value": "110", "units": "%ftp"}, "distance": "500"},
                {"power": {"value": "80", "units": "%ftp"}, "duration": "90"},
            ],
        },
        {"power": {"value": "80", "units": "%ftp"}, "duration": "600", "cooldown": True},
    ],
}


def test_docstring_example_renders():
    """The documented example must format without raising."""
    doc = WorkoutDoc.from_dict(DOCSTRING_EXAMPLE)
    rendered = str(doc)
    assert "High-intensity workout for increasing VO2 max" in rendered
    assert "15m" in rendered  # 900 seconds
    assert "80% ftp" in rendered
    assert "500mtr" in rendered


def test_string_numbers_are_coerced():
    """String-valued numbers end up as real numbers on the dataclasses."""
    doc = WorkoutDoc.from_dict(DOCSTRING_EXAMPLE)
    first, repeat = doc.steps[0], doc.steps[1]
    assert first.duration == 900 and isinstance(first.duration, int)
    assert first.power.value == 80.0 and isinstance(first.power.value, float)
    assert repeat.reps == 2 and isinstance(repeat.reps, int)
    assert repeat.steps[0].distance == 500.0 and isinstance(repeat.steps[0].distance, float)


def test_workout_doc_top_level_numbers_are_coerced():
    """The doc's own numeric fields are coerced too."""
    doc = WorkoutDoc.from_dict(
        {"duration": "3600", "distance": "40000.5", "ftp": "250", "lthr": "165",
         "threshold_pace": "3.5"}
    )
    assert doc.duration == 3600
    assert doc.distance == 40000.5
    assert doc.ftp == 250
    assert doc.lthr == 165
    assert doc.threshold_pace == 3.5


def test_value_range_strings_are_coerced():
    """Ranges and ramps given as strings still format as a range."""
    step = Step.from_dict(
        {"ramp": True, "duration": "300", "power": {"start": "80", "end": "90", "units": "%ftp"}}
    )
    assert step.power.start == 80.0
    assert step.power.end == 90.0
    assert "80%-90%" in str(step)


def test_zone_values_are_not_double_prefixed():
    """A zone given as "Z2" renders as Z2, and a bare 2 is prefixed."""
    assert str(Value.from_dict({"value": "Z2", "units": "power_zone"})) == "Z2 W"
    assert str(Value.from_dict({"value": "2", "units": "power_zone"})) == "Z2 W"


def test_pace_strings_are_coerced():
    """A pace given as a string still formats as mm:ss."""
    value = Value.from_dict({"value": "435", "units": "pace", "pace_units": "MINS_KM"})
    assert value.pace_units is PaceUnits.MINS_KM
    assert value.units is ValueUnits.PACE
    assert str(value) == "7:15/km Pace"


def test_uncoercible_values_do_not_raise():
    """Junk is left alone rather than crashing the formatter."""
    assert str(Step(duration="abc")).strip() == "- abc"
    assert str(Step(distance="abc")).strip() == "- abc"
    assert str(Value(value="abc", units=ValueUnits.WATTS)) == "abcW"


def test_coercion_helpers():
    """as_int and as_float coerce what they can and pass through what they cannot."""
    assert as_int("900") == 900
    assert as_int("900.7") == 900
    assert as_int(900) == 900
    assert as_int(None) is None
    assert as_int("Z2") == "Z2"
    assert as_int(True) is True
    assert as_float("40000.5") == 40000.5
    assert as_float(5) == 5.0
    assert as_float(None) is None
    assert as_float("abc") == "abc"
