# from enum import Enum
#
# # Define an Enum for Victory Status
# class VictoryStatus(Enum):
#     ABSENT = 0
#     UNDETERMINED = 1
#     SPECTATING = 2
#     LOSS = 3
#     WIN = 4
#     DEFEATED = 5


VICTORY_STATUS_ABSENT = 0
VICTORY_STATUS_UNDETERMINED = 1
VICTORY_STATUS_SPECTATING = 2
VICTORY_STATUS_LOSS = 3
VICTORY_STATUS_WIN = 4
VICTORY_STATUS_DEFEATED = 5

victory_status_dict = {
    VICTORY_STATUS_ABSENT: "Absent",
    VICTORY_STATUS_UNDETERMINED: "Playing",
    VICTORY_STATUS_SPECTATING: "Spec",
    VICTORY_STATUS_LOSS: "Loss",
    VICTORY_STATUS_WIN: "Win",
    VICTORY_STATUS_DEFEATED: "Defeat",  # Not necessarily loss
}


# Defined in "inc\dune2000.inc"
GES_ENDEDNORMALLY = 0
GES_ISURRENDERED = 1
GES_OPPONENTSURRENDERED = 2
GES_OUTOFSYNC = 3
GES_CONNECTIONLOST = 4
GES_WASHGAME = 5
GES_DRAWGAME = 6
GES_UNKNOWNENDSTATE = 7
DEFAULT_ENDSTATE = 8  # GameEndState (0x4DB9E0) default value

game_end_state_dict = {
    GES_ENDEDNORMALLY: "Ended normally",
    GES_ISURRENDERED: "I surrendered",
    GES_OPPONENTSURRENDERED: "Opponent surrendered",
    GES_OUTOFSYNC: "Out of sync",
    GES_CONNECTIONLOST: "Connection lost",
    GES_WASHGAME: "Wash game",
    GES_DRAWGAME: "Draw game",
    GES_UNKNOWNENDSTATE: "Unknown end state",
    DEFAULT_ENDSTATE: "No spawner default (8)",
}

color_idx_to_hex_string = {
    0: '#0000FF',
    1: '#FF0000',
    2: '#008080',
    3: "#800080",
    4: "#808080",
    5: "#A52A2A",
    6: "#FFD700",
    7: "#F4A460"
}

TEAM_INDEX_SPECTATOR = 9  # Team index of spectator player
TEAM_INDEX_NONE = 10  # Team index of absent player slot
