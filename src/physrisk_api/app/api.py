import json
import os
from datetime import datetime, timedelta, timezone

from dependency_injector.wiring import Provide, inject
from flask import Blueprint, abort, current_app, jsonify, request
from flask.helpers import make_response
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, unset_jwt_cookies, verify_jwt_in_request
from jwt import ExpiredSignatureError
from physrisk.container import Container
from physrisk.requests import Requester

api = Blueprint("api", __name__, url_prefix="/api")


@api.post("/token")
def create_token():
    log = current_app.logger

    email = request.json.get("email", None)
    password = request.json.get("password", None)
    log.info(f"EMB - email:{email}")

    # Handle missing OSC_TEST_USER_KEY
    osc_test_user_key = os.environ.get("OSC_TEST_USER_KEY")
    if osc_test_user_key is None:
        msg = "Servver configuration error: OSC_TEST_USER_KEY environment variable is not set."
        status = 500
        log.error(f"EMB - msg:{msg} status:{status}")
        return {"msg": msg}, status

    osc_test_user_key = os.environ["OSC_TEST_USER_KEY"]
    # log.info(f"EMB - osc_test_user_key:{osc_test_user_key}")
    if email != "test" or password != osc_test_user_key:
        msg = "Wrong email or password"
        status = 401
        log.info(f"EMB - msg:{msg} status:{status}")
        return {"msg": msg}, status

    access_token = create_access_token(identity=email, additional_claims={"data_access": "osc"})
    log.info(f"EMB - access_token generated")

    response = {"access_token": access_token}

    return response


@api.post("/get_hazard_data")
@api.post("/get_hazard_data_availability")
@api.post("/get_asset_exposure")
@api.post("/get_asset_impact")
@inject
def hazard_data(requester: Requester = Provide[Container.requester]):
    """Retrieve data from physrisk library based on request URL and JSON data."""

    log = current_app.logger
    request_id = os.path.basename(request.path)
    log.info(f"EMB - request_id:{request_id}")
    request_dict = request.json
    # log.info(f"EMB - request_dict:{json.dumps(request_dict)}")

    log.info(f"Received '{request_id}' request")

    try:
        try:
            verify_jwt_in_request(optional=True)
            # if no JWT, default to 'public' access level
            data_access: str = get_jwt().get("data_access", "osc")
        except ExpiredSignatureError:
            log.info("Signature has expired")
            data_access = "osc"
        except Exception as exc_info:
            log.warning(f"No JWT for '{request_id}' request", exc_info=exc_info)
            # 'public' or 'osc'
            data_access: str = "osc"  # type:ignore
        request_dict["group_ids"] = [data_access]  # type:ignore
        resp_data = requester.get(request_id=request_id, request_dict=request_dict)
        resp_data = json.loads(resp_data)
    except Exception as exc_info:
        log.error(f"Invalid '{request_id}' request", exc_info=exc_info)
        abort(400)


    # log.info(f"EMB - (A) resp_data:{json.dumps(resp_data)}")

    # Response object should hold a list of items, models or measures.
    # If not, none were found matching the request's criteria.
    if not (
        resp_data.get("items")
        or resp_data.get("models")
        or resp_data.get("asset_impacts")
        or resp_data.get("risk_measures")
    ):
        log.error(f"No results returned for '{request_id}' request")
        abort(404)

    # log.info(f"EMB - (B) resp_data:{json.dumps(resp_data)}")

    return resp_data


@api.get("/images/<path:resource>.<format>")
@api.get("/tiles/<path:resource>/<z>/<x>/<y>.<format>")
@inject
def get_image(resource, x=None, y=None, z=None, format="png", requester: Requester = Provide[Container.requester]):
    """Request that physrisk converts an array to image.
    In the tiled form of the request will return the requested tile if an array pyramid exists; otherwise an
    exception is thrown.
    If tiles are not specified then a whole-aray image is created. This is  intended for small arrays,
    say <~ 1500x1500 pixels. Otherwise we use tiled form of request or Mapbox to host tilesets.
    """

    log = current_app.logger
    log.info(f"EMB - resource:{resource} x:{x} y:{y} z:{z} format:{format} requester:{requester}")
    log.info(f"Creating raster image for {resource}.")

    request_id = os.path.basename(request.path)
    min_value_arg = request.args.get("minValue")
    min_value = float(min_value_arg) if min_value_arg is not None else None
    max_value_arg = request.args.get("maxValue")
    max_value = float(max_value_arg) if max_value_arg is not None else None
    colormap = request.args.get("colormap")
    scenario_id = request.args.get("scenarioId")
    year = int(request.args.get("year"))  # type:ignore

    log.info(f"EMB - request_id:{request_id} min_value_arg:{min_value_arg} min_value:{min_value} max_value_arg:{max_value_arg} max_value:{max_value}")
    log.info(f"EMB - colormap:{colormap} scenario_id:{scenario_id} year:{year}")

    try:
        verify_jwt_in_request(optional=True)
        # if no JWT, default to 'osc' access level
        data_access: str = get_jwt().get("data_access", "osc")
    except Exception as exc_info:
        log.info(f"EMB - warning: No JWT for '{request_id}' request")
        log.warning(f"No JWT for '{request_id}' request", exc_info=exc_info)
        # 'public' or 'osc'
        data_access: str = "osc"  # type:ignore

    tilex = None if not x or not y or not z else (int(x), int(y), int(z))
    group_idx = [data_access]
    log.info(f"EMB - tilex:{tilex} group_idx:{group_idx} resource:{resource}")

    response = None
    try:
        image_binary = requester.get_image(
            request_dict={
                "resource": resource,
                "tile": tilex,
                "colormap": colormap,
                "scenario_id": scenario_id,
                "year": year,
                "group_ids": group_idx,
                "max_value": max_value,
                "min_value": min_value,
            }
        )
        response = make_response(image_binary)
        response.headers.set("Content-Type", "image/png")
    except Exception as e:
        log.error("EMB - error getting image", exc_info=e)
        raise e
    return response


@api.get("/reset")
@inject
def reset(container: Container = Provide[Container]):
    # container.requester.reset()
    container.reset_singletons()
    return "Reset successful"


@api.after_request
def refresh_expiring_jwts(response):
    if request.method == "OPTIONS":
        return response
    try:
        verify_jwt_in_request(optional=True)
        jwt = get_jwt()
        if "exp" not in jwt:
            return response
        exp_timestamp = jwt["exp"]
        RuntimeError
        now = datetime.now(timezone.utc)
        target_timestamp = datetime.timestamp(now + timedelta(minutes=30))
        if target_timestamp > exp_timestamp:
            access_token = create_access_token(identity=get_jwt_identity())
            data = response.get_json()
            if type(data) is dict:
                data["access_token"] = access_token
                response.data = json.dumps(data)
        return response
    except ExpiredSignatureError:
        log = current_app.logger
        log.info("Signature has expired")
        return response
    except Exception as exc_info:
        log = current_app.logger
        log.warning("Cannot refresh JWT", exc_info=exc_info)
        # Case where there is not a valid JWT. Just return the original response
        return response


@api.post("/logout")
def logout():
    response = jsonify({"msg": "logout successful"})
    unset_jwt_cookies(response)
    return response


@api.post("/profile")
def profile():
    verify_jwt_in_request()
    identity = get_jwt_identity()
    response_body = {"id": identity}
    return response_body
