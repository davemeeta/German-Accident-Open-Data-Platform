from enum import Enum


class Category(str, Enum):
    """Accident severity. Maps to the backend's integer category (1/2/3)."""
    fatal = "fatal"
    serious = "serious"
    light = "light"


CATEGORY_TO_INT = {Category.fatal: 1, Category.serious: 2, Category.light: 3}


class State(str, Enum):
    """The 16 German state abbreviations the backend actually accepts for its
    `state` query param. Exposing this as an enum (rather than a free string)
    means an invalid guess like "MUC" or "BAU" is rejected by the tool schema
    itself, before any HTTP round trip - not just reported as a runtime error
    after the fact.
    """
    SH = "SH"  # Schleswig-Holstein
    HH = "HH"  # Hamburg
    NI = "NI"  # Niedersachsen
    HB = "HB"  # Bremen
    NW = "NW"  # Nordrhein-Westfalen
    HE = "HE"  # Hessen
    RP = "RP"  # Rheinland-Pfalz
    BW = "BW"  # Baden-Württemberg
    BY = "BY"  # Bayern
    SL = "SL"  # Saarland
    BE = "BE"  # Berlin
    BB = "BB"  # Brandenburg
    MV = "MV"  # Mecklenburg-Vorpommern
    SN = "SN"  # Sachsen
    ST = "ST"  # Sachsen-Anhalt
    TH = "TH"  # Thüringen


class Level(str, Enum):
    state = "state"
    district = "district"
    municipality = "municipality"


class Order(str, Enum):
    desc = "desc"
    asc = "asc"


class VehicleType(str, Enum):
    pedestrian = "pedestrian"
    bicycle = "bicycle"
    car = "car"
    motorcycle = "motorcycle"
    goods = "goods"


def vehicle_types_to_flags(vehicle_types: list[VehicleType] | None) -> dict[str, bool]:
    """Translate the LLM-facing enum list into the backend's independent boolean flags."""
    selected = set(vehicle_types or [])
    return {vt.value: (vt in selected) for vt in VehicleType}
