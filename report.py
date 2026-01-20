"""
Work Log - Report Module

CSV and PDF export functionality with Hebrew language support.
"""

import io
import os
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd

from utils import (
    get_all_weeks, format_hhmm, PERIOD_START, PERIOD_END
)
from storage import (
    load_data, get_matter_by_id, get_all_entries, get_entries_by_week
)

# Retrospective disclaimer text
DISCLAIMER_TEXT = "Work log organized retrospectively from existing records."
DISCLAIMER_TEXT_HE = "יומן עבודה מאורגן רטרוספקטיבית מרשומות קיימות."

# Font directory
FONTS_DIR = Path(__file__).parent / "fonts"


def get_entries_with_matter_info(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get all entries with matter name and case_type included.
    """
    entries = []
    for entry in get_all_entries(data):
        matter = get_matter_by_id(data, entry["matter_id"])
        entry_with_matter = entry.copy()
        entry_with_matter["matter_name"] = matter["name"] if matter else "Unknown"
        entry_with_matter["case_type"] = matter["case_type"] if matter else ""
        entries.append(entry_with_matter)
    return entries


def generate_work_entries_csv(data: Dict[str, Any], 
                               matter_filter: Optional[str] = None,
                               case_type_filter: Optional[str] = None,
                               date_start: Optional[date] = None,
                               date_end: Optional[date] = None) -> bytes:
    """
    Generate CSV with one row per action.
    
    Columns:
    - week_index
    - entry_date
    - matter_name
    - case_type
    - action_description
    - action_minutes
    - entry_id
    - invoice_original_filename
    - invoice_path
    - created_at
    - updated_at
    
    Returns:
        CSV content as bytes (UTF-8 with BOM for Excel compatibility)
    """
    entries = get_entries_with_matter_info(data)
    
    # Apply filters
    if matter_filter:
        entries = [e for e in entries if e["matter_id"] == matter_filter]
    
    if case_type_filter:
        entries = [e for e in entries if e["case_type"] == case_type_filter]
    
    if date_start:
        entries = [e for e in entries 
                   if date.fromisoformat(e["entry_date"]) >= date_start]
    
    if date_end:
        entries = [e for e in entries 
                   if date.fromisoformat(e["entry_date"]) <= date_end]
    
    # Flatten to one row per action
    rows = []
    for entry in entries:
        for action in entry.get("actions", []):
            rows.append({
                "week_index": entry["week_index"],
                "action_date": action.get("action_date", entry["entry_date"]),  # Use action date, fallback to entry date
                "matter_name": entry["matter_name"],
                "case_type": entry["case_type"],
                "action_description": action.get("action_description", ""),
                "action_minutes": format_hhmm(action.get("duration_minutes", 0)),
                "entry_id": entry["id"],
                "invoice_original_filename": entry.get("invoice_original_filename", ""),
                "invoice_path": entry.get("invoice_path", ""),
                "created_at": entry.get("created_at", ""),
                "updated_at": entry.get("updated_at", "")
            })
    
    df = pd.DataFrame(rows)
    
    # Add disclaimer as first row
    disclaimer_row = pd.DataFrame([{col: DISCLAIMER_TEXT if col == "matter_name" else "" 
                                    for col in df.columns}])
    
    if not df.empty:
        df = pd.concat([disclaimer_row, df], ignore_index=True)
    else:
        df = disclaimer_row
    
    # Return as UTF-8 with BOM
    buffer = io.BytesIO()
    buffer.write(b'\xef\xbb\xbf')  # UTF-8 BOM
    df.to_csv(buffer, index=False, encoding='utf-8')
    return buffer.getvalue()


def generate_weekly_summary_csv(data: Dict[str, Any],
                                 matter_filter: Optional[str] = None,
                                 case_type_filter: Optional[str] = None) -> bytes:
    """
    Generate CSV with one row per week (all weeks included).
    
    Columns:
    - week_index
    - week_start
    - week_end
    - total_minutes
    - total_hhmm
    
    Returns:
        CSV content as bytes (UTF-8 with BOM)
    """
    all_weeks = get_all_weeks()
    entries = get_entries_with_matter_info(data)
    
    # Apply filters to entries
    if matter_filter:
        entries = [e for e in entries if e["matter_id"] == matter_filter]
    
    if case_type_filter:
        entries = [e for e in entries if e["case_type"] == case_type_filter]
    
    # Calculate totals per week
    week_totals = {}
    for entry in entries:
        week_idx = entry["week_index"]
        week_totals[week_idx] = week_totals.get(week_idx, 0) + entry["total_minutes"]
    
    # Build rows for all weeks
    rows = []
    for week in all_weeks:
        total_min = week_totals.get(week["week_index"], 0)
        rows.append({
            "week_index": week["week_index"],
            "week_start": week["week_start"].isoformat(),
            "week_end": week["week_end"].isoformat(),
            "total_minutes": total_min,
            "total_hhmm": format_hhmm(total_min)
        })
    
    df = pd.DataFrame(rows)
    
    # Add disclaimer
    disclaimer_row = pd.DataFrame([{
        "week_index": "",
        "week_start": DISCLAIMER_TEXT,
        "week_end": "",
        "total_minutes": "",
        "total_hhmm": ""
    }])
    df = pd.concat([disclaimer_row, df], ignore_index=True)
    
    buffer = io.BytesIO()
    buffer.write(b'\xef\xbb\xbf')
    df.to_csv(buffer, index=False, encoding='utf-8')
    return buffer.getvalue()


# PDF Generation

def register_hebrew_font():
    """
    Register Hebrew font for ReportLab.
    
    Returns:
        Font name to use, or None if registration failed
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import logging
    
    font_path = FONTS_DIR / "NotoSansHebrew-Regular.ttf"
    
    if font_path.exists():
        try:
            pdfmetrics.registerFont(TTFont('NotoSansHebrew', str(font_path)))
            return 'NotoSansHebrew'
        except Exception as e:
            logging.warning(f"Failed to register Hebrew font: {e}. Hebrew text may not display correctly.")
            return 'Helvetica'
    else:
        logging.warning(f"Hebrew font not found at {font_path}. Hebrew text may not display correctly.")
        return 'Helvetica'


def generate_pdf_report(data: Dict[str, Any],
                        matter_filter: Optional[str] = None,
                        case_type_filter: Optional[str] = None,
                        date_start: Optional[date] = None,
                        date_end: Optional[date] = None) -> bytes:
    """
    Generate PDF report with weekly totals and breakdown.
    
    Includes:
    - Title
    - Date range
    - Generation timestamp
    - Retrospective disclaimer
    - Weekly totals table (all weeks)
    - Grand total
    - Full breakdown by Week → Matter → Entry → Actions
    
    Returns:
        PDF content as bytes
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    )
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER
    
    # Register Hebrew font
    font_name = register_hebrew_font()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, 
                           rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleHebrew',
        parent=styles['Title'],
        fontName=font_name,
        fontSize=18,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'HeadingHebrew',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=14,
        alignment=TA_RIGHT
    )
    
    normal_style = ParagraphStyle(
        'NormalHebrew',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        alignment=TA_RIGHT
    )
    
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.gray
    )
    
    elements = []
    
    # Title
    elements.append(Paragraph("דוח יומן עבודה / Work Log Report", title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Date range
    date_range_text = f"{PERIOD_START.isoformat()} to {PERIOD_END.isoformat()}"
    elements.append(Paragraph(f"Period: {date_range_text}", normal_style))
    
    # Generation timestamp
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    elements.append(Paragraph(f"Generated: {gen_time}", normal_style))
    elements.append(Spacer(1, 0.3*cm))
    
    # Disclaimer
    elements.append(Paragraph(DISCLAIMER_TEXT, disclaimer_style))
    elements.append(Paragraph(DISCLAIMER_TEXT_HE, disclaimer_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Get data
    all_weeks = get_all_weeks()
    entries = get_entries_with_matter_info(data)
    
    # Apply filters
    if matter_filter:
        entries = [e for e in entries if e["matter_id"] == matter_filter]
    
    if case_type_filter:
        entries = [e for e in entries if e["case_type"] == case_type_filter]
    
    if date_start:
        entries = [e for e in entries 
                   if date.fromisoformat(e["entry_date"]) >= date_start]
    
    if date_end:
        entries = [e for e in entries 
                   if date.fromisoformat(e["entry_date"]) <= date_end]
    
    # Calculate week totals
    week_totals = {}
    for entry in entries:
        week_idx = entry["week_index"]
        week_totals[week_idx] = week_totals.get(week_idx, 0) + entry["total_minutes"]
    
    grand_total = sum(week_totals.values())
    
    # Weekly Summary Table
    elements.append(Paragraph("סיכום שבועי / Weekly Summary", heading_style))
    elements.append(Spacer(1, 0.3*cm))
    
    table_data = [["Week", "Start", "End", "Total"]]
    for week in all_weeks:
        total_min = week_totals.get(week["week_index"], 0)
        table_data.append([
            str(week["week_index"]),
            week["week_start"].isoformat(),
            week["week_end"].isoformat(),
            format_hhmm(total_min)
        ])
    
    # Add grand total row
    table_data.append(["", "", "Grand Total / סה״כ", format_hhmm(grand_total)])
    
    table = Table(table_data, colWidths=[2*cm, 3*cm, 3*cm, 2.5*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), font_name),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 1*cm))
    
    # Detailed breakdown
    elements.append(Paragraph("פירוט / Detailed Breakdown", heading_style))
    elements.append(Spacer(1, 0.3*cm))
    
    # Group entries by week, then by matter
    for week in all_weeks:
        week_entries = [e for e in entries if e["week_index"] == week["week_index"]]
        
        if not week_entries:
            continue
        
        # Week header
        week_header = f"Week {week['week_index']}: {week['week_start'].isoformat()} - {week['week_end'].isoformat()}"
        elements.append(Paragraph(week_header, heading_style))
        elements.append(Spacer(1, 0.2*cm))
        
        # Group by matter
        matters_in_week = {}
        for entry in week_entries:
            matter_name = entry["matter_name"]
            if matter_name not in matters_in_week:
                matters_in_week[matter_name] = []
            matters_in_week[matter_name].append(entry)
        
        for matter_name, matter_entries in matters_in_week.items():
            matter_total = sum(e["total_minutes"] for e in matter_entries)
            
            elements.append(Paragraph(
                f"<b>{matter_name}</b> ({format_hhmm(matter_total)})", 
                normal_style
            ))
            
            for entry in matter_entries:
                entry_line = f"  {entry['entry_date']} - {format_hhmm(entry['total_minutes'])}"
                if entry.get("invoice_original_filename"):
                    entry_line += f" [Invoice: {entry['invoice_original_filename']}]"
                elements.append(Paragraph(entry_line, normal_style))
                
                for action in entry.get("actions", []):
                    action_line = f"    • {action['action_description']} ({format_hhmm(action['duration_minutes'])})"
                    elements.append(Paragraph(action_line, normal_style))
            
            elements.append(Spacer(1, 0.2*cm))
        
        elements.append(Spacer(1, 0.3*cm))
    
    # Build PDF
    doc.build(elements)
    return buffer.getvalue()
