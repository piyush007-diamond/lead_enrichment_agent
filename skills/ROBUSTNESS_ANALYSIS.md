# 🛡️ System Robustness Analysis

> **Goal**: Identify every scenario where an appointment might **fail to book, cancel, or reschedule**, and recommend mitigations to achieve "real receptionist" level reliability.

---

## 📊 Executive Summary

| Flow | Critical Gaps | Risk Level |
|------|---------------|------------|
| **Booking** | No retry on GCal failure, No rollback on partial failure | 🔴 HIGH |
| **Cancel** | Single-event deletion misses duplicates, No partial failure handling | 🟡 MEDIUM |
| **Lookup** | No fuzzy matching on name, Phone format variations | 🟡 MEDIUM |
| **Availability** | No handling for "invalid day" (e.g., past dates) | 🟢 LOW |

---

## 🔴 CRITICAL FAILURE MODES

### 1. **GCal Booking Succeeds, Supabase Fails → Orphan Calendar Event**
**Scenario**: Event created in Google Calendar (line 362), but Supabase `upsert_patient` throws an error (line 392).
**Current Behavior**: Calendar event remains, but no database record exists. User thinks they're booked; system has no way to find them later.
**Risk**: HIGH - Patient calls to cancel, but lookup fails → Manual cleanup required.

**Mitigation**:
```python
# BEFORE: Sequential - no rollback
event = gcal_service.create_appointment(...)
result = await supabase_service.upsert_patient(patient)  # If this fails, event is orphaned

# AFTER: Transactional - rollback on failure
try:
    event = gcal_service.create_appointment(...)
    result = await supabase_service.upsert_patient(patient)
except Exception as e:
    if event:
        gcal_service.delete_event(event['id'])  # ROLLBACK
    raise e
```

---

### 2. **Duplicate Calendar Events on Retry**
**Scenario**: User says "Book me for Friday 10am". First call creates event, but response times out (network). User retries → Second event created.
**Current Behavior**: No idempotency check. Each call creates a new event.
**Risk**: HIGH - Doctor's calendar shows 2 patients at 10am (overbooking).

**Mitigation**:
- Check if patient already has an appointment before creating new one.
- Use `vapi_call_id` as idempotency key.
```python
existing = await supabase_service.get_patient(phone_number)
if existing and existing.get('appointment_date') == target_date_str:
    return _format_response("You already have an appointment on that day.", tool_call_id)
```

---

### 3. **Time Format Parsing Failure**
**Scenario**: User says "Book me at half past three" or "3 o'clock" or "15:00 hours".
**Current Behavior**: Uses `dateparser`, which is good but not perfect. If it fails, booking is rejected (line 347-349).
**Risk**: MEDIUM - Valid intent lost due to parsing limitation.

**Current Coverage (dateparser handles)**:
- "4pm", "4:00 PM", "16:00" ✅
- "half past 3" ✅ (usually)
- "3 o'clock" ✅

**Edge Cases NOT Handled**:
- "At around 3" (vague)
- "Morning" (no specific time)
- "After lunch" (contextual)

**Mitigation**:
- For vague times, prompt user for specific slot instead of failing.
```python
if not appt_datetime:
    available_slots = get_available_slots_for_day(target_date)
    return _format_response(f"I couldn't catch the exact time. We have {available_slots}. Which one works?", tool_call_id)
```

---

### 4. **Race Condition: Slot Taken Between Check and Book**
**Scenario**: User A and User B both check availability at 10am → Both see "10am available". User A books first. User B's booking should fail, but if `is_slot_available` check is done before A's write is committed...
**Current Behavior**: `is_slot_available` (line 354) checks GCal in real-time. Good, but GCal API has ~1-2s propagation delay.
**Risk**: LOW - Mitigated by current check, but race window exists (~1s).

**Mitigation (Optional)**:
- Use Supabase as secondary lock (check if DB already has that slot).
- Implement optimistic locking with retry.

---

## 🟡 MEDIUM RISK FAILURE MODES

### 5. **Phone Number Format Variations**
**Scenario**: User books with "755-858-596", tries to cancel with "7558585960".
**Current Behavior**: `get_patient` does fuzzy search on last 10 digits (line 131-136). Good!
**Gap**: If user says "Add country code 91" → "917558585960", last 10 digits are "7558585960" ✅. But if original was stored as "755858596" (9 digits), match fails.

**Mitigation**:
- Normalize phone on INSERT (strip to last 10 digits always).
```python
# In supabase_service.py create_patient
patient.phone_number = patient.phone_number[-10:]  # Store normalized
```

---

### 6. **Name Mismatch Between GCal and Supabase**
**Scenario**: User says "My name is Piyush Hire". Vapi sends `name: "Piyush Hire"`. GCal event summary = "Piyush Hire". Later, user cancels with "My name is piyush" (lowercase, partial).
**Current Behavior**: `find_event` (line 521) searches GCal for exact match. If Vapi sends partial name, event is not found.
**Risk**: MEDIUM - Event remains in calendar, but DB record is deleted.

**Mitigation**:
- Always use name FROM DATABASE (line 524-525 already does this as fallback, good!).
- Make `find_event` more fuzzy (case-insensitive, substring match).
- Store GCal `event_id` in Supabase patient record for direct lookup.

---

### 7. **Cancel Deletes Only ONE Duplicate**
**Scenario**: Due to earlier bugs, multiple events exist for same person.
**Current Behavior**: `find_event` returns first match only. One event deleted, others remain.
**Discovered During Session**: This caused user to see "appointment still there" after cancel.

**Mitigation**:
```python
# Loop until no more events found
while True:
    event = gcal_service.find_event(patient.get("name"))
    if not event:
        break
    gcal_service.delete_event(event['id'])
```

---

### 8. **Past Date Booking**
**Scenario**: User says "Book me for January 20th" (current date is January 29th). Date parser returns "2026-01-20" (past).
**Current Behavior**: `calculate_free_slots` filters out past times within today, but does NOT block booking for past DATES explicitly.
**Risk**: LOW - GCal will probably reject it, but error message is confusing.

**Mitigation**:
```python
if target_date < datetime.date.today():
    return _format_response("That date has already passed. Would you like to book for a future date?", tool_call_id)
```

---

## 🟢 LOW RISK / ALREADY HANDLED

### 9. **User Doesn't Provide Required Info**
**Scenario**: User says "Book an appointment" (no date, name, phone).
**Current Behavior**: Vapi's prompt engineering handles conversational collection. Tool returns helpful error if data is missing (line 200-201, 442-443).
**Status**: ✅ Handled.

### 10. **GCal API Down**
**Scenario**: Google Cloud has an outage.
**Current Behavior**: Returns graceful error message (line 228-229, 373-375).
**Status**: ✅ Handled (graceful degradation).

### 11. **Supabase API Down**
**Scenario**: Supabase has an outage.
**Current Behavior**: Returns error message (line 411-413).
**Status**: ✅ Handled.

### 12. **Email Service Failure**
**Scenario**: SMTP server unreachable.
**Current Behavior**: Prints error but does NOT fail the booking (line 406-407). Booking still succeeds.
**Status**: ✅ Handled (non-blocking).

---

## 🚀 ENHANCEMENT RECOMMENDATIONS

| Priority | Enhancement | Impact |
|----------|-------------|--------|
| **P0** | Implement rollback on partial failure (GCal success, Supabase fail) | Prevents orphan records |
| **P0** | Normalize phone numbers on save (last 10 digits) | Prevents lookup failures |
| **P1** | Store GCal `event_id` in Supabase for direct delete | Eliminates name-matching issues |
| **P1** | Add past-date validation before booking | Prevents confusing errors |
| **P2** | Loop delete for duplicate event cleanup | Handles edge cases from bugs |
| **P2** | Idempotency check using `vapi_call_id` | Prevents double-booking on retry |
| **P3** | Fuzzy time parsing fallback (prompt for slot list) | Handles vague time expressions |

---

## 📋 TEST CASES TO VALIDATE

Run these manually to verify robustness:

1. **Partial Failure**: Kill Supabase mid-request (simulate API error). Verify GCal event is rolled back.
2. **Duplicate Retry**: Book same slot twice with same phone. Verify second attempt is blocked.
3. **Phone Variations**: Book with "7558585960", cancel with "+91-755-858-596". Verify lookup works.
4. **Past Date**: Say "Book me for yesterday". Verify clear error message.
5. **Name Case**: Book as "PIYUSH HIRE", cancel as "piyush hire". Verify event is found.
6. **Duplicate Events**: Manually create 2 GCal events with same name. Cancel. Verify BOTH are deleted.
7. **Vague Time**: Say "Book me sometime in the morning". Verify system prompts for specific slot.

---

## 📂 Files Impacted by Enhancements

| File | Changes Required |
|------|------------------|
| `server.py` | Rollback logic, past-date check, idempotency |
| `supabase_service.py` | Store `gcal_event_id`, normalize phone |
| `gcal_service.py` | Fuzzy `find_event`, return `event_id` on create |

---

*Generated: 2026-01-29 | Context: Full system analysis*
