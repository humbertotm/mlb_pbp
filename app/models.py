from datetime import date
from typing import List
from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, Index, Integer, String

from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB


Base = declarative_base()


class Player(Base):
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


class Team(Base):
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


class Game(Base):
    __tablename__ = "games"

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
    )


class AtBatDetails(Base):
    __tablename__ = "at_bat_details"

    id: Mapped[int] = Column(Integer, primary_key=True)
    game_mlb_id: Mapped[int] = Column(Integer, ForeignKey("games.mlb_id"))
    sport_id: Mapped[int] = Column(Integer, nullable=True)
    season: Mapped[int] = Column(Integer, nullable=False)
    details: Mapped[dict] = Column(JSONB)


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
    )


class Pitch(Base):
    __tablename__ = "pitches"

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
