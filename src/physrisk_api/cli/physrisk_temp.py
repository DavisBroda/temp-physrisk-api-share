from typing import Dict, Iterable, List, Optional, Sequence
from pydantic import BaseModel, ConfigDict, Field

#####
# HAZARDS
#####


class HazardDataRequestItem(BaseModel):
    longitudes: List[float]
    latitudes: List[float]
    request_item_id: str
    hazard_type: Optional[str] = None  # e.g. RiverineInundation
    event_type: Optional[str] = (
        None  # e.g. RiverineInundation; deprecated: use hazard_type
    )
    indicator_id: str
    indicator_model_gcm: Optional[str] = ""
    path: Optional[str] = None
    scenario: str  # e.g. rcp8p5
    year: int


#####
# ASSETS
#####


class Asset(BaseModel):
    """Defines an asset.

    An asset is identified first by its asset_class and then by its type within the class.
    An asset's value may be impacted through damage or through disruption
    disruption being reduction of an asset's ability to generate cashflows
    (or equivalent value, e.g. by reducing expenses or increasing sales).
    """

    model_config = ConfigDict(extra="allow")

    asset_class: str = Field(
        description="name of asset class; corresponds to physrisk class names, e.g. PowerGeneratingAsset"
    )
    latitude: float = Field(description="Latitude in degrees")
    longitude: float = Field(description="Longitude in degrees")
    type: Optional[str] = Field(
        None, description="Type of the asset <level_1>/<level_2>/<level_3>"
    )
    location: Optional[str] = Field(
        None,
        description="Location (e.g. Africa, Asia, Europe, Global, Oceania, North America, South America)",
    )
    capacity: Optional[float] = Field(None, description="Power generation capacity")
    attributes: Optional[Dict[str, str]] = Field(
        None,
        description="Bespoke attributes (e.g. number of storeys, structure type, occupancy type)",
    )


class Assets(BaseModel):
    """Defines a collection of assets."""
    items: List[Asset]


class CalcSettings(BaseModel):
    hazard_interp: str = Field(
        "floor",
        description="Method used for interpolation of hazards: 'floor' or 'bilinear'.",
    )


class AssetExposureRequest(BaseModel):
    """Impact calculation request."""

    assets: Assets
    calc_settings: CalcSettings = Field(
        default_factory=CalcSettings,  # type:ignore
        description="Interpolation method.",
    )
    scenario: str = Field("rcp8p5", description="Name of scenario ('rcp8p5')")
    year: int = Field(
        2050,
        description="Projection year (2030, 2050, 2080). Any year before 2030, e.g. 1980, is treated as historical.",
    )
    provider_max_requests: Dict[str, int] = Field(
        {},
        description="The maximum permitted number of \
        requests to external providers. This setting is intended in particular for paid-for data. The key \
        is the provider ID and the value is the maximum permitted requests.",
    )


class AssetImpactRequest(BaseModel):
    """Impact calculation request."""

    assets: Assets
    calc_settings: CalcSettings = Field(
        default_factory=CalcSettings,  # type:ignore
        description="Interpolation method.",
    )
    include_asset_level: bool = Field(
        True, description="If true, include asset-level impacts."
    )
    include_measures: bool = Field(
        False, description="If true, include calculation of risk measures."
    )
    include_calc_details: bool = Field(
        True, description="If true, include impact calculation details."
    )
    use_case_id: str = Field(
        "",
        description="Identifier for 'use case' used in the risk measures calculation.",
    )
    provider_max_requests: Dict[str, int] = Field(
        {},
        description="The maximum permitted number of requests \
        to external providers. This setting is intended in particular for paid-for data. The key is the provider \
        ID and the value is the maximum permitted requests.",
    )
    scenarios: Optional[Sequence[str]] = Field(
        [], description="Name of scenarios ('rcp8p5')"
    )
    years: Optional[Sequence[int]] = Field(
        [],
        description="""Projection year (2030, 2050, 2080). Any year before 2030,
        e.g. 1980, is treated as historical.""",
    )
    # to be deprecated
    scenario: str = Field("rcp8p5", description="Name of scenario ('rcp8p5')")
    year: int = Field(
        [2050],
        description="""Projection years (e.g. 2030, 2050, 2080). Any year before 2030,
        e.g. 1980, is treated as historical.""",
    )
