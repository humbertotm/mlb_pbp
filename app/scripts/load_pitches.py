import argparse
from datetime import datetime

from sqlalchemy.orm import Session
from app.schemas import PitchSchema
from app.scripts import db_engine

from app.models import AtBat, Game, Pitch


def _get_at_bats_for_season(sport_id: int, season: int) -> list[AtBat]:
    with Session(db_engine) as session:
        at_bats = (
            session.query(AtBat)
            .join(Game, AtBat.game_id == Game.id)
            .filter(
                AtBat.sport_id == sport_id,
                Game.season == season,
            )
        ).all()
        return at_bats


def load_pitches(sport_id: int, start_season: int, end_season: int) -> None:
    with Session(db_engine) as session:
        for season in range(start_season, end_season):
            start_time = datetime.now()
            at_bats = _get_at_bats_for_season(sport_id, season)
            print(
                f"{len(at_bats)} AtBats for season {season} of the {sport_id} league to process"
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

            session.bulk_save_objects(pitches_to_persist)

            print(
                f"Stored {len(pitches_to_persist)} Pitches for season {season} in {(datetime.now() - start_time) / 60} minutes"
            )
        session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load AtBats data")
    parser.add_argument("--sport-id", type=int, required=True, help="ID of the league")
    parser.add_argument("--start-season", type=int, required=True, help="Start season")
    parser.add_argument("--end-season", type=int, required=True, help="End season")
    args = parser.parse_args()

    load_pitches(args.sport_id, args.start_season, args.end_season)
