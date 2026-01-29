from execution.supabase_service import SupabaseService
import asyncio

async def test_lookup():
    service = SupabaseService()
    print("--- 1. Fetching ALL Patients ---")
    try:
        patients = await service.get_all_patients()
        for p in patients:
            print(f"Name: {p.get('name')}, Phone: {p.get('phone_number')}")
    except Exception as e:
        print(f"Error listing patients: {e}")

    print("\n--- 2. Testing Lookup '755858596' ---")
    try:
        found = await service.get_patient("755858596")
        if found:
            print(f"[FOUND]: {found}")
        else:
            print("[NOT FOUND]")
    except Exception as e:
        print(f"Error querying: {e}")

if __name__ == "__main__":
    asyncio.run(test_lookup())
