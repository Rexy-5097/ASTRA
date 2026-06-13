"""
ASTRA — Label definitions for stellar classification.

Single source of truth for class names, integer labels, and VSX type mappings.
All other modules import from here.
"""

# Canonical class names ordered by integer label (0-4)
CLASS_NAMES: list[str] = [
    "rr_lyrae",          # 0
    "cepheid",           # 1
    "eclipsing_binary",  # 2
    "solar_like",        # 3
    "stable",            # 4
]

NUM_CLASSES: int = len(CLASS_NAMES)

# Convenience mappings
NAME_TO_LABEL: dict[str, int] = {name: idx for idx, name in enumerate(CLASS_NAMES)}
LABEL_TO_NAME: dict[int, str] = {idx: name for idx, name in enumerate(CLASS_NAMES)}

# VSX variability-type substrings used during catalog construction.
# Each key maps to a list of VSX 'Type' field prefixes that belong to
# that ASTRA class.  The catalog builder matches these with startswith().
VSX_TYPE_MAP: dict[str, list[str]] = {
    "rr_lyrae": ["RRAB", "RRC", "RRD", "RR"],
    "cepheid": ["DCEP", "DCEPS", "CEP", "CW", "CWA", "CWB"],
    "eclipsing_binary": ["EA", "EB", "EW", "EP"],
}

# solar_like and stable are NOT in VSX — they use separate catalog strategies.
