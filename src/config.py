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

# Monthly multipliers calibrated against 218 IDSP outbreak reports for
# Telangana (2009-2023), from EpiClim (Zenodo 14580510, arXiv 2501.18602).
#
# IDSP records outbreak REPORTS, not routine caseload, so the raw monthly
# counts overstate amplitude — a low-report month means fewer outbreaks were
# declared, not that incidence collapsed. We therefore take the IDSP monthly
# distribution as the SHAPE and compress it around 1.0 by a factor of 0.55,
# which preserves the peak ordering (Jul > Aug > Jun > Sep for diarrhoeal)
# while keeping amplitude within a plausible range for routine demand.
#
# Source: data/raw/Final_data.csv
SEASONALITY = {
    # IDSP diarrhoeal + cholera: 0,6,6,6,7,23,26,25,17,11,5,2
    "diarrhoeal": [0.63, 0.71, 0.71, 0.71, 0.76, 1.46, 1.59, 1.55, 1.20, 0.93, 0.67, 0.54],
    "cholera":    [0.63, 0.71, 0.71, 0.71, 0.76, 1.46, 1.59, 1.55, 1.20, 0.93, 0.67, 0.54],

    # IDSP dengue + chikungunya: 2,2,4,11,5,4,12,14,12,6,4,2
    "fever":      [0.62, 0.62, 0.79, 1.39, 0.87, 0.79, 1.47, 1.63, 1.47, 0.96, 0.79, 0.62],
    "malaria":    [0.62, 0.62, 0.79, 1.39, 0.87, 0.79, 1.47, 1.63, 1.47, 0.96, 0.79, 0.62],

    "chronic":    [1.0] * 12,
}
# ---------------------------------------------------------------- incidence
# Diarrhoeal baseline is calibrated against NFHS-5 (2019-21) measured
# prevalence for Telangana: 5.46% of under-5 children reported diarrhoea in
# the 2 weeks preceding the survey. Converted to weekly cases per 100,000
# total population, assuming under-5s are ~9% of population (Census 2011).
#   0.0546 prevalence / 2 weeks x 0.09 x 100,000 = ~246 weekly under-5 cases
#   x 0.7109 (NFHS: share taken to a health facility) = ~175 presenting
#   Adults roughly double the presenting caseload -> ~350
# Source: data/raw/NFHS_5_Factsheets_Data.xls
BASE_INCIDENCE = {
    "diarrhoeal": 350.0,
    "malaria":      6.0,
    "cholera":      2.5,
    "fever":      110.0,
    "chronic":     85.0,
}

# NFHS-5 Telangana treatment rates — what fraction of presenting cases
# actually receive each medicine. Previously assumed 100%.
NFHS_TREATMENT_RATE = {
    "ORS001": 0.6178,   # received oral rehydration salts
    "ZNC001": 0.3931,   # received zinc
}

NFHS_FACILITY_SEEKING = 0.7109   # share of cases reaching a health provider
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