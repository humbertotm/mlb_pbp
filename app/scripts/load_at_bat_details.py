import argparse
from datetime import datetime

import statsapi
from app.models import Game, AtBatDetails
from sqlalchemy.orm import Session

from app.schemas import AtBatDetailsSchema


from . import db_engine


def get_at_bats_data_for_game(game_id):
    try:
        # call the "game_playByPlay" api with {"gamePk": game_id}
        game_plays_data = statsapi.get("game_playByPlay", {"gamePk": game_id}) or {}
        # Extract the "allPlays" list from the api response to plays_list
        all_plays = game_plays_data.get("allPlays", [])
        # Compile the at_bats_list by selecting the plays from the plays_list where
        # play["result"]["type"] == "atBat"
        at_bats_list = [play for play in all_plays if play.get("result", {}).get("type") == "atBat"]
        return at_bats_list
    except Exception as e:
        print(f"Failure for game {game_id}, error: {e}")
        return []

def load_at_bat_details(sport_id, start_season, end_season):
    with Session(db_engine) as session:
        for season in range(start_season, end_season):
            season_game_ids = session.query(Game.id).filter(
                Game.season == season,
                Game.sport_id == sport_id
            ).all()
            game_ids = [id for id, in season_game_ids]
            start_time = datetime.now()
            print(f"{len(game_ids)} games for season {season} of the {sport_id} league")

            season_at_bats_to_persist = []
            for game_id in game_ids:
                game_at_bats = get_at_bats_data_for_game(game_id)
                for ab in game_at_bats:

                    ab_data = AtBatDetails(
                        game_id=game_id,
                        sport_id=sport_id,
                        season=season,
                        details=ab
                    )

                    try:
                        AtBatDetailsSchema.from_orm(ab_data)
                        season_at_bats_to_persist.append(ab_data)
                    except Exception as e:
                        print(f"Failed validation for an AB for game {game_id}, season: {season} league {sport_id}, error: {e}")

            print(f"Writing {len(season_at_bats_to_persist)} at bats for season {season}")
            session.bulk_save_objects(season_at_bats_to_persist)
            print(f"Processed {len(season_at_bats_to_persist)} games in {start_time - datetime.now()} seconds")

        session.commit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load At Bat details data")
    parser.add_argument("--sport-id", type=int, required=True, help="ID of the league")
    parser.add_argument("--start-season", type=int, required=True, help="Start season")
    parser.add_argument("--end-season", type=int, required=True, help="End season")
    args = parser.parse_args()

    load_at_bat_details(args.sport_id, args.start_season, args.end_season)