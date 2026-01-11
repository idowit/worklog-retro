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
    upsert_matter, get_all_entries, get_entries_by_week,
    add_entry, update_entry, delete_entry,
    save_invoice_file, delete_invoice_file, get_invoice_path,
    get_matter_total_minutes
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
    
    st.sidebar.markdown("### סטטיסטיקה / Stats")
    st.sidebar.metric("רישומים / Entries", total_entries)
    st.sidebar.metric("תיקים / Matters", total_matters)
    st.sidebar.metric("סה״כ שעות / Total Time", format_hhmm(total_minutes))


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
    
    # Form
    with st.form("entry_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Date picker
            default_date = date.fromisoformat(entry["entry_date"]) if entry else PERIOD_START
            entry_date = st.date_input(
                "תאריך / Date",
                value=default_date,
                min_value=PERIOD_START,
                max_value=PERIOD_END,
                format="YYYY-MM-DD"
            )
            
            # Matter selection
            matters = get_all_matters(data)
            matter_names = [m["name"] for m in matters]
            
            # Add "new matter" option
            matter_options = ["-- בחר תיק / Select Matter --", "➕ תיק חדש / New Matter"] + matter_names
            
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
            
            # New matter fields
            new_matter_name = ""
            new_case_type = ""
            if selected_matter_option == "➕ תיק חדש / New Matter":
                new_matter_name = st.text_input("שם תיק חדש / New Matter Name")
                new_case_type = st.text_input("סוג תיק / Case Type")
            elif selected_matter_option not in ["-- בחר תיק / Select Matter --"]:
                # Show case type for existing matter
                existing_matter = get_matter_by_name(data, selected_matter_option)
                if existing_matter:
                    st.text(f"סוג: {existing_matter.get('case_type', '-')}")
        
        with col2:
            # Live preview
            st.markdown("### תצוגה מקדימה / Preview")
            
            if validate_date_in_range(entry_date):
                week_idx = compute_week_index(entry_date)
                week_start, week_end = get_week_boundaries(week_idx)
                st.info(f"""
                **שבוע / Week:** {week_idx}  
                **התחלה / Start:** {week_start.isoformat()}  
                **סיום / End:** {week_end.isoformat()}
                """)
            else:
                st.warning("תאריך מחוץ לטווח / Date out of range")
        
        st.divider()
        
        # Actions editor
        st.markdown("### פעולות / Actions")
        
        # Determine initial action count
        if entry and 'actions_initialized' not in st.session_state:
            st.session_state.action_count = max(1, len(entry.get("actions", [])))
            st.session_state.actions_initialized = True
        
        actions = []
        total_minutes = 0
        
        for i in range(st.session_state.action_count):
            col_desc, col_dur, col_del = st.columns([3, 1, 0.5])
            
            # Default values
            default_desc = ""
            default_dur = 15
            if entry and i < len(entry.get("actions", [])):
                default_desc = entry["actions"][i].get("action_description", "")
                default_dur = entry["actions"][i].get("duration_minutes", 15)
            
            with col_desc:
                desc = st.text_input(
                    f"תיאור / Description {i+1}",
                    value=default_desc,
                    key=f"action_desc_{i}"
                )
            
            with col_dur:
                dur = st.number_input(
                    f"דקות / Minutes",
                    min_value=15,
                    step=15,
                    value=default_dur,
                    key=f"action_dur_{i}"
                )
            
            actions.append({
                "action_description": desc,
                "duration_minutes": dur
            })
            total_minutes += dur
        
        # Action buttons (outside form for immediate effect)
        st.markdown(f"**סה״כ / Total: {format_hhmm(total_minutes)}**")
        
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
        submitted = st.form_submit_button(
            "💾 שמור / Save" if not is_edit else "💾 עדכן / Update",
            use_container_width=True
        )
        
        if submitted:
            # Validation
            errors = []
            
            if not validate_date_in_range(entry_date):
                errors.append(f"תאריך חייב להיות בין {PERIOD_START} ל-{PERIOD_END}")
            
            # Get matter
            matter_id = None
            if selected_matter_option == "➕ תיק חדש / New Matter":
                if not new_matter_name.strip():
                    errors.append("שם תיק חדש נדרש / New matter name required")
                else:
                    # Create new matter
                    new_matter = upsert_matter(data, new_matter_name, new_case_type)
                    matter_id = new_matter["id"]
            elif selected_matter_option == "-- בחר תיק / Select Matter --":
                errors.append("יש לבחור תיק / Please select a matter")
            else:
                existing = get_matter_by_name(data, selected_matter_option)
                if existing:
                    matter_id = existing["id"]
                else:
                    errors.append("תיק לא נמצא / Matter not found")
            
            # Validate actions
            valid_actions = [a for a in actions if a["action_description"].strip()]
            if not valid_actions:
                errors.append("נדרשת לפחות פעולה אחת / At least one action required")
            
            for i, action in enumerate(valid_actions, 1):
                is_valid, error = validate_duration(action["duration_minutes"])
                if not is_valid:
                    errors.append(f"פעולה {i}: {error}")
            
            if errors:
                for error in errors:
                    st.error(error)
            else:
                # Handle invoice
                invoice_info = None
                
                if uploaded_file:
                    # Save new invoice
                    invoice_info = save_invoice_file(uploaded_file)
                    # Delete old invoice if exists
                    if entry and entry.get("invoice_storage_filename"):
                        delete_invoice_file(entry["invoice_storage_filename"])
                elif remove_invoice and entry:
                    # Remove invoice
                    if entry.get("invoice_storage_filename"):
                        delete_invoice_file(entry["invoice_storage_filename"])
                    invoice_info = {}  # Empty dict signals removal
                elif entry and entry.get("invoice_original_filename") and not remove_invoice:
                    # Keep existing
                    invoice_info = None  # None means keep existing
                
                # Save entry
                if is_edit:
                    update_entry(
                        data, 
                        st.session_state.edit_entry_id,
                        entry_date,
                        matter_id,
                        valid_actions,
                        invoice_info
                    )
                else:
                    add_entry(data, entry_date, matter_id, valid_actions, 
                             invoice_info if invoice_info else None)
                
                if save_and_reload():
                    st.success("✅ נשמר בהצלחה / Saved successfully!")
                    st.session_state.edit_entry_id = None
                    st.session_state.action_count = 1
                    if 'actions_initialized' in st.session_state:
                        del st.session_state.actions_initialized
                    st.rerun()
    
    # Add/remove action buttons (outside form)
    col_add, col_remove = st.columns(2)
    with col_add:
        if st.button("➕ הוסף פעולה / Add Action"):
            st.session_state.action_count += 1
            st.rerun()
    with col_remove:
        if st.session_state.action_count > 1:
            if st.button("➖ הסר פעולה / Remove Action"):
                st.session_state.action_count -= 1
                st.rerun()
    
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
        filtered_entries = [e for e in filtered_entries 
                           if get_matter_by_id(data, e["matter_id"]).get("case_type") == case_type_filter]
    
    filtered_entries = [e for e in filtered_entries 
                       if date.fromisoformat(e["entry_date"]) >= date_start]
    filtered_entries = [e for e in filtered_entries 
                       if date.fromisoformat(e["entry_date"]) <= date_end]
    
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
                                st.markdown(f"  • {action['action_description']} ({format_hhmm(action['duration_minutes'])})")
                            
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
    matters = get_all_matters(data)
    
    if not matters:
        st.info("אין תיקים עדיין / No matters yet. Add entries to create matters.")
        return
    
    # Matters table
    import pandas as pd
    
    matters_data = []
    for matter in matters:
        total_min = get_matter_total_minutes(data, matter["id"])
        matters_data.append({
            "שם תיק / Name": matter["name"],
            "סוג / Type": matter.get("case_type", ""),
            "סה״כ זמן / Total Time": format_hhmm(total_min),
            "נוצר / Created": matter.get("created_at", "")[:10]
        })
    
    df = pd.DataFrame(matters_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
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
