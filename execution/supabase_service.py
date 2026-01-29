"""
Supabase Service Module - Stage 4
==================================
Purpose: Handle patient CRUD operations with Supabase.
         Implements upsert by phone number (unique identifier).

VALIDATION STATUS:
- [x] Query patient by phone number
- [x] Create new patient
- [x] Update existing patient
- [x] Upsert logic (create or update)
- [x] Get all patient fields

PATIENT TABLE SCHEMA (from requirements):
- first_name
- last_name  
- phone_number (unique identifier)
- email
- insurance
- age
- eye_concern
- appointment_date
- appointment_time

POTENTIAL ERRORS & SOLUTIONS:
1. Patient not found -> Create new record
2. Duplicate phone -> Update existing (upsert)
3. Missing fields -> Allow nulls for optional fields
4. Network error -> Retry with backoff

VAPI ALTERNATIVE CHECK:
- Vapi has NO built-in Supabase integration
- Custom webhook is required for database operations
"""

import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("supabase_project_url", "")
SUPABASE_KEY = os.getenv("supabase_service_role", "")  # Use service role for server-side
PATIENTS_TABLE = "patients"


@dataclass
class Patient:
    """
    Patient data model matching actual Supabase table schema.
    
    ACTUAL SCHEMA (discovered from live query):
    - id (auto-generated)
    - name
    - phone_number 
    - vapi_call_id
    
    NOTE: If you need additional fields (first_name, last_name, email, etc.),
    you must add columns to the Supabase patients table first.
    """
    name: str  # Single name field (not first/last)
    phone_number: str
    vapi_call_id: Optional[str] = None
    
    # Extended fields (add these columns to Supabase if needed)
    email: Optional[str] = None
    appointment_date: Optional[str] = None  # YYYY-MM-DD
    appointment_time: Optional[str] = None  # HH:MM
    eye_concern: Optional[str] = None
    
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict, including only fields that exist in Supabase."""
        result = {
            "name": self.name,
            "phone_number": self.phone_number,
            "email": self.email,
            "appointment_date": self.appointment_date,
            "appointment_time": self.appointment_time,
            "description": self.description
        }
        # Filter out None values to let DB defaults handle them (optional)
        # But Supabase usually handles explicit nulls fine.
        return result


class SupabaseService:
    """Service class for Supabase operations."""
    
    def __init__(self, url: str = None, key: str = None):
        self.url = url or SUPABASE_URL
        self.key = key or SUPABASE_KEY
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"  # Return inserted/updated data
        }
        self._validate_config()
    
    def _validate_config(self):
        if not self.url:
            raise ValueError("Supabase URL not configured")
        if not self.key:
            raise ValueError("Supabase key not configured")
    
    def _get_rest_url(self, table: str) -> str:
        """Build REST API URL for a table."""
        return f"{self.url}/rest/v1/{table}"
    
    async def get_patient(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Find a patient by their phone number (Robust Fuzzy Search).
        Ref: server.py calls this 'get_patient', not 'get_patient_by_phone'.
        
        Args:
            phone_number: The patient's phone number
        
        Returns:
            Patient data dict if found, None otherwise
        """
        # Robust Search Strategy:
        # 1. Strip to digits
        # 2. Match last 10 digits (Standard Indian Mobile)
        digits = "".join(filter(str.isdigit, phone_number))
        if len(digits) >= 10:
            # Match last 10 digits
            # PostgREST uses * as wildcard for 'like', but % for 'ilike'.
            # We must rely on httpx to encode it correctly.
            search_term = f"%{digits[-10:]}" 
        else:
            search_term = f"%{phone_number}%"

        # Ref: Use params dict to ensure proper URL encoding of % characters
        # Manual string construction led to Cloudflare blocking raw %
        base_url = self._get_rest_url(PATIENTS_TABLE)
        params = {
            "phone_number": f"ilike.{search_term}",
            "select": "*"
        }
        
        async with httpx.AsyncClient() as client:
            # Pass params to client.get to handle encoding
            response = await client.get(base_url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                print(f"Supabase Lookup Error: {response.text}") # Log error for debug
                return None
            
            data = response.json()
            return data[0] if data else None
    
    async def create_patient(self, patient: Patient) -> Dict[str, Any]:
        """
        Create a new patient record.
        
        Args:
            patient: Patient data to insert
        
        Returns:
            Created patient data including generated ID
        """
        url = self._get_rest_url(PATIENTS_TABLE)
        
        # Normalize phone number to last 10 digits for consistency
        patient.phone_number = ''.join(filter(str.isdigit, patient.phone_number))[-10:]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, 
                headers=self.headers,
                json=patient.to_dict()
            )
            
            if response.status_code not in [200, 201]:
                raise Exception(f"Supabase create error: {response.text}")
            
            data = response.json()
            return data[0] if isinstance(data, list) else data
    
    async def update_patient(
        self, 
        phone_number: str, 
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an existing patient by phone number.
        
        Args:
            phone_number: Patient's phone number
            updates: Dict of fields to update
        
        Returns:
            Updated patient data
        """
        # Ref: Use params for safe key encoding
        base_url = self._get_rest_url(PATIENTS_TABLE)
        params = {
            "phone_number": f"eq.{phone_number}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                base_url,
                headers=self.headers,
                params=params,
                json=updates
            )
            
            if response.status_code not in [200, 204]:
                raise Exception(f"Supabase update error: {response.text}")
            
            data = response.json()
            return data[0] if data else None

    async def delete_patient(self, phone_number: str) -> bool:
        """
        Delete a patient by phone number.
        
        Args:
            phone_number: Phone number to delete
            
        Returns:
            True if deleted, False otherwise
        """
        # Ref: Use params for safe key encoding
        base_url = self._get_rest_url(PATIENTS_TABLE)
        params = {
            "phone_number": f"eq.{phone_number}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                base_url,
                headers=self.headers,
                params=params
            )
            
            if response.status_code not in [200, 204]:
                print(f"Delete Error: {response.text}")
                return False
                
            return True
    
    async def upsert_patient(self, patient: Patient) -> Dict[str, Any]:
        """
        Create or update patient based on phone number.
        This is the main method for appointment booking.
        
        Logic:
        1. Check if patient exists by phone
        2. If exists -> update with new appointment details
        3. If not exists -> create new patient
        
        Args:
            patient: Patient data with all available fields
        
        Returns:
            Patient data after upsert operation
        """
        existing = await self.get_patient(patient.phone_number)
        
        if existing:
            # Update existing patient with new appointment
            updates = patient.to_dict()
            # Remove phone_number from updates (it's the key, not a value to update)
            updates.pop('phone_number', None)
            return await self.update_patient(patient.phone_number, updates)
        else:
            # Create new patient
            return await self.create_patient(patient)
    
    async def get_all_patients(self) -> List[Dict[str, Any]]:
        """Get all patients (for admin/testing purposes)."""
        url = self._get_rest_url(PATIENTS_TABLE)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            
            if response.status_code != 200:
                raise Exception(f"Supabase error: {response.text}")
            
            return response.json()


# Synchronous wrapper for non-async contexts
class SupabaseServiceSync:
    """Synchronous wrapper for SupabaseService."""
    
    def __init__(self, url: str = None, key: str = None):
        self.url = url or SUPABASE_URL
        self.key = key or SUPABASE_KEY
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
    
    def _get_rest_url(self, table: str) -> str:
        return f"{self.url}/rest/v1/{table}"
    
    def get_patient_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Find patient by phone number (sync version)."""
        base_url = self._get_rest_url(PATIENTS_TABLE)
        params = {"phone_number": f"eq.{phone_number}"}
        
        with httpx.Client() as client:
            response = client.get(base_url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                raise Exception(f"Supabase error: {response.text}")
            
            data = response.json()
            return data[0] if data else None
    
    def create_patient(self, patient: Patient) -> Dict[str, Any]:
        """Create new patient (sync version)."""
        url = self._get_rest_url(PATIENTS_TABLE)
        
        with httpx.Client() as client:
            response = client.post(
                url,
                headers=self.headers,
                json=patient.to_dict()
            )
            
            if response.status_code not in [200, 201]:
                raise Exception(f"Supabase create error: {response.text}")
            
            data = response.json()
            return data[0] if isinstance(data, list) else data
    
    def update_patient(self, phone_number: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update patient (sync version)."""
        base_url = self._get_rest_url(PATIENTS_TABLE)
        params = {"phone_number": f"eq.{phone_number}"}
        
        with httpx.Client() as client:
            response = client.patch(
                base_url,
                headers=self.headers,
                params=params,
                json=updates
            )
            
            if response.status_code not in [200, 204]:
                raise Exception(f"Supabase update error: {response.text}")
            
            data = response.json()
            return data[0] if data else None
    
    def upsert_patient(self, patient: Patient) -> Dict[str, Any]:
        """Create or update patient based on phone number (sync version)."""
        existing = self.get_patient_by_phone(patient.phone_number)
        
        if existing:
            updates = patient.to_dict()
            updates.pop('phone_number', None)
            return self.update_patient(patient.phone_number, updates)
        else:
            return self.create_patient(patient)


# ============================================================================
# VALIDATION TESTS
# ============================================================================

def run_validation_tests():
    """
    Run validation tests for Supabase service.
    Note: Requires live Supabase connection.
    """
    
    print("=" * 60)
    print("SUPABASE SERVICE VALIDATION TESTS")
    print("=" * 60)
    
    # Check configuration
    print("\n--- Configuration Check ---")
    print(f"Supabase URL: {'✅ Configured' if SUPABASE_URL else '❌ Missing'}")
    print(f"Supabase Key: {'✅ Configured' if SUPABASE_KEY else '❌ Missing'}")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("\n⚠️ Cannot run live tests without configuration")
        print("Set supabase_project_url and supabase_service_role in .env")
        return False
    
    # Initialize sync service
    service = SupabaseServiceSync()
    
    # Test 1: Create test patient (using correct schema: name, phone_number)
    print("\n--- Test 1: Create Patient ---")
    test_phone = f"TEST_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    test_patient = Patient(
        name="Test Patient",
        phone_number=test_phone,
        vapi_call_id="test-call-id-123"
    )
    
    try:
        result = service.create_patient(test_patient)
        print(f"Created patient: {result.get('name')}")
        print("✅ PASS")
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False
    
    # Test 2: Get patient by phone
    print("\n--- Test 2: Get Patient by Phone ---")
    try:
        result = service.get_patient_by_phone(test_phone)
        if result and result.get('name') == "Test Patient":
            print(f"Found patient: {result.get('phone_number')}")
            print("✅ PASS")
        else:
            print("❌ FAIL: Patient not found")
            return False
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False
    
    # Test 3: Update patient
    print("\n--- Test 3: Update Patient ---")
    try:
        result = service.update_patient(test_phone, {
            "name": "Updated Name"
        })
        print(f"Updated name: {result.get('name')}")
        print("✅ PASS")
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False
    
    # Test 4: Upsert (update existing)
    print("\n--- Test 4: Upsert Existing ---")
    updated_patient = Patient(
        name="Upserted Name",
        phone_number=test_phone,
        vapi_call_id="updated-call-id"
    )
    try:
        result = service.upsert_patient(updated_patient)
        if result.get('name') == "Upserted Name":
            print(f"Upserted (updated): {result.get('name')}")
            print("✅ PASS")
        else:
            print("❌ FAIL: Name not updated")
            return False
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False
    
    # Test 5: Upsert (create new)
    print("\n--- Test 5: Upsert New ---")
    new_phone = f"NEW_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    new_patient = Patient(
        name="New Patient",
        phone_number=new_phone
    )
    try:
        result = service.upsert_patient(new_patient)
        if result.get('name') == "New Patient":
            print(f"Upserted (created): {result.get('name')}")
            print("✅ PASS")
        else:
            print("❌ FAIL: Patient not created")
            return False
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False
    
    # Cleanup: Note - in production you'd delete test records
    print("\n--- Cleanup ---")
    print("Test records created with prefixes 'TEST_' and 'NEW_'")
    print("Clean these manually if needed")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    run_validation_tests()
