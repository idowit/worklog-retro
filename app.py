"""
Work Log - Streamlit Application

A retrospective work diary for organizing work records from 2024-06-01 to 2024-12-31.

CRITICAL: This application only organizes existing records.
It does NOT fabricate, infer, estimate, or auto-generate any work data.
All entries are explicitly entered by the user.
"""

import streamlit as st
from datetime import date, datetime
from typing import Optional

from utils import (
    PERIOD_START, PERIOD_END,
    compute_week_index, get_week_boundaries, get_all_weeks,
    format_hhmm, validate_duration, validate_date_in_range,
    validate_entry, get_rtl_css, generate_uuid
)
from storage import (
    load_data, save_data,
    get_matter_by_id, get_matter_by_name, get_all_matters,
    upsert_matter, update_matter, delete_matter, get_all_entries, get_entries_by_week,
    add_entry, update_entry, delete_entry,
    save_invoice_file, delete_invoice_file, get_invoice_path,
    get_matter_total_minutes, get_unique_action_descriptions
)
from report import (
    generate_work_entries_csv, generate_weekly_summary_csv, generate_pdf_report
)

# Page config
st.set_page_config(
    page_title="יומן עבודה / Work Log",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply RTL CSS
st.markdown(get_rtl_css(), unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if 'data' not in st.session_state:
        try:
            st.session_state.data = load_data()
        except Exception as e:
            st.error(f"Failed to load data: {e}")
            st.session_state.data = {"matters": [], "entries": []}
    
    if 'edit_entry_id' not in st.session_state:
        st.session_state.edit_entry_id = None
    
    if 'selected_week' not in st.session_state:
        st.session_state.selected_week = None
    
    if 'action_count' not in st.session_state:
        st.session_state.action_count = 1
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "add_entry"


def reload_data():
    """Reload data from file."""
    try:
        st.session_state.data = load_data()
    except Exception as e:
        st.error(f"Failed to reload data: {e}")


def save_and_reload():
    """Save data and reload."""
    try:
        save_data(st.session_state.data)
        reload_data()
        return True
    except Exception as e:
        st.error(f"Failed to save: {e}")
        return False


def auto_save():
    """
    Auto-save current session data without reloading.
    Used for background saves to prevent data loss.
    """
    try:
        save_data(st.session_state.data)
        return True
    except Exception:
        return False


# ============================================================================
# SIDEBAR NAVIGATION
# ============================================================================

def render_sidebar():
    """Render sidebar navigation."""
    st.sidebar.title("📋 יומן עבודה")
    st.sidebar.markdown("Work Log")
    st.sidebar.divider()
    
    if st.sidebar.button("➕ הוספת רישום / Add Entry", use_container_width=True):
        st.session_state.current_page = "add_entry"
        st.session_state.edit_entry_id = None
        st.session_state.action_count = 1
        st.rerun()
    
    if st.sidebar.button("📅 תצוגה שבועית / Weekly View", use_container_width=True):
        st.session_state.current_page = "weekly_view"
        st.rerun()
    
    if st.sidebar.button("📁 תיקים / Matters", use_container_width=True):
        st.session_state.current_page = "matters"
        st.rerun()
    
    if st.sidebar.button("📊 ייצוא / Export", use_container_width=True):
        st.session_state.current_page = "export"
        st.rerun()
    
    st.sidebar.divider()
    
    # Quick stats
    data = st.session_state.data
    total_entries = len(data.get("entries", []))
    total_matters = len(data.get("matters", []))
    total_minutes = sum(e.get("total_minutes", 0) for e in data.get("entries", []))
    
    # Calculate week statistics
    all_weeks = get_all_weeks()
    week_totals = {}
    for entry in data.get("entries", []):
        week_idx = entry.get("week_index", 0)
        week_totals[week_idx] = week_totals.get(week_idx, 0) + entry.get("total_minutes", 0)
    
    # Count weeks below thresholds
    weeks_under_12h = sum(1 for w in all_weeks if week_totals.get(w["week_index"], 0) < 720)  # 12 * 60
    weeks_under_20h = sum(1 for w in all_weeks if week_totals.get(w["week_index"], 0) < 1200)  # 20 * 60
    
    st.sidebar.markdown("### סטטיסטיקה / Stats")
    st.sidebar.metric("רישומים / Entries", total_entries)
    st.sidebar.metric("תיקים / Matters", total_matters)
    st.sidebar.metric("סה״כ שעות / Total Time", format_hhmm(total_minutes))
    
    st.sidebar.divider()
    st.sidebar.markdown("### שבועות חסרים / Low Hours")
    st.sidebar.metric("פחות מ-12 שעות / Under 12h", weeks_under_12h, delta=None, delta_color="inverse")
    st.sidebar.metric("פחות מ-20 שעות / Under 20h", weeks_under_20h, delta=None, delta_color="inverse")


# ============================================================================
# ADD / EDIT ENTRY PAGE
# ============================================================================

def render_add_entry_page():
    """Render the add/edit entry page."""
    data = st.session_state.data
    is_edit = st.session_state.edit_entry_id is not None
    
    if is_edit:
        st.title("✏️ עריכת רישום / Edit Entry")
        entry = None
        for e in data.get("entries", []):
            if e["id"] == st.session_state.edit_entry_id:
                entry = e
                break
        if not entry:
            st.error("Entry not found")
            st.session_state.edit_entry_id = None
            st.rerun()
            return
    else:
        st.title("➕ הוספת רישום / Add Entry")
        entry = None
    
    
    # Form - removed st.form to allow dynamic "New Action" showing
    col1, col2 = st.columns(2)
    
    with col1:
        # Matter selection
        matters = get_all_matters(data)
        matter_names = [m["name"] for m in matters]
        
        # Simple options - just select matter or nothing
        matter_options = ["-- בחר תיק / Select Matter --"] + matter_names
        
        if entry:
            current_matter = get_matter_by_id(data, entry["matter_id"])
            default_idx = matter_options.index(current_matter["name"]) if current_matter else 0
        else:
            default_idx = 0
        
        selected_matter_option = st.selectbox(
            "תיק / Matter",
            options=matter_options,
            index=default_idx
        )
        
        # New matter fields - always available in expander
        new_matter_name = ""
        new_case_type = ""
        
        # Show new matter input in an expander (collapsed by default)
        with st.expander("✏️ תיק חדש / New Matter", expanded=False):
            st.caption("💡 השאר את בחירת התיק ריק כדי ליצור תיק חדש")
            new_matter_name = st.text_input("שם תיק חדש / New Matter Name", key="new_matter_name")
            new_case_type = st.text_input("סוג תיק / Case Type", key="new_case_type")
        
        # Show case type for existing matter
        if selected_matter_option not in ["-- בחר תיק / Select Matter --"]:
            existing_matter = get_matter_by_name(data, selected_matter_option)
            if existing_matter:
                st.info(f"📋 סוג תיק: {existing_matter.get('case_type', '-')}")
    
    with col2:
        # Statistics panel instead of date preview
        st.markdown("### סטטיסטיקה / Statistics")
        st.info(f"**תיקים קיימים / Matters:** {len(get_all_matters(data))}")
    
    st.divider()
    
    # Actions editor
    st.markdown("### פעולות / Actions")
    
    # Determine initial action count and clear stale state
    if entry and 'actions_initialized' not in st.session_state:
        st.session_state.action_count = max(1, len(entry.get("actions", [])))
        st.session_state.actions_initialized = True
        # Clear any stale current_actions from previous edits
        if 'current_actions' in st.session_state:
            del st.session_state.current_actions
    elif 'actions_initialized' not in st.session_state:
        # New entry mode
        st.session_state.action_count = 1
        st.session_state.actions_initialized = True
        if 'current_actions' in st.session_state:
            del st.session_state.current_actions
        
    actions = []
    total_minutes = 0
    
    # Get existing action suggestions (prioritize current matter)
    current_matter_id = None
    if selected_matter_option not in ["-- בחר תיק / Select Matter --", "➕ תיק חדש / New Matter"]:
        existing_matter = get_matter_by_name(data, selected_matter_option)
        if existing_matter:
            current_matter_id = existing_matter["id"]
    
    action_suggestions = get_unique_action_descriptions(data, current_matter_id)
    suggestion_options = ["-- בחר פעולה / Select Action --", "✏️ הזנה חדשה / New Action"] + action_suggestions
    
    # Track which action was deleted in this run
    delete_action_index = None

    for i in range(st.session_state.action_count):
        # Default values initialization
        default_desc = ""
        default_dur = 15
        default_date = PERIOD_START
        
        # Determine source of truth for defaults:
        # 1. current_actions (if we just deleted/manipulated the list)
        # 2. entry (if we are editing an existing record)
        source_action = None
        if 'current_actions' in st.session_state and i < len(st.session_state.current_actions):
            source_action = st.session_state.current_actions[i]
        elif entry and i < len(entry.get("actions", [])):
            source_action = entry["actions"][i]
        
        if source_action:
            default_desc = source_action.get("action_description", "")
            default_dur = source_action.get("duration_minutes", 15)
            # Get action date or fall back to entry date (if migration handled it)
            action_date_str = source_action.get("action_date", source_action.get("entry_date")) 
            
            if action_date_str:
                try:
                    default_date = date.fromisoformat(str(action_date_str))
                except:
                    default_date = PERIOD_START
        
        # Layout: Date | Action | Duration | Delete
        col_date, col_select, col_dur, col_del = st.columns([1, 2, 1.2, 0.3])
        
        with col_date:
            action_date = st.date_input(
                f"תאריך / Date {i+1}",
                value=default_date,
                min_value=PERIOD_START,
                max_value=PERIOD_END,
                format="YYYY-MM-DD",
                key=f"action_date_{i}"
            )
        
        with col_select:
            # Check if default_desc is in suggestions
            if default_desc and default_desc in action_suggestions:
                default_idx = suggestion_options.index(default_desc)
            else:
                # If editing with a custom value or new entry
                default_idx = 1 if default_desc else 0  # "New Action" or "Select"
            
            selected_action = st.selectbox(
                f"פעולה / Action {i+1}",
                options=suggestion_options,
                index=default_idx,
                key=f"action_select_{i}"
            )
            
            # Show text input if "New Action" selected or if we have a non-matching default
            if selected_action == "✏️ הזנה חדשה / New Action":
                desc = st.text_input(
                    f"תיאור חדש / New Description",
                    value=default_desc if default_desc and default_desc not in action_suggestions else "",
                    key=f"action_desc_{i}"
                )
            elif selected_action == "-- בחר פעולה / Select Action --":
                desc = ""
            else:
                desc = selected_action
        
        with col_dur:
            st.markdown("**זמן / Duration**")
            
            # Parse default duration to hours and minutes
            default_hours = default_dur // 60
            default_mins = default_dur % 60
            
            # Create columns for HH : MM (reversed for RTL)
            col_m, col_colon, col_h = st.columns([1, 0.3, 1])
            
            with col_h:
                hours = st.number_input(
                    "HH",
                    min_value=0,
                    max_value=99,
                    value=default_hours,
                    key=f"action_hours_{i}",
                    label_visibility="collapsed"
                )
            
            with col_colon:
                st.markdown("## :")
            
            with col_m:
                mins = st.selectbox(
                    "MM",
                    options=[0, 15, 30, 45],
                    index=[0, 15, 30, 45].index(default_mins) if default_mins in [0, 15, 30, 45] else 0,
                    key=f"action_mins_{i}",
                    label_visibility="collapsed"
                )
            
            dur = (hours * 60) + mins
            if dur < 15: dur = 15
        
        with col_del:
            st.markdown("### &nbsp;") # spacing
            if st.button("🗑️", key=f"del_action_{i}"):
                delete_action_index = i

        actions.append({
            "action_description": desc,
            "duration_minutes": dur,
            "action_date": action_date.isoformat()
        })
        total_minutes += dur

    # Handle deletion if a button was clicked
    if delete_action_index is not None:
        # Remove the item
        actions.pop(delete_action_index)
        # Update session state
        st.session_state.current_actions = actions
        st.session_state.action_count = len(actions)
        # Clear all widget keys to force reload from current_actions defaults
        for k in list(st.session_state.keys()):
            if k.startswith("action_"):
                del st.session_state[k]
        st.rerun()
        
    # Total display for actions
    st.markdown(f"**סה״כ / Total: {format_hhmm(total_minutes)}**")
    
    # Add/remove action buttons
    col_add, col_remove = st.columns(2)
    with col_add:
        add_action = st.button("➕ הוסף פעולה / Add Action")
    with col_remove:
        remove_action = st.button("➖ הסר פעולה / Remove Action") if st.session_state.action_count > 1 else False
    
    st.divider()
    
    # Invoice upload
    st.markdown("### חשבונית / Invoice (Optional)")
    
    current_invoice = None
    if entry and entry.get("invoice_original_filename"):
        current_invoice = entry.get("invoice_original_filename")
        st.info(f"📎 חשבונית נוכחית / Current: {current_invoice}")
    
    uploaded_file = st.file_uploader(
        "העלאת חשבונית / Upload Invoice",
        type=["pdf", "png", "jpg", "jpeg", "doc", "docx"],
        key="invoice_upload"
    )
    
    remove_invoice = False
    if current_invoice:
        remove_invoice = st.checkbox("הסר חשבונית / Remove Invoice")
    
    st.divider()
    
    # Submit button
    submitted = st.button(
        "💾 שמור / Save" if not is_edit else "💾 עדכן / Update",
        use_container_width=True,
        type="primary"
    )
    
    # Handle add/remove action buttons
    if add_action:
        st.session_state.action_count += 1
        st.rerun()
    
    if remove_action:
        st.session_state.action_count -= 1
        st.rerun()
    
    if submitted:
        # Validation
        errors = []
        
        # Validate action dates instead of entry date
        for i, action in enumerate(actions, 1):
            action_date_str = action.get("action_date")
            if action_date_str:
                try:
                    action_date_obj = date.fromisoformat(action_date_str)
                    if not validate_date_in_range(action_date_obj):
                        errors.append(f"תאריך פעולה {i} חייב להיות בין {PERIOD_START} ל-{PERIOD_END} / Action {i} date must be between {PERIOD_START} and {PERIOD_END}")
                except:
                    errors.append(f"תאריך פעולה {i} לא תקין / Action {i} date is invalid")
        
        # Get matter - validate that user chose either existing OR new, not both
        matter_id = None
        new_matter_created = None  # Track if we created a new matter
        
        has_existing_matter = selected_matter_option not in ["-- בחר תיק / Select Matter --"]
        has_new_matter = new_matter_name.strip() != ""
        
        if has_existing_matter and has_new_matter:
            errors.append("לא ניתן לבחור תיק קיים ולמלא תיק חדש בו זמנית / Cannot select existing matter AND create new matter")
        elif has_new_matter:
            # Create new matter (will be rolled back if save fails)
            new_matter_created = upsert_matter(data, new_matter_name, new_case_type)
            matter_id = new_matter_created["id"]
        elif has_existing_matter:
            existing = get_matter_by_name(data, selected_matter_option)
            if existing:
                matter_id = existing["id"]
            else:
                errors.append("תיק לא נמצא / Matter not found")
        else:
            errors.append("יש לבחור תיק קיים או למלא פרטי תיק חדש / Please select existing matter or fill new matter details")
        
        # Validate actions
        valid_actions = [a for a in actions if a["action_description"].strip()]
        if not valid_actions:
            errors.append("נדרשת לפחות פעולה אחת / At least one action required")
        
        for i, action in enumerate(valid_actions, 1):
            is_valid, error = validate_duration(action["duration_minutes"])
            if not is_valid:
                errors.append(f"פעולה {i}: {error}")
        
        if errors:
            # Rollback new matter if it was created
            if new_matter_created:
                data["matters"] = [m for m in data["matters"] if m["id"] != new_matter_created["id"]]
            
            for error in errors:
                st.error(error)
        else:
            # Prepare invoice info (but don't save file yet)
            invoice_info = None
            old_invoice_to_delete = None
            new_invoice_file = None
            
            if uploaded_file:
                # Mark for saving after successful entry save
                new_invoice_file = uploaded_file
                # Mark old invoice for deletion
                if entry and entry.get("invoice_storage_filename"):
                    old_invoice_to_delete = entry["invoice_storage_filename"]
            elif remove_invoice and entry:
                # Remove invoice
                if entry.get("invoice_storage_filename"):
                    old_invoice_to_delete = entry["invoice_storage_filename"]
                invoice_info = {}  # Empty dict signals removal
            elif entry and entry.get("invoice_original_filename") and not remove_invoice:
                # Keep existing
                invoice_info = None  # None means keep existing
            
            # Save entry first (entry_date is calculated from action dates)
            try:
                if is_edit:
                    update_entry(
                        data, 
                        st.session_state.edit_entry_id,
                        PERIOD_START,  # Placeholder - actual date calculated from actions
                        matter_id,
                        valid_actions,
                        invoice_info
                    )
                else:
                    add_entry(data, PERIOD_START, matter_id, valid_actions, 
                             invoice_info if invoice_info else None)  # Placeholder - actual date calculated from actions
                
                # Try to save data
                if save_and_reload():
                    # Only now save the invoice file (after successful data save)
                    if new_invoice_file:
                        invoice_info = save_invoice_file(new_invoice_file)
                        # Update the entry with invoice info
                        if is_edit:
                            entry_to_update = None
                            for e in st.session_state.data.get("entries", []):
                                if e["id"] == st.session_state.edit_entry_id:
                                    entry_to_update = e
                                    break
                            if entry_to_update:
                                entry_to_update["invoice_original_filename"] = invoice_info.get("original_filename")
                                entry_to_update["invoice_storage_filename"] = invoice_info.get("storage_filename")
                                entry_to_update["invoice_path"] = invoice_info.get("path")
                        else:
                            # For new entry, it's the last one added
                            if st.session_state.data.get("entries"):
                                last_entry = st.session_state.data["entries"][-1]
                                last_entry["invoice_original_filename"] = invoice_info.get("original_filename")
                                last_entry["invoice_storage_filename"] = invoice_info.get("storage_filename")
                                last_entry["invoice_path"] = invoice_info.get("path")
                        
                        save_and_reload()
                    
                    # Delete old invoice if needed
                    if old_invoice_to_delete:
                        delete_invoice_file(old_invoice_to_delete)
                    
                    st.success("נשמר בהצלחה! / Saved successfully!")
                    
                    # Reset state
                    st.session_state.edit_entry_id = None
                    st.session_state.action_count = 1
                    if 'actions_initialized' in st.session_state:
                        del st.session_state.actions_initialized
                    if 'current_actions' in st.session_state:
                         del st.session_state.current_actions
                        
                    st.session_state.current_page = "weekly_view"
                    st.rerun()
            except Exception as e:
                st.error(f"שגיאה בשמירה / Error saving: {e}")
                # Rollback new matter on save error
                if new_matter_created:
                    data["matters"] = [m for m in data["matters"] if m["id"] != new_matter_created["id"]]

    # Cancel edit button
    if is_edit:
        if st.button("❌ ביטול / Cancel"):
            st.session_state.edit_entry_id = None
            st.session_state.action_count = 1
            if 'actions_initialized' in st.session_state:
                del st.session_state.actions_initialized
            st.session_state.current_page = "weekly_view"
            st.rerun()


# ============================================================================
# WEEKLY VIEW PAGE
# ============================================================================

def render_weekly_view_page():
    """Render the weekly view page."""
    st.title("📅 תצוגה שבועית / Weekly View")
    
    data = st.session_state.data
    all_weeks = get_all_weeks()
    entries = data.get("entries", [])
    
    # Filters
    with st.expander("🔍 סינון / Filters", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            matters = get_all_matters(data)
            matter_options = ["הכל / All"] + [m["name"] for m in matters]
            matter_filter = st.selectbox("תיק / Matter", matter_options)
            matter_filter_id = None
            if matter_filter != "הכל / All":
                m = get_matter_by_name(data, matter_filter)
                if m:
                    matter_filter_id = m["id"]
        
        with col2:
            case_types = list(set(m.get("case_type", "") for m in matters if m.get("case_type")))
            case_type_options = ["הכל / All"] + case_types
            case_type_filter = st.selectbox("סוג תיק / Case Type", case_type_options)
            case_type_filter = None if case_type_filter == "הכל / All" else case_type_filter
        
        with col3:
            date_range = st.date_input(
                "טווח תאריכים / Date Range",
                value=(PERIOD_START, PERIOD_END),
                min_value=PERIOD_START,
                max_value=PERIOD_END
            )
            if isinstance(date_range, tuple) and len(date_range) == 2:
                date_start, date_end = date_range
            else:
                date_start, date_end = PERIOD_START, PERIOD_END
    
    # Apply filters to get matching entries
    filtered_entries = entries
    
    if matter_filter_id:
        filtered_entries = [e for e in filtered_entries if e["matter_id"] == matter_filter_id]
    
    if case_type_filter:
        filtered_entries = [
            e for e in filtered_entries 
            if (matter := get_matter_by_id(data, e["matter_id"])) 
            and matter.get("case_type") == case_type_filter
        ]
    
    # Apply date filters with error handling
    try:
        filtered_entries = [e for e in filtered_entries 
                           if date.fromisoformat(e["entry_date"]) >= date_start]
        filtered_entries = [e for e in filtered_entries 
                           if date.fromisoformat(e["entry_date"]) <= date_end]
    except (ValueError, TypeError) as e:
        st.warning(f"Some entries have invalid dates and were skipped: {e}")
    
    # Calculate week totals
    week_totals = {}
    for entry in filtered_entries:
        week_idx = entry["week_index"]
        week_totals[week_idx] = week_totals.get(week_idx, 0) + entry["total_minutes"]
    
    # Weekly summary table
    st.markdown("### סיכום שבועי / Weekly Summary")
    
    week_data = []
    for week in all_weeks:
        total = week_totals.get(week["week_index"], 0)
        week_data.append({
            "שבוע / Week": week["week_index"],
            "התחלה / Start": week["week_start"].isoformat(),
            "סיום / End": week["week_end"].isoformat(),
            "סה״כ / Total": format_hhmm(total)
        })
    
    import pandas as pd
    df = pd.DataFrame(week_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Grand total
    grand_total = sum(week_totals.values())
    st.markdown(f"**סה״כ כללי / Grand Total: {format_hhmm(grand_total)}**")
    
    st.divider()
    
    # Week detail selection
    st.markdown("### פירוט שבוע / Week Detail")
    
    week_options = [f"שבוע {w['week_index']} ({w['week_start']} - {w['week_end']})" 
                    for w in all_weeks]
    selected_week_str = st.selectbox("בחר שבוע / Select Week", week_options)
    
    if selected_week_str:
        week_idx = int(selected_week_str.split()[1])
        week_entries = [e for e in filtered_entries if e["week_index"] == week_idx]
        
        if not week_entries:
            st.info("אין רישומים בשבוע זה / No entries in this week")
        else:
            # Group by matter
            entries_by_matter = {}
            for entry in week_entries:
                matter = get_matter_by_id(data, entry["matter_id"])
                matter_name = matter["name"] if matter else "Unknown"
                if matter_name not in entries_by_matter:
                    entries_by_matter[matter_name] = []
                entries_by_matter[matter_name].append(entry)
            
            for matter_name, matter_entries in entries_by_matter.items():
                matter_total = sum(e["total_minutes"] for e in matter_entries)
                
                with st.expander(f"📁 {matter_name} - {format_hhmm(matter_total)}", expanded=True):
                    for entry in matter_entries:
                        col1, col2, col3 = st.columns([3, 1, 1])
                        
                        with col1:
                            st.markdown(f"**{entry['entry_date']}** - {format_hhmm(entry['total_minutes'])}")
                            
                            for action in entry.get("actions", []):
                                action_date = action.get('action_date', entry['entry_date'])
                                st.markdown(f"  • [{action_date}] {action['action_description']} ({format_hhmm(action['duration_minutes'])})")
                            
                            if entry.get("invoice_original_filename"):
                                st.markdown(f"📎 {entry['invoice_original_filename']}")
                        
                        with col2:
                            if st.button("✏️ ערוך", key=f"edit_{entry['id']}"):
                                st.session_state.edit_entry_id = entry['id']
                                st.session_state.current_page = "add_entry"
                                st.rerun()
                        
                        with col3:
                            if st.button("🗑️ מחק", key=f"delete_{entry['id']}"):
                                st.session_state.delete_confirm = entry['id']
                                st.rerun()
                        
                        # Delete confirmation
                        if st.session_state.get('delete_confirm') == entry['id']:
                            st.warning("האם למחוק? / Confirm delete?")
                            col_yes, col_no = st.columns(2)
                            with col_yes:
                                if st.button("✅ כן / Yes", key=f"confirm_del_{entry['id']}"):
                                    # Delete invoice file if exists
                                    if entry.get("invoice_storage_filename"):
                                        delete_invoice_file(entry["invoice_storage_filename"])
                                    delete_entry(data, entry['id'])
                                    save_and_reload()
                                    st.session_state.delete_confirm = None
                                    st.rerun()
                            with col_no:
                                if st.button("❌ לא / No", key=f"cancel_del_{entry['id']}"):
                                    st.session_state.delete_confirm = None
                                    st.rerun()
                        
                        # Download invoice
                        if entry.get("invoice_storage_filename"):
                            invoice_path = get_invoice_path(entry["invoice_storage_filename"])
                            if invoice_path and invoice_path.exists():
                                with open(invoice_path, "rb") as f:
                                    st.download_button(
                                        "⬇️ הורד חשבונית / Download Invoice",
                                        data=f.read(),
                                        file_name=entry["invoice_original_filename"],
                                        key=f"download_{entry['id']}"
                                    )
                        
                        st.divider()


# ============================================================================
# MATTERS PAGE
# ============================================================================

def render_matters_page():
    """Render the matters management page."""
    st.title("📁 תיקים / Matters")
    
    data = st.session_state.data
    
    # Add new matter form
    with st.expander("➕ הוספת תיק חדש / Add New Matter", expanded=False):
        with st.form("add_matter_form"):
            new_name = st.text_input("שם תיק / Matter Name")
            new_case_type = st.text_input("סוג תיק / Case Type")
            
            if st.form_submit_button("💾 שמור תיק / Save Matter", use_container_width=True):
                if new_name.strip():
                    # Check if matter already exists
                    existing = get_matter_by_name(data, new_name)
                    if existing:
                        st.error("תיק בשם זה כבר קיים / Matter with this name already exists")
                    else:
                        upsert_matter(data, new_name.strip(), new_case_type.strip())
                        if save_and_reload():
                            st.success("✅ תיק נוסף בהצלחה / Matter added successfully!")
                            st.rerun()
                else:
                    st.error("שם תיק נדרש / Matter name required")
    
    st.divider()
    
    matters = get_all_matters(data)
    
    if not matters:
        st.info("אין תיקים עדיין / No matters yet. Use the form above to add matters.")
        return
    
    # Matters table - Custom rendering to support actions
    # Header
    col1, col2, col3, col4, col5 = st.columns([3, 2, 1.5, 1.5, 1])
    col1.markdown("**שם תיק / Name**")
    col2.markdown("**סוג / Type**")
    col3.markdown("**סה״כ זמן / Total Time**")
    col4.markdown("**נוצר / Created**")
    col5.markdown("**פעולות / Actions**")
    
    st.divider()
    
    for matter in matters:
        total_min = get_matter_total_minutes(data, matter["id"])
        
        col1, col2, col3, col4, col5 = st.columns([3, 2, 1.5, 1.5, 1])
        col1.markdown(f"{matter['name']}")
        col2.markdown(f"{matter.get('case_type', '-')}")
        col3.markdown(f"{format_hhmm(total_min)}")
        col4.markdown(f"{matter.get('created_at', '')[:10]}")
        
        with col5:
            if st.button("🗑️", key=f"del_matter_{matter['id']}"):
                st.session_state.delete_matter_confirm = matter['id']
                st.rerun()
    
    # Delete confirmation modal-like
    if 'delete_matter_confirm' in st.session_state and st.session_state.delete_matter_confirm:
        matter_to_del_id = st.session_state.delete_matter_confirm
        matter_to_del = get_matter_by_id(data, matter_to_del_id)
        
        if matter_to_del:
            st.warning(f"האם למחוק את התיק '{matter_to_del['name']}'? / Delete matter '{matter_to_del['name']}'?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ כן, מחק / Yes, Delete", key="confirm_del_matter", type="primary"):
                    success, msg = delete_matter(data, matter_to_del_id)
                    if success:
                        save_and_reload()
                        st.success(msg)
                        del st.session_state.delete_matter_confirm
                        st.rerun()
                    else:
                        st.error(msg)
            with c2:
                if st.button("❌ ביטול / Cancel", key="cancel_del_matter"):
                    del st.session_state.delete_matter_confirm
                    st.rerun()
        else:
            # Matter not found (maybe already deleted)
            del st.session_state.delete_matter_confirm
            st.rerun()
    
    # Total
    total_all = sum(get_matter_total_minutes(data, m["id"]) for m in matters)
    st.markdown(f"**סה״כ כללי / Grand Total: {format_hhmm(total_all)}**")


# ============================================================================
# EXPORT PAGE
# ============================================================================

def render_export_page():
    """Render the export page."""
    st.title("📊 ייצוא / Export")
    
    data = st.session_state.data
    
    st.info("כל הקבצים המיוצאים כוללים הצהרה: " + 
            "\"Work log organized retrospectively from existing records.\"")
    
    # Filters for export
    with st.expander("🔍 סינון ייצוא / Export Filters", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            matters = get_all_matters(data)
            matter_options = ["הכל / All"] + [m["name"] for m in matters]
            exp_matter = st.selectbox("תיק / Matter", matter_options, key="exp_matter")
            exp_matter_id = None
            if exp_matter != "הכל / All":
                m = get_matter_by_name(data, exp_matter)
                if m:
                    exp_matter_id = m["id"]
        
        with col2:
            case_types = list(set(m.get("case_type", "") for m in matters if m.get("case_type")))
            case_type_options = ["הכל / All"] + case_types
            exp_case_type = st.selectbox("סוג תיק / Case Type", case_type_options, key="exp_case")
            exp_case_type = None if exp_case_type == "הכל / All" else exp_case_type
    
    st.divider()
    
    # CSV Exports
    st.markdown("### 📄 CSV Exports")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**רישומי עבודה / Work Entries**")
        st.caption("שורה אחת לכל פעולה / One row per action")
        
        csv_entries = generate_work_entries_csv(
            data, 
            matter_filter=exp_matter_id,
            case_type_filter=exp_case_type
        )
        st.download_button(
            "⬇️ הורד WorkEntries.csv",
            data=csv_entries,
            file_name="WorkEntries.csv",
            mime="text/csv"
        )
    
    with col2:
        st.markdown("**סיכום שבועי / Weekly Summary**")
        st.caption("שורה אחת לכל שבוע / One row per week")
        
        csv_summary = generate_weekly_summary_csv(
            data,
            matter_filter=exp_matter_id,
            case_type_filter=exp_case_type
        )
        st.download_button(
            "⬇️ הורד WeeklySummary.csv",
            data=csv_summary,
            file_name="WeeklySummary.csv",
            mime="text/csv"
        )
    
    st.divider()
    
    # PDF Export
    st.markdown("### 📑 PDF Report")
    st.caption("דוח מלא עם פירוט שבועי / Full report with weekly breakdown")
    
    try:
        pdf_data = generate_pdf_report(
            data,
            matter_filter=exp_matter_id,
            case_type_filter=exp_case_type
        )
        st.download_button(
            "⬇️ הורד דוח PDF / Download PDF Report",
            data=pdf_data,
            file_name="WorkLog_Report.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"שגיאה ביצירת PDF / Error generating PDF: {e}")
        st.info("וודא שכל החבילות מותקנות / Ensure all packages are installed")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main application entry point."""
    init_session_state()
    render_sidebar()
    
    page = st.session_state.current_page
    
    if page == "add_entry":
        render_add_entry_page()
    elif page == "weekly_view":
        render_weekly_view_page()
    elif page == "matters":
        render_matters_page()
    elif page == "export":
        render_export_page()
    else:
        render_add_entry_page()


if __name__ == "__main__":
    main()
