import argparse

from sqlalchemy.orm import Session
import statsapi

from app.scripts import db_engine
from app.models import Team
from app.schemas import TeamSchema


def get_existing_teams_map() -> dict:
    with Session(db_engine) as session:
        teams = session.query(Team).all()
        return {team.mlb_id: team.name for team in teams}

def get_teams_data(sport_id, start_season, end_season):
    # Declare a teams_map.
    teams_map = {}
    existing_teams = get_existing_teams_map()

    # Iterate over every season in the desired range.
    for season in range(start_season, end_season):
        # Extract the "teams" list from the response.
        teams_api_response = statsapi.get("teams", {"sportId": sport_id, "season": season}) or {}
        teams_list = teams_api_response.get("teams", [])
        # Write the team objects to the teams_map. Key is the team "id", value is the object.
        for team in teams_list:
            team_id = team.get("id")
            if team_id in existing_teams:
                continue

            # Use the freshest data if collision occurs.
            teams_map[team_id] = team

        print(f"Done processing teams {len(teams_list)} for season {season}")

    print(
        f"A total of {len(teams_map)} unique teams in mlb from {start_season} to {end_season - 1}"
    )

    return teams_map

def load_teams(sport_id, start_season, end_season):
    # Declare teams list.
    teams_list = []
    # Get teams map.
    teams_map = get_teams_data(sport_id, start_season, end_season)
    # With an open slqalchemy Session,
    with Session(db_engine) as session:
        # iterate over every team in the map.
        for team in teams_map.values():
            # For every team, instantiate a Team object and append it to the teams list.
            team_instance = Team(
                mlb_id=int(team.get("id")),
                sport_id=sport_id,
                name=team.get("name"),
                active=team.get("active", False),
                hometown=team.get("locationName"),
                details=team,
            )

            try:
                TeamSchema.from_orm(team_instance)
                teams_list.append(team_instance)
            except Exception as e:
                print(f"Failed validation for team with mlb_id {team.get('id')}")

        # Bulk write the teams list to the teams table.
        session.bulk_save_objects(teams_list)
        # Commit the session.
        session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load team data")
    parser.add_argument("--sport-id", type=int, required=True, help="ID of the league")
    parser.add_argument("--start-season", type=int, required=True, help="Start season")
    parser.add_argument("--end-season", type=int, required=True, help="End season")
    args = parser.parse_args()

    load_teams(args.sport_id, args.start_season, args.end_season)
