import argparse

from sqlalchemy.orm import Session
import statsapi

from app.scripts import db_engine
from app.models import Team
from app.schemas import TeamSchema


def get_existing_teams_map() -> dict:
    with Session(db_engine) as session:
        teams = session.query(Team).all()
        return {team.mlb_id: team for team in teams}


def get_teams_data(sport_id, start_season, end_season):
    # Declare a teams_map.
    teams_map = {}

    # Iterate over every season in the desired range.
    for season in range(start_season, end_season):
        # Extract the "teams" list from the response.
        teams_api_response = (
            statsapi.get("teams", {"sportId": sport_id, "season": season}) or {}
        )
        teams_list = teams_api_response.get("teams", [])
        # Write the team objects to the teams_map. Key is the team "id", value is the object.
        for team in teams_list:
            team_id = team.get("id")
            # Always store the freshest data
            teams_map[team_id] = team

        print(f"Done processing teams {len(teams_list)} for season {season}")

    print(
        f"A total of {len(teams_map)} unique teams in mlb from {start_season} to {end_season - 1}"
    )

    return teams_map


def load_teams(sport_id, start_season, end_season):
    # Get teams map and existing teams
    teams_map = get_teams_data(sport_id, start_season, end_season)
    existing_teams = get_existing_teams_map()

    stats = {"updated": 0, "inserted": 0, "failed": 0}

    # With an open sqlalchemy Session,
    with Session(db_engine) as session:
        # Disable autoflush during the entire operation
        with session.no_autoflush:
            # iterate over every team in the map.
            for team_data in teams_map.values():
                try:
                    team_mlb_id = int(team_data.get("id"))
                    team_id = None
                    if team_mlb_id in existing_teams:
                        team_id = existing_teams[team_mlb_id].id
                        stats["updated"] += 1
                    else:
                        stats["inserted"] += 1

                    # For every team, instantiate a Team object
                    team_instance = Team(
                        id=team_id,
                        mlb_id=team_mlb_id,
                        sport_id=sport_id,
                        name=team_data.get("name"),
                        active=team_data.get("active", False),
                        hometown=team_data.get("locationName"),
                        details=team_data,
                    )

                    # Validate the team data
                    TeamSchema.from_orm(team_instance)

                    # Merge will handle both insert and update
                    session.merge(team_instance)

                except Exception as e:
                    stats["failed"] += 1
                    print(
                        f"Failed validation for team with mlb_id {team_data.get('id')}: {str(e)}"
                    )
                    session.rollback()

            # Flush all changes at once
            session.flush()

        # Commit all changes
        session.commit()
        print(f"Sync complete:")
        print(f"- Updated: {stats['updated']} teams")
        print(f"- Inserted: {stats['inserted']} new teams")
        print(f"- Failed: {stats['failed']} teams")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load team data")
    parser.add_argument("--sport-id", type=int, required=True, help="ID of the league")
    parser.add_argument("--start-season", type=int, required=True, help="Start season")
    parser.add_argument("--end-season", type=int, required=True, help="End season")
    args = parser.parse_args()

    load_teams(args.sport_id, args.start_season, args.end_season)
