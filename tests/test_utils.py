"""
Tests for utils.py - Week calculations, validation, and formatting.
"""

import pytest
from datetime import date
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import (
    PERIOD_START, PERIOD_END,
    compute_week_index, get_week_boundaries, get_all_weeks, get_total_weeks,
    format_hhmm, validate_duration, validate_date_in_range,
    validate_action, validate_entry, normalize_matter_name
)


class TestWeekCalculations:
    """Test week index and boundary calculations."""
    
    def test_week_index_first_day(self):
        """2024-06-01 should be week 1."""
        assert compute_week_index(date(2024, 6, 1)) == 1
    
    def test_week_index_last_day_of_week1(self):
        """2024-06-07 should be week 1."""
        assert compute_week_index(date(2024, 6, 7)) == 1
    
    def test_week_index_first_day_of_week2(self):
        """2024-06-08 should be week 2."""
        assert compute_week_index(date(2024, 6, 8)) == 2
    
    def test_week_index_mid_period(self):
        """Test a date in the middle of the period."""
        # 2024-07-01 is 30 days after start, so day 31, which is week 5
        assert compute_week_index(date(2024, 7, 1)) == 5
    
    def test_week_index_last_day(self):
        """2024-12-31 should be week 31."""
        # Days from 2024-06-01 to 2024-12-31: 214 days (0-indexed: day 213)
        # Week = 213 // 7 + 1 = 30 + 1 = 31
        assert compute_week_index(date(2024, 12, 31)) == 31
    
    def test_week_index_out_of_range_before(self):
        """Date before period should raise ValueError."""
        with pytest.raises(ValueError):
            compute_week_index(date(2024, 5, 31))
    
    def test_week_index_out_of_range_after(self):
        """Date after period should raise ValueError."""
        with pytest.raises(ValueError):
            compute_week_index(date(2025, 1, 1))
    
    def test_week_boundaries_week1(self):
        """Week 1 boundaries should be 2024-06-01 to 2024-06-07."""
        start, end = get_week_boundaries(1)
        assert start == date(2024, 6, 1)
        assert end == date(2024, 6, 7)
    
    def test_week_boundaries_week2(self):
        """Week 2 boundaries should be 2024-06-08 to 2024-06-14."""
        start, end = get_week_boundaries(2)
        assert start == date(2024, 6, 8)
        assert end == date(2024, 6, 14)
    
    def test_week_boundaries_last_week(self):
        """Last week should end at 2024-12-31."""
        start, end = get_week_boundaries(31)
        assert end == date(2024, 12, 31)
    
    def test_get_all_weeks_count(self):
        """Should return 31 weeks."""
        weeks = get_all_weeks()
        assert len(weeks) == 31
    
    def test_get_all_weeks_first(self):
        """First week should be correct."""
        weeks = get_all_weeks()
        assert weeks[0]['week_index'] == 1
        assert weeks[0]['week_start'] == date(2024, 6, 1)
        assert weeks[0]['week_end'] == date(2024, 6, 7)
    
    def test_get_all_weeks_last(self):
        """Last week should be correct."""
        weeks = get_all_weeks()
        assert weeks[-1]['week_index'] == 31
        assert weeks[-1]['week_end'] == date(2024, 12, 31)
    
    def test_get_total_weeks(self):
        """Total weeks should be 31."""
        assert get_total_weeks() == 31


class TestDurationValidation:
    """Test duration validation (15-minute increments)."""
    
    def test_valid_15(self):
        """15 minutes should be valid."""
        is_valid, error = validate_duration(15)
        assert is_valid is True
        assert error is None
    
    def test_valid_30(self):
        """30 minutes should be valid."""
        is_valid, error = validate_duration(30)
        assert is_valid is True
    
    def test_valid_45(self):
        """45 minutes should be valid."""
        is_valid, error = validate_duration(45)
        assert is_valid is True
    
    def test_valid_60(self):
        """60 minutes should be valid."""
        is_valid, error = validate_duration(60)
        assert is_valid is True
    
    def test_valid_large(self):
        """Large multiples of 15 should be valid."""
        is_valid, error = validate_duration(480)  # 8 hours
        assert is_valid is True
    
    def test_invalid_zero(self):
        """0 minutes should be invalid."""
        is_valid, error = validate_duration(0)
        assert is_valid is False
        assert "greater than 0" in error.lower()
    
    def test_invalid_negative(self):
        """Negative duration should be invalid."""
        is_valid, error = validate_duration(-15)
        assert is_valid is False
    
    def test_invalid_not_multiple_10(self):
        """10 minutes (not multiple of 15) should be invalid."""
        is_valid, error = validate_duration(10)
        assert is_valid is False
        assert "multiple of 15" in error.lower()
    
    def test_invalid_not_multiple_20(self):
        """20 minutes (not multiple of 15) should be invalid."""
        is_valid, error = validate_duration(20)
        assert is_valid is False
    
    def test_invalid_not_integer(self):
        """Non-integer should be invalid."""
        is_valid, error = validate_duration(15.5)
        assert is_valid is False


class TestDateValidation:
    """Test date range validation."""
    
    def test_valid_start(self):
        """Start date should be valid."""
        assert validate_date_in_range(date(2024, 6, 1)) is True
    
    def test_valid_end(self):
        """End date should be valid."""
        assert validate_date_in_range(date(2024, 12, 31)) is True
    
    def test_valid_middle(self):
        """Middle date should be valid."""
        assert validate_date_in_range(date(2024, 9, 15)) is True
    
    def test_invalid_before(self):
        """Date before range should be invalid."""
        assert validate_date_in_range(date(2024, 5, 31)) is False
    
    def test_invalid_after(self):
        """Date after range should be invalid."""
        assert validate_date_in_range(date(2025, 1, 1)) is False
    
    def test_invalid_way_before(self):
        """Date way before range should be invalid."""
        assert validate_date_in_range(date(2023, 1, 1)) is False


class TestFormatting:
    """Test time formatting."""
    
    def test_format_15(self):
        """15 minutes should be 00:15."""
        assert format_hhmm(15) == "00:15"
    
    def test_format_30(self):
        """30 minutes should be 00:30."""
        assert format_hhmm(30) == "00:30"
    
    def test_format_60(self):
        """60 minutes should be 01:00."""
        assert format_hhmm(60) == "01:00"
    
    def test_format_90(self):
        """90 minutes should be 01:30."""
        assert format_hhmm(90) == "01:30"
    
    def test_format_large(self):
        """480 minutes (8 hours) should be 08:00."""
        assert format_hhmm(480) == "08:00"
    
    def test_format_very_large(self):
        """720 minutes (12 hours) should be 12:00."""
        assert format_hhmm(720) == "12:00"
    
    def test_format_zero(self):
        """0 minutes should be 00:00."""
        assert format_hhmm(0) == "00:00"
    
    def test_format_negative(self):
        """Negative minutes should be 00:00."""
        assert format_hhmm(-15) == "00:00"


class TestMatterNameNormalization:
    """Test matter name normalization."""
    
    def test_lowercase(self):
        """Should lowercase."""
        assert normalize_matter_name("Test Matter") == "test matter"
    
    def test_strip_whitespace(self):
        """Should strip whitespace."""
        assert normalize_matter_name("  Test  ") == "test"
    
    def test_hebrew(self):
        """Should work with Hebrew."""
        assert normalize_matter_name("תיק בדיקה") == "תיק בדיקה"


class TestActionValidation:
    """Test action validation."""
    
    def test_valid_action(self):
        """Valid action should pass."""
        action = {"action_description": "Test work", "duration_minutes": 30}
        is_valid, error = validate_action(action)
        assert is_valid is True
    
    def test_empty_description(self):
        """Empty description should fail."""
        action = {"action_description": "", "duration_minutes": 30}
        is_valid, error = validate_action(action)
        assert is_valid is False
        assert "empty" in error.lower()
    
    def test_whitespace_description(self):
        """Whitespace-only description should fail."""
        action = {"action_description": "   ", "duration_minutes": 30}
        is_valid, error = validate_action(action)
        assert is_valid is False
    
    def test_invalid_duration(self):
        """Invalid duration should fail."""
        action = {"action_description": "Test", "duration_minutes": 10}
        is_valid, error = validate_action(action)
        assert is_valid is False


class TestEntryValidation:
    """Test complete entry validation."""
    
    def test_valid_entry(self):
        """Valid entry should pass."""
        entry = {
            "entry_date": date(2024, 6, 15),
            "matter_id": "test-uuid",
            "actions": [
                {"action_description": "Work 1", "duration_minutes": 30},
                {"action_description": "Work 2", "duration_minutes": 45}
            ]
        }
        is_valid, errors = validate_entry(entry)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_missing_date(self):
        """Missing date should fail."""
        entry = {
            "matter_id": "test-uuid",
            "actions": [{"action_description": "Work", "duration_minutes": 30}]
        }
        is_valid, errors = validate_entry(entry)
        assert is_valid is False
        assert any("date" in e.lower() for e in errors)
    
    def test_out_of_range_date(self):
        """Out of range date should fail."""
        entry = {
            "entry_date": date(2025, 1, 1),
            "matter_id": "test-uuid",
            "actions": [{"action_description": "Work", "duration_minutes": 30}]
        }
        is_valid, errors = validate_entry(entry)
        assert is_valid is False
    
    def test_missing_matter(self):
        """Missing matter should fail."""
        entry = {
            "entry_date": date(2024, 6, 15),
            "actions": [{"action_description": "Work", "duration_minutes": 30}]
        }
        is_valid, errors = validate_entry(entry)
        assert is_valid is False
        assert any("matter" in e.lower() for e in errors)
    
    def test_no_actions(self):
        """No actions should fail."""
        entry = {
            "entry_date": date(2024, 6, 15),
            "matter_id": "test-uuid",
            "actions": []
        }
        is_valid, errors = validate_entry(entry)
        assert is_valid is False
        assert any("action" in e.lower() for e in errors)
    
    def test_invalid_action_in_entry(self):
        """Entry with invalid action should fail."""
        entry = {
            "entry_date": date(2024, 6, 15),
            "matter_id": "test-uuid",
            "actions": [
                {"action_description": "Valid", "duration_minutes": 30},
                {"action_description": "", "duration_minutes": 15}  # Invalid
            ]
        }
        is_valid, errors = validate_entry(entry)
        assert is_valid is False
