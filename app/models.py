from datetime import date
from typing import List
from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, Integer, String

from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB


Base = declarative_base()


class Player(Base):
    __tablename__ = "players"

    # [TODO] Fix relationships based on this piece of documentation:
    # https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html#setting-bi-directional-many-to-many
    id: Mapped[int] = Column(Integer, primary_key=True)
    mlb_id: Mapped[int] = Column(Integer, nullable=False, unique=True)
    full_name: Mapped[str] = Column(String, nullable=False)
    is_player: Mapped[bool] = Column(Boolean, nullable=False)
    throws: Mapped[str] = Column(String, nullable=True)
    bats: Mapped[str] = Column(String, nullable=True)
    birth_date: Mapped[date] = Column(Date)
    primary_position_code: Mapped[str] = Column(String)
    primary_position: Mapped[str] = Column(String)
    active: Mapped[bool] = Column(Boolean)
    mlb_debut_date: Mapped[date] = Column(Date, nullable=True)
    last_played_date: Mapped[date] = Column(Date, nullable=True)
    details: Mapped[dict] = Column(JSONB)
    # To be filled later upon player enrichment
    # batter_type: Mapped[int] = Column(Integer, nullable=True)

    # Relationships
    # at_bats: Mapped[List["AtBat"]] = relationship("AtBat", back_populates="AtBat.batter")
    # at_bats: Mapped[List["AtBat"]] = relationship(
    #     secondary=association_table, back_populates="AtBat.batter"
    # )
    # pitched_at_bats: Mapped[List["AtBat"]] = relationship(
    #     "AtBat", back_populates="AtBat.pitcher"
    # )
    # pitched_at_bats: Mapped[List["AtBat"]] = relationship(
    #     secondary=association_table, back_populates="AtBat.pitcher",
    # )


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
    # at_bats: Mapped[List["AtBat"]] = relationship(back_populates="AtBat.game")


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
    mlb_id: Mapped[int] = Column(Integer, nullable=False, unique=True)
    sport_id: Mapped[int] = Column(Integer, nullable=True)
    call: Mapped[str] = Column(String, nullable=False)
    score_before_at_bat: Mapped[int] = Column(Integer, nullable=False)
    score_after_at_bat: Mapped[int] = Column(Integer, nullable=False)
    outs: Mapped[int] = Column(Integer, nullable=False)
    inning: Mapped[int] = Column(Integer, nullable=False)
    top: Mapped[bool] = Column(Boolean, nullable=False)
    r1b: Mapped[bool] = Column(Boolean, nullable=False)
    r2b: Mapped[bool] = Column(Boolean, nullable=False)
    r3b: Mapped[bool] = Column(Boolean, nullable=False)

    # Relationships
    game_id: Mapped[int] = Column(Integer, ForeignKey("games.id"))
    game: Mapped["Game"] = relationship("Game", foreign_keys=[game_id])
    pitcher_id: Mapped[int] = Column(Integer, ForeignKey("players.id"))
    pitcher: Mapped["Player"] = relationship("Player", foreign_keys=[pitcher_id])
    batter_id: Mapped[int] = Column(Integer, ForeignKey("players.id"))
    batter: Mapped["Player"] = relationship("Player", foreign_keys=[batter_id])
    # pitches: Mapped[List["Pitch"]] = relationship(back_populates="Pitch.at_bat")


class Pitch(Base):
    __tablename__ = "pitches"

    id: Mapped[int] = Column(Integer, primary_key=True)
    ball_count: Mapped[int] = Column(Integer, nullable=False)
    strike_count: Mapped[int] = Column(Integer, nullable=False)
    pitch_type_code: Mapped[str] = Column(String, nullable=False)
    pitch_type_description: Mapped[str] = Column(String, nullable=False)
    call_code: Mapped[str] = Column(String, nullable=False)
    call_description: Mapped[str] = Column(String, nullable=False)
    is_out: Mapped[bool] = Column(Boolean, nullable=False)
    start_speed: Mapped[float] = Column(Float, nullable=False)
    zone: Mapped[int] = Column(Integer, nullable=False)
    pitch_index: Mapped[int] = Column(Integer, nullable=False)
    r1b: Mapped[bool] = Column(Boolean, nullable=False)
    r2b: Mapped[bool] = Column(Boolean, nullable=False)
    r3b: Mapped[bool] = Column(Boolean, nullable=False)

    # Relationships
    at_bat_id: Mapped[int] = Column(Integer, ForeignKey("at_bats.id"))
    at_bat: Mapped["AtBat"] = relationship("AtBat", foreign_keys=[at_bat_id])
