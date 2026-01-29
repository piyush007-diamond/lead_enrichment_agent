# Future Enhancements (Nice to Have)

> These features are deferred until specific issues arise in production.

## 🔮 Backlog

### #2 - Idempotency Check (Duplicate Booking Prevention)
**Trigger**: If users report "I have two appointments but only booked once"
**Impact**: Prevents duplicate calendar events from network retries
**Implementation**: Check if patient already has appointment for same date/time before creating new one
**Complexity**: Low (1-2 hour)
**Trade-off**: Might block legitimate multiple bookings on same day

---

### #6 - Direct Event ID Storage
**Trigger**: If cancellations frequently fail with "event not found" errors
**Impact**: 100% accurate event deletion (no name matching issues)
**Implementation**: 
1. Add `gcal_event_id` column to Supabase `patients` table
2. Store event ID during booking
3. Delete by ID during cancellation
**Complexity**: Medium (requires DB migration)
**Trade-off**: One-time migration effort

---

## ✅ Production-Ready Features (Already Implemented)

1. **Rollback on Partial Failure** - Prevents orphan calendar events
2. **Phone Number Normalization** - Consistent lookup (last 10 digits)
3. **Past Date Validation** - Clear error for booking in the past
4. **Time Parsing Fallback** - Offers slots when time is unclear
5. **Duplicate Event Cleanup** - Deletes all duplicates during cancel

---

*Last Updated: 2026-01-30*
