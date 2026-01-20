# Work Log - Retrospective Work Diary

A production-quality Streamlit application for organizing retrospective work records from June 1 - December 31, 2024.

[![Tests](https://img.shields.io/badge/tests-66%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.12-blue)]()
[![Streamlit](https://img.shields.io/badge/streamlit-1.30%2B-red)]()

---

## Features

### 📝 Entry Management
- Add, edit, and delete work entries
- Multiple actions per entry with 15-minute increments
- Invoice file upload and management
- Automatic week calculation (31 custom weeks)

### 📊 Viewing & Filtering
- Weekly view with matter grouping
- Filter by matter, case type, or date range
- Hebrew RTL support throughout the UI
- Real-time totals and statistics

### 📤 Export Options
- **CSV**: Work entries (detailed) and weekly summary
- **PDF**: Full report with Hebrew font support
- UTF-8 BOM encoding for Excel compatibility
- Retrospective disclaimer included in all exports

### 🛡️ Data Safety
- Atomic file writes prevent corruption
- Automatic backup before each save
- Transaction rollback on failures
- Comprehensive error handling

---

## Quick Start

### Installation
```bash
pip install -r requirements.txt
```

### Run Locally
```bash
streamlit run app.py
```

Access at: http://localhost:8501

---

## Requirements

- Python 3.12+
- streamlit >= 1.30.0
- pandas >= 2.0.0
- reportlab >= 4.0.0
- pytest >= 7.0.0

---

## Project Structure

```
worklog-retro/
├── app.py                 # Main Streamlit application
├── storage.py             # Data persistence layer
├── utils.py               # Helper functions
├── report.py              # Export functionality
├── requirements.txt       # Python dependencies
├── data/                  # Data directory (auto-created)
│   ├── worklog.json      # Main data file
│   └── worklog.json.bak  # Automatic backup
├── invoices/              # Invoice files (auto-created)
├── fonts/                 # Hebrew font for PDFs
│   └── NotoSansHebrew-Regular.ttf
├── tests/                 # Test suite
│   ├── test_storage.py   # Storage tests
│   └── test_utils.py     # Utility tests
└── docs/                  # Documentation
    ├── USER_GUIDE.md
    ├── DEPLOYMENT_CHECKLIST.md
    ├── STABILITY_FIXES.md
    └── READY_FOR_USERS.md
```

---

## Testing

Run the test suite:
```bash
pytest tests/ -v
```

All 66 tests should pass.

---

## Documentation

- **[USER_GUIDE.md](USER_GUIDE.md)** - User instructions and troubleshooting
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Technical verification
- **[STABILITY_FIXES.md](STABILITY_FIXES.md)** - Recent improvements
- **[READY_FOR_USERS.md](READY_FOR_USERS.md)** - Production readiness summary

---

## Key Design Decisions

### Date Range
The app uses a **fixed date range** (2024-06-01 to 2024-12-31) as this is a retrospective work log for organizing existing records, not for planning future work.

### Custom Weeks
Uses **31 consecutive 7-day weeks** starting from June 1, 2024:
- Week 1: June 1-7
- Week 2: June 8-14
- ...
- Week 31: December 29-31

### Time Increments
All durations use **15-minute increments** for billing accuracy.

### Retrospective Disclaimer
All exports include: *"Work log organized retrospectively from existing records."*

---

## Stability Features

### Automatic Backups
Every save creates a backup at `data/worklog.json.bak`

### Atomic Writes
Uses temp file + rename pattern to prevent corruption

### Transaction Rollback
Failed saves don't leave partial data in memory

### Schema Validation
Validates JSON structure on load to detect corruption early

### Error Recovery
Graceful handling of:
- Missing or deleted matters
- Malformed dates
- Invalid JSON
- Missing font files
- File I/O errors

---

## Deployment

### Streamlit Cloud (Recommended)
1. Push to GitHub
2. Deploy on share.streamlit.io
3. Set Python version to 3.12
4. App auto-deploys on push

### Docker
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "app.py"]
```

---

## Contributing

This is a production application. Before making changes:
1. Run the test suite
2. Verify all 66 tests pass
3. Test manually with real data
4. Update documentation as needed

---

## License

[Add your license here]

---

## Support

For issues or questions:
1. Check the [USER_GUIDE.md](USER_GUIDE.md) troubleshooting section
2. Review [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
3. Check terminal output for error messages
4. Verify backup file exists for data recovery

---

## Status

✅ **Production Ready**
- All tests passing (66/66)
- All stability fixes applied
- Comprehensive error handling
- Full documentation
- No known critical bugs

---

**Built with ❤️ using Streamlit**
