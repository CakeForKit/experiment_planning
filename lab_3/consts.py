
FACTOR_RANGES = {
    "λ1": (0.3, 0.4),
    "λ2": (0.2, 0.4),
    "μ": (2, 2.6),
    "r": (2.4, 4)
}
FACTOR_NAMES = list(FACTOR_RANGES.keys())
NUM_FACTORS = len(FACTOR_NAMES)
RESULT_COLUMNS = [
    "№", "λ1", "λ2", "μ", "r", 
    "y1", "y1_lin", "y1_nlin", "Δy1_lin", "Δy1_nlin",
    "y2", "y2_lin", "y2_nlin", "Δy2_lin", "Δy2_nlin"
]
MAX_REQUESTS = 1000
