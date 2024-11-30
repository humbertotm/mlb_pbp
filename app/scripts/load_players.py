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
        return {player.mlb_id: player.full_name for player in players}


def get_players_data(sport_id: int, start_season: int, end_season: int) -> dict:
    players_map = {}
    existing_players = get_existing_players_map()

    for season in range(start_season, end_season):
        sports_players_api_response = (
            statsapi.get("sports_players", {"sportId": sport_id, "season": season})
            or {}
        )

        players = sports_players_api_response.get("people", [])
        for player in players:
            player_id = player.get("id")
            if player_id in existing_players:
                continue

            # It doesn't matter if it's already present in the dict. I want the freshest data.
            players_map[player_id] = player

        print(f"Done processing players {len(players)} for season {season}")

    print(
        f"A total of {len(players_map)} unique players in mlb from {start_season} to {end_season}"
    )

    return players_map


def load_players(sport_id: int, start_season: int, end_season: int) -> None:
    players_list = []
    players_map = get_players_data(sport_id, start_season, end_season)

    with Session(db_engine) as session:
        for player in players_map.values():
            player_instance = Player(
                mlb_id=int(player.get("id")),
                full_name=player.get("fullName"),
                is_player=player.get("isPlayer"),
                throws=player.get("pitchHand", {}).get("code"),
                bats=player.get("batSide", {}).get("code"),
                birth_date=datetime.strptime(player["birthDate"], "%Y-%m-%d").date()
                if player.get("birthDate")
                else None,
                primary_position_code=player.get("primaryPosition", {}).get("code"),
                primary_position=player.get("primaryPosition", {}).get("name"),
                active=player.get("active"),
                mlb_debut_date=datetime.strptime(
                    player["mlbDebutDate"], "%Y-%m-%d"
                ).date()
                if player.get("mlbDebutDate")
                else None,
                last_played_date=datetime.strptime(
                    player["lastPlayedDate"], "%Y-%m-%d"
                ).date()
                if player.get("lastPlayedDate")
                else None,
                details=player,
            )
            try:
                # If validation fails, the exception will be raised; otherwise,
                # the record will be appended to the list.
                PlayerSchema.from_orm(player_instance)
                players_list.append(player_instance)
            except Exception as e:
                print(f"Failed validation for player with mlb_id {player['id']}")

        session.bulk_save_objects(players_list)
        print(f"Saving {len(players_list)} new player records")
        session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load player data")
    parser.add_argument("--sport-id", type=int, required=True, help="ID of the league")
    parser.add_argument("--start-season", type=int, required=True, help="Start season")
    parser.add_argument("--end-season", type=int, required=True, help="End season")
    args = parser.parse_args()

    load_players(args.sport_id, args.start_season, args.end_season)
