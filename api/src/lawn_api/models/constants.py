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
    "fertilizer",
    "herbicide_pre",
    "herbicide_post",
    "fungicide",
    "insecticide",
    "biostimulant",
    "soil_amendment",
    "seed",
    "other",
)
PRODUCT_UNITS = ("lb", "oz", "fl_oz", "gal")

TREATMENT_APPLICATORS = ("self", "spouse", "lawn_service", "other")

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
