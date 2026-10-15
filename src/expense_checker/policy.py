"""Policy thresholds. Mirrors docs/policy.md - change both together and bump the version."""
POLICY_VERSION = "1.0"

MEAL_LIMIT_USD = 75.00
LODGING_LIMIT_USD = 250.00
RECEIPT_THRESHOLD_USD = 25.00
APPROVAL_THRESHOLD_USD = 500.00
LATE_SUBMISSION_DAYS = 60
PROHIBITED_CATEGORIES = frozenset({"Alcohol", "Personal"})
