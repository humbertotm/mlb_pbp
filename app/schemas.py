from pydantic import BaseModel
from datetime import date
from typing import Optional


class PlayerSchema(BaseModel):
    mlb_id: int
    full_name: str
    is_player: bool
    throws: Optional[str]
    bats: Optional[str]
    birth_date: date
    primary_position_code: str
    primary_position: str
    active: bool
    mlb_debut_date: Optional[date]
    last_played_date: Optional[date]
    details: dict

    class Config:
        orm_mode = True


class TeamSchema(BaseModel):
    mlb_id: int
    sport_id: int
    name: str
    active: bool
    hometown: str
    details: dict

    class Config:
        orm_mode = True


class GameSchema(BaseModel):
    mlb_id: int
    sport_id: int
    game_date: date
    game_type: str
    season: int
    details: dict

    class Config:
        orm_mode = True


class AtBatDetailsSchema(BaseModel):
    game_mlb_id: int
    sport_id: int
    season: int
    details: dict

    class Config:
        orm_mode = True


class AtBatSchema(BaseModel):
    sport_id: int
    at_bat_index: int
    has_out: bool
    outs: int
    balls: int
    strikes: int
    total_pitch_count: int
    inning: int
    is_top_inning: bool
    result: dict
    rbi: int
    event_type: Optional[str]
    is_scoring_play: bool
    r1b: bool
    r2b: bool
    r3b: bool
    details: dict

    # Relationships
    game_id: int
    game_mlb_id: int
    pitcher_id: int
    pitcher_mlb_id: int
    batter_id: int
    batter_mlb_id: int

    class Config:
        orm_mode = True
