import statsapi

from . import constants


def get_mlb_id() -> int:
    sports_api_response = statsapi.get("sports", {}) or {}
    sports_list = sports_api_response.get("sports", [])
    mlb_sport = next(
        (sport for sport in sports_list if sport.get("code") == constants.MLB_CODE),
        None,
    )

    return mlb_sport.get("id")
