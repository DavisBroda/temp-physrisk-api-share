import argparse
import json
import logging
import sys
from typing import List, Dict
import httpx
import httputilities
import asyncio

import state


from physrisk_temp import Asset, Assets
from physrisk_temp import HazardDataRequestItem, AssetExposureRequest, AssetImpactRequest


# Set up logging
LOGGING_FORMAT = \
    "%(asctime)s - %(module)s:%(funcName)s %(levelname)s - %(message)s"
logging.basicConfig(level=logging.WARNING, format=LOGGING_FORMAT)
logger = logging.getLogger(__name__)


STATE_PARSER="parser"


def cmd_token(args):
    output = None

    if not args.host or not args.port:
        usage("Missing parameter host or port")
        sys.exit(0)
    host = args.host
    port = args.port

    if not args.email or not args.password:
        usage("Missing parameter email or password")
        sys.exit(0)
    email = args.email
    password = args.password

    token = _acquire_token(host, port, email, password)

    output = {
        "access_token": token
    }
    return output


def cmd_hazards(args):
    output = None

    if not args.host or not args.port:
        usage("Missing parameter host or port")
        sys.exit(0)
    host = args.host
    port = args.port

    response = None
    if args.data:
        # Create sample HazardDataRequestItem instances
        items: List[HazardDataRequestItem] = [
            HazardDataRequestItem(
                longitudes=[9.401096694467753],  # Longitude of location
                latitudes=[53.6863523860041],  # Latitude of location
                request_item_id="item1",  # Unique request item ID
                hazard_type="RiverineInundation",  # Type of hazard (e.g., Flood, RiverineInundation)
                indicator_id="flood_depth",  # Indicator (e.g., flood depth)
                scenario="historical",  # Climate change scenario (e.g., ssp585)
                year=1985  # Year for the scenario
            )
        ]

        # Convert the list of HazardDataRequestItem to dictionaries using model_dump()
        items_serialized = [item.model_dump() for item in items]

        # Interpolation and provider_max_requests parameters
        interpolation = "floor"
        provider_max_requests: Dict[str, int] = {"provider_id": 10}

        response = _acquire_hazard_data(
            host, port, items_serialized,
            interpolation=interpolation, provider_max_requests=provider_max_requests)

    elif args.availability:
        response = _acquire_hazard_data_availability(host, port)

    else:
        usage("Missing parameter data or availability parameter")
        sys.exit(0)

    output = response
    return output


def cmd_assets(args):
    output = None

    if not args.host or not args.port:
        usage("Missing parameter host or port")
        sys.exit(0)
    host = args.host
    port = args.port

    provider_max_requests: Dict[str, int] = {"provider_id": 10}
    scenario = "historical"
    year = 1985

    base_latitude = 53.6864
    base_longitude = 9.4011
    lat_variance = 0.01  # e.g., ±0.01 degrees for latitude
    lon_variance = 0.01  # e.g., ±0.01 degrees for longitude
    seed = 100

    response = None
    if args.exposure:

        num_assets = 10000
        assets = _generate_assets(
            base_latitude, base_longitude,
            lat_variance, lon_variance,
            seed=seed, num_assets=num_assets)

        response = _acquire_asset_exposure(
            host=host,
            port=port,
            assets=assets,
            scenario=scenario,
            year=year,
            provider_max_requests=provider_max_requests
        )

    elif args.impact:

        num_assets = 1
        assets = _generate_assets(
            base_latitude, base_longitude,
            lat_variance, lon_variance,
            seed=seed, num_assets=num_assets)

        response = _acquire_asset_impact(
            host=host,
            port=port,
            assets=assets,
            scenario=scenario,
            year=year,
            provider_max_requests=provider_max_requests
        )

    else:
        usage("Missing parameter data or availability parameter")
        sys.exit(0)

    output = response
    return output


def cmd_tiles(args):
    if not args.host or not args.port:
        usage("Missing parameter host or port")
        sys.exit(0)
    host = args.host
    port = args.port

    latitude = 53.6864
    longitude = 9.4011
    zoom = 8
    x, y = _convert_latlon(latitude, longitude, zoom)
    logger.info(f"Converting latitude:{latitude} longitude:{longitude} zoom:{zoom} x:{x} y:{y}")

    # Example parameters for the tile request
    resource = "inundation/river_tudelft/v2/flood_depth_unprot_{scenario}_{year}"
    formatx = "png"
    scenario = "historical"
    year = 1985
    min_value = 0.0
    max_value = 5.0

    tile_data = _acquire_tile(
        host=host,
        port=port,
        resource=resource,
        z=zoom,
        x=x,
        y=y,
        format=formatx,
        scenario=scenario,
        year=year,
        min_value=min_value,
        max_value=max_value
    )

    if tile_data:
        # Save the tile as an image file
        with open(f"tile_{zoom}_{x}_{y}.{formatx}", "wb") as f:
            f.write(tile_data)
        print(f"Tile saved successfully: tile_{zoom}_{x}_{y}.{format}")
    else:
        print("Failed to acquire tile.")
    output = {
        "tile_len": len(tile_data)
    }
    return output


def cmd_images(args):
    if not args.host or not args.port:
        usage("Missing parameter host or port")
        sys.exit(0)
    host = args.host
    port = args.port

    # Example parameters for the image request
    resource = "hazard_map"
    formatx = "png"
    scenario = "ssp585"
    year = 2030
    colormap = "coolwarm"
    min_value = 0.0
    max_value = 100.0

    # Call the function
    response = _acquire_image(
        host=host,
        port=port,
        resource=resource,
        format=formatx,
        scenario=scenario,
        year=year,
        colormap=colormap,
        min_value=min_value,
        max_value=max_value
    )
    return response


#####
# INTERNAL
#####


def _generate_assets(
        base_latitude: float, base_longitude: float,
        lat_variance: float, lon_variance: float,
        num_assets: int=1, seed: int=42):

    logger.info(f"Generating {num_assets} assets")

    import random
    random.seed(seed)

    assets = []

    # Define a variance range (in degrees)
    for _ in range(num_assets):
        # Add random variances to latitude and longitude
        latitude = base_latitude + random.uniform(-lat_variance, lat_variance)
        longitude = base_longitude + random.uniform(-lon_variance, lon_variance)
        # logger.info(f"Using asset latitude:{latitude} longitude:{longitude}")

        # Create the asset with the random location
        asset = Asset(
            asset_class="PowerGeneratingAsset",
            latitude=latitude,
            longitude=longitude,
            location="Europe",
            capacity=500,
            attributes={"number_of_storeys": "2"}
        )

        assets.append(asset)
    return assets


def _convert_latlon(latitude: float, longitude: float, zoom: int):
    import math
    x = int((longitude + 180.0) / 360.0 * (2 ** zoom))
    lat_rad = math.radians(latitude)
    y = int((1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * (2 ** zoom))
    return x, y


def _acquire_tile(
        host: str, port: str,
        resource: str, z: int, x: int, y: int, format: str = "png",
        scenario: str = "rcp8p5", year: int = 2050,
        min_value: float = None, max_value: float = None):


    email = "test"
    password = "test"
    token = _acquire_token(host, port, email, password)

    # Construct the URL for the GET request
    service = f"/api/tiles/{resource}/{z}/{x}/{y}.{format}"
    method = "GET"

    # Prepare query parameters
    params = {
        "scenarioId": scenario,
        "year": year,
    }

    # if colormap:
    #     params["colormap"] = colormap
    if min_value is not None:
        params["minValue"] = min_value
    if max_value is not None:
        params["maxValue"] = max_value
    logger.info(f"Image request for resource '{resource}' with params: {params}")

    # Headers
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'  # If authentication is needed
    }

    timeout = httpx.Timeout(120.0, connect=120.0, read=120.0)
    response = asyncio.run(httputilities.httprequest(
        host, port, service, method,
        params=params, headers=headers, timeout=timeout))
    logger.info(f"Executed service: {service}, response (len): {len(response)}")

    output = response
    return output


def _acquire_image(
        host: str, port: str,
        resource: str, format: str, scenario: str = "rcp8p5", year: int = 2050,
        colormap: str = None, min_value: float = None, max_value: float = None,
        provider_max_requests: Dict[str, int] = {"provider_id": 10}):

    email = "test"
    password = "test"
    token = _acquire_token(host, port, email, password)

    # Construct the URL for the GET request
    service = f"/api/images/{resource}.{format}"
    method = "GET"

    # Prepare query parameters
    params = {
        "scenarioId": scenario,
        "year": year,
    }

    if colormap:
        params["colormap"] = colormap
    if min_value is not None:
        params["minValue"] = min_value
    if max_value is not None:
        params["maxValue"] = max_value
    logger.info(f"Image request for resource '{resource}' with params: {params}")

    # Headers
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'  # If authentication is needed
    }

    timeout = httpx.Timeout(120.0, connect=120.0, read=120.0)
    response = asyncio.run(httputilities.httprequest(
        host, port, service, method,
        params=params, headers=headers, timeout=timeout))
    logger.info(f"Executed service: {service}, response: {response}")

    output = response
    return output


def _acquire_asset_impact(
        host: str, port: str,
        assets: List[Asset], scenario: str = "rcp8p5", year: int = 2050,
        provider_max_requests: Dict[str, int] = {"provider_id": 10}):

    email = "test"
    password = "test"
    token = _acquire_token(host, port, email, password)

    service = "/api/get_asset_impact"
    method = "POST"

    # Create AssetImpactRequest
    request_obj = AssetImpactRequest(
        assets=Assets(items=assets),
        scenario=scenario,
        year=year,
        provider_max_requests=provider_max_requests or {}
    )

    # logger.info(f"AssetImpactRequest: {request_obj.model_dump()}")

    # Headers
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'  # If authentication is needed
    }

    timeout = httpx.Timeout(120.0, connect=120.0, read=120.0)
    response = asyncio.run(httputilities.httprequest(
        host, port, service, method,
        obj=request_obj.model_dump(),  # Convert to dict
        headers=headers, timeout=timeout))
    logger.info(f"Executed service: {service}, response (len): {len(response)}")

    output = response
    output = None
    return output


def _acquire_asset_exposure(
        host: str, port: str,
        assets: List[Asset], scenario: str = "rcp8p5", year: int = 2050,
        provider_max_requests: Dict[str, int] = {"provider_id": 10}):

    email = "test"
    password = "test"
    token = _acquire_token(host, port, email, password)

    service = "/api/get_asset_exposure"
    method = "POST"

    # Create AssetExposureRequest
    request_obj = AssetExposureRequest(
        assets=Assets(items=assets),
        scenario=scenario,
        year=year,
        provider_max_requests=provider_max_requests or {}
    )

    logger.info(f"AssetExposureRequest: {request_obj.model_dump()}")

    # Headers
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'  # If authentication is needed
    }

    timeout = httpx.Timeout(120.0, connect=120.0, read=120.0)
    response = asyncio.run(httputilities.httprequest(
        host, port, service, method,
        obj=request_obj.model_dump(),  # Convert to dict
        headers=headers, timeout=timeout))
    logger.info(f"Executed service: {service}, response (len): {len(response)}")

    output = response
    return output


def _acquire_hazard_data_availability(host: str, port: str):

    email = "test"
    password = "test"
    token = _acquire_token(host, port, email, password)

    service = "/api/get_hazard_data_availability"
    method = "POST"

    request_obj = {
        "items": []
    }
    logger.info(f"request_obj:{request_obj}")

    # Headers
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'  # If authentication is needed
    }

    timeout = httpx.Timeout(120.0, connect=120.0, read=120.0)
    response = asyncio.run(httputilities.httprequest(
        host, port, service, method,
        obj=request_obj, headers=headers, timeout=timeout))
    logger.info(f"Executed service:{service}, response:{response}")

    output = {
        "models": response["models"]
    }
    return output


def _acquire_hazard_data(
        host: str, port: str,
        items: List, interpolation: str="floor",
        provider_max_requests: Dict[str, int] = {"provider_id": 10}):

    email = "test"
    password = "test"
    token = _acquire_token(host, port, email, password)

    service = "/api/get_hazard_data"
    method = "POST"

    request_obj = {
        "items": items,
        "interpolation": interpolation,
        "provider_max_requests": provider_max_requests
    }
    logger.info(f"request_obj:{request_obj}")

    # Headers
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'  # If authentication is needed
    }

    timeout = httpx.Timeout(120.0, connect=120.0, read=120.0)
    response = asyncio.run(httputilities.httprequest(
        host, port, service, method,
        obj=request_obj, headers=headers, timeout=timeout))
    logger.info(f"Executed service:{service}, response:{response}")
    return response


def _acquire_token(host: str, port: int, email: str, password: str):
    service = "/api/token"
    method = "POST"

    request_obj = {
        "email": email,
        "password": password,
    }
    logger.info(f"request_obj:{request_obj}")

    timeout = httpx.Timeout(120.0, connect=120.0, read=120.0)
    response = asyncio.run(httputilities.httprequest(
        host, port, service, method,
        obj=request_obj, timeout=timeout))
    logger.info(f"Executed service:{service}, response:{response}")
    return response["access_token"]


#####
# CLI
#####


def usage(msg: str):
    msg = f"Error: {msg}\n"
    print(msg)
    parser = state.gstate(STATE_PARSER)
    parser.print_help()


def execute(xargs=None):
    """
    Main function that sets up the argparse CLI interface.
    """

    # Initialize argparse and set general CLI description
    parser = argparse.ArgumentParser(description="Sample Hazards CLI")
    state.gstate(STATE_PARSER, parser)

    # Parser for top-level commands
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument("--host", required=True, help="Registry host")
    parser.add_argument("--port", required=True, help="Registry port")

    # Create subparsers to handle multiple commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    token_parser = subparsers.add_parser("token", help="Acquire a token")
    token_parser.add_argument("--email", required=True, help="Email")
    token_parser.add_argument("--password", required=True, help="Password for provided email")

    hazards_parser = subparsers.add_parser("hazards", help="Hazards inquiry")
    hazards_group = hazards_parser.add_mutually_exclusive_group(required=True)
    hazards_group.add_argument("--data", action="store_true", help="Get data")
    hazards_group.add_argument("--availability", action="store_true", help="Get data availability")

    assets_parser = subparsers.add_parser("assets", help="Assets inquiry")
    assets_group = assets_parser.add_mutually_exclusive_group(required=True)
    assets_group.add_argument("--exposure", action="store_true", help="Get asset exposure")
    assets_group.add_argument("--impact", action="store_true", help="Get asset impact")

    tiles_parser = subparsers.add_parser("tiles", help="Tiles inquiry")
    tiles_parser.add_argument("--parameter", required=True, help="Using parameter")

    # Could not get to work - remove for now
    # images_parser = subparsers.add_parser("images", help="Images inquiry")
    # images_parser.add_argument("--parameter", required=True, help="Using parameter")

    # Execute corresponding function based on provided command
    args: argparse.Namespace = parser.parse_args(xargs if xargs is not None else sys.argv[1:])
    logger.info(f"Using args:{args}")

    output = None
    if args.command == "token":
        output = cmd_token(args)
    elif args.command == "hazards":
        output = cmd_hazards(args)
    elif args.command == "assets":
        output = cmd_assets(args)
    elif args.command == "tiles":
        output = cmd_tiles(args)
    # elif args.command == "images":
    #     output = cmd_images(args)
    else:
        usage(f"Invalid command:{args.command}")
        sys.exit(0)
    output = json.dumps(output)
    return output


def main(args=None):
    # experiment()
    # a = 1/0
    output = execute(args)
    print(output)
    return output


if __name__ == "__main__":
    main(sys.argv[1:])


