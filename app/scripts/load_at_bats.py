import argparse
from typing import Dict
from sqlalchemy.orm import Session

from . import db_engine
from app.models import AtBat, AtBatDetails


def get_league_season_game_ids(sport_id: int, season: int) -> Dict[int, int]:
    # Fetch all games for given league and season
    # Return a dictionary of mlb_id: id
    return

def load_at_bats(sport_id: int, start_season: int, end_season: int) -> None:
    with Session(db_engine) as session:
        # Iterate over the range of seasons
        for season in range(start_season, end_season):
            at_bats = []
            game_id_mappings = get_league_season_game_ids(sport_id, season)
            player_id_mappings = {}
            season_ab_details = session.query(AtBatDetails).filter(AtBatDetails.season == season, AtBatDetails.sport_id == sport_id).all()
            for ab_details in season_ab_details:
                details = ab_details.details
                at_bat = AtBat(
                    sport_id=sport_id,
                    at_bat_index=details.get("about", {}).get("atBatIndex"),
                    has_out=details.get("about", {}).get("hasOut"),
                    outs=details.get("count", {}).get("outs"),
                    balls=details.get("count", {}).get("balls"),
                    strikes=details.get("count", {}).get("strikes"),
                    # [wololo] this is more complex. I'll get back to it.
                    total_pitch_count=details.get("pitchCount"),
                    inning=details.get("about", {}).get("inning"),
                    is_top_inning=details.get("about", {}).get("isTopInning"),
                    result=details.get("result"),
                    rbi=details.get("result", {}).get("rbi"),
                    event_type=details.get("result", {}).get("eventType"),
                    is_scoring_play=details.get("about", {}).get("isScoringPlay"),
                    # [wololo] this is more complex. I'll get back to it.
                    r1b=details.get("runners", {}).get("r1b"),
                    r2b=details.get("runners", {}).get("r2b"),
                    r3b=details.get("runners", {}).get("r3b"),
                    details=details,
                    game_id=game_id_mappings.get(ab_details.game_mlb_id),
                    game_mlb_id=ab_details.game_mlb_id,
                    pitcher_mlb_id=details.get("matchup", {}).get("pitcher", {}).get("id"),
                    pitcher_id=player_id_mappings.get(details.get("matchup", {}).get("pitcher", {}).get("id")),
                    batter_mlb_id=details.get("matchup", {}).get("batter", {}).get("id"),
                    batter_id=player_id_mappings.get(details.get("matchup", {}).get("batter", {}).get("id")),
                )
                at_bats.append(at_bat)
        # Get all AtBatDetails records for the given league and season
        # Iterate over the AtBatDetails records
        # Instantiate AtBat record and validate before appending to list of records to bulk persist
    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load AtBats data")
    parser.add_argument("--sport-id", type=int, required=True, help="ID of the league")
    parser.add_argument("--start-season", type=int, required=True, help="Start season")
    parser.add_argument("--end-season", type=int, required=True, help="End season")
    args = parser.parse_args()

    load_at_bats(args.sport_id, args.start_season, args.end_season)
