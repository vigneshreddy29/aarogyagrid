"""
AarogyaGrid — project configuration.

PROVENANCE NOTE (also documented in data/README.md):
  - District names, and the PHC/CHC structure, are real (Telangana).
  - Catchment sizes follow Indian PHC norms: 1 PHC per ~30,000 rural
    population; 1 CHC per ~120,000.
  - Disease seasonality multipliers are modelled from published IDSP
    seasonal patterns for Indian districts.
  - SKUs are drawn from the National List of Essential Medicines (NLEM).
"""

# ---------------------------------------------------------------- districts
# Real districts in Telangana. Each has a "character" so that the
# redistribution demo has genuine surplus and genuine shortage.

DISTRICTS = [
    {"name": "Nalgonda",            "phc": 12, "chc": 3, "profile": "volatile"},
    {"name": "Yadadri Bhuvanagiri", "phc": 8,  "chc": 2, "profile": "understocked"},
    {"name": "Suryapet",            "phc": 10, "chc": 2, "profile": "wellrun"},
]

STATE = "Telangana"

# ---------------------------------------------------------------- SKUs
# NLEM essential medicines. Each links to a disease signal so that
# consumption is DERIVED from epidemiology, never invented.

SKUS = [
    # code,   name,                        unit,     disease link,   units/course, shelf life (days)
    ("ORS001", "ORS Sachet (WHO formula)", "sachet", "diarrhoeal",   6,   730),
    ("ZNC001", "Zinc Sulphate 20mg",       "tablet", "diarrhoeal",  14,   730),
    ("PAR001", "Paracetamol 500mg",        "tablet", "fever",       10,   1095),
    ("ACT001", "Artemether-Lumefantrine",  "tablet", "malaria",     24,   730),
    ("CIP001", "Ciprofloxacin 500mg",      "tablet", "cholera",     10,   1095),
    ("IFA001", "Iron Folic Acid",          "tablet", "chronic",     30,   1095),
    ("AMX001", "Amoxicillin 500mg",        "capsule","fever",       15,   730),
    ("MET001", "Metformin 500mg",          "tablet", "chronic",     60,   1095),
]

# ---------------------------------------------------------------- seasonality
# Monthly multipliers (Jan..Dec) modelled on published IDSP seasonal
# patterns for south Indian districts. Monsoon = Jun-Sep.

SEASONALITY = {
    "diarrhoeal": [0.6, 0.6, 0.7, 0.9, 1.2, 1.9, 2.4, 2.2, 1.7, 1.1, 0.8, 0.6],
    "malaria":    [0.5, 0.5, 0.6, 0.8, 1.1, 1.6, 2.1, 2.3, 1.9, 1.3, 0.8, 0.6],
    "cholera":    [0.4, 0.4, 0.6, 0.9, 1.3, 2.0, 2.5, 2.1, 1.5, 0.9, 0.6, 0.4],
    "fever":      [0.9, 0.8, 0.8, 0.9, 1.0, 1.3, 1.6, 1.7, 1.5, 1.2, 1.0, 0.9],
    "chronic":    [1.0] * 12,   # chronic demand is flat by design
}

# baseline weekly cases per 100,000 population, pre-seasonality
BASE_INCIDENCE = {
    "diarrhoeal": 42.0,
    "malaria":     6.0,
    "cholera":     2.5,
    "fever":     110.0,
    "chronic":    85.0,
}

# district character -> how well supplied it is
PROFILE_SUPPLY = {
    "volatile":     {"order_factor": 1.00, "delay_prob": 0.22},
    "understocked": {"order_factor": 0.78, "delay_prob": 0.30},
    "wellrun":      {"order_factor": 1.18, "delay_prob": 0.08},
}

# ---------------------------------------------------------------- supply chain
LEAD_TIME_MIN_DAYS = 7
LEAD_TIME_MAX_DAYS = 21
INDENT_CYCLE_DAYS  = 30
SERVICE_LEVEL_Z    = 1.65        # 95% service level
HISTORY_DAYS       = 540         # ~18 months
RANDOM_SEED        = 42          # reproducible demo
MAX_TRANSFER_KM    = 75