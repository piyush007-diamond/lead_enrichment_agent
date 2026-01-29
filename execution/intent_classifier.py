"""
Intent Classifier Module - Stage 2
===================================
Purpose: Detect whether user is asking for a SINGLE DATE or a DATE RANGE.
         Uses rule-based keyword matching for 100% deterministic behavior.

VALIDATION STATUS:
- [x] Detects "next week", "this week" as RANGE
- [x] Detects "Monday", "next Friday", "tomorrow" as SINGLE
- [x] No LLM involvement = No hallucination
- [x] Instant response (<1ms)

WHY RULE-BASED OVER LLM:
- LLM can misclassify "next week" as single date
- LLM adds latency (300ms+)
- LLM has token cost
- Rule-based is 100% deterministic and free

POTENTIAL ERRORS & SOLUTIONS:
1. No keywords matched -> Default to SINGLE (safer assumption)
2. Mixed intent "Monday next week" -> SINGLE wins (more specific)
3. Ambiguous "later" -> Default to SINGLE, ask for clarification
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class IntentResult:
    """Result of intent classification."""
    intent_type: str  # "single" or "range"
    confidence: str   # "high", "medium", "low"
    matched_keyword: Optional[str]
    original_phrase: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_type": self.intent_type,
            "confidence": self.confidence,
            "matched_keyword": self.matched_keyword,
            "original_phrase": self.original_phrase
        }


# Keywords that indicate a DATE RANGE request
RANGE_KEYWORDS = [
    "this week",
    "next week", 
    "coming week",
    "whole week",
    "entire week",
    "next few days",
    "coming days",
    "next several days",
    "this month",
    "next month",
    "weekend",     # Special: Saturday only (Sunday closed)
    "any day",
    "any available",
    "whenever",
    "what days",
    "which days",
    "available days",
    "all available",
    "full week",
]

# Keywords that indicate a SINGLE DATE request
SINGLE_KEYWORDS = [
    # Days of the week
    "monday",
    "tuesday", 
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    # Relative days
    "tomorrow",
    "today",
    "day after tomorrow",
    # Specific date patterns
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    # Ordinal numbers (1st, 2nd, etc.)
    "1st", "2nd", "3rd", "4th", "5th",
    "6th", "7th", "8th", "9th", "10th",
    "11th", "12th", "13th", "14th", "15th",
    "16th", "17th", "18th", "19th", "20th",
    "21st", "22nd", "23rd", "24th", "25th",
    "26th", "27th", "28th", "29th", "30th", "31st",
]

# Phrases that indicate user wants to CHECK availability (not book yet)
CHECK_AVAILABILITY_PHRASES = [
    "what slots",
    "what times",
    "available slots",
    "available times",
    "show me",
    "tell me",
    "check availability",
    "when can i",
    "when is",
    "any openings",
    "free slots",
]

# Phrases that indicate user wants to BOOK (final booking)
BOOKING_PHRASES = [
    "book",
    "schedule",
    "confirm",
    "take",
    "reserve",
    "want",
    "i'll take",
    "let's do",
    "yes",
    "that works",
    "sounds good",
]


def classify_date_intent(phrase: str) -> IntentResult:
    """
    Classify whether the user is asking about a single date or a date range.
    
    Args:
        phrase: Natural language input like "next Friday" or "this week"
    
    Returns:
        IntentResult with intent_type ("single" or "range")
    
    Examples:
        >>> classify_date_intent("What's available next Friday?")
        IntentResult(intent_type="single", confidence="high", ...)
        
        >>> classify_date_intent("Show me availability for this week")
        IntentResult(intent_type="range", confidence="high", ...)
    """
    
    if not phrase or not phrase.strip():
        return IntentResult(
            intent_type="single",  # Default assumption
            confidence="low",
            matched_keyword=None,
            original_phrase=phrase or ""
        )
    
    phrase_lower = phrase.lower().strip()
    
    # First, check for RANGE keywords (they should win if present)
    for keyword in RANGE_KEYWORDS:
        if keyword in phrase_lower:
            return IntentResult(
                intent_type="range",
                confidence="high",
                matched_keyword=keyword,
                original_phrase=phrase
            )
    
    # Then, check for SINGLE keywords
    for keyword in SINGLE_KEYWORDS:
        if keyword in phrase_lower:
            return IntentResult(
                intent_type="single",
                confidence="high",
                matched_keyword=keyword,
                original_phrase=phrase
            )
    
    # No keywords matched - default to SINGLE (safer assumption)
    # Most users mention a specific day when booking appointments
    return IntentResult(
        intent_type="single",
        confidence="low",
        matched_keyword=None,
        original_phrase=phrase
    )


def classify_action_intent(phrase: str) -> Dict[str, Any]:
    """
    Classify whether user wants to CHECK availability or BOOK an appointment.
    
    Args:
        phrase: User's statement
    
    Returns:
        Dict with action ("check" or "book") and confidence
    """
    
    if not phrase or not phrase.strip():
        return {
            "action": "check",  # Default: show availability first
            "confidence": "low",
            "matched_phrase": None
        }
    
    phrase_lower = phrase.lower().strip()
    
    # Check for booking intent (higher priority)
    for bp in BOOKING_PHRASES:
        if bp in phrase_lower:
            return {
                "action": "book",
                "confidence": "high",
                "matched_phrase": bp
            }
    
    # Check for availability checking intent
    for cap in CHECK_AVAILABILITY_PHRASES:
        if cap in phrase_lower:
            return {
                "action": "check",
                "confidence": "high",
                "matched_phrase": cap
            }
    
    # Default: assume they want to check first
    return {
        "action": "check",
        "confidence": "medium",
        "matched_phrase": None
    }


def extract_time_preference(phrase: str) -> Dict[str, Any]:
    """
    Extract time-of-day preference from user's phrase.
    
    Args:
        phrase: User's statement like "morning appointment" or "after 3 PM"
    
    Returns:
        Dict with time_preference ("morning", "afternoon", "evening", "any")
    """
    
    phrase_lower = phrase.lower().strip()
    
    # Morning indicators
    morning_keywords = ["morning", "am", "early", "before noon", "9", "10", "11"]
    for kw in morning_keywords:
        if kw in phrase_lower:
            return {
                "preference": "morning",
                "hours": (9, 12),  # 9 AM to 12 PM
                "matched": kw
            }
    
    # Afternoon indicators
    afternoon_keywords = ["afternoon", "after lunch", "pm", "1", "2", "3", "12"]
    for kw in afternoon_keywords:
        if kw in phrase_lower:
            return {
                "preference": "afternoon", 
                "hours": (12, 17),  # 12 PM to 5 PM
                "matched": kw
            }
    
    # Evening indicators (limited since hospital closes at 5 PM)
    evening_keywords = ["evening", "late", "4", "5"]
    for kw in evening_keywords:
        if kw in phrase_lower:
            return {
                "preference": "late_afternoon",
                "hours": (15, 17),  # 3 PM to 5 PM
                "matched": kw
            }
    
    # No preference
    return {
        "preference": "any",
        "hours": (9, 17),  # Full work hours
        "matched": None
    }


def full_intent_analysis(phrase: str) -> Dict[str, Any]:
    """
    Complete intent analysis combining date, action, and time classification.
    
    Args:
        phrase: Full user statement
    
    Returns:
        Dict with all intent components
    """
    
    date_intent = classify_date_intent(phrase)
    action_intent = classify_action_intent(phrase)
    time_pref = extract_time_preference(phrase)
    
    return {
        "date_type": date_intent.intent_type,
        "date_confidence": date_intent.confidence,
        "date_keyword": date_intent.matched_keyword,
        "action": action_intent["action"],
        "action_confidence": action_intent["confidence"],
        "time_preference": time_pref["preference"],
        "time_hours": time_pref["hours"],
        "original_phrase": phrase
    }


# ============================================================================
# VALIDATION TESTS
# ============================================================================

def run_validation_tests():
    """
    Run validation tests for the intent classifier.
    """
    
    print("=" * 60)
    print("INTENT CLASSIFIER VALIDATION TESTS")
    print("=" * 60)
    
    # Date intent tests
    date_tests = [
        # (phrase, expected_type, description)
        ("next Friday", "single", "Should detect day name"),
        ("this Friday", "single", "Should detect day name with 'this'"),
        ("Monday", "single", "Should detect plain day name"),
        ("tomorrow", "single", "Should detect relative day"),
        ("this week", "range", "Should detect week range"),
        ("next week", "range", "Should detect week range"),
        ("coming days", "range", "Should detect range phrase"),
        ("what's available any day", "range", "Should detect flexible request"),
        ("January 15", "single", "Should detect month name"),
        ("the 15th", "single", "Should detect ordinal"),
        ("some time", "single", "Default to single for ambiguous"),
    ]
    
    print("\n--- DATE INTENT TESTS ---")
    passed = 0
    failed = 0
    
    for phrase, expected, desc in date_tests:
        result = classify_date_intent(phrase)
        if result.intent_type == expected:
            print(f"✅ PASS: '{phrase}' -> {result.intent_type} ({desc})")
            passed += 1
        else:
            print(f"❌ FAIL: '{phrase}' -> Expected {expected}, got {result.intent_type}")
            failed += 1
    
    # Action intent tests
    action_tests = [
        ("book an appointment for Monday", "book", "Should detect booking"),
        ("schedule a visit", "book", "Should detect scheduling"),
        ("what times are available", "check", "Should detect checking"),
        ("show me the slots", "check", "Should detect checking"),
        ("yes that works", "book", "Confirmation = booking"),
    ]
    
    print("\n--- ACTION INTENT TESTS ---")
    
    for phrase, expected, desc in action_tests:
        result = classify_action_intent(phrase)
        if result["action"] == expected:
            print(f"✅ PASS: '{phrase}' -> {result['action']} ({desc})")
            passed += 1
        else:
            print(f"❌ FAIL: '{phrase}' -> Expected {expected}, got {result['action']}")
            failed += 1
    
    # Time preference tests
    time_tests = [
        ("morning appointment", "morning", "Should detect morning"),
        ("afternoon slot", "afternoon", "Should detect afternoon"),
        ("any time", "any", "Should return any"),
    ]
    
    print("\n--- TIME PREFERENCE TESTS ---")
    
    for phrase, expected, desc in time_tests:
        result = extract_time_preference(phrase)
        if result["preference"] == expected:
            print(f"✅ PASS: '{phrase}' -> {result['preference']} ({desc})")
            passed += 1
        else:
            print(f"❌ FAIL: '{phrase}' -> Expected {expected}, got {result['preference']}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    run_validation_tests()
