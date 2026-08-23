"""
Real mandal locations for facility placement.

Indian PHCs are sited at mandal headquarters — one PHC per mandal is the
standard rural configuration under IPHS. Facilities are therefore named
after and placed at real mandals in the three prototype districts, rather
than scattered randomly.

Several of these are confirmed PHC locations in the National Health Mission's
published Hospital Development Society list for Nalgonda district (Addagudur,
Chilkur, Chityala, Gurrampode, Mothkur, Yadagirigutta).

PRECISION NOTE: coordinates are mandal headquarter positions accurate to
roughly 1-2 km, not surveyed facility entrances. The Health Facility Registry
(facility.abdm.gov.in) publishes exact positions behind authentication; a
deployment would ingest those directly through the same schema.
"""

# district -> [(mandal name, latitude, longitude), ...]
MANDALS = {
    "Nalgonda": [
        ("Nalgonda",       17.054, 79.267),
        ("Chityala",       17.100, 79.100),
        ("Narketpally",    17.183, 79.150),
        ("Nakrekal",       17.150, 79.033),
        ("Kattangur",      17.183, 79.083),
        ("Kanagal",        17.000, 79.283),
        ("Kethepally",     17.033, 79.150),
        ("Devarakonda",    16.700, 78.917),
        ("Gurrampode",     16.900, 79.033),
        ("Munugode",       17.083, 78.933),
        ("Chandur",        17.017, 78.900),
        ("Miryalaguda",    16.872, 79.566),
        ("Damaracherla",   16.783, 79.550),
        ("Tripuraram",     16.717, 79.383),
        ("Nidamanoor",     16.933, 79.450),
    ],
    "Yadadri Bhuvanagiri": [
        ("Bhongir",        17.511, 78.889),
        ("Choutuppal",     17.267, 78.933),
        ("Pochampally",    17.350, 78.817),
        ("Valigonda",      17.383, 79.033),
        ("Yadagirigutta",  17.583, 78.950),
        ("Alair",          17.583, 79.033),
        ("Mothkur",        17.450, 79.183),
        ("Ramannapet",     17.283, 79.083),
        ("Bibinagar",      17.450, 78.833),
        ("Addagudur",      17.400, 79.183),
    ],
    "Suryapet": [
        ("Suryapet",       17.140, 79.623),
        ("Kodad",          16.996, 79.966),
        ("Huzurnagar",     16.900, 79.867),
        ("Neredcherla",    17.050, 79.500),
        ("Thungathurthy",  17.183, 79.417),
        ("Chivvemla",      17.083, 79.717),
        ("Mattampally",    16.850, 79.783),
        ("Munagala",       16.933, 79.983),
        ("Garidepally",    17.183, 79.550),
        ("Chilkur",        17.017, 79.700),
        ("Penpahad",       17.033, 79.783),
        ("Nuthankal",      17.217, 79.667),
    ],
}

# Mandals with a PHC confirmed in NHM's published Hospital Development
# Society list for the district. Cited in the interface as verified.
NHM_CONFIRMED = {
    "Addagudur", "Chilkur", "Chityala", "Gurrampode",
    "Mothkur", "Yadagirigutta",
}