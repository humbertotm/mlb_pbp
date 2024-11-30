from datetime import date, datetime

import statsapi
from app.models import AtBat
from app.scripts import constants, utils
from sqlalchemy.orm import Session


def get_pitches_for_at_bat(at_bat_obj):
    # Extract the "playEvents" list from the at_bat_obj to pitches
    pitches_list = at_bat_obj.get("playEvents", [])
    return pitches_list

def get_runner_movements_for_at_bat(at_bat_obj):
    # Extract the runner_movements_list from at_bat_obj["runners"]
    runners_data = at_bat_obj.get["runners", []]
    # Return [{"start", "end", "play/pitch index"}]
    runner_movements_list = [
        {
            "start": movement.get("start"),
            "end": movement.get("end"),

        } for movement in runners_data
    ]

    return runner_movements_list

def load_at_bats_and_pitches():
    # With an open sqlalchemy Session:
    # Iterate the desired season range:
    # Get the games_list by calling load_games.get_games_data_for_season
    # Compile the list of game_ids
    # Declare the at_bats_to_persist list
    # Declare the pitches_to_persis_list
    # For game_id in the game_ids:
    # at_bats = get_at_bats_data_for_game(game_id)
    # Iterate over every at_bat in the at_bats list:
    # Instantiate the AtBat object and append it to the at_bats_to_persist list.
    # pitches = get_pitches_for_at_bat(at_bat)
    # runner_movements = get_runner_movements_for_at_bat(at_bat_obj)
    # Iterate over the pitches list:
    # Check if there are any runner movements associated to the previous pitch
    # (I think they can be matched by the play index, confirm)
    # Adjust runners position
    # Instantiate Pitch object and append it to the pitches_to_persis_list
    #
    # When done iterating, bulk create AtBat and Pitch objects.
    # Commit the session.

    return
