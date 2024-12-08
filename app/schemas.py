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


class PitchSchema(BaseModel):
    pitch_index: int
    ball_count: int
    strike_count: int
    pitch_type_code: Optional[str]
    pitch_type_description: Optional[str]
    call_code: Optional[str]
    call_description: Optional[str]
    zone: Optional[int]
    start_speed: Optional[float]
    is_ball: bool
    is_strike: bool
    is_foul: bool
    is_out: bool
    is_in_play: bool
    r1b: Optional[bool]
    r2b: Optional[bool]
    r3b: Optional[bool]
    details: dict

    # Relationship
    at_bat_id: int

    class Config:
        orm_mode = True
