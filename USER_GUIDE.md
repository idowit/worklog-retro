# Work Log - User Guide

## Quick Start

This app helps you organize a retrospective work diary for **June 1 - December 31, 2024**.

**Important**: This app only organizes existing records. It does NOT create, estimate, or infer any work data. All entries must be explicitly entered by you.

---

## Getting Started

### Installation
```bash
pip install -r requirements.txt
streamlit run app.py
```

The app will open in your browser at http://localhost:8501

---

## Main Features

### 1. Adding Work Entries

1. Click **"➕ הוספת רישום / Add Entry"** in the sidebar
2. Select a date (must be between June 1 - Dec 31, 2024)
3. Choose a matter (case/project) or create a new one
4. Add one or more actions:
   - Describe what you did
   - Set duration in 15-minute increments (15, 30, 45, 60, etc.)
5. Optionally upload an invoice (PDF, image, or document)
6. Click **"💾 שמור / Save"**

**The app automatically saves and creates a backup!**

---

### 2. Viewing Your Work

#### Weekly View
- Click **"📅 תצוגה שבועית / Weekly View"**
- See all entries organized by week
- Filter by matter, case type, or date range
- Edit or delete entries
- Download invoices

#### Matters View
- Click **"📁 תיקים / Matters"**
- See all your cases/projects
- View total time spent on each

---

### 3. Exporting Reports

Click **"📊 ייצוא / Export"** to generate:

1. **Work Entries CSV**: One row per action (detailed)
2. **Weekly Summary CSV**: One row per week (summary)
3. **PDF Report**: Full report with weekly breakdown

All exports include the disclaimer: *"Work log organized retrospectively from existing records."*

---

## Understanding Weeks

The app uses **custom 7-day weeks** starting from June 1, 2024:

- **Week 1**: June 1-7, 2024
- **Week 2**: June 8-14, 2024
- ...
- **Week 31**: December 29-31, 2024

When you select a date, the app automatically calculates which week it belongs to.

---

## Tips & Best Practices

### ✅ Do's
- Save frequently (though the app auto-saves)
- Use descriptive action names
- Keep durations in 15-minute increments
- Upload invoices for important entries
- Use the weekly view to review your work

### ❌ Don'ts
- Don't enter dates outside June 1 - Dec 31, 2024
- Don't use durations less than 15 minutes
- Don't delete the `data/` or `invoices/` folders
- Don't manually edit `worklog.json` while the app is running

---

## Data Safety

### Automatic Backups
Every time you save, the app creates a backup at:
```
data/worklog.json.bak
```

### If Something Goes Wrong
1. Close the app
2. Copy `data/worklog.json.bak` to `data/worklog.json`
3. Restart the app

### Your Data Location
- **Main data**: `data/worklog.json`
- **Backup**: `data/worklog.json.bak`
- **Invoices**: `invoices/[filename]`

---

## Troubleshooting

### "Failed to load data"
- Check if `data/worklog.json` exists and is valid JSON
- Try restoring from `data/worklog.json.bak`

### "Failed to save"
- Check if you have write permissions
- Ensure disk space is available
- Check if `data/` folder exists

### Hebrew text not showing in PDF
- This is expected if the font file is missing
- Check that `fonts/NotoSansHebrew-Regular.ttf` exists
- English text will still work

### Invoice upload failed
- Check file size (keep under 10MB)
- Ensure file type is supported (PDF, PNG, JPG, DOC, DOCX)
- Check disk space

---

## Keyboard Shortcuts

- **Ctrl+R**: Refresh the page
- **Ctrl+Shift+R**: Hard refresh (clears cache)

---

## Support

If you encounter issues:
1. Check the error message in the app
2. Look at the terminal/console for detailed logs
3. Verify all dependencies are installed
4. Check the `DEPLOYMENT_CHECKLIST.md` for common issues

---

## Data Format

### Time Format
All times are displayed as `HH:MM` (hours:minutes)
- Example: `02:30` = 2 hours 30 minutes

### Date Format
All dates use ISO format: `YYYY-MM-DD`
- Example: `2024-06-15` = June 15, 2024

---

## Privacy & Security

- All data is stored **locally** on your computer
- No data is sent to external servers (unless you deploy to Streamlit Cloud)
- Invoice files are stored with unique IDs to prevent conflicts
- Backup files are created automatically for safety

---

## Limitations

- **Date range**: Only 2024-06-01 to 2024-12-31
- **Time increments**: Minimum 15 minutes
- **Retrospective only**: This is for organizing past work, not planning future work

---

## Need Help?

Check these files for more information:
- `DEPLOYMENT_CHECKLIST.md` - Technical details
- `STABILITY_FIXES.md` - Recent improvements
- `README.md` - Project overview (if available)

---

**Enjoy using the Work Log app!** 📋
