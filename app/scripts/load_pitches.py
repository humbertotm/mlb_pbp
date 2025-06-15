import argparse
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select
from app.schemas import PitchSchema
from app.scripts import db_engine

from app.models import AtBat, Game, Pitch


def get_at_bats_without_pitches(sport_id: int, season: int = None) -> list[AtBat]:
    """
    Get all AtBats that don't have any associated Pitch records.
    
    Args:
        sport_id (int): The ID of the sport/league
        season (int, optional): If provided, only check at-bats from this season
    
    Returns:
        list[AtBat]: List of AtBat records that need Pitch records
    """
    with Session(db_engine) as session:
        query = (
            session.query(AtBat)
            .join(Game, AtBat.game_id == Game.id)
            .filter(
                AtBat.sport_id == sport_id,
                ~AtBat.id.in_(
                    select(Pitch.at_bat_id)
                    .distinct()
                )
            )
        )
        
        # Add season filter if provided
        if season is not None:
            query = query.filter(Game.season == season)
            
        return query.all()


def load_pitches(sport_id: int, season: int = None) -> None:
    """
    Load Pitch records for all AtBats that don't have any Pitch records.
    
    Args:
        sport_id (int): The ID of the sport/league
        season (int, optional): If provided, only process at-bats from this season
    """
    with Session(db_engine) as session:
        start_time = datetime.now()
        
        # Get AtBats that need processing
        at_bats = get_at_bats_without_pitches(sport_id, season)
        print(
            f"Processing {len(at_bats)} AtBats that have no Pitch records"
            + (f" for season {season}" if season else "")
        )

        pitches_to_persist = []
        for at_bat in at_bats:
            starting_count = {"balls": 0, "strikes": 0}
            play_events = at_bat.details.get("playEvents", [])

            for i, event in enumerate(play_events):
                is_pitch = event.get("type") == "pitch"
                end_count = event.get("count", {})

                if not is_pitch:
                    starting_count = {
                        "balls": end_count.get("balls"),
                        "strikes": end_count.get("strikes"),
                    }
                    continue

                pitch = Pitch(
                    pitch_index=i,
                    ball_count=starting_count["balls"],
                    strike_count=starting_count["strikes"],
                    pitch_type_code=event.get("details", {})
                    .get("type", {})
                    .get("code"),
                    pitch_type_description=event.get("details", {})
                    .get("type", {})
                    .get("description"),
                    call_code=event.get("details", {}).get("call", {}).get("code"),
                    call_description=event.get("details", {})
                    .get("call", {})
                    .get("description"),
                    zone=event.get("pitchData", {}).get("zone"),
                    start_speed=event.get("pitchData", {}).get("startSpeed"),
                    is_ball=event.get("details", {}).get("isBall"),
                    is_strike=event.get("details", {}).get("isStrike"),
                    is_foul=event.get("details", {}).get("call") == "F",
                    is_out=event.get("details", {}).get("isOut"),
                    is_in_play=event.get("details", {}).get("isInPlay"),
                    details=event,
                    at_bat_id=at_bat.id,
                )
                try:
                    PitchSchema.from_orm(pitch)
                    pitches_to_persist.append(pitch)
                except Exception as e:
                    print(f"Error validating pitch: {e}")
                finally:
                    starting_count = {
                        "balls": end_count.get("balls"),
                        "strikes": end_count.get("strikes"),
                    }

        print(f"Storing {len(pitches_to_persist)} Pitches")
        session.bulk_save_objects(pitches_to_persist)
        session.commit()
        print(
            f"Processed all pitches in {(datetime.now() - start_time).total_seconds() / 60:.2f} minutes"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load Pitches data")
    parser.add_argument("--sport-id", type=int, required=True, help="ID of the league")
    parser.add_argument("--season", type=int, help="Season to process. If not provided, processes all seasons.")
    args = parser.parse_args()

    print(f"Loading pitches for sport {args.sport_id}" + (f" for season {args.season}" if args.season else ""))
    load_pitches(args.sport_id, args.season)
