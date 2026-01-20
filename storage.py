"""
Work Log - Storage Module

File-based JSON persistence with atomic writes and data validation.
"""

import json
import os
import shutil
import tempfile
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pathlib import Path

from utils import generate_uuid, normalize_matter_name, compute_week_index

# File paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
INVOICES_DIR = BASE_DIR / "invoices"
DATA_FILE = DATA_DIR / "worklog.json"


def ensure_directories():
    """Ensure data and invoices directories exist."""
    DATA_DIR.mkdir(exist_ok=True)
    INVOICES_DIR.mkdir(exist_ok=True)


def get_empty_data() -> Dict[str, Any]:
    """Return empty data structure."""
    return {
        "matters": [],
        "entries": []
    }


def _serialize_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Python objects to JSON-serializable format."""
    result = {
        "matters": [],
        "entries": []
    }
    
    for matter in data.get("matters", []):
        result["matters"].append({
            "id": matter["id"],
            "name": matter["name"],
            "case_type": matter.get("case_type", ""),
            "created_at": matter["created_at"] if isinstance(matter["created_at"], str) 
                         else matter["created_at"].isoformat()
        })
    
    for entry in data.get("entries", []):
        entry_date = entry["entry_date"]
        if isinstance(entry_date, date):
            entry_date = entry_date.isoformat()
        
        created_at = entry.get("created_at", "")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        
        updated_at = entry.get("updated_at", "")
        if isinstance(updated_at, datetime):
            updated_at = updated_at.isoformat()
        
        result["entries"].append({
            "id": entry["id"],
            "entry_date": entry_date,
            "week_index": entry["week_index"],
            "matter_id": entry["matter_id"],
            "actions": entry["actions"],
            "total_minutes": entry["total_minutes"],
            "invoice_original_filename": entry.get("invoice_original_filename"),
            "invoice_storage_filename": entry.get("invoice_storage_filename"),
            "invoice_path": entry.get("invoice_path"),
            "created_at": created_at,
            "updated_at": updated_at
        })
    
    return result


def _deserialize_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert JSON data to Python objects."""
    result = {
        "matters": [],
        "entries": []
    }
    
    for matter in data.get("matters", []):
        result["matters"].append({
            "id": matter["id"],
            "name": matter["name"],
            "case_type": matter.get("case_type", ""),
            "created_at": matter["created_at"]
        })
    
    for entry in data.get("entries", []):
        entry_date = entry.get("entry_date")
        
        # Migrate actions: add action_date if not present
        actions = entry.get("actions", [])
        for action in actions:
            if "action_date" not in action:
                # Migration: use entry date for existing actions
                action["action_date"] = entry_date
        
        result["entries"].append({
            "id": entry["id"],
            "entry_date": entry_date,  # Keep for compatibility
            "week_index": entry["week_index"],
            "matter_id": entry["matter_id"],
            "actions": actions,
            "total_minutes": entry["total_minutes"],
            "invoice_original_filename": entry.get("invoice_original_filename"),
            "invoice_storage_filename": entry.get("invoice_storage_filename"),
            "invoice_path": entry.get("invoice_path"),
            "created_at": entry.get("created_at", ""),
            "updated_at": entry.get("updated_at", "")
        })
    
    return result


def load_data() -> Dict[str, Any]:
    """
    Load data from JSON file.
    
    Returns:
        Data dictionary with matters and entries
        
    Raises:
        Exception with clear message if file is corrupted
    """
    ensure_directories()
    
    if not DATA_FILE.exists():
        return get_empty_data()
    
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        # Validate structure
        if not isinstance(raw_data, dict):
            raise ValueError("Data file must contain a JSON object")
        
        if "matters" not in raw_data or "entries" not in raw_data:
            raise ValueError("Data file must contain 'matters' and 'entries' arrays")
        
        # Validate matters schema
        for i, matter in enumerate(raw_data.get("matters", [])):
            if not isinstance(matter, dict):
                raise ValueError(f"Matter {i} is not a valid object")
            required_fields = ["id", "name", "created_at"]
            for field in required_fields:
                if field not in matter:
                    raise ValueError(f"Matter {i} missing required field: {field}")
        
        # Validate entries schema
        for i, entry in enumerate(raw_data.get("entries", [])):
            if not isinstance(entry, dict):
                raise ValueError(f"Entry {i} is not a valid object")
            required_fields = ["id", "entry_date", "week_index", "matter_id", "actions", "total_minutes"]
            for field in required_fields:
                if field not in entry:
                    raise ValueError(f"Entry {i} missing required field: {field}")
            
            # Validate actions array
            if not isinstance(entry.get("actions"), list):
                raise ValueError(f"Entry {i} actions must be an array")
        
        return _deserialize_data(raw_data)
        
    except json.JSONDecodeError as e:
        raise Exception(f"Data file is corrupted (invalid JSON): {e}")
    except Exception as e:
        raise Exception(f"Failed to load data: {e}")


def save_data(data: Dict[str, Any]) -> None:
    """
    Save data to JSON file using atomic write.
    
    Uses temp file + rename pattern for safe writes.
    Creates a backup file before saving.
    
    Args:
        data: Data dictionary with matters and entries
    """
    ensure_directories()
    
    # Create backup of existing file before saving
    backup_file = DATA_DIR / "worklog.json.bak"
    if DATA_FILE.exists():
        try:
            shutil.copy2(DATA_FILE, backup_file)
        except Exception:
            # Don't fail if backup creation fails, but continue with save
            pass
    
    serialized = _serialize_data(data)
    
    # Write to temp file first
    fd, temp_path = tempfile.mkstemp(suffix='.json', dir=DATA_DIR)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(serialized, f, ensure_ascii=False, indent=2)
        
        # Atomic replace (works on Windows too with shutil.move)
        shutil.move(temp_path, DATA_FILE)
        
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise Exception(f"Failed to save data: {e}")


# Matter operations

def get_matter_by_id(data: Dict[str, Any], matter_id: str) -> Optional[Dict[str, Any]]:
    """Get matter by ID."""
    for matter in data.get("matters", []):
        if matter["id"] == matter_id:
            return matter
    return None


def get_matter_by_name(data: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    """Get matter by name (case-insensitive)."""
    normalized = normalize_matter_name(name)
    for matter in data.get("matters", []):
        if normalize_matter_name(matter["name"]) == normalized:
            return matter
    return None


def get_all_matters(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get all matters."""
    return data.get("matters", [])


def upsert_matter(data: Dict[str, Any], name: str, case_type: str = "") -> Dict[str, Any]:
    """
    Create or update a matter.
    
    If matter with same name exists (case-insensitive), updates case_type.
    Otherwise creates new matter.
    
    Args:
        data: Data dictionary
        name: Matter name
        case_type: Case type
        
    Returns:
        The created or updated matter
    """
    existing = get_matter_by_name(data, name)
    
    if existing:
        # Update existing
        existing["case_type"] = case_type
        return existing
    else:
        # Create new
        matter = {
            "id": generate_uuid(),
            "name": name.strip(),
            "case_type": case_type,
            "created_at": datetime.now().isoformat()
        }
        data["matters"].append(matter)
        return matter


def update_matter(data: Dict[str, Any], matter_id: str, name: str, case_type: str) -> Optional[Dict[str, Any]]:
    """
    Update an existing matter by ID.
    
    Args:
        data: Data dictionary
        matter_id: Matter ID to update
        name: New name
        case_type: New case type
        
    Returns:
        Updated matter or None if not found
    """
    matter = get_matter_by_id(data, matter_id)
    if matter:
        matter["name"] = name.strip()
        matter["case_type"] = case_type
        return matter
    return None


# Entry operations

def get_entry_by_id(data: Dict[str, Any], entry_id: str) -> Optional[Dict[str, Any]]:
    """Get entry by ID."""
    for entry in data.get("entries", []):
        if entry["id"] == entry_id:
            return entry
    return None


def get_all_entries(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get all entries."""
    return data.get("entries", [])


def get_entries_by_week(data: Dict[str, Any], week_index: int) -> List[Dict[str, Any]]:
    """Get all entries for a specific week."""
    return [e for e in data.get("entries", []) if e["week_index"] == week_index]


def get_entries_by_matter(data: Dict[str, Any], matter_id: str) -> List[Dict[str, Any]]:
    """Get all entries for a specific matter."""
    return [e for e in data.get("entries", []) if e["matter_id"] == matter_id]


def add_entry(data: Dict[str, Any], entry_date: date, matter_id: str, 
              actions: List[Dict[str, Any]], invoice_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Add a new entry.
    
    Args:
        data: Data dictionary
        entry_date: DEPRECATED - calculated from action dates
        matter_id: Matter ID
        actions: List of action dicts with action_description, duration_minutes, and action_date
        invoice_info: Optional dict with original_filename, storage_filename, path
        
    Returns:
        The created entry
    """
    now = datetime.now().isoformat()
    
    # Calculate entry_date from action dates (use earliest)
    action_dates = []
    for action in actions:
        if "action_date" in action:
            try:
                action_dates.append(date.fromisoformat(action["action_date"]))
            except:
                pass
    
    if action_dates:
        calculated_entry_date = min(action_dates)
    else:
        # Fallback to provided entry_date if no action dates
        calculated_entry_date = entry_date
    
    total_minutes = sum(a.get("duration_minutes", 0) for a in actions)
    week_index = compute_week_index(calculated_entry_date)
    
    entry = {
        "id": generate_uuid(),
        "entry_date": calculated_entry_date.isoformat(),
        "week_index": week_index,
        "matter_id": matter_id,
        "actions": actions,
        "total_minutes": total_minutes,
        "invoice_original_filename": invoice_info.get("original_filename") if invoice_info else None,
        "invoice_storage_filename": invoice_info.get("storage_filename") if invoice_info else None,
        "invoice_path": invoice_info.get("path") if invoice_info else None,
        "created_at": now,
        "updated_at": now
    }
    
    data["entries"].append(entry)
    return entry


def update_entry(data: Dict[str, Any], entry_id: str, entry_date: date, 
                 matter_id: str, actions: List[Dict[str, Any]],
                 invoice_info: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Update an existing entry.
    
    Args:
        data: Data dictionary
        entry_id: Entry ID to update
        entry_date: DEPRECATED - calculated from action dates
        matter_id: New matter ID
        actions: New actions list with action_date fields
        invoice_info: Optional invoice info (None means keep existing, empty dict means remove)
        
    Returns:
        Updated entry or None if not found
    """
    entry = get_entry_by_id(data, entry_id)
    if not entry:
        return None
    
    # Calculate entry_date from action dates (use earliest)
    action_dates = []
    for action in actions:
        if "action_date" in action:
            try:
                action_dates.append(date.fromisoformat(action["action_date"]))
            except:
                pass
    
    if action_dates:
        calculated_entry_date = min(action_dates)
    else:
        # Fallback to provided entry_date if no action dates
        calculated_entry_date = entry_date
    
    entry["entry_date"] = calculated_entry_date.isoformat()
    entry["week_index"] = compute_week_index(calculated_entry_date)
    entry["matter_id"] = matter_id
    entry["actions"] = actions
    entry["total_minutes"] = sum(a.get("duration_minutes", 0) for a in actions)
    entry["updated_at"] = datetime.now().isoformat()
    
    # Handle invoice update
    if invoice_info is not None:
        if invoice_info:  # New invoice
            entry["invoice_original_filename"] = invoice_info.get("original_filename")
            entry["invoice_storage_filename"] = invoice_info.get("storage_filename")
            entry["invoice_path"] = invoice_info.get("path")
        else:  # Remove invoice (empty dict)
            entry["invoice_original_filename"] = None
            entry["invoice_storage_filename"] = None
            entry["invoice_path"] = None
    
    return entry


def delete_entry(data: Dict[str, Any], entry_id: str) -> Optional[Dict[str, Any]]:
    """
    Delete an entry by ID.
    
    Args:
        data: Data dictionary
        entry_id: Entry ID to delete
        
    Returns:
        Deleted entry or None if not found
    """
    entries = data.get("entries", [])
    for i, entry in enumerate(entries):
        if entry["id"] == entry_id:
            return entries.pop(i)
    return None


# Invoice file operations

def save_invoice_file(uploaded_file) -> Dict[str, Any]:
    """
    Save an uploaded invoice file.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        Dict with original_filename, storage_filename, path
    """
    ensure_directories()
    
    original_filename = uploaded_file.name
    storage_filename = f"{generate_uuid()}_{original_filename}"
    file_path = INVOICES_DIR / storage_filename
    
    with open(file_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    
    return {
        "original_filename": original_filename,
        "storage_filename": storage_filename,
        "path": str(file_path)
    }


def delete_invoice_file(storage_filename: str) -> bool:
    """
    Delete an invoice file.
    
    Args:
        storage_filename: UUID-based filename
        
    Returns:
        True if deleted, False if not found or error
    """
    if not storage_filename:
        return False
    
    file_path = INVOICES_DIR / storage_filename
    
    try:
        if file_path.exists():
            file_path.unlink()
            return True
    except Exception:
        pass
    
    return False


def get_invoice_path(storage_filename: str) -> Optional[Path]:
    """
    Get full path to invoice file.
    
    Args:
        storage_filename: UUID-based filename
        
    Returns:
        Path object or None if not found
    """
    if not storage_filename:
        return None
    
    file_path = INVOICES_DIR / storage_filename
    return file_path if file_path.exists() else None


def get_matter_total_minutes(data: Dict[str, Any], matter_id: str) -> int:
    """
    Calculate total minutes for a matter.
    
    Args:
        data: Data dictionary
        matter_id: Matter ID
        
    Returns:
        Total minutes
    """
    entries = get_entries_by_matter(data, matter_id)
    return sum(e.get("total_minutes", 0) for e in entries)


def get_unique_action_descriptions(data: Dict[str, Any], matter_id: Optional[str] = None) -> List[str]:
    """
    Get unique action descriptions from all entries.
    
    Args:
        data: Data dictionary
        matter_id: Optional matter ID to prioritize (those actions listed first)
        
    Returns:
        List of unique action descriptions, sorted with matter-specific first
    """
    matter_actions = set()
    other_actions = set()
    
    for entry in data.get("entries", []):
        for action in entry.get("actions", []):
            desc = action.get("action_description", "").strip()
            if desc:
                if matter_id and entry.get("matter_id") == matter_id:
                    matter_actions.add(desc)
                else:
                    other_actions.add(desc)
    
    # Return matter actions first, then others (excluding duplicates)
    result = sorted(matter_actions)
    result.extend(sorted(other_actions - matter_actions))
    return result
