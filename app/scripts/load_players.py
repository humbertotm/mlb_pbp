import argparse
from datetime import datetime

import statsapi
from app.models import Player
from app.schemas import PlayerSchema
from sqlalchemy.orm import Session

from app.scripts import db_engine


def get_existing_players_map() -> dict:
    with Session(db_engine) as session:
        players = session.query(Player).all()
        return {player.mlb_id: player for player in players}


def get_players_data(sport_id: int, start_season: int, end_season: int) -> dict:
    players_map = {}

    for season in range(start_season, end_season):
        sports_players_api_response = (
            statsapi.get("sports_players", {"sportId": sport_id, "season": season})
            or {}
        )

        players = sports_players_api_response.get("people", [])
        for player in players:
            player_id = player.get("id")
            # Always store the freshest data
            players_map[player_id] = player

        print(f"Done processing players {len(players)} for season {season}")

    print(
        f"A total of {len(players_map)} unique players in mlb from {start_season} to {end_season}"
    )

    return players_map


def load_players(sport_id: int, start_season: int, end_season: int) -> None:
    players_map = get_players_data(sport_id, start_season, end_season)
    existing_players = get_existing_players_map()
    
    stats = {"updated": 0, "inserted": 0, "failed": 0}

    with Session(db_engine) as session:
        # Disable autoflush during the entire operation
        with session.no_autoflush:
            for player_data in players_map.values():
                try:
                    player_mlb_id = int(player_data.get("id"))
                    player_id = None
                    if player_mlb_id in existing_players:
                        player_id = existing_players[player_mlb_id].id

                    player_instance = Player(
                        id=player_id,
                        mlb_id=int(player_data.get("id")),
                        full_name=player_data.get("fullName"),
                        is_player=player_data.get("isPlayer"),
                        throws=player_data.get("pitchHand", {}).get("code"),
                        bats=player_data.get("batSide", {}).get("code"),
                        birth_date=datetime.strptime(player_data["birthDate"], "%Y-%m-%d").date()
                        if player_data.get("birthDate")
                        else None,
                        primary_position_code=player_data.get("primaryPosition", {}).get("code"),
                        primary_position=player_data.get("primaryPosition", {}).get("name"),
                        active=player_data.get("active"),
                        mlb_debut_date=datetime.strptime(
                            player_data["mlbDebutDate"], "%Y-%m-%d"
                        ).date()
                        if player_data.get("mlbDebutDate")
                        else None,
                        last_played_date=datetime.strptime(
                            player_data["lastPlayedDate"], "%Y-%m-%d"
                        ).date()
                        if player_data.get("lastPlayedDate")
                        else None,
                        details=player_data,
                    )
                    
                    # Validate the player data
                    PlayerSchema.from_orm(player_instance)
                    
                    # Check if player exists
                    player_id = player_instance.mlb_id
                    if player_id in existing_players:
                        stats["updated"] += 1
                    else:
                        stats["inserted"] += 1
                    
                    # Merge will handle both insert and update
                    # merge() already attaches the instance to the session
                    session.merge(player_instance)
                    
                except Exception as e:
                    stats["failed"] += 1
                    print(f"Failed validation for player with mlb_id {player_data['id']}: {str(e)}")
                    session.rollback()

            # Flush all changes at once
            session.flush()
            
        # Commit all changes
        session.commit()
        print(f"Sync complete:")
        print(f"- Updated: {stats['updated']} players")
        print(f"- Inserted: {stats['inserted']} new players")
        print(f"- Failed: {stats['failed']} players")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load player data")
    parser.add_argument("--sport-id", type=int, required=True, help="ID of the league")
    parser.add_argument("--start-season", type=int, required=True, help="Start season")
    parser.add_argument("--end-season", type=int, required=True, help="End season")
    args = parser.parse_args()

    load_players(args.sport_id, args.start_season, args.end_season)
