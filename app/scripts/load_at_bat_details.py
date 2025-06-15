import argparse
import concurrent.futures
from datetime import datetime
from typing import List, Dict

import statsapi
from app.models import Game, AtBatDetails
from app.scripts.constants import LEAGUE_MAP
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.schemas import AtBatDetailsSchema


from . import db_engine


def get_games_without_at_bats(sport_id: int, season: int = None) -> List[tuple]:
    """
    Get a list of game MLB IDs that don't have any corresponding AtBatDetails records.
    
    Args:
        sport_id (int): The ID of the sport/league
        season (int, optional): If provided, only check games from this season
    
    Returns:
        List[tuple]: List of tuples containing (game_mlb_id, game_date) for games needing at-bat details
    """
    with Session(db_engine) as session:
        # Build base query for games
        games_query = select(Game.mlb_id, Game.game_date).where(Game.sport_id == sport_id)
        
        # Add season filter if provided
        if season is not None:
            games_query = games_query.where(Game.season == season)
        
        # Add subquery to exclude games that have at-bat details
        games_with_abs = (
            select(AtBatDetails.game_mlb_id)
            .distinct()
            .where(AtBatDetails.sport_id == sport_id)
        )
        if season is not None:
            games_with_abs = games_with_abs.where(AtBatDetails.season == season)
        
        # Get games that don't exist in AtBatDetails
        missing_games = games_query.where(~Game.mlb_id.in_(games_with_abs))
        
        return [(game_id, game_date) for game_id, game_date in session.execute(missing_games)]


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


def load_at_bat_details(sport_id: int, season: int = None) -> None:
    """
    Load at-bat details for all games that don't have them yet.
    
    Args:
        sport_id (int): The ID of the sport/league
        season (int, optional): If provided, only process games from this season
    """
    with Session(db_engine) as session:
        # Get games without at-bat details
        games_to_process = get_games_without_at_bats(sport_id, season)
        start_time = datetime.now()
        print(
            f"Processing {len(games_to_process)} games without at-bat details for the {LEAGUE_MAP[sport_id]['name']} league"
            + (f" in season {season}" if season else "")
        )

        # Concurrent fetch of at_bats data
        at_bats_to_save = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_game = {
                executor.submit(fetch_game_at_bats, game_mlb_id): (game_mlb_id, game_date)
                for game_mlb_id, game_date in games_to_process
            }

            for future in concurrent.futures.as_completed(future_to_game):
                game_mlb_id, game_date = future_to_game[future]
                try:
                    game_at_bats = future.result()
                    season = game_date.year if game_date else None
                    print(f"Processing {len(game_at_bats)} at-bats for game {game_mlb_id} in season {season}")
                    
                    for ab in game_at_bats:
                        ab_data = AtBatDetails(
                            game_mlb_id=game_mlb_id,
                            sport_id=sport_id,
                            season=season,
                            details=ab,
                        )
                        try:
                            AtBatDetailsSchema.from_orm(ab_data)
                            at_bats_to_save.append(ab_data)
                        except Exception as e:
                            print(
                                f"Failed validation for AB in game {game_mlb_id}, error: {e}"
                            )
                except Exception as e:
                    print(f"Failed fetching game {game_mlb_id}, error: {e}")

        print(f"Writing {len(at_bats_to_save)} at bats")
        session.bulk_save_objects(at_bats_to_save)
        session.commit()
        print(
            f"Processed all games in {(datetime.now() - start_time).total_seconds() / 60:.2f} minutes"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load At Bat details data")
    parser.add_argument("--sport-id", type=int, required=True, help="ID of the league")
    parser.add_argument("--season", type=int, help="Season to process. If not provided, processes all seasons.")
    args = parser.parse_args()

    print(f"Loading at-bat details for sport {args.sport_id}" + (f" for season {args.season}" if args.season else ""))
    load_at_bat_details(args.sport_id, args.season)
