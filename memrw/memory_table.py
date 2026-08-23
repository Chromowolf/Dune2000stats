from ctypes import c_int32, c_uint8, c_uint32
from dataclasses import dataclass

PLAYER_DATA_LENGTH = 0x26990  # CSide stride

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

# BUILDINGS_OWNING_TABLE = 0x7BCE30  # u8[104] for each player
BUILDINGS_EXIST_PER_GROUP = 0x7BCE31  # u8[100] for each player (current owned)
UNITS_EXIST_PER_TYPE = 0x7BCE98  # int32[60] for each player (current owned)

UNITS_OWNED_TABLE = 0x7BCFF8  # int32[60] for each player
BUILDINGS_OWNED_TABLE = 0x7BD0E8  # int32[100] for each player
TOTAL_BUILDINGS_LOST = 0x7BD27C
UNITS_LOST_TABLE = 0x7BD280  # int32[60] for each player
UNITS_KILLED_TABLE = 0x7BD508  # int32[60][8] for each player
BUILDINGS_KILLED_TABLE = 0x7BDC88  # int32[100][8] for each player

TOTAL_BUILDINGS_KILLED = 0x7BD504

ORIG_MAP_FILE_NAME = 0x6F9840

@dataclass(frozen=True)
class AddressPath:
    entry_point: int
    jumps: tuple
    default: int = 0


#############################
# Gruntmod variables
#############################

# Each jump is defined as:
#     (expected opcode, offset after following the jump/call)
#
# 0xE9 = jmp rel32
# 0xE8 = call rel32
#
# After the final jump/call and offset, the uint32 at that position is
# read as the absolute address of the target Gruntmod variable.

ADDRESS_PATHS = {
    # Spawner Map name (When SpawnerActive is True)
    # /src/spawner/stats.asm#L48 UseSpawnIniMapNameIfMapNotInStringTable
    "SPAWNER_MAP_NAME": AddressPath(
        entry_point=0x40D828,
        jumps=((0xE9, 30),),
        default=ORIG_MAP_FILE_NAME,
    ),

    # MapScript (equivalent to the map's hash)
    # /src/spawner/mission-events.asm#L43 LoadCustomOnlineMapScript
    "SPAWNER_MAP_SCRIPT": AddressPath(
        entry_point=0x4752FE,
        jumps=((0xE9, 10),),
        default=0,
    ),

    # SpawnerActive
    # /src/spawner/spawner.asm#L27 Spawner_Settings
    "SpawnerActive_ADDR": AddressPath(
        entry_point=0x45A942,
        jumps=((0xE9, 2),),
        default=0,
    ),

    # BUILDINGS_OWNED_TABLE_CNC
    # /src/spawner/stats.asm#L254 SaveBuildingsOwnedStats
    "BUILDINGS_OWNED_TABLE_CNC": AddressPath(
        entry_point=0x4563E5,
        jumps=((0xE9, 50),),
        default=0,
    ),

    # UNITS_OWNED_TABLE_CNC
    # /src/spawner/stats.asm#L226 SaveUnitOwnedStats
    "UNITS_OWNED_TABLE_CNC": AddressPath(
        entry_point=0x455938,
        jumps=((0xE9, 47),),
        default=0,
    ),

    # SpawnerGameEndState
    # /src/spawner/stats.asm#L154 UseSpawnerGameEndState
    "SpawnerGameEndState_ADDR": AddressPath(
        entry_point=0x40D8A0,
        jumps=((0xE9, 10),),
    ),

    # MeIsSpectator
    # /src/spawner/spectators.asm#L143 set bool Lose to true on game start
    "MeIsSpectator_ADDR": AddressPath(
        entry_point=0x44FC53,
        jumps=((0xE9, 20),),
    ),

    # Human info (NetPlayersExt), need to get the address of IsSpectator() function first
    # /src/spawner/spectators.asm#L83 SkipSpawningStartingUnitsForSpectators
    # The first offset 26 is where the "call IsSpectator" code is located,
    # starting from the byte "call".
    # After following that call, offset 2 arrives at the NetPlayersExt address.
    "NetPlayersExt_ADDR": AddressPath(
        # hack 0x00469ECD, 0x00469ED6 ; SkipSpawningStartingUnitsForSpectators:
        entry_point=0x469ECD,  # Superseded by Mod__setupmapstuff for version later than 2025-04-15
        jumps=((0xE9, 26), (0xE8, 2)),  # Superseded by Mod__setupmapstuff for version later than 2025-04-15
    ),

    # MCVDeployed, need 2 jumps
    # src/load-save-restart-exit.asm#L6 Skirmish/SinglePlayer load saved game function
    # The first offset 9 is where the "call LoadSavedGame" code is located,
    # starting from the byte "call".
    # After following that call, offset 9 arrives at the MCVDeployed address.
    "MCVDeployed_ADDR": AddressPath(
        entry_point=0x441CC5,
        jumps=((0xE9, 9), (0xE8, 9)),
    ),

    # StatsDmpBuffer, need 2 jumps, need to get the address of
    # WriteStatsDmp(const void *buffer, int length) function first
    # /src/spawner/stats.asm#L35 CallWriteStatsDmp
    # The first offset 3 is where the "call WriteStatsDmp" code is located,
    # starting from the byte "call".
    # After following that call, offset 47 arrives at the StatsDmpBuffer address.
    "StatsDmpBuffer_ADDR": AddressPath(
        entry_point=0x40DB75,
        jumps=((0xE9, 3), (0xE8, 47)),
    ),
}

def is_valid_jump_address(address: int) -> bool:
    if address < 0x8CF000 or address >= 0x1000000:
        return False
    return True

class MemoryAddresses:
    def __init__(self, handle=None):
        self._handle = handle

        # Addresses
        self.SPAWNER_MAP_NAME = ADDRESS_PATHS["SPAWNER_MAP_NAME"].default  # char[60], the MapName: gstring MapName, "", 60 in stats.asm
        self.SPAWNER_MAP_SCRIPT = ADDRESS_PATHS["SPAWNER_MAP_SCRIPT"].default  # char[128], the MapScript, defined in spawner-func.c
        self.SpawnerActive_ADDR = ADDRESS_PATHS["SpawnerActive_ADDR"].default  # Bool
        self.BUILDINGS_OWNED_TABLE_CNC = ADDRESS_PATHS["BUILDINGS_OWNED_TABLE_CNC"].default  # int32[8][62]
        self.UNITS_OWNED_TABLE_CNC = ADDRESS_PATHS["UNITS_OWNED_TABLE_CNC"].default  # int32[8][30]
        self.SpawnerGameEndState_ADDR = ADDRESS_PATHS["SpawnerGameEndState_ADDR"].default  # int32
        self.Actual_GameEndState_ADDR = GameEndState_ADDR  # Need to be modified based on whether SpawnActive
        self.MeIsSpectator_ADDR = ADDRESS_PATHS["MeIsSpectator_ADDR"].default  # bool

        self.MCVDeployed_ADDR = ADDRESS_PATHS["MCVDeployed_ADDR"].default  # bool[8], special
        self.NetPlayersExt_ADDR = ADDRESS_PATHS["NetPlayersExt_ADDR"].default  # Special: need to jump twice. 24-byte * 6
        self.StatsDmpBuffer_ADDR = ADDRESS_PATHS["StatsDmpBuffer_ADDR"].default  # Special: need to jump twice. static char StatsDmpBuffer[1024 * 20];

        self.resolution_errors = {}

        # dll
        self.effi_dll_base = 0  # effi.dll module base address

        if self._handle:
            self.initialize_addresses()

    def __bool__(self):
        return bool(self._handle)

    def set_handle(self, handle):
        self._handle = handle

    def set_effi_dll_base(self, addr):
        self.effi_dll_base = addr

    def get_effi_dll_base(self):
        return self.effi_dll_base

    def follow_jump(self, address, expected_opcode):
        """
        Applies to 1 byte machine code + 4 bytes signed relative offset:

            E9 XXXXXXXX    jmp rel32
            E8 XXXXXXXX    call rel32

        The opcode is manually verified before following the jump/call.
        """
        actual_opcode = self._handle.read_simple_data(address, c_uint8())
        if actual_opcode != expected_opcode:
            # Should print an error!!! Not Raise an error!
            # And why is the value error not shown????
            raise ValueError(
                f"Unexpected opcode at 0x{address:08X}: "
                f"expected 0x{expected_opcode:02X}, "
                f"found 0x{actual_opcode:02X}"
            )

        relative_offset = self._handle.read_simple_data(address + 1, c_int32())
        jump_to_address =  address + 5 + relative_offset
        if not is_valid_jump_address(jump_to_address):
            raise ValueError(
                f"Unexpected jump address at 0x{address:08X}."
            )
        return jump_to_address  # Do not put "& 0xFFFFFFFF" here yet

    def locate_address(self, path):
        """
        Follow all jumps/calls defined by an AddressPath, then read the
        uint32 absolute address of the target Gruntmod variable.

        For example, SpawnerActive is hacked by:

            hack 0x0045A942, 0x0045A94C ; Spawner_Settings
                cmp byte[SpawnerActive], 1
                jnz .out
                ...

        The path starts at 0x45A942, verifies and follows the E9 hook, then
        adds 2 because the address of SpawnerActive appears at +2 in the
        injected "cmp byte[SpawnerActive], 1" instruction.
        """
        address = path.entry_point

        for expected_opcode, offset in path.jumps:
            address = self.follow_jump(address, expected_opcode) + offset

        final_located_address = self._handle.read_simple_data(address, c_uint32())
        if not is_valid_jump_address(final_located_address):
            raise ValueError(f"Unexpected located address: 0x{final_located_address:08X}")
        return final_located_address

    def resolve_address(self, name):
        path = ADDRESS_PATHS[name]
        try:
            address = self.locate_address(path)
            if not address:
                raise ValueError("Resolved address is null")
        except (ValueError, OSError) as error:
            address = path.default
            self.resolution_errors[name] = str(error)
            print(
                f"Error obtaining address. name={name}, "
                f"entry_point=0x{path.entry_point:08X}, "
                f"default=0x{path.default:08X}, "
                f"error: {error}"
            )
        else:
            self.resolution_errors.pop(name, None)

        setattr(self, name, address)
        return address

    def initialize_addresses(self):
        # Every address is resolved independently. If a hack was removed,
        # overwritten, or changed, only that variable degrades to its default.
        self.resolution_errors.clear()

        for name in ADDRESS_PATHS:
            self.resolve_address(name)


mem = MemoryAddresses()
