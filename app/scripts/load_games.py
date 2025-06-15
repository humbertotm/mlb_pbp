import argparse
from datetime import date, datetime, timedelta
from functools import lru_cache

import statsapi
from sqlalchemy import func
from app.models import Game, Team
from app.schemas import GameSchema
from sqlalchemy.orm import Session


from . import db_engine


def get_max_game_date():
    with Session(db_engine) as session:
        max_date = session.query(func.max(Game.game_date)).scalar()
        if max_date is None:
            # If no games exist, default to a reasonable start date
            return date(2023, 1, 1)
        return max_date


@lru_cache()
def get_team_ids(sport_id):
    print(f"Retrieving team IDs for sport {sport_id}")
    with Session(db_engine) as session:
        teams = (
            session.query(Team)
            .filter(Team.sport_id == sport_id)
            .order_by(Team.mlb_id)
            .all()
        )
        return [team.mlb_id for team in teams]


def get_existing_games_map() -> dict:
    with Session(db_engine) as session:
        games = session.query(Game).all()
        return {game.mlb_id: game for game in games}


def get_games_data_for_date_range(sport_id, start_date, end_date):
    # Format dates for the API call
    start_date_str = start_date.strftime("%m/%d/%Y")
    end_date_str = end_date.strftime("%m/%d/%Y")

    # Call the schedule function with sportId and date range
    games = statsapi.schedule(
        sportId=sport_id, start_date=start_date_str, end_date=end_date_str
    )
    games_map = {}
    team_ids = get_team_ids(sport_id)

    for game in games:
        game_id = game.get("game_id")

        if game.get("home_id") is None or game.get("away_id") is None:
            continue

        if game.get("home_id") not in team_ids or game.get("away_id") not in team_ids:
            continue

        games_map[game_id] = game

    print(f"Retrieved {len(games_map)} games between {start_date} and {end_date}")
    return games_map


def load_games(sport_id, start_date, end_date):
    # Get games data and existing games
    games_data = get_games_data_for_date_range(sport_id, start_date, end_date)
    existing_games = get_existing_games_map()

    stats = {"updated": 0, "inserted": 0, "failed": 0}

    # With an open sqlalchemy Session:
    with Session(db_engine) as session:
        # Disable autoflush during the entire operation
        with session.no_autoflush:
            # For every game in the games data:
            for game_data in games_data.values():
                # Ignore All-Stars and unofficial games
                if game_data.get("game_type") in ["A", "E"]:
                    continue

                try:
                    game_mlb_id = game_data.get("game_id")
                    game_id = None
                    if game_mlb_id in existing_games:
                        game_id = existing_games[game_mlb_id].id
                        stats["updated"] += 1
                    else:
                        stats["inserted"] += 1

                    game_date = (
                        datetime.strptime(game_data["game_date"], "%Y-%m-%d").date()
                        if game_data.get("game_date")
                        else None
                    )

                    # Instantiate a Game object
                    game_instance = Game(
                        id=game_id,
                        mlb_id=game_mlb_id,
                        sport_id=sport_id,
                        game_date=game_date,
                        game_type=game_data.get("game_type"),
                        season=game_date.year if game_date else None,
                        details=game_data,
                        home_team_mlb_id=game_data.get("home_id"),
                        away_team_mlb_id=game_data.get("away_id"),
                    )

                    # Validate the game data
                    GameSchema.from_orm(game_instance)

                    # Merge will handle both insert and update
                    session.merge(game_instance)

                except Exception as e:
                    stats["failed"] += 1
                    print(
                        f"Failed validation for game with mlb_id {game_data.get('game_id')}, error: {e}"
                    )
                    session.rollback()

            # Flush all changes at once
            session.flush()

        # Commit all changes
        session.commit()
        print("Sync complete:")
        print(f"- Updated: {stats['updated']} games")
        print(f"- Inserted: {stats['inserted']} new games")
        print(f"- Failed: {stats['failed']} games")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load games data")
    parser.add_argument("--sport-id", type=int, required=True, help="ID of the league")
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date (YYYY-MM-DD). If not provided, uses the most recent game date from the database.",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date (YYYY-MM-DD). If not provided, uses today's date.",
    )
    args = parser.parse_args()

    # Get the end date (today if not specified)
    if args.end_date:
        try:
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
        except ValueError:
            print("Error: End date must be in YYYY-MM-DD format")
            exit(1)
    else:
        end_date = date.today()

    # Get the start date (from database if not specified)
    if args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        except ValueError:
            print("Error: Start date must be in YYYY-MM-DD format")
            exit(1)
    else:
        start_date = get_max_game_date()
        # Add one day to avoid reloading the last day we already have
        start_date += timedelta(days=1)
        print(
            f"Using start date: {start_date} (day after most recent game in database)"
        )

    if end_date < start_date:
        print("Error: End date must be after start date")
        exit(1)

    print(f"Loading games for {args.sport_id} from {start_date} to {end_date}")

    load_games(args.sport_id, start_date, end_date)
