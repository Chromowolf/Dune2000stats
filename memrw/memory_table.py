from ctypes import c_int32, c_uint32

PLAYER_DATA_LENGTH = 0x26990

GameEndState_ADDR = 0x4DB9E0

MULTI_SETTING_UNIT_COUNT = 0x4E3B00  # int32
MULTI_SETTING_TECH_LEVEL = 0x4E3B04  # int32
MULTI_SETTING_CREDITS = 0x4E3B08  # int32
MULTI_SETTING_AI_PLAYERS = 0x4E3B0C  # int32

HAS_BUILDING = 0x6B87C0  # bool[8]
HAS_UNIT = 0x6B8268  # bool[8]

LOCAL_PLAYER_NAME = 0x6B93F8

BUILDINGS_PROPERTY_DATA = 0x6DC540  # bytes[268][100]
UNITS_PROPERTY_DATA = 0x77E250  # bytes[256][60]

SCREEN_X_ADDR = 0x798538  # int32
SCREEN_Y_ADDR = 0x79853C  # int32

HUMAN_PLAYER_NAME = 0x798630  # Only available if number of human >= 1
# 0x96D080, 0x4F2898
HUMAN_PLAYER_NAME_SIZE = 60

NetPlayerCount_ADDR = 0x7984C0
NetworkGame = 0x7984C4  # Bool, is more than 1 human

UNIT_TABLE_HEAD_POINTER_ADDR = 0x798878  # pointer (u32)
BUILDING_TABLE_HEAD_POINTER_ADDR = 0x798880  # pointer (u32)

BUILDINGS_OWNING_TABLE = 0x7BCE30  # u8[104] for each player

UNITS_OWNED_TABLE = 0x7BCFF8  # u32[60] for each player
BUILDINGS_OWNED_TABLE = 0x7BD0E8  # u32[100] for each player
TOTAL_BUILDINGS_LOST = 0x7BD27C
UNITS_LOST_TABLE = 0x7BD280  # u32[60] for each player
UNITS_KILLED_TABLE = 0x7BD508  # u32[60][8] for each player

TOTAL_BUILDINGS_KILLED = 0x7BD504
#############################
# CNCnet
#############################
# CNC Map name
CNC_MAP_NAME_ENTRY_POINT = 0x40D828  # /src/spawner/stats.asm#L48 UseSpawnIniMapNameIfMapNotInStringTable
CNC_MAP_NAME_APPEAR_OFFSET = 30

# CNC Map hash (MapScript)
CNC_MAP_HASH_ENTRY_POINT = 0x4752FE  # /src/spawner/mission-events.asm#L43 LoadCustomOnlineMapScript
CNC_MAP_HASH_APPEAR_OFFSET = 10


# SpawnerActive
SpawnerActive_ENTRY_POINT = 0x45A942  # /src/spawner/spawner.asm#L27 Spawner_Settings
SpawnerActive_APPEAR_OFFSET = 2

# BUILDINGS_OWNED_TABLE_CNC
BuildingTracker_ENTRY_POINT = 0x4563E5  # /src/spawner/stats.asm#L254 SaveBuildingsOwnedStats
BuildingTracker_APPEAR_OFFSET = 50

# UNITS_OWNED_TABLE_CNC
UnitTracker_ENTRY_POINT = 0x455938  # /src/spawner/stats.asm#L226 SaveUnitOwnedStats
UnitTracker_APPEAR_OFFSET = 47

# SpawnerGameEndState
SpawnerGameEndState_ENTRY_POINT = 0x40D8A0  # /src/spawner/stats.asm#L154 UseSpawnerGameEndState
SpawnerGameEndState_APPEAR_OFFSET = 10

# MeIsSpectator
MeIsSpectator_ENTRY_POINT = 0x44FC53  # /src/spawner/spectators.asm#L143 set bool Lose to true on game start
MeIsSpectator_APPEAR_OFFSET = 20

# Human info (NetPlayersExt), need to get the address of IsSpectator() function first
IsSpectator_ENTRY_POINT = 0x469ECD  # /src/spawner/spectators.asm#L83 SkipSpawningStartingUnitsForSpectators
IsSpectator_APPEAR_OFFSET = 26  # Where the "call IsSpectator" code is located, starting from the byte "call"
NetPlayersExt_APPEAR_OFFSET = 2

# MCVDeployed, need 2 jumps
LoadSavedGame_ENTRY_POINT = 0x441CC5  # src/load-save-restart-exit.asm#L6 Skirmish/SinglePlayer load saved game function
LoadSavedGame_APPEAR_OFFSET = 9  # Where the "call LoadSavedGame" code is located, starting from the byte "call"
MCVDeployed_APPEAR_OFFSET = 9

# StatsDmpBuffer, need 2 jumps, need to get the address of WriteStatsDmp(const void *buffer, int length) function first
CallWriteStatsDmp_ENTRY_POINT = 0x40DB75  # /src/spawner/stats.asm#L35 CallWriteStatsDmp
WriteStatsDmp_APPEAR_OFFSET = 3  # Where the "call WriteStatsDmp" code is located, starting from the byte "call"
StatsDmpBuffer_APPEAR_OFFSET = 47

class MemoryAddresses:
    def __init__(self, handle=None):
        self._handle = handle

        # Addresses
        self.CNC_MAP_NAME = 0  # char[60]
        self.CNC_MAP_HASH = 0  # char[50] ?
        self.SpawnerActive_ADDR = 0  # Bool
        self.BUILDINGS_OWNED_TABLE_CNC = 0  # u32[8][62]
        self.UNITS_OWNED_TABLE_CNC = 0  # u32[8]
        self.SpawnerGameEndState_ADDR = 0  # int32
        self.Actual_GameEndState_ADDR = GameEndState_ADDR  # Need to be modified based on whether SpawnActive
        self.MeIsSpectator_ADDR = 0  # bool

        self.MCVDeployed_ADDR = 0  # bool[8], special
        self.NetPlayersExt_ADDR = 0  # Special: need to jump twice. 24-byte * 6
        self.StatsDmpBuffer_ADDR = 0  # Special: need to jump twice. static char StatsDmpBuffer[1024 * 20];
        if self._handle:
            self.initialize_addresses()

    def __bool__(self):
        return bool(self._handle)

    def set_handle(self, handle):
        self._handle = handle

    def initialize_addresses(self):
        self.CNC_MAP_NAME = self.locate_address(CNC_MAP_NAME_ENTRY_POINT, CNC_MAP_NAME_APPEAR_OFFSET)
        self.CNC_MAP_HASH = self.locate_address(CNC_MAP_HASH_ENTRY_POINT, CNC_MAP_HASH_APPEAR_OFFSET)
        self.SpawnerActive_ADDR = self.locate_address(SpawnerActive_ENTRY_POINT, SpawnerActive_APPEAR_OFFSET)
        self.BUILDINGS_OWNED_TABLE_CNC = self.locate_address(BuildingTracker_ENTRY_POINT, BuildingTracker_APPEAR_OFFSET)
        self.UNITS_OWNED_TABLE_CNC = self.locate_address(UnitTracker_ENTRY_POINT, UnitTracker_APPEAR_OFFSET)
        self.SpawnerGameEndState_ADDR = self.locate_address(SpawnerGameEndState_ENTRY_POINT, SpawnerGameEndState_APPEAR_OFFSET)
        self.MeIsSpectator_ADDR = self.locate_address(MeIsSpectator_ENTRY_POINT, MeIsSpectator_APPEAR_OFFSET)

        # NetPlayersExt_ADDR is special:
        NetPlayersExt_ENTRY_POINT = self.jump_from_address(IsSpectator_ENTRY_POINT) + IsSpectator_APPEAR_OFFSET
        self.NetPlayersExt_ADDR = self.locate_address(NetPlayersExt_ENTRY_POINT, NetPlayersExt_APPEAR_OFFSET)

        # MCVDeployed is special:
        MCVDeployed_ENTRY_POINT = self.jump_from_address(LoadSavedGame_ENTRY_POINT) + LoadSavedGame_APPEAR_OFFSET
        self.MCVDeployed_ADDR = self.locate_address(MCVDeployed_ENTRY_POINT, MCVDeployed_APPEAR_OFFSET)

        # StatsDmpBuffer_ADDR is special:
        WriteStatsDmp_ENTRY_POINT = self.jump_from_address(CallWriteStatsDmp_ENTRY_POINT) + WriteStatsDmp_APPEAR_OFFSET
        self.StatsDmpBuffer_ADDR = self.locate_address(WriteStatsDmp_ENTRY_POINT, StatsDmpBuffer_APPEAR_OFFSET)

    def jump_from_address(self, entry_point):
        """
        Applies to 1 byte machine code + 4 bytes jump offset
        jmp XXXXXXXX
        call XXXXXXXX
        :param entry_point:
        :return: The destination address
        """
        return self._handle.read_simple_data(entry_point + 1, c_int32()) + entry_point + 5

    def locate_address(self, hack_entry_point, offset, default=0x000000):
        """
        For example, to locate the address of SpawnerActive. We assume it's hacked by the following:
            hack 0x0045A942, 0x0045A94C ; Spawner_Settings
            cmp byte[SpawnerActive], 1
            jnz .out
            ...
        So, hack_entry_point is 0x45A942
        offset is 2, because the "cmp" takes 2 bytes. So the real address of SpawnerActive appears at +2 of the function Spawner_Settings

        :param hack_entry_point:
        :param offset:
        :param default: default address
        :return: The memory address of the target variable
        """
        jmp_to = self.jump_from_address(hack_entry_point)
        try:
            addr = self._handle.read_simple_data(jmp_to + offset, c_uint32())
        except ValueError as e:
            print(f"Error obtaining address. hack_entry_point=0x{hack_entry_point:08X}, jump_to_read_result=0x{jmp_to:08X}, offset=0x{offset:08X},\n"
                  f"Error message: {e}")
            addr = default
        return addr


mem = MemoryAddresses()
