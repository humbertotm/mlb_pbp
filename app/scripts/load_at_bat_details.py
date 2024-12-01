import argparse
import concurrent.futures
from datetime import datetime
from typing import List, Dict

import statsapi
from app.models import Game, AtBatDetails
from app.scripts.constants import LEAGUE_MAP
from sqlalchemy.orm import Session

from app.schemas import AtBatDetailsSchema


from . import db_engine


def get_at_bats_data_for_game(game_id: int) -> List[Dict]:
    try:
        # call the "game_playByPlay" api with {"gamePk": game_id}
        game_plays_data = statsapi.get("game_playByPlay", {"gamePk": game_id}) or {}
        # Extract the "allPlays" list from the api response to plays_list
        all_plays = game_plays_data.get("allPlays", [])
        # Compile the at_bats_list by selecting the plays from the plays_list where
        # play["result"]["type"] == "atBat"
        at_bats_list = [
            play for play in all_plays if play.get("result", {}).get("type") == "atBat"
        ]
        return at_bats_list
    except Exception as e:
        print(f"Failure for game {game_id}, error: {e}")
        return []


def fetch_game_at_bats(game_id: int) -> List[Dict]:
    return get_at_bats_data_for_game(game_id)


def load_at_bat_details(sport_id: int, start_season: int, end_season: int) -> None:
    with Session(db_engine) as session:
        for season in range(start_season, end_season):
            # Get game IDs for season
            season_game_mlb_ids = (
                session.query(Game.mlb_id)
                .filter(Game.season == season, Game.sport_id == sport_id)
                .all()
            )
            game_mlb_ids = [id for (id,) in season_game_mlb_ids]
            start_time = datetime.now()
            print(
                f"{len(game_mlb_ids)} games for season {season} of the {LEAGUE_MAP[sport_id]["name"]} league"
            )

            # Concurrent fetch of at_bats data
            season_at_bats = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                future_to_game = {
                    executor.submit(fetch_game_at_bats, game_mlb_id): game_mlb_id
                    for game_mlb_id in game_mlb_ids
                }

                for future in concurrent.futures.as_completed(future_to_game):
                    game_mlb_id = future_to_game[future]
                    try:
                        game_at_bats = future.result()
                        for ab in game_at_bats:
                            ab_data = AtBatDetails(
                                game_mlb_id=game_mlb_id,
                                sport_id=sport_id,
                                season=season,
                                details=ab,
                            )
                            try:
                                AtBatDetailsSchema.from_orm(ab_data)
                                season_at_bats.append(ab_data)
                            except Exception as e:
                                print(
                                    f"Failed validation for AB in game {game_mlb_id}, error: {e}"
                                )
                    except Exception as e:
                        print(f"Failed fetching game {game_mlb_id}, error: {e}")

            print(f"Writing {len(season_at_bats)} at bats for season {season}")
            session.bulk_save_objects(season_at_bats)
            print(
                f"Processed season {season} in {(datetime.now() - start_time) / 60} minutes"
            )

        session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load At Bat details data")
    parser.add_argument("--sport-id", type=int, required=True, help="ID of the league")
    parser.add_argument("--start-season", type=int, required=True, help="Start season")
    parser.add_argument("--end-season", type=int, required=True, help="End season")
    args = parser.parse_args()

    load_at_bat_details(args.sport_id, args.start_season, args.end_season)
