# Start a DB connection using the adbc postgres driver for better perf
import json
import adbc_driver_postgresql.dbapi as dbapi
import pandas as pd
from tabulate import tabulate


DB_URI = "postgresql://mlb_pbp:mlb_pbp@localhost:5432/mlb_pbp"


def get_pitcher_pitches(
    pitcher_id: int,
    sport_id: int = None,
    season: int = None,
    count: dict = None,
    options: dict = None,
) -> pd.DataFrame:
    pitches_query_template = """
    SELECT 
    p.*, 
    g.sport_id, 
    g.season, 
    ab.details as ab_details,
    batter.details->'batSide'->>'code' as batter_hand,
    pitcher.details->'pitchHand'->>'code' as pitcher_hand,
    batter.details->'strikeZoneTop' as batter_sz_top,
    batter.details->'strikeZoneBottom' as batter_sz_bottom
    FROM pitches p
    JOIN at_bats ab ON p.at_bat_id = ab.id
    JOIN games g ON ab.game_id = g.id
    JOIN players batter ON ab.batter_id = batter.id
    JOIN players pitcher ON ab.pitcher_id = pitcher.id
    WHERE ab.pitcher_id = {pitcher_id}
    """

    pitches_query = pitches_query_template.format(pitcher_id=pitcher_id)

    with dbapi.connect(DB_URI) as conn:
        player_pitches_df = pd.read_sql_query(pitches_query, conn, index_col="id")
        player_pitches_df["batter_hand"] = player_pitches_df.apply(
            annotate_effective_batter_hand, axis=1
        )

        if sport_id:
            player_pitches_df = player_pitches_df[
                player_pitches_df["sport_id"] == sport_id
            ]

        if season:
            player_pitches_df = player_pitches_df[player_pitches_df["season"] == season]

        if count:
            if "ball_count" in count:
                player_pitches_df = player_pitches_df[
                    player_pitches_df["ball_count"] == count["ball_count"]
                ]

            if "strike_count" in count:
                player_pitches_df = player_pitches_df[
                    player_pitches_df["strike_count"] == count["strike_count"]
                ]

        if options:
            batter_hand = options.get("batter_hand")
            if batter_hand:
                player_pitches_df = player_pitches_df[
                    player_pitches_df["batter_hand"] == batter_hand
                ]

        return player_pitches_df


def get_batter_pitches(
    batter_id: int, sport_id: int = None, season: int = None, count: dict = None
) -> pd.DataFrame:
    pitches_query_template = """
    SELECT 
    p.*, 
    g.sport_id, 
    g.season, 
    ab.details as ab_details,
    batter.details->'batSide'->>'code' as batter_hand,
    pitcher.details->'pitchHand'->>'code' as pitcher_hand,
    batter.details->'strikeZoneTop' as batter_sz_top,
    batter.details->'strikeZoneBottom' as batter_sz_bottom
    FROM pitches p
    JOIN at_bats ab ON p.at_bat_id = ab.id
    JOIN games g ON ab.game_id = g.id
    JOIN players batter ON ab.batter_id = batter.id
    JOIN players pitcher ON ab.pitcher_id = pitcher.id
    WHERE ab.batter_id = {batter_id}
    """

    pitches_query = pitches_query_template.format(batter_id=batter_id)

    with dbapi.connect(DB_URI) as conn:
        player_pitches_df = pd.read_sql_query(pitches_query, conn, index_col="id")
        if sport_id:
            player_pitches_df = player_pitches_df[
                player_pitches_df["sport_id"] == sport_id
            ]

        if season:
            player_pitches_df = player_pitches_df[player_pitches_df["season"] == season]

        if count:
            if "ball_count" in count:
                player_pitches_df = player_pitches_df[
                    player_pitches_df["ball_count"] == count["ball_count"]
                ]

            if "strike_count" in count:
                player_pitches_df = player_pitches_df[
                    player_pitches_df["strike_count"] == count["strike_count"]
                ]

        return player_pitches_df


def annotate_px_pz(row: pd.Series) -> pd.Series:
    details = json.loads(row["details"])
    px = details.get("pitchData", {}).get("coordinates", {}).get("pX")
    pz = details.get("pitchData", {}).get("coordinates", {}).get("pZ")

    return pd.Series({"px": px, "pz": pz})


def annotate_effective_batter_hand(row: pd.Series) -> str:
    pitcher_hand = row["pitcher_hand"]
    batter_hand = row["batter_hand"]
    if batter_hand == "S":
        batter_hand = "R" if pitcher_hand == "L" else "L"

    return batter_hand


def annotate_is_chasing_pitch(row: pd.Series) -> bool:
    px = float(row["px"])
    pz = float(row["pz"])
    zone = int(row["zone"])
    sz_bottom = float(row["batter_sz_bottom"])
    sz_top = float(row["batter_sz_top"])

    if zone >= 1 and zone <= 9:
        return False

    # From the catcher's perspective
    bottom_threshold = sz_bottom - 0.42
    top_threshold = sz_top + 0.42
    left_threshold = -1.12
    right_threshold = 1.12

    is_chasing_pitch = False

    if (
        px < left_threshold
        or px > right_threshold
        or pz < bottom_threshold
        or pz > top_threshold
    ):
        is_chasing_pitch = True

    return is_chasing_pitch


def annotate_pitch_location(row: pd.Series) -> str:
    pitch_location = []
    batter_hand = row["batter_hand"]
    sz_bottom = float(row["batter_sz_bottom"])
    sz_top = float(row["batter_sz_top"])
    sz_height = sz_top - sz_bottom
    sz_band_height = sz_height / 3
    zone = int(row["zone"])

    # Pitches in the strike zone
    if zone >= 1 and zone <= 9:
        if zone in [1, 4, 7]:
            pitch_location.append("I") if batter_hand == "R" else pitch_location.append(
                "O"
            )

            if zone in [1]:
                pitch_location.append("U")
            if zone in [4]:
                pitch_location.append("M")
            if zone in [7]:
                pitch_location.append("D")

        if zone in [2, 5, 8]:
            pitch_location.append("M")

            if zone in [2]:
                pitch_location.append("U")
            if zone in [5]:
                pitch_location.append("M")
            if zone in [8]:
                pitch_location.append("D")

        if zone in [3, 6, 9]:
            pitch_location.append("O") if batter_hand == "R" else pitch_location.append(
                "I"
            )

            if zone in [3]:
                pitch_location.append("U")
            if zone in [6]:
                pitch_location.append("M")
            if zone in [9]:
                pitch_location.append("D")

    # Pitches outside the strike zone
    else:
        # All these are measured in feet since px and pz are in feet
        up_threshold = sz_top - sz_band_height
        down_threshold = sz_bottom + sz_band_height
        inside_threshold = -0.25 if batter_hand == "R" else 0.25
        outside_threshold = 0.25 if batter_hand == "R" else -0.25
        px = float(row["px"])
        pz = float(row["pz"])

        if batter_hand == "R":
            if px >= outside_threshold:
                pitch_location.append("O")
            elif px <= inside_threshold:
                pitch_location.append("I")
            else:
                pitch_location.append("M")
        else:
            if px <= outside_threshold:
                pitch_location.append("O")
            elif px >= inside_threshold:
                pitch_location.append("I")
            else:
                pitch_location.append("M")

        if pz >= up_threshold:
            pitch_location.append("U")
        elif pz <= down_threshold:
            pitch_location.append("D")
        else:
            pitch_location.append("M")

    return "".join(pitch_location)


def get_in_sz_data(
    pitcher_id: int,
    sport_id: int = None,
    season: int = None,
    count: dict = None,
    options: dict = None,
) -> None:
    # Get the dataframe with the data
    player_pitches_df = get_pitcher_pitches(
        pitcher_id, sport_id, season, count, options
    )

    # Process the dataframe
    player_pitches_df = player_pitches_df.dropna(subset=["start_speed"])
    total_pitch_count = len(player_pitches_df)
    # Group by pitch type
    grouped_by_pitch_type_df = (
        player_pitches_df.groupby("pitch_type_code")
        .agg(
            count=("pitch_type_code", "size"),
            avg_speed=("start_speed", "mean"),
        )
        .reset_index()
    )
    # Get sz pitch dataframe and get the by pitch type counts
    in_sz_pitches_df = player_pitches_df[
        player_pitches_df["zone"].isin([1, 2, 3, 4, 5, 6, 7, 8, 9])
    ]
    # .loc[] requires the assigned series to have named indices
    in_sz_pitches_df.loc[:, ["px", "pz"]] = in_sz_pitches_df.apply(
        annotate_px_pz, axis=1
    )
    in_sz_pitches_df = in_sz_pitches_df.dropna(subset=["px", "pz"])
    in_sz_pitches_df["pitch_location"] = in_sz_pitches_df.apply(
        annotate_pitch_location, axis=1
    )
    in_sz_counts = (
        in_sz_pitches_df.groupby("pitch_type_code")
        .size()
        .reset_index(name="in_sz_count")
    )
    # Merge in_sz_counts with the base dataframe
    grouped_by_pitch_type_df = grouped_by_pitch_type_df.merge(
        in_sz_counts, on="pitch_type_code", how="left"
    )
    # Calculate in-zone rate
    grouped_by_pitch_type_df["in_sz_rate"] = (
        (
            grouped_by_pitch_type_df["in_sz_count"] / grouped_by_pitch_type_df["count"]
        ).fillna(0)
        * 100
    ).round(1)
    # Add Usage Rate column and average speed per pitch type
    grouped_by_pitch_type_df["usage_rate"] = (
        (grouped_by_pitch_type_df["count"] / total_pitch_count) * 100
    ).round(1)
    grouped_by_pitch_type_df["avg_speed"] = grouped_by_pitch_type_df["avg_speed"].round(
        1
    )

    # Add in-zone pitch location breakdown
    in_sz_location_counts = (
        in_sz_pitches_df.groupby(["pitch_type_code", "pitch_location"])
        .size()
        .reset_index(name="in_sz_location_count")
    )
    in_sz_location_counts = in_sz_location_counts.pivot(
        index="pitch_type_code", columns="pitch_location", values="in_sz_location_count"
    ).fillna(0)

    # Merge in_sz_location_counts with the base dataframe
    grouped_by_pitch_type_df = grouped_by_pitch_type_df.merge(
        in_sz_location_counts, on="pitch_type_code", how="left"
    )
    location_columns = ["ID", "IM", "IU", "MD", "MM", "MU", "OD", "OM", "OU"]
    # Calculate the rate of each location
    for col in location_columns:
        grouped_by_pitch_type_df[col] = (
            (grouped_by_pitch_type_df[col] / grouped_by_pitch_type_df["in_sz_count"])
            * 100
        ).round(1)

    if options:
        print(f"IN-ZONE PITCH DATA VS {options.get("batter_hand")}\n")
    else:
        print("IN-ZONE PITCH DATA\n")

    print(tabulate(grouped_by_pitch_type_df, headers="keys", tablefmt="github"))


def get_out_sz_data(
    pitcher_id: int,
    sport_id: int = None,
    season: int = None,
    count: dict = None,
    options: dict = None,
) -> None:
    # Get the dataframe with the data
    player_pitches_df = get_pitcher_pitches(
        pitcher_id, sport_id, season, count, options
    )

    # Process the dataframe
    player_pitches_df = player_pitches_df.dropna(subset=["start_speed"])
    total_pitch_count = len(player_pitches_df)
    # Group by pitch type
    grouped_by_pitch_type_df = (
        player_pitches_df.groupby("pitch_type_code")
        .agg(
            count=("pitch_type_code", "size"),
            avg_speed=("start_speed", "mean"),
        )
        .reset_index()
    )
    # Get sz pitch dataframe and get the by pitch type counts
    out_sz_pitches_df = player_pitches_df[
        player_pitches_df["zone"].isin([11, 12, 13, 14])
    ]
    # .loc[] requires the assigned series to have named indices
    out_sz_pitches_df.loc[:, ["px", "pz"]] = out_sz_pitches_df.apply(
        annotate_px_pz, axis=1
    )
    out_sz_pitches_df = out_sz_pitches_df.dropna(subset=["px", "pz"])
    out_sz_pitches_df["pitch_location"] = out_sz_pitches_df.apply(
        annotate_pitch_location, axis=1
    )
    out_sz_pitches_df["is_chasing_pitch"] = out_sz_pitches_df.apply(
        annotate_is_chasing_pitch, axis=1
    )
    out_sz_counts = (
        out_sz_pitches_df.groupby("pitch_type_code")
        .size()
        .reset_index(name="out_sz_count")
    )
    # Merge out_sz_counts with the base dataframe
    grouped_by_pitch_type_df = grouped_by_pitch_type_df.merge(
        out_sz_counts, on="pitch_type_code", how="left"
    )
    # Calculate in-zone rate
    grouped_by_pitch_type_df["out_sz_rate"] = (
        (
            grouped_by_pitch_type_df["out_sz_count"] / grouped_by_pitch_type_df["count"]
        ).fillna(0)
        * 100
    ).round(1)
    # Add Usage Rate column and average speed per pitch type
    grouped_by_pitch_type_df["usage_rate"] = (
        (grouped_by_pitch_type_df["count"] / total_pitch_count) * 100
    ).round(1)
    grouped_by_pitch_type_df["avg_speed"] = grouped_by_pitch_type_df["avg_speed"].round(
        1
    )

    # Calculate chasing rate
    chasing_pitches_df = out_sz_pitches_df[
        out_sz_pitches_df["is_chasing_pitch"] == True
    ]
    chasing_counts = (
        chasing_pitches_df.groupby("pitch_type_code")
        .size()
        .reset_index(name="chasing_count")
    )
    grouped_by_pitch_type_df = grouped_by_pitch_type_df.merge(
        chasing_counts, on="pitch_type_code", how="left"
    )
    grouped_by_pitch_type_df["chasing_rate"] = (
        (
            grouped_by_pitch_type_df["chasing_count"]
            / grouped_by_pitch_type_df["out_sz_count"]
        ).fillna(0)
        * 100
    ).round(1)
    grouped_by_pitch_type_df = grouped_by_pitch_type_df.drop(columns=["chasing_count"])

    # Add in-zone pitch location breakdown
    out_sz_location_counts = (
        out_sz_pitches_df.groupby(["pitch_type_code", "pitch_location"])
        .size()
        .reset_index(name="out_sz_location_count")
    )
    out_sz_location_counts = out_sz_location_counts.pivot(
        index="pitch_type_code",
        columns="pitch_location",
        values="out_sz_location_count",
    ).fillna(0)

    # Merge in_sz_location_counts with the base dataframe
    grouped_by_pitch_type_df = grouped_by_pitch_type_df.merge(
        out_sz_location_counts, on="pitch_type_code", how="left"
    )
    location_columns = ["ID", "IM", "IU", "MD", "MU", "OD", "OM", "OU"]
    # Calculate the rate of each location
    for col in location_columns:
        grouped_by_pitch_type_df[col] = (
            (grouped_by_pitch_type_df[col] / grouped_by_pitch_type_df["out_sz_count"])
            * 100
        ).round(1)

    if options:
        print(f"OUT-OF-ZONE PITCH DATA VS {options.get("batter_hand")}\n")
    else:
        print("OUT-OF-ZONE PITCH DATA\n")

    print(tabulate(grouped_by_pitch_type_df, headers="keys", tablefmt="github"))
