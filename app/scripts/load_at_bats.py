import argparse
from datetime import datetime
from typing import Dict, List, Tuple
from pydantic import ValidationError
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.schemas import AtBatSchema

from . import db_engine
from app.models import AtBat, AtBatDetails, Game, Player


def get_games_without_at_bats(
    sport_id: int, season: int = None
) -> List[Tuple[int, int, datetime.date]]:
    """
    Get a list of games that have no AtBat records.

    Args:
        sport_id (int): The ID of the sport/league
        season (int, optional): If provided, only check games from this season

    Returns:
        List[Tuple[int, int, datetime.date]]: List of tuples containing (game_mlb_id, game_id, game_date)
        for games that need AtBat records
    """
    with Session(db_engine) as session:
        # Get all games that don't have AtBat records
        games_query = select(Game.mlb_id, Game.id, Game.game_date).where(
            Game.sport_id == sport_id,
            ~Game.mlb_id.in_(
                select(AtBat.game_mlb_id).distinct().where(AtBat.sport_id == sport_id)
            ),
        )

        # Add season filter if provided
        if season is not None:
            games_query = games_query.where(Game.season == season)

        return [
            (mlb_id, id, game_date)
            for mlb_id, id, game_date in session.execute(games_query)
        ]


def get_player_id_mappings() -> Dict[int, int]:
    # Fetch all players for given league and season
    with Session(db_engine) as session:
        players = session.query(Player).all()
        # Return a dictionary of mlb_id: id
        return {player.mlb_id: player.id for player in players}


def load_at_bats(sport_id: int, season: int = None) -> None:
    """
    Load AtBat records for all games that have AtBatDetails but no AtBat records.

    Args:
        sport_id (int): The ID of the sport/league
        season (int, optional): If provided, only process games from this season
    """
    player_id_mappings = get_player_id_mappings()
    with Session(db_engine) as session:
        start_time = datetime.now()
        at_bats = []

        # Get games that need processing
        games_to_process = get_games_without_at_bats(sport_id, season)
        print(
            f"Processing {len(games_to_process)} games that have AtBatDetails but no AtBat records"
            + (f" for season {season}" if season else "")
        )

        # Process each game
        for game_mlb_id, game_id, game_date in games_to_process:
            game_at_bat_details = (
                session.query(AtBatDetails)
                .filter(
                    AtBatDetails.game_mlb_id == game_mlb_id,
                    AtBatDetails.sport_id == sport_id,
                )
                .all()
            )

            for ab_details in game_at_bat_details:
                details = ab_details.details
                pitches = [
                    event
                    for event in details["playEvents"]
                    if event.get("type") == "pitch"
                ]
                if not pitches:
                    continue
                last_pitch = pitches[-1]
                end_count = last_pitch.get("count", {})
                runners = details.get("runners", [])
                runner_positions = {
                    "1B": False,
                    "2B": False,
                    "3B": False,
                }
                for runner in runners:
                    if runner.get("movement", {}).get("start") == "1B":
                        runner_positions["1B"] = True
                    if runner.get("movement", {}).get("start") == "2B":
                        runner_positions["2B"] = True
                    if runner.get("movement", {}).get("start") == "3B":
                        runner_positions["3B"] = True

                at_bat = AtBat(
                    sport_id=sport_id,
                    at_bat_index=details.get("about", {}).get("atBatIndex"),
                    has_out=details.get("about", {}).get("hasOut"),
                    outs=end_count.get("outs"),
                    balls=end_count.get("balls"),
                    strikes=end_count.get("strikes"),
                    total_pitch_count=len(pitches),
                    inning=details.get("about", {}).get("inning"),
                    is_top_inning=details.get("about", {}).get("isTopInning"),
                    result=details.get("result"),
                    rbi=details.get("result", {}).get("rbi"),
                    event_type=details.get("result", {}).get("eventType"),
                    is_scoring_play=details.get("about", {}).get("isScoringPlay"),
                    r1b=runner_positions["1B"],
                    r2b=runner_positions["2B"],
                    r3b=runner_positions["3B"],
                    details=details,
                    game_id=game_id,  # Using the game_id we already have
                    game_mlb_id=game_mlb_id,
                    pitcher_mlb_id=details.get("matchup", {})
                    .get("pitcher", {})
                    .get("id"),
                    pitcher_id=player_id_mappings.get(
                        details.get("matchup", {}).get("pitcher", {}).get("id")
                    ),
                    batter_mlb_id=details.get("matchup", {})
                    .get("batter", {})
                    .get("id"),
                    batter_id=player_id_mappings.get(
                        details.get("matchup", {}).get("batter", {}).get("id")
                    ),
                )

                try:
                    AtBatSchema.from_orm(at_bat)
                    at_bats.append(at_bat)
                except ValidationError as e:
                    print(f"Error validating AtBat from AtBatDetails {ab_details.id}")
                    print(e)

        # Save all at bats in one batch
        session.bulk_save_objects(at_bats)
        session.commit()
        print(
            f"Stored {len(at_bats)} AtBats in {(datetime.now() - start_time).total_seconds() / 60:.2f} minutes"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load AtBats data")
    parser.add_argument("--sport-id", type=int, required=True, help="ID of the league")
    parser.add_argument(
        "--season",
        type=int,
        help="Season to process. If not provided, processes all seasons.",
    )
    args = parser.parse_args()

    print(
        f"Loading at-bats for sport {args.sport_id}"
        + (f" for season {args.season}" if args.season else "")
    )
    load_at_bats(args.sport_id, args.season)
