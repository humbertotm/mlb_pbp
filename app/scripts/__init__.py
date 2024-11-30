from sqlalchemy import create_engine


db_engine = create_engine("postgresql://mlb_pbp:mlb_pbp@localhost:5432/mlb_pbp")
