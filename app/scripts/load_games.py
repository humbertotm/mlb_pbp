import argparse
from datetime import date, datetime
from functools import lru_cache

import statsapi
from app.models import Game, Team
from app.schemas import GameSchema
from app.scripts import constants, utils
from sqlalchemy.orm import Session

from app.scripts.load_teams import get_teams_data

from . import db_engine

@lru_cache()
def get_team_ids(sport_id):
    print(f"Retrieving team IDs for sport {sport_id}")
    with Session(db_engine) as session:
        teams = session.query(Team).filter(Team.sport_id == sport_id).order_by(Team.mlb_id).all()
        return [team.mlb_id for team in teams]

def get_games_data_for_season(sport_id, season):
    # Define start_date based on season
    start_date = date(season, 1, 1)
    start_date_str = start_date.strftime("%m/%d/%Y")
    # Define end_date based on season
    end_date = date(season, 12, 31)
    end_date_str = end_date.strftime("%m/%d/%Y")
    # Call the schedule function with sportId=mlb_id, start_date and end_date
    season_games = statsapi.schedule(sportId=sport_id, start_date=start_date_str, end_date=end_date_str)
    season_games_map = {}
    teamd_ids = get_team_ids(sport_id)
    for game in season_games:
        game_id = game.get("game_id")

        if game.get("home_id") is None or game.get("away_id") is None:
            continue

        if game.get("home_id") not in teamd_ids or game.get("away_id") not in teamd_ids:
            continue

        season_games_map[game_id] = game

    # Return the response as it already is a list of game objects and there's no expected collision
    return season_games_map

def load_games(sport_id, start_season, end_season):
    # With an open sqlalchemy Session:
    with Session(db_engine) as session:
        # Iterate over the desired range of seasons
        for season in range(start_season, end_season):
            # Get games_list for season (call get_games_data_for_season(season))
            games_to_persist = []
            season_games_data = get_games_data_for_season(sport_id, season)
            print(f"Retrieved {len(season_games_data)} games for season {season}")
            # For every game in the games_list:
            for game in season_games_data.values():
                # Ignore All-Stars and unofficial games
                if game.get("game_type") in ["A", "E"]:
                    continue

                # Instantiate a Game object and append it to the games_to_persist list
                game_instance = Game(
                    mlb_id=game.get("game_id"),
                    sport_id=sport_id,
                    game_date=datetime.strptime(
                        game["game_date"], "%Y-%m-%d"
                    ).date() if game.get("game_date") else None,
                    game_type=game.get("game_type"),
                    season=season,
                    details=game,
                    home_team_mlb_id=game.get("home_id"),
                    away_team_mlb_id=game.get("away_id"),
                )

                try:
                    GameSchema.from_orm(game_instance)
                    games_to_persist.append(game_instance)
                except Exception as e:
                    print(f"Failed validation for game with mlb_id {game.get('game_id')}, error: {e}")


            # Bulk create the game objects for the current season.
            print(f"Storing {len(games_to_persist)} games for season {season}")
            session.bulk_save_objects(games_to_persist)
        
        # When iteration is done, commit the session once
        session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load games data")
    parser.add_argument("--sport-id", type=int, required=True, help="ID of the league")
    parser.add_argument("--start-season", type=int, required=True, help="Start season")
    parser.add_argument("--end-season", type=int, required=True, help="End season")
    args = parser.parse_args()

    load_games(args.sport_id, args.start_season, args.end_season)
