import argparse
from datetime import datetime
from typing import Dict
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.schemas import AtBatSchema

from . import db_engine
from app.models import AtBat, AtBatDetails, Game, Player


def get_league_season_game_ids(sport_id: int, season: int) -> Dict[int, int]:
    # Fetch all games for given league and season
    with Session(db_engine) as session:
        games = (
            session.query(Game)
            .filter(Game.sport_id == sport_id, Game.season == season)
            .all()
        )
        # Return a dictionary of mlb_id: id
        return {game.mlb_id: game.id for game in games}


def get_player_id_mappings() -> Dict[int, int]:
    # Fetch all players for given league and season
    with Session(db_engine) as session:
        players = session.query(Player).all()
        # Return a dictionary of mlb_id: id
        return {player.mlb_id: player.id for player in players}


def load_at_bats(sport_id: int, start_season: int, end_season: int) -> None:
    player_id_mappings = get_player_id_mappings()
    with Session(db_engine) as session:
        # Iterate over the range of seasons
        for season in range(start_season, end_season):
            start_time = datetime.now()
            at_bats = []
            game_id_mappings = get_league_season_game_ids(sport_id, season)
            season_ab_details = (
                session.query(AtBatDetails)
                .filter(
                    AtBatDetails.season == season, AtBatDetails.sport_id == sport_id
                )
                .all()
            )
            print(
                f"{len(season_ab_details)} AtBatDetails for season {season} of the {sport_id} league to process"
            )

            for ab_details in season_ab_details:
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
                    game_id=game_id_mappings.get(ab_details.game_mlb_id),
                    game_mlb_id=ab_details.game_mlb_id,
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

            session.bulk_save_objects(at_bats)
            print(
                f"Stored {len(at_bats)} AtBats for season {season} in {(datetime.now() - start_time) / 60} minutes"
            )

        session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load AtBats data")
    parser.add_argument("--sport-id", type=int, required=True, help="ID of the league")
    parser.add_argument("--start-season", type=int, required=True, help="Start season")
    parser.add_argument("--end-season", type=int, required=True, help="End season")
    args = parser.parse_args()

    load_at_bats(args.sport_id, args.start_season, args.end_season)
