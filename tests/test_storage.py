"""
Tests for storage.py - Data persistence operations.
"""

import pytest
import json
import tempfile
import shutil
from datetime import date, datetime
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage import (
    get_empty_data, _serialize_data, _deserialize_data,
    get_matter_by_id, get_matter_by_name, upsert_matter,
    add_entry, update_entry, delete_entry,
    get_entries_by_week, get_matter_total_minutes
)
from utils import compute_week_index


class TestDataStructure:
    """Test data structure operations."""
    
    def test_empty_data_structure(self):
        """Empty data should have matters and entries arrays."""
        data = get_empty_data()
        assert "matters" in data
        assert "entries" in data
        assert isinstance(data["matters"], list)
        assert isinstance(data["entries"], list)
    
    def test_serialize_deserialize_roundtrip(self):
        """Serialization and deserialization should be lossless."""
        data = {
            "matters": [
                {
                    "id": "test-id",
                    "name": "Test Matter",
                    "case_type": "Type A",
                    "created_at": "2024-06-15T10:30:00"
                }
            ],
            "entries": [
                {
                    "id": "entry-id",
                    "entry_date": "2024-06-15",
                    "week_index": 3,
                    "matter_id": "test-id",
                    "actions": [{"action_description": "Work", "duration_minutes": 30}],
                    "total_minutes": 30,
                    "invoice_original_filename": None,
                    "invoice_storage_filename": None,
                    "invoice_path": None,
                    "created_at": "2024-06-15T10:30:00",
                    "updated_at": "2024-06-15T10:30:00"
                }
            ]
        }
        
        serialized = _serialize_data(data)
        deserialized = _deserialize_data(serialized)
        
        assert len(deserialized["matters"]) == 1
        assert len(deserialized["entries"]) == 1
        assert deserialized["matters"][0]["name"] == "Test Matter"


class TestMatterOperations:
    """Test matter CRUD operations."""
    
    def test_get_matter_by_id_found(self):
        """Should find matter by ID."""
        data = {
            "matters": [
                {"id": "id-1", "name": "Matter 1", "case_type": ""},
                {"id": "id-2", "name": "Matter 2", "case_type": ""}
            ],
            "entries": []
        }
        
        matter = get_matter_by_id(data, "id-1")
        assert matter is not None
        assert matter["name"] == "Matter 1"
    
    def test_get_matter_by_id_not_found(self):
        """Should return None for non-existent ID."""
        data = {"matters": [], "entries": []}
        assert get_matter_by_id(data, "non-existent") is None
    
    def test_get_matter_by_name_case_insensitive(self):
        """Should find matter by name case-insensitively."""
        data = {
            "matters": [
                {"id": "id-1", "name": "Test Matter", "case_type": ""}
            ],
            "entries": []
        }
        
        matter = get_matter_by_name(data, "test matter")
        assert matter is not None
        assert matter["id"] == "id-1"
    
    def test_upsert_matter_create_new(self):
        """Should create new matter if not exists."""
        data = {"matters": [], "entries": []}
        
        matter = upsert_matter(data, "New Matter", "Type A")
        
        assert matter["name"] == "New Matter"
        assert matter["case_type"] == "Type A"
        assert "id" in matter
        assert len(data["matters"]) == 1
    
    def test_upsert_matter_update_existing(self):
        """Should update existing matter by name."""
        data = {
            "matters": [
                {"id": "id-1", "name": "Existing Matter", "case_type": "Old Type", 
                 "created_at": "2024-06-01"}
            ],
            "entries": []
        }
        
        matter = upsert_matter(data, "Existing Matter", "New Type")
        
        assert matter["id"] == "id-1"
        assert matter["case_type"] == "New Type"
        assert len(data["matters"]) == 1  # Should not create duplicate


class TestEntryOperations:
    """Test entry CRUD operations."""
    
    def test_add_entry(self):
        """Should add entry with computed values."""
        data = {"matters": [], "entries": []}
        
        entry = add_entry(
            data,
            entry_date=date(2024, 6, 15),
            matter_id="matter-1",
            actions=[
                {"action_description": "Work 1", "duration_minutes": 30},
                {"action_description": "Work 2", "duration_minutes": 45}
            ]
        )
        
        assert entry["entry_date"] == "2024-06-15"
        assert entry["week_index"] == 3  # June 15 is week 3
        assert entry["total_minutes"] == 75  # 30 + 45
        assert "id" in entry
        assert "created_at" in entry
        assert "updated_at" in entry
        assert len(data["entries"]) == 1
    
    def test_add_entry_with_invoice(self):
        """Should add entry with invoice info."""
        data = {"matters": [], "entries": []}
        
        entry = add_entry(
            data,
            entry_date=date(2024, 6, 15),
            matter_id="matter-1",
            actions=[{"action_description": "Work", "duration_minutes": 30}],
            invoice_info={
                "original_filename": "invoice.pdf",
                "storage_filename": "uuid-invoice.pdf",
                "path": "/path/to/file"
            }
        )
        
        assert entry["invoice_original_filename"] == "invoice.pdf"
        assert entry["invoice_storage_filename"] == "uuid-invoice.pdf"
    
    def test_update_entry(self):
        """Should update existing entry."""
        data = {
            "matters": [],
            "entries": [
                {
                    "id": "entry-1",
                    "entry_date": "2024-06-15",
                    "week_index": 3,
                    "matter_id": "matter-1",
                    "actions": [{"action_description": "Old", "duration_minutes": 30}],
                    "total_minutes": 30,
                    "invoice_original_filename": None,
                    "invoice_storage_filename": None,
                    "invoice_path": None,
                    "created_at": "2024-06-15T10:00:00",
                    "updated_at": "2024-06-15T10:00:00"
                }
            ]
        }
        
        updated = update_entry(
            data,
            entry_id="entry-1",
            entry_date=date(2024, 7, 1),  # Change date
            matter_id="matter-2",
            actions=[{"action_description": "New", "duration_minutes": 60}]
        )
        
        assert updated is not None
        assert updated["entry_date"] == "2024-07-01"
        assert updated["week_index"] == 5  # July 1 is week 5
        assert updated["matter_id"] == "matter-2"
        assert updated["total_minutes"] == 60
    
    def test_update_entry_not_found(self):
        """Should return None for non-existent entry."""
        data = {"matters": [], "entries": []}
        
        result = update_entry(
            data,
            entry_id="non-existent",
            entry_date=date(2024, 6, 15),
            matter_id="matter-1",
            actions=[]
        )
        
        assert result is None
    
    def test_delete_entry(self):
        """Should delete entry and return it."""
        data = {
            "matters": [],
            "entries": [
                {
                    "id": "entry-1",
                    "entry_date": "2024-06-15",
                    "week_index": 3,
                    "matter_id": "matter-1",
                    "actions": [],
                    "total_minutes": 0,
                    "invoice_original_filename": None,
                    "invoice_storage_filename": None,
                    "invoice_path": None,
                    "created_at": "",
                    "updated_at": ""
                }
            ]
        }
        
        deleted = delete_entry(data, "entry-1")
        
        assert deleted is not None
        assert deleted["id"] == "entry-1"
        assert len(data["entries"]) == 0
    
    def test_delete_entry_not_found(self):
        """Should return None for non-existent entry."""
        data = {"matters": [], "entries": []}
        assert delete_entry(data, "non-existent") is None


class TestQueries:
    """Test query operations."""
    
    def test_get_entries_by_week(self):
        """Should filter entries by week."""
        data = {
            "matters": [],
            "entries": [
                {"id": "1", "week_index": 1, "total_minutes": 30},
                {"id": "2", "week_index": 1, "total_minutes": 45},
                {"id": "3", "week_index": 2, "total_minutes": 60}
            ]
        }
        
        week1_entries = get_entries_by_week(data, 1)
        assert len(week1_entries) == 2
        
        week2_entries = get_entries_by_week(data, 2)
        assert len(week2_entries) == 1
        
        week3_entries = get_entries_by_week(data, 3)
        assert len(week3_entries) == 0
    
    def test_get_matter_total_minutes(self):
        """Should calculate total minutes for matter."""
        data = {
            "matters": [{"id": "m1", "name": "Matter 1", "case_type": ""}],
            "entries": [
                {"id": "1", "matter_id": "m1", "total_minutes": 30},
                {"id": "2", "matter_id": "m1", "total_minutes": 45},
                {"id": "3", "matter_id": "m2", "total_minutes": 60}
            ]
        }
        
        total = get_matter_total_minutes(data, "m1")
        assert total == 75  # 30 + 45
        
        total_m2 = get_matter_total_minutes(data, "m2")
        assert total_m2 == 60
        
        total_none = get_matter_total_minutes(data, "non-existent")
        assert total_none == 0
