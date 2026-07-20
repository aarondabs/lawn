SOIL_TYPES = (
    "sand",
    "sandy_loam",
    "loam",
    "silty_loam",
    "silty_clay_loam",
    "clay_loam",
    "clay",
)

WATER_SOURCES = ("city", "well", "mixed")

IRRIGATION_HEAD_TYPES = ("rotor", "spray", "mp_rotator", "drip", "hybrid")
IRRIGATION_SUN_EXPOSURES = ("full_sun", "partial_sun", "partial_shade", "full_shade")
IRRIGATION_SLOPES = ("flat", "mild", "moderate", "steep")
IRRIGATION_ZONE_CATEGORIES = (
    "turf",
    "trees_shrubs",
    "ornamental",
    "inactive",
)

EQUIPMENT_TYPES = ("sprayer", "spreader", "aerator", "dethatcher", "mower", "edger", "other")

PRODUCT_TYPES = (
    "fertilizer_synthetic",
    "fertilizer_organic",
    "herbicide_pre",
    "herbicide_post_broadleaf",
    "herbicide_post_grassy",
    "herbicide_non_selective",
    "fungicide",
    "insecticide",
    "biostimulant",
    "soil_amendment",
    "surfactant",
    "wetting_agent",
    "dye_marker",
    "seed",
    "other",
)

RATE_UNITS = (
    "lb_per_1000",
    "oz_per_1000",
    "fl_oz_per_1000",
    "gal_per_1000",
    "fl_oz_per_gal",
    "pct_vv",
    "lb_per_acre",
)

# Rate units that are NOT area-based (used for adjuvants, surfactants, etc.)
# Tank mixes with only these units are invalid.
NON_AREA_RATE_UNITS = ("fl_oz_per_gal", "pct_vv")

TREATMENT_APPLICATORS = ("self", "spouse", "lawn_service", "other")

# Mow detail values. These live in cultural_practice.details (JSONB), so there is
# no DB CHECK constraint backing them -- the pydantic Literal is the enforcement point.
MOW_ORIENTATIONS = (
    "north_south",
    "east_west",
    "diagonal_ne_sw",
    "diagonal_nw_se",
    "other",
)

CULTURAL_PRACTICE_TYPES = (
    "mow",
    "aerate",
    "dethatch",
    "overseed",
    "scalp",
    "leveling",
    "edge",
    "other",
)

IRRIGATION_EVENT_SOURCES = (
    "rachio_scheduled",
    "rachio_manual",
    "rachio_quick_run",
    "manual_logged",
)

REMINDER_TYPES = ("treatment", "cultural", "check", "other")
