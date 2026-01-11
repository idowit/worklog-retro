"""
Work Log - Utility Functions

Core helper functions for week calculations, validation, formatting, and RTL CSS.
"""

from datetime import date, timedelta
from typing import Tuple, List, Optional
import uuid

# Date range constants
PERIOD_START = date(2024, 6, 1)
PERIOD_END = date(2024, 12, 31)


def compute_week_index(entry_date: date) -> int:
    """
    Compute 1-based week index from the period start date.
    
    Weeks are consecutive 7-day blocks:
    - Week 1: 2024-06-01 to 2024-06-07
    - Week 2: 2024-06-08 to 2024-06-14
    - etc.
    
    Args:
        entry_date: The date to compute week index for
        
    Returns:
        1-based week index
        
    Raises:
        ValueError: If date is outside allowed range
    """
    if not validate_date_in_range(entry_date):
        raise ValueError(f"Date {entry_date} is outside allowed range ({PERIOD_START} to {PERIOD_END})")
    
    days_since_start = (entry_date - PERIOD_START).days
    week_index = (days_since_start // 7) + 1
    return week_index


def get_week_boundaries(week_index: int) -> Tuple[date, date]:
    """
    Get the start and end dates for a given week index.
    
    Args:
        week_index: 1-based week index
        
    Returns:
        Tuple of (start_date, end_date)
    """
    if week_index < 1:
        raise ValueError("Week index must be >= 1")
    
    start_date = PERIOD_START + timedelta(days=(week_index - 1) * 7)
    end_date = start_date + timedelta(days=6)
    
    # Clamp end date to period end
    if end_date > PERIOD_END:
        end_date = PERIOD_END
    
    return start_date, end_date


def get_all_weeks() -> List[dict]:
    """
    Generate a list of all weeks in the period.
    
    Returns:
        List of dicts with week_index, week_start, week_end
    """
    weeks = []
    current_date = PERIOD_START
    week_index = 1
    
    while current_date <= PERIOD_END:
        start_date, end_date = get_week_boundaries(week_index)
        weeks.append({
            'week_index': week_index,
            'week_start': start_date,
            'week_end': end_date
        })
        week_index += 1
        current_date = start_date + timedelta(days=7)
    
    return weeks


def get_total_weeks() -> int:
    """
    Get total number of weeks in the period.
    
    Returns:
        Total number of weeks (31)
    """
    total_days = (PERIOD_END - PERIOD_START).days + 1
    return (total_days + 6) // 7  # Ceiling division


def format_hhmm(minutes: int) -> str:
    """
    Format minutes as hh:mm string.
    
    Args:
        minutes: Total minutes
        
    Returns:
        Formatted string like "01:30" or "00:15"
    """
    if minutes < 0:
        return "00:00"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def validate_duration(minutes: int) -> Tuple[bool, Optional[str]]:
    """
    Validate that duration is a positive multiple of 15.
    
    Args:
        minutes: Duration in minutes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(minutes, int):
        return False, "Duration must be an integer"
    if minutes <= 0:
        return False, "Duration must be greater than 0"
    if minutes % 15 != 0:
        return False, "Duration must be a multiple of 15 minutes"
    return True, None


def validate_date_in_range(entry_date: date) -> bool:
    """
    Check if date is within the allowed period.
    
    Args:
        entry_date: Date to validate
        
    Returns:
        True if date is within range
    """
    return PERIOD_START <= entry_date <= PERIOD_END


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


def get_rtl_css() -> str:
    """
    Get custom CSS for RTL (Right-to-Left) layout support in Streamlit.
    
    Returns:
        CSS string to inject via st.markdown
    """
    return """
    <style>
    /* RTL Support for Hebrew */
    .stApp {
        direction: rtl;
        text-align: right;
    }
    
    /* Keep specific elements LTR */
    .stNumberInput input,
    .stDateInput input,
    code, pre {
        direction: ltr;
        text-align: left;
    }
    
    /* Fix table alignment */
    .stDataFrame {
        direction: rtl;
    }
    
    .stDataFrame th,
    .stDataFrame td {
        text-align: right !important;
    }
    
    /* Keep numbers LTR in tables */
    .stDataFrame td:has(> span) {
        direction: ltr;
    }
    
    /* Sidebar RTL */
    section[data-testid="stSidebar"] {
        direction: rtl;
        text-align: right;
    }
    
    /* Button alignment */
    .stButton {
        text-align: right;
    }
    
    /* Text areas and inputs */
    .stTextInput input,
    .stTextArea textarea,
    .stSelectbox > div {
        direction: rtl;
        text-align: right;
    }
    
    /* Markdown content */
    .stMarkdown {
        direction: rtl;
        text-align: right;
    }
    
    /* Allow mixed content (Hebrew + English/numbers) */
    .stMarkdown p,
    .stMarkdown li {
        unicode-bidi: plaintext;
    }
    
    /* Expander headers */
    .streamlit-expanderHeader {
        direction: rtl;
        text-align: right;
    }
    
    /* Metrics */
    [data-testid="metric-container"] {
        direction: rtl;
        text-align: right;
    }
    
    /* File uploader */
    .stFileUploader {
        direction: rtl;
    }
    </style>
    """


def normalize_matter_name(name: str) -> str:
    """
    Normalize matter name for case-insensitive comparison.
    
    Args:
        name: Matter name to normalize
        
    Returns:
        Lowercased, stripped name
    """
    return name.strip().lower()


def validate_action(action: dict) -> Tuple[bool, Optional[str]]:
    """
    Validate a single action entry.
    
    Args:
        action: Dict with action_description and duration_minutes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not action.get('action_description', '').strip():
        return False, "Action description cannot be empty"
    
    duration = action.get('duration_minutes', 0)
    return validate_duration(duration)


def validate_entry(entry: dict) -> Tuple[bool, List[str]]:
    """
    Validate a complete work entry.
    
    Args:
        entry: Dict with entry data
        
    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    errors = []
    
    # Validate date
    entry_date = entry.get('entry_date')
    if not entry_date:
        errors.append("Entry date is required")
    elif isinstance(entry_date, str):
        try:
            entry_date = date.fromisoformat(entry_date)
            if not validate_date_in_range(entry_date):
                errors.append(f"Date must be between {PERIOD_START} and {PERIOD_END}")
        except ValueError:
            errors.append("Invalid date format")
    elif isinstance(entry_date, date):
        if not validate_date_in_range(entry_date):
            errors.append(f"Date must be between {PERIOD_START} and {PERIOD_END}")
    
    # Validate matter
    if not entry.get('matter_id'):
        errors.append("Matter is required")
    
    # Validate actions
    actions = entry.get('actions', [])
    if not actions:
        errors.append("At least one action is required")
    else:
        for i, action in enumerate(actions, 1):
            valid, error = validate_action(action)
            if not valid:
                errors.append(f"Action {i}: {error}")
    
    return len(errors) == 0, errors
