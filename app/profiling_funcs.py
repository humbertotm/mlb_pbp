import json
import adbc_driver_postgresql.dbapi as dbapi
import pandas as pd
from tabulate import tabulate

from app.scripts.constants import (
    BREAKING_PITCH_CODES,
    FASTBALL_PITCH_CODES,
    OFFSPEED_PITCH_CODES,
    OUTSIDE_STRIKEZONE_ZONES,
    STRIKEZONE_ZONES,
    SWUNG_AT_PITCH_CODES,
)


DB_URI = "postgresql://mlb_pbp:mlb_pbp@localhost:5432/mlb_pbp"


def get_pitcher_pitches(
    pitcher_id: int,
    sport_id: int = None,
    season: int = None,
    count: dict = None,
    options: dict = None,
) -> pd.DataFrame:
    """
    Get all pitches thrown by a pitcher. The set can be narrowed by providing
    - sport_id: The sport ID of the league
    - season: The season year
    - count: A dictionary with the ball and strike count
    - options: A dictionary with additional filters (Example: batter_hand, game_type)
    """

    pitches_query_template = """
    SELECT 
    p.*, 
    g.sport_id, 
    g.season, 
    g.game_type as game_type,
    ab.id as ab_id,
    ab.details as ab_details,
    batter.full_name as batter_name,
    pitcher.full_name as pitcher_name,
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

    # Start a DB connection using the adbc postgres driver for better perf
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
            game_type = options.get("game_type")
            if batter_hand:
                player_pitches_df = player_pitches_df[
                    player_pitches_df["batter_hand"] == batter_hand
                ]

            if game_type:
                player_pitches_df = player_pitches_df[
                    player_pitches_df["game_type"] == game_type
                ]

        return player_pitches_df


def get_batter_pitches(
    batter_id: int,
    sport_id: int = None,
    season: int = None,
    count: dict = None,
    options: dict = None,
) -> pd.DataFrame:
    """
    Get all pitches faced by a batter. The set can be narrowed by providing
    - sport_id: The sport ID of the league
    - season: The season year
    - count: A dictionary with the ball and strike count
    - options: A dictionary with additional filters (Example: pitcher_hand, game_type)
    """

    pitches_query_template = """
    SELECT 
    p.*, 
    g.sport_id, 
    g.season, 
    g.game_type as game_type,
    ab.details as ab_details,
    ab.id as ab_id,
    batter.details->'batSide'->>'code' as batter_hand,
    pitcher.details->'pitchHand'->>'code' as pitcher_hand,
    batter.full_name as batter_name,
    pitcher.full_name as pitcher_name,
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

    # Start a DB connection using the adbc postgres driver for better perf
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
            pitcher_hand = options.get("pitcher_hand")
            game_type = options.get("game_type")
            if pitcher_hand:
                player_pitches_df = player_pitches_df[
                    player_pitches_df["pitcher_hand"] == pitcher_hand
                ]

            if game_type:
                player_pitches_df = player_pitches_df[
                    player_pitches_df["game_type"] == game_type
                ]

        return player_pitches_df


def annotate_px_pz(row: pd.Series) -> pd.Series:
    """
    Extract the px and pz values for pitch location from the details column.
    px: Horizontal location of the pitch in feet. Negative values are on the catcher's left from the middle of the plate.
    pz: Vertical location of the pitch in feet. Negative values are below the low part of the strike zone.
    """
    details = json.loads(row["details"])
    px = details.get("pitchData", {}).get("coordinates", {}).get("pX")
    pz = details.get("pitchData", {}).get("coordinates", {}).get("pZ")

    return pd.Series({"px": px, "pz": pz})


def annotate_effective_batter_hand(row: pd.Series) -> str:
    """
    Get the effective batter hand.
    If a batter is a switch batter, the effective batter hand will be based on the pitcher's hand.
    """
    pitcher_hand = row["pitcher_hand"]
    batter_hand = row["batter_hand"]
    if batter_hand == "S":
        batter_hand = "R" if pitcher_hand == "L" else "L"

    return batter_hand


def annotate_is_chasing_pitch(row: pd.Series) -> bool:
    """
    Determine if a pitch is a chasing pitch.
    A chasing pitch is a pitch that is outside the strike zone and is at least 5 inches away from the edge of the strike zone.
    """
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
    """
    Determine the qualitative location of a pitch.
    It is any combination of I (Inside), O (Outside), U (Up), M (Middle), D (Down).
    This is based on the batter's handedness and the location of the pitch in the strike zone.
    """
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


def annotate_pitch_type(row: pd.Series) -> str:
    """
    Determine the type of pitch based on the pitch type code.
    The pitch types are classified as:
    - BREAKING: Curveball, Slider, Sweeper, etc.
    - OFFSPEED: Changeup, Eephus, etc.
    - FASTBALL: 4-Seam Fastball, 2-Seam Fastball, Cutter, etc.
    - UNKNOWN: Any other pitch type
    """
    pitch_type_code = row["pitch_type_code"]
    if pitch_type_code in BREAKING_PITCH_CODES:
        return "BREAKING"
    elif pitch_type_code in OFFSPEED_PITCH_CODES:
        return "OFFSPEED"
    elif pitch_type_code in FASTBALL_PITCH_CODES:
        return "FASTBALL"
    else:
        return "UNKNOWN"


# ************* PITCHER PROFILING FUNCTIONS *************


def get_in_sz_data(
    pitcher_id: int,
    sport_id: int = None,
    season: int = None,
    count: dict = None,
    options: dict = None,
) -> None:
    """
    Get in-zone pitch data for a pitcher.
    The data includes:
    - Pitch type breakdown
    - Location breakdown by pitch type
    - In-zone rate by pitch type
    - Usage rate by pitch type
    """
    # Get the dataframe with the data
    player_pitches_df = get_pitcher_pitches(
        pitcher_id, sport_id, season, count, options
    )

    pitcher_name = player_pitches_df.iloc[0]["pitcher_name"]

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
        player_pitches_df["zone"].isin(STRIKEZONE_ZONES)
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
    location_columns = in_sz_location_counts.columns.tolist()
    # Calculate the rate of each location
    for col in location_columns:
        grouped_by_pitch_type_df[col] = (
            (grouped_by_pitch_type_df[col] / grouped_by_pitch_type_df["in_sz_count"])
            * 100
        ).round(1)

    if options:
        print(
            f"IN-ZONE PITCH DATA VS {options.get("batter_hand")} FOR {pitcher_name}\n"
        )
    else:
        print(f"IN-ZONE PITCH DATA FOR {pitcher_name}\n")

    print(tabulate(grouped_by_pitch_type_df, headers="keys", tablefmt="github"))


def get_out_sz_data(
    pitcher_id: int,
    sport_id: int = None,
    season: int = None,
    count: dict = None,
    options: dict = None,
) -> None:
    """
    Get out-of-zone pitch data for a pitcher.
    The data includes:
    - Pitch type breakdown
    - Location breakdown by pitch type
    - Out-of-zone rate by pitch type
    - Usage rate by pitch type
    """
    # Get the dataframe with the data
    player_pitches_df = get_pitcher_pitches(
        pitcher_id, sport_id, season, count, options
    )

    pitcher_name = player_pitches_df.iloc[0]["pitcher_name"]

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
        player_pitches_df["zone"].isin(OUTSIDE_STRIKEZONE_ZONES)
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
        out_sz_pitches_df["is_chasing_pitch"] == True  # noqa: E712
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
    location_columns = out_sz_location_counts.columns.tolist()
    # Calculate the rate of each location
    for col in location_columns:
        grouped_by_pitch_type_df[col] = (
            (grouped_by_pitch_type_df[col] / grouped_by_pitch_type_df["out_sz_count"])
            * 100
        ).round(1)

    if options:
        print(
            f"OUT-OF-ZONE PITCH DATA VS {options.get("batter_hand")} FOR {pitcher_name}\n"
        )
    else:
        print(f"OUT-OF-ZONE PITCH DATA FOR {pitcher_name}\n")

    print(tabulate(grouped_by_pitch_type_df, headers="keys", tablefmt="github"))


def get_ab_breaking_ball_insights(
    pitcher_id: int,
    sport_id: int = None,
    season: int = None,
    include_ch: bool = False,
    options: dict = None,
) -> None:
    """
    Get insights on the in-zone usage of breaking balls by a pitcher.
    The idea is mostly to gauge the rate at which the pitcher throws two or more breaking balls in the strike zone in ABs with at least 3 pitches.
    """
    breaking_ball_in_sz_threshold = 2
    if options:
        breaking_ball_in_sz_threshold = options.get("breaking_ball_in_sz_threshold", 2)

    # Get the dataframe with the data
    player_pitches_df = get_pitcher_pitches(
        pitcher_id=pitcher_id, sport_id=sport_id, season=season, options=options
    )
    pitcher_name = player_pitches_df.iloc[0]["pitcher_name"]
    ab_counts = player_pitches_df["ab_id"].value_counts()
    # Get the ABs with at least 3 pitches
    abs_of_interest_ids = ab_counts[ab_counts >= 3].index
    abs_of_interest_count = len(abs_of_interest_ids)

    pitches_for_abs = player_pitches_df[
        player_pitches_df["ab_id"].isin(abs_of_interest_ids)
    ]

    pitch_type_codes = BREAKING_PITCH_CODES
    if include_ch:
        pitch_type_codes = OFFSPEED_PITCH_CODES

    breaking_pitches_for_abs = pitches_for_abs[
        pitches_for_abs["pitch_type_code"].isin(pitch_type_codes)
    ]
    breaking_pitches_in_sz = breaking_pitches_for_abs[
        breaking_pitches_for_abs["zone"].isin(STRIKEZONE_ZONES)
    ]
    breaking_pitches_in_sz_counts = (
        breaking_pitches_in_sz.groupby("ab_id").size().reset_index(name="in_sz_count")
    )
    valid_ab_ids = breaking_pitches_in_sz_counts[
        breaking_pitches_in_sz_counts["in_sz_count"] >= breaking_ball_in_sz_threshold
    ]
    count_of_valid_ab_ids = len(valid_ab_ids)

    breaking_pitch_dominant_rate = (count_of_valid_ab_ids / abs_of_interest_count) * 100
    print(
        f"Breaking Ball AB Dominance Rate for {pitcher_name}: {breaking_pitch_dominant_rate:.1f}%"
    )


# ************* BATTER PROFILING FUNCTIONS *************


def get_batter_chase_rate(
    batter_id: int,
    sport_id: int,
    season: int | None = None,
    count: dict | None = None,
    options: dict = {},
) -> None:
    """
    Get the chase rate for a batter.
    The chase rate is the percentage of pitches outside the strike zone that the batter swings at.
    Can be further narrowed down by considering only pitches that are >5in away from the strike zone.
    """
    # Get the dataframe with the data
    player_pitches_df = get_batter_pitches(batter_id, sport_id, season, count, options)
    batter_name = player_pitches_df.iloc[0]["batter_name"]

    # Drop rows with no call code
    player_pitches_df = player_pitches_df.dropna(subset=["call_code"])
    out_sz_pitches_df = player_pitches_df[
        player_pitches_df["zone"].isin(OUTSIDE_STRIKEZONE_ZONES)
    ]

    only_chasing_pitches = options.get("only_chasing_pitches", False)
    # If considering only pitches that are >5in away from the strike zone
    if only_chasing_pitches:
        out_sz_pitches_df.loc[:, ["px", "pz"]] = out_sz_pitches_df.apply(
            annotate_px_pz, axis=1
        )
        out_sz_pitches_df = out_sz_pitches_df.dropna(subset=["px", "pz"])
        out_sz_pitches_df["is_chasing_pitch"] = out_sz_pitches_df.apply(
            annotate_is_chasing_pitch, axis=1
        )
        out_sz_pitches_df = out_sz_pitches_df[
            out_sz_pitches_df["is_chasing_pitch"] == True  # noqa: E712
        ]

    chased_pitches_df = out_sz_pitches_df[
        out_sz_pitches_df["call_code"].isin(SWUNG_AT_PITCH_CODES)
    ]
    chased_pitches_count = len(chased_pitches_df)
    total_out_sz_pitches = len(out_sz_pitches_df)

    chase_rate = (chased_pitches_count / total_out_sz_pitches) * 100
    msg_str = f"Chashing Rate for {batter_name}"
    if only_chasing_pitches:
        msg_str = (
            f"Chasing Rate for {batter_name} on pitches >5in away from the strike zone"
        )
    print(f"{msg_str}: {chase_rate:.1f}%")


def get_batter_pitch_location_breakdown(
    batter_id: int,
    sport_id: int,
    season: int | None = None,
    count: dict | None = None,
    options: dict | None = None,
) -> None:
    """
    Get the pitch location breakdown for a batter.
    The breakdown includes the percentage of pitches in each location as well as the strike zone rate by pitch type.
    """
    # Get the dataframe with the data
    player_pitches_df = get_batter_pitches(batter_id, sport_id, season, count, options)
    batter_name = player_pitches_df.iloc[0]["batter_name"]
    # Drop rows with no call code
    player_pitches_df = player_pitches_df.dropna(subset=["pitch_type_code"])
    total_pitch_count = len(player_pitches_df)

    player_pitches_df["pitch_type"] = player_pitches_df.apply(
        annotate_pitch_type, axis=1
    )
    in_sz_pitches_df = player_pitches_df[
        player_pitches_df["zone"].isin(STRIKEZONE_ZONES)
    ]
    grouped_by_pitch_type_in_sz_df = (
        in_sz_pitches_df.groupby("pitch_type")
        .size()
        .reset_index(name="in_sz_pitch_type_count")
    )
    grouped_by_pitch_type_df = (
        player_pitches_df.groupby("pitch_type")
        .size()
        .reset_index(name="pitch_type_count")
    )
    grouped_by_pitch_type_base_df = grouped_by_pitch_type_df.merge(
        grouped_by_pitch_type_in_sz_df, on="pitch_type", how="left"
    )
    grouped_by_pitch_type_base_df = grouped_by_pitch_type_base_df.assign(
        pitch_type_in_sz_rate=(
            (
                grouped_by_pitch_type_base_df["in_sz_pitch_type_count"]
                / grouped_by_pitch_type_base_df["pitch_type_count"]
            )
            * 100
        ).round(1)
    )

    grouped_by_pitch_type_df["pitch_type_rate"] = (
        (grouped_by_pitch_type_df["pitch_type_count"] / total_pitch_count) * 100
    ).round(1)
    player_pitches_df.loc[:, ["px", "pz"]] = player_pitches_df.apply(
        annotate_px_pz, axis=1
    )
    player_pitches_df = player_pitches_df.dropna(subset=["px", "pz"])
    player_pitches_df["pitch_location"] = player_pitches_df.apply(
        annotate_pitch_location, axis=1
    )
    grouped_by_pitch_type_location_df = (
        player_pitches_df.groupby(["pitch_type", "pitch_location"])
        .size()
        .reset_index(name="pitch_type_location_count")
    )
    grouped_by_pitch_type_location_df = grouped_by_pitch_type_location_df.assign(
        pitch_type_location_rate=(
            (
                grouped_by_pitch_type_location_df["pitch_type_location_count"]
                / total_pitch_count
            )
            * 100
        ).round(1)
    )
    grouped_by_pitch_type_location_df = grouped_by_pitch_type_location_df.pivot(
        index="pitch_type", columns="pitch_location", values="pitch_type_location_rate"
    ).fillna(0)

    grouped_by_pitch_type_df = grouped_by_pitch_type_df.merge(
        grouped_by_pitch_type_location_df, on="pitch_type", how="left"
    )
    grouped_by_pitch_type_base_df = grouped_by_pitch_type_base_df.merge(
        grouped_by_pitch_type_df, on="pitch_type", how="left"
    )
    grouped_by_pitch_type_base_df = grouped_by_pitch_type_base_df.drop(
        columns=[
            "pitch_type_count_x",
            "in_sz_pitch_type_count",
            "pitch_type_count_y",
            "pitch_type_rate",
        ]
    )

    print(f"TOTAL PITCH COUNT FOR {batter_name}: {total_pitch_count}\n")
    print(tabulate(grouped_by_pitch_type_base_df, headers="keys", tablefmt="github"))
    print(
        "\n NOTE: BREAKDOWN DATA IN PERCENTAGE; LOCATION BREAKDOWN ACCOUNTS FOR BOTH IN AND OUT OF SZ PITCHES\n"
    )


def get_batter_first_strike_take_rate(
    batter_id: int,
    sport_id: int,
    season: int | None = None,
    options: dict | None = None,
) -> None:
    """
    Provides insight on how often a batter takes the first pitch in the strike zone during an AB.
    """
    # Get the dataframe with the data
    player_pitches_df = get_batter_pitches(
        batter_id=batter_id, sport_id=sport_id, season=season, options=options
    )
    # Get all first strike pitches
    first_strike_pitches_df = player_pitches_df[
        (player_pitches_df["strike_count"] == 0)
        & (player_pitches_df["zone"].isin(STRIKEZONE_ZONES))
    ]
    first_strike_pitch_count = len(first_strike_pitches_df)
    first_strike_swung_at_pitches_df = first_strike_pitches_df[
        first_strike_pitches_df["call_code"].isin(SWUNG_AT_PITCH_CODES)
    ]
    first_strike_swung_at_pitch_count = len(first_strike_swung_at_pitches_df)
    first_strike_pitch_take_count = (
        first_strike_pitch_count - first_strike_swung_at_pitch_count
    )

    first_strike_take_rate = (
        first_strike_pitch_take_count / first_strike_pitch_count
    ) * 100

    batter_name = player_pitches_df.iloc[0]["batter_name"]

    print(f"First Strike Take Rate for {batter_name}: {first_strike_take_rate:.1f}%")
