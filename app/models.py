from datetime import date, datetime
from typing import List
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)

from sqlalchemy.orm import declarative_mixin, Mapped, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB


Base = declarative_base()


@declarative_mixin
class TimestampMixin:
    created_at: Mapped[datetime] = Column(
        DateTime, default=datetime.now(), nullable=False
    )
    updated_at: Mapped[datetime] = Column(
        DateTime, default=datetime.now(), onupdate=datetime.now(), nullable=False
    )


class Player(Base, TimestampMixin):
    __tablename__ = "players"

    id: Mapped[int] = Column(Integer, primary_key=True)
    mlb_id: Mapped[int] = Column(Integer, nullable=False, unique=True)
    full_name: Mapped[str] = Column(String, nullable=False)
    is_player: Mapped[bool] = Column(Boolean, nullable=True)
    throws: Mapped[str] = Column(String, nullable=True)
    bats: Mapped[str] = Column(String, nullable=True)
    birth_date: Mapped[date] = Column(Date, nullable=True)
    birth_city: Mapped[str] = Column(String, nullable=True)
    birth_country: Mapped[str] = Column(String, nullable=True)
    primary_position_code: Mapped[str] = Column(String, nullable=True)
    primary_position: Mapped[str] = Column(String, nullable=True)
    active: Mapped[bool] = Column(Boolean, nullable=True)
    mlb_debut_date: Mapped[date] = Column(Date, nullable=True)
    last_played_date: Mapped[date] = Column(Date, nullable=True)
    details: Mapped[dict] = Column(JSONB)
    # To be filled later upon player enrichment
    # batter_type: Mapped[int] = Column(Integer, nullable=True)

    # Relationships
    at_bats: Mapped[List["AtBat"]] = relationship(
        "AtBat", back_populates="batter", foreign_keys="AtBat.batter_id"
    )
    pitched_at_bats: Mapped[List["AtBat"]] = relationship(
        "AtBat", back_populates="pitcher", foreign_keys="AtBat.pitcher_id"
    )

    __table_args__ = (
        Index("idx_player_created_at", "created_at"),
        Index("idx_player_updated_at", "updated_at"),
    )


class Team(Base, TimestampMixin):
    __tablename__ = "teams"

    id: Mapped[int] = Column(Integer, primary_key=True)
    mlb_id: Mapped[int] = Column(Integer, nullable=False, unique=True)
    sport_id: Mapped[int] = Column(Integer, nullable=True)
    name: Mapped[str] = Column(String, nullable=False)
    active: Mapped[bool] = Column(Boolean)
    hometown: Mapped[str] = Column(String)
    details: Mapped[dict] = Column(JSONB)

    # Relationships
    home_games: Mapped[List["Game"]] = relationship(
        "Game", back_populates="home_team", foreign_keys="Game.home_team_mlb_id"
    )
    away_games: Mapped[List["Game"]] = relationship(
        "Game", back_populates="away_team", foreign_keys="Game.away_team_mlb_id"
    )

    __table_args__ = (
        Index("idx_team_created_at", "created_at"),
        Index("idx_team_updated_at", "updated_at"),
    )


class Game(Base, TimestampMixin):
    __tablename__ = "games"

    """
    Game Types:
    S: Spring Training
    R: Regular Season
    W: World Series
    D: Divisional Series
    C: ?? No games in MLB at least
    L: League Championship Series
    F: Wild Card
    """

    id: Mapped[int] = Column(Integer, primary_key=True)
    mlb_id: Mapped[int] = Column(Integer, nullable=False, unique=True)
    sport_id: Mapped[int] = Column(Integer, nullable=True)
    game_date: Mapped[date] = Column(Date)
    game_type: Mapped[str] = Column(String, nullable=False)
    season: Mapped[int] = Column(Integer, nullable=False)
    details: Mapped[dict] = Column(JSONB)

    # Relationships
    home_team_mlb_id: Mapped[int] = Column(Integer, ForeignKey("teams.mlb_id"))
    home_team: Mapped["Team"] = relationship("Team", foreign_keys=[home_team_mlb_id])
    away_team_mlb_id: Mapped[int] = Column(Integer, ForeignKey("teams.mlb_id"))
    away_team: Mapped["Team"] = relationship("Team", foreign_keys=[away_team_mlb_id])
    at_bats: Mapped[List["AtBat"]] = relationship(
        "AtBat", back_populates="game", foreign_keys="AtBat.game_id"
    )
    mlb_at_bats: Mapped[List["AtBat"]] = relationship(
        "AtBat", back_populates="mlb_game", foreign_keys="AtBat.game_mlb_id"
    )

    __table_args__ = (
        Index("idx_game_mlb_id", "mlb_id"),
        Index("idx_game_season", "season"),
        Index("idx_game_created_at", "created_at"),
        Index("idx_game_updated_at", "updated_at"),
    )


class AtBatDetails(Base):
    __tablename__ = "at_bat_details"

    id: Mapped[int] = Column(Integer, primary_key=True)
    game_mlb_id: Mapped[int] = Column(Integer, ForeignKey("games.mlb_id"))
    sport_id: Mapped[int] = Column(Integer, nullable=True)
    season: Mapped[int] = Column(Integer, nullable=False)
    details: Mapped[dict] = Column(JSONB)

    __table_args__ = (Index("idx_abdetails_game_mlb_id", "game_mlb_id"),)


class AtBat(Base):
    __tablename__ = "at_bats"

    id: Mapped[int] = Column(Integer, primary_key=True)
    sport_id: Mapped[int] = Column(Integer, nullable=True)
    at_bat_index: Mapped[int] = Column(Integer, nullable=False)
    has_out: Mapped[bool] = Column(Boolean, nullable=False)
    outs: Mapped[int] = Column(Integer, nullable=False)
    balls: Mapped[int] = Column(Integer, nullable=False)
    strikes: Mapped[int] = Column(Integer, nullable=False)
    total_pitch_count: Mapped[int] = Column(Integer, nullable=False)
    inning: Mapped[int] = Column(Integer, nullable=False)
    is_top_inning: Mapped[bool] = Column(Boolean, nullable=False)
    result: Mapped[dict] = Column(JSONB)
    rbi: Mapped[int] = Column(Integer, nullable=False)
    event_type: Mapped[str] = Column(String, nullable=True)
    is_scoring_play: Mapped[bool] = Column(Boolean, nullable=False)
    r1b: Mapped[bool] = Column(Boolean, nullable=False)
    r2b: Mapped[bool] = Column(Boolean, nullable=False)
    r3b: Mapped[bool] = Column(Boolean, nullable=False)
    details: Mapped[dict] = Column(JSONB)

    # Relationships
    game_id: Mapped[int] = Column(Integer, ForeignKey("games.id"))
    game: Mapped["Game"] = relationship("Game", foreign_keys=[game_id])
    game_mlb_id: Mapped[int] = Column(Integer, ForeignKey("games.mlb_id"))
    mlb_game: Mapped["Game"] = relationship("Game", foreign_keys=[game_mlb_id])
    pitcher_id: Mapped[int] = Column(Integer, ForeignKey("players.id"))
    pitcher: Mapped["Player"] = relationship("Player", foreign_keys=[pitcher_id])
    pitcher_mlb_id: Mapped[int] = Column(Integer, ForeignKey("players.mlb_id"))
    mlb_pitcher: Mapped["Player"] = relationship(
        "Player", foreign_keys=[pitcher_mlb_id]
    )
    batter_id: Mapped[int] = Column(Integer, ForeignKey("players.id"))
    batter: Mapped["Player"] = relationship("Player", foreign_keys=[batter_id])
    batter_mlb_id: Mapped[int] = Column(Integer, ForeignKey("players.mlb_id"))
    mlb_batter: Mapped["Player"] = relationship("Player", foreign_keys=[batter_mlb_id])
    pitches: Mapped[List["Pitch"]] = relationship(
        "Pitch", back_populates="at_bat", foreign_keys="Pitch.at_bat_id"
    )

    __table_args__ = (
        Index("idx_at_bat_sport_id", "sport_id"),
        Index("idx_at_bat_pitcher_id", "pitcher_id"),
        Index("idx_at_bat_batter_id", "batter_id"),
        Index("idx_at_bat_pitcher_mlb_id", "pitcher_mlb_id"),
        Index("idx_at_bat_batter_mlb_id", "batter_mlb_id"),
        Index("idx_at_bat_game_id", "game_id"),
        Index("idx_at_bat_game_mlb_id", "game_mlb_id"),
    )


class Pitch(Base):
    __tablename__ = "pitches"

    """
    Pitch Types
    - (AB,"Automatic Ball")
    - (CH,Changeup)
    - (CS,"Slow Curve")
    - (CU,Curveball)
    - (EP,Eephus)
    - (FA,Fastball)
    - (FC,Cutter)
    - (FF,"Four-Seam Fastball")
    - (FO,Forkball)
    - (FS,Splitter)
    - (FT,"Two-Seam Fastball")
    - (IN,"Intentional Ball")
    - (KC,"Knuckle Curve")
    - (KN,"Knuckle Ball")
    - (PO,Pitchout)
    - (SC,Screwball)
    - (SI,Sinker)
    - (SL,Slider)
    - (ST,Sweeper)
    - (SV,Slurve)

    Pitch Calls
    - (*B,"Ball In Dirt")
    - (B,Ball)
    - (C,"Called Strike")
    - (D,"In play, no out")
    - (E,"In play, run(s)")
    - (F,Foul)
    - (H,"Hit By Pitch")
    - (I,"Intent Ball")
    - (J,"In play, no out")
    - (L,"Foul Bunt")
    - (M,"Missed Bunt")
    - (O,"Foul Tip")
    - (P,Pitchout)
    - (Q,"Swinging Pitchout")
    - (R,"Foul Pitchout")
    - (S,"Swinging Strike")
    - (T,"Foul Tip")
    - (W,"Swinging Strike (Blocked)")
    - (X,"In play, out(s)")
    - (Y,"In play, out(s)")
    - (Z,"In play, run(s)")
    """

    id: Mapped[int] = Column(Integer, primary_key=True)
    pitch_index: Mapped[int] = Column(Integer, nullable=False)
    ball_count: Mapped[int] = Column(Integer, nullable=False)
    strike_count: Mapped[int] = Column(Integer, nullable=False)
    pitch_type_code: Mapped[str] = Column(String, nullable=True)
    pitch_type_description: Mapped[str] = Column(String, nullable=True)
    call_code: Mapped[str] = Column(String, nullable=False)
    call_description: Mapped[str] = Column(String, nullable=False)
    zone: Mapped[int] = Column(Integer, nullable=True)
    start_speed: Mapped[float] = Column(Float, nullable=True)
    is_ball: Mapped[bool] = Column(Boolean, nullable=False)
    is_strike: Mapped[bool] = Column(Boolean, nullable=False)
    is_foul: Mapped[bool] = Column(Boolean, nullable=False)
    is_out: Mapped[bool] = Column(Boolean, nullable=False)
    is_in_play: Mapped[bool] = Column(Boolean, nullable=False)
    r1b: Mapped[bool] = Column(Boolean, nullable=True)
    r2b: Mapped[bool] = Column(Boolean, nullable=True)
    r3b: Mapped[bool] = Column(Boolean, nullable=True)
    details: Mapped[dict] = Column(JSONB)

    # Relationships
    at_bat_id: Mapped[int] = Column(Integer, ForeignKey("at_bats.id"))
    at_bat: Mapped["AtBat"] = relationship("AtBat", foreign_keys=[at_bat_id])

    __table_args__ = (Index("idx_pitch_at_bat_id", "at_bat_id"),)
