"""Tunable thresholds for pipeline_analysis reports — kept out of logic.py and
the templates so recalibrating a band doesn't mean hunting through Jinja."""

# Risk grading for an agent's own prompt size (Context Budget's Total KB —
# skills + artifacts + tool output + own <write> output). Calibrated for
# frontier ~1M-token context windows, where a single agent's own prompt is
# meant to stay a small slice of the overall budget: below RISK_OK_MAX_KB is
# unremarkable, above RISK_HIGH_MIN_KB is a real context-bloat signal, the
# band between is worth a look but not urgent.
RISK_OK_MAX_KB = 150.0
RISK_HIGH_MIN_KB = 300.0
