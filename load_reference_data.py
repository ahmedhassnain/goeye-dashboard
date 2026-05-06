# load_reference_data.py
from database import SessionLocal
from models.units import Unit
from models.applications import Application
from models.scopes import Scope
from models.scope_units import ScopeUnit
import csv

# Here, the approach is that we will load all this data into our application table.
# Session is passed externally because we want load_applications, load_scope_units and load_scopes to share the same session.
def load_applications(session):
    apps = [
        # Games
        {"file_key": "curr_among_us",               "app_name": "Among Us",                 "category": "Games"},
        {"file_key": "curr_apex_legends",            "app_name": "Apex Legends",             "category": "Games"},
        {"file_key": "curr_bfv",                     "app_name": "Battlefield V",            "category": "Games"},
        {"file_key": "curr_cod",                     "app_name": "Call of Duty",             "category": "Games"},
        {"file_key": "curr_counterstrike2",          "app_name": "Counter Strike 2",         "category": "Games"},
        {"file_key": "curr_diablo3",                 "app_name": "Diablo 3",                 "category": "Games"},
        {"file_key": "curr_diablo4",                 "app_name": "Diablo 4",                 "category": "Games"},
        {"file_key": "curr_dota2",                   "app_name": "Dota 2",                   "category": "Games"},
        {"file_key": "curr_efootball_2024",          "app_name": "eFootball 2024",           "category": "Games"},
        {"file_key": "curr_fc24",                    "app_name": "FC 24",                    "category": "Games"},
        {"file_key": "curr_fifa21",                  "app_name": "FIFA 21",                  "category": "Games"},
        {"file_key": "curr_fortnite",                "app_name": "Fortnite",                 "category": "Games"},
        {"file_key": "curr_free_fire_max",           "app_name": "Free Fire Max",            "category": "Games"},
        {"file_key": "curr_gears5",                  "app_name": "Gears 5",                  "category": "Games"},
        {"file_key": "curr_halo_infinite",           "app_name": "Halo Infinite",            "category": "Games"},
        {"file_key": "curr_hearthstone",             "app_name": "Hearthstone",              "category": "Games"},
        {"file_key": "curr_heroes_of_the_storm",     "app_name": "Heroes of the Storm",      "category": "Games"},
        {"file_key": "curr_honor_of_kings",          "app_name": "Honor of Kings",           "category": "Games"},
        {"file_key": "curr_league_of_legends",       "app_name": "League of Legends",        "category": "Games"},
        {"file_key": "curr_mobile_legends_bang_bang","app_name": "Mobile Legends Bang Bang",  "category": "Games"},
        {"file_key": "curr_overwatch",               "app_name": "Overwatch",                "category": "Games"},
        {"file_key": "curr_pubg",                    "app_name": "PUBG",                     "category": "Games"},
        {"file_key": "curr_pubg_mobile",             "app_name": "PUBG Mobile",              "category": "Games"},
        {"file_key": "curr_rainbow_six_siege",       "app_name": "Rainbow Six Siege",        "category": "Games"},
        {"file_key": "curr_roblox",                  "app_name": "Roblox",                   "category": "Games"},
        {"file_key": "curr_rocket_league",           "app_name": "Rocket League",            "category": "Games"},
        {"file_key": "curr_starcraft2",              "app_name": "Starcraft 2",              "category": "Games"},
        {"file_key": "curr_valorant",                "app_name": "Valorant",                 "category": "Games"},
        {"file_key": "curr_world_of_warcraft",       "app_name": "World of Warcraft",        "category": "Games"},
        # Social Media
        {"file_key": "curr_social_media",            "app_name": "Social Media",             "category": "Social Media"},
        # Video Conferencing
        {"file_key": "curr_video_conferencing",      "app_name": "Video Conferencing",       "category": "Video Conferencing"},
    ]
    for app in apps:
    # Application - the application table.
        application = Application(
            file_key = app["file_key"],
            app_name = app["app_name"],
            category = app["category"]
        )
    # session.add() - used for tracking new objects
    # This means that this object would get into the identity map of the session.
    # It would only get inserted when we run session.commit()
        session.add(application)
    print(f"Queued {len(apps)} applications.")

def load_scopes(session):
    scopes = [
        {
            "scope_name":        "GO/FTTH",
            "operator_filter":   "GO",
            "technology_filter": "FTTH"
        },
        {
            "scope_name":        "GO/B2B",
            "operator_filter":   "GO",
            "technology_filter": "B2B"
        },
        {
            "scope_name":        "KSA Average",
            "operator_filter":   "STC,Mobily",
            "technology_filter": "FTTH"
        },
    ]

    for scope in scopes:
        s = Scope(
            scope_name        = scope["scope_name"],
            operator_filter   = scope["operator_filter"],
            technology_filter = scope["technology_filter"]
        )
        session.add(s)
    print(f"Queued {len(scopes)} scopes.")

# This is only to be called once the previous two have been flushed.
# Why? Because scope has IDs that are automatically generated. This function calls those IDS at the end, and our approach is we want all three to be committed from the session at the same time.
# What this function does: Inserts data for the Junction table called scope_units.
def load_scope_units(session):
    # Here we query the table Scope and get all the rows.
    # Our options: GO/FTTH, GO/B2B, STC/Mobily
    scopes = session.query(Scope).all()
    for scope in scopes:
        # scope.operator_filter.split(",") - takes any operator_filter from scope table and splits it by comma
        # o.strip() removes any whitespaces in surrounding.
        # [] would help us return a list again.
        operators = [o.strip() for o in scope.operator_filter.split(",")]
        matching_units = session.query(Unit).filter(
            Unit.operator.in_(operators),
            Unit.technology == scope.technology_filter,
            Unit.is_active == True
        ).all()
        # .all() Returns the result of matching_units in a Python List.
        for unit in matching_units:
        # This is where we feed data into the Junction Table.
            su = ScopeUnit(
                scope_id=scope.id,
                unit_id=unit.unit_id
            )
            session.add(su)

        print(f"Scope '{scope.scope_name}': {len(matching_units)} units assigned.")
# This is unit_name sorting out function called in load_units.
def parse_unit_name(unit_name):
    if not unit_name or unit_name.strip() == "-":
        return None, None, None
    parts = unit_name.strip().split("/")
    operator   = parts[0] if len(parts) > 0 else None
    technology = parts[1] if len(parts) > 1 else None
    identifier = "/".join(parts[2:]) if len(parts) > 2 else None
    return operator, technology, identifier

def load_units(filepath):
    session = SessionLocal()
    try:
        with open(filepath, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                unit_name = row["Unit Name"].strip()
                operator, technology, identifier = parse_unit_name(unit_name)
                is_active = unit_name != "-"
                unit = Unit(
                    unit_id    = int(row["unit_id"]),
                    mac        = row["mac"].strip(),
                    unit_name  = unit_name,
                    operator   = operator,
                    technology = technology,
                    identifier = identifier,
                    is_active  = is_active
                )
                session.add(unit)
        session.commit()
        print("Units loaded successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error loading units: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    # Step 1 - units loaded in their own session first
    load_units(r"Units_Data.csv")  # place Units_Data.csv in the project root before running

    # Steps 2, 3, 4 - share one session so they commit together
    session = SessionLocal()
    try:
        load_applications(session)
        load_scopes(session)

        # Must flush before load_scope_units so scope IDs exist in DB
        # even before final commit
        session.flush()

        load_scope_units(session)
        session.commit()
        print("All reference data loaded successfully.")
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()