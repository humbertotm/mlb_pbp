import argparse
from datetime import datetime
from typing import Dict
from app.models import AtBat, Player, Game

from sqlalchemy.orm import Session
from app.scripts import db_engine


def get_player_id_mappings() -> Dict[int, int]:
    # Fetch all players for given league and season
    with Session(db_engine) as session:
        players = session.query(Player).all()
        # Return a dictionary of mlb_id: id
        return {player.mlb_id: player.id for player in players}


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


def fix_at_bats(
    sport_id: int, start_season: int, end_season: int, event_type: str
) -> None:
    player_id_mappings = get_player_id_mappings()
    with Session(db_engine) as session:
        # Iterate over the range of seasons
        for season in range(start_season, end_season):
            start_time = datetime.now()
            season_game_mlb_ids = get_league_season_game_ids(sport_id, season).keys()
            at_bats = (
                session.query(AtBat)
                .filter(
                    AtBat.sport_id == sport_id,
                    AtBat.game_mlb_id.in_(season_game_mlb_ids),
                )
                .all()
            )
            fixed_ab_count = 0
            for ab in at_bats:
                details = ab.details
                play_events = details.get("playEvents", [])
                for ev in play_events:
                    if ev.get("type") == "action":
                        description = ev.get("details", {}).get("eventType")
                        if description == event_type:
                            new_player_mlb_id = ev.get("player", {}).get("id")
                            if new_player_mlb_id:
                                new_player_id = player_id_mappings.get(
                                    new_player_mlb_id
                                )
                                if not new_player_id:
                                    print(
                                        f"Player with mlb_id {new_player_mlb_id} not found"
                                    )
                                    continue

                                if event_type == "pitching_substitution":
                                    ab.pitcher_id = new_player_id
                                    ab.pitcher_mlb_id = new_player_mlb_id
                                elif event_type == "offensive_substitution":
                                    ab.batter_id = new_player_id
                                    ab.batter_mlb_id = new_player_mlb_id
                                fixed_ab_count += 1

            session.bulk_save_objects(at_bats)
            print(
                f"Fixed {fixed_ab_count} AtBats for season {season} in {(datetime.now() - start_time) / 60} minutes"
            )

        session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load AtBats data")
    parser.add_argument("--sport-id", type=int, required=True, help="ID of the league")
    parser.add_argument("--start-season", type=int, required=True, help="Start season")
    parser.add_argument("--end-season", type=int, required=True, help="End season")
    parser.add_argument(
        "--event-type", type=str, required=True, help="Event type to fix"
    )

    args = parser.parse_args()

    fix_at_bats(args.sport_id, args.start_season, args.end_season, args.event_type)
