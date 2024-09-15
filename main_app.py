import warnings
import sys
import os
import ctypes
# import time
from datetime import timedelta, datetime, timezone

from memrw.memory_table import *
from memrw import global_handle
from memrw.read_tables import read_array, read_u32_table  # Later discard

from gamedata.gamevars import game_vars as gv
from gamedata.unitsdata import *
from enums import *

from GetProcessIDctypes import get_d2k_pid
import tkinter as tk
from tkinter import ttk

# from helpers import *  # Already included game_vars!
from memrw import color_idx_to_name, side_idx_to_name, color_idx_to_hex_string
import speed_boost

import capture_production

import pandas as pd
import numpy as np
from pandastable import Table

from find_cliques import find_maximal_cliques_with_pivot

from redirect_output import setup_logging, close_logging

from dump_data import dump_game_data

from file_operations import export_stats, import_stats  # Import the functions from the new module

# Suppress FutureWarning: Downcasting object dtype arrays on .fillna, .ffill, .bfill is deprecated...
warnings.simplefilter(action='ignore', category=FutureWarning)

debug_mode = False

in_game = False
in_game_prev = False  # if the game starts when last time we check
exe_initialized = False  # The run-once flag for init_at_running


# gv.gGameTicks = 0
# gv.gGameTicks_prev = 0

# def get_g_var_name_and_addr():
#     cur_addr = 0x4C94A8
#     while cur_addr <= 0x4CA820:
#         cur_str = ""
#         var_name = global_handle.read_simple_data(cur_addr, ctypes.create_string_buffer(60)).decode()
#         cur_str += var_name
#         cur_addr += 60
#         var_addr = global_handle.read_simple_data(cur_addr, ctypes.c_uint32())
#         cur_str += f": 0x{var_addr:06X}"
#         cur_addr += 4
#         _4th_byte = global_handle.read_simple_data(cur_addr + 3, ctypes.c_uint8())
#         while not _4th_byte:  # 4th byte is null, meaning this is pointer, or null
#             var_addr = global_handle.read_simple_data(cur_addr, ctypes.c_uint32())
#             if var_addr:
#                 cur_str += f", 0x{var_addr:06X}"
#             cur_addr += 4
#             _4th_byte = global_handle.read_simple_data(cur_addr + 3, ctypes.c_uint8())
#         print(cur_str)


def exec_in_game():
    """
    Constantly run in game for every loop. The first run is when gametick = 0.
    However, some code must run once only when gametick > 0
    """
    gv.elapsed_real_sec = (gv.real_timestamp - gv.game_start_timestamp).total_seconds()
    gv.game_end_state = global_handle.read_simple_data(mem.Actual_GameEndState_ADDR, ctypes.c_int32())

    if gv.gGameTicks > gv.gGameTicks_prev:  # Game not paused or frozen
        # Run once:
        if not gv.first_loop_of_positive_gametick_finished and gv.gGameTicks > 0:
            if not gv.spawner_active:
                gv.units_owned_at_start = np.stack([
                    read_array(UNITS_OWNED_TABLE + PLAYER_DATA_LENGTH * i, ctypes.c_uint32, NUM_UNITS) for i in range(8)
                ])
            else:
                gv.units_owned_at_start = read_u32_table(mem.UNITS_OWNED_TABLE_CNC, (8, NUM_UNITS))

            gv.starting_units_excluding_mvc = gv.units_owned_at_start.copy()
            gv.starting_units_excluding_mvc[gv.starting_units_excluding_mvc[:, MCV_INDEX] > 0, MCV_INDEX] -= 1  # Minus 1 MCV if there is any
            # Debug
            # print(f"Game ticks: {gv.gGameTicks}")
            # print(f"Starting units: {gv.units_owned_at_start}")

        #########################
        # Update live game stats
        #########################
        # gv.mouse_pos_map_pixel_x = global_handle.read_simple_data(0x517560, ctypes.c_int32())
        # gv.mouse_pos_map_pixel_y = global_handle.read_simple_data(0x517564, ctypes.c_int32())
        # gv.mouse_pos_view_pixel_x = global_handle.read_simple_data(0x4EB048, ctypes.c_int32())
        # gv.mouse_pos_view_pixel_y = global_handle.read_simple_data(0x4EB04C, ctypes.c_int32())
        # gv.mouse_is_at_map = False
        # gv.mouse_pos_map_tile_x = 0
        # gv.mouse_pos_map_tile_y = 0
        # if gv.mouse_pos_view_pixel_y >= 20 and gv.mouse_pos_view_pixel_x < gv.game_width - 160:
        #     gv.mouse_is_at_map = True
        #     gv.mouse_pos_map_tile_x = gv.mouse_pos_map_pixel_x // 32
        #     gv.mouse_pos_map_tile_y = (gv.mouse_pos_map_pixel_y - 20) // 32

        # cur_tile_addr = 0x517DF0 + (gv.mouse_pos_map_tile_y * gv.map_width + gv.mouse_pos_map_tile_x) * 12

        # Update player defeat status:
        # noinspection all
        gv.gDeadOrder = np.array(global_handle.read_from_memory(0x797B70, (ctypes.c_int8 * 8)()))
        # noinspection all
        has_units = np.array(global_handle.read_from_memory(0x6B8268, (ctypes.c_bool * 8)()))
        # noinspection all
        has_buildings = np.array(global_handle.read_from_memory(0x6B87C0, (ctypes.c_bool * 8)()))
        gv.has_nothing = ~(has_units | has_buildings)

        # If player has quitted program
        gv.left_game_at = np.array([
            global_handle.read_simple_data(0x6B91F8 + 60 * idx + 0x30, ctypes.c_int32()) for idx in range(8)
        ])

        # Alliance and teams
        # noinspection all
        alliance_array = global_handle.read_from_memory(0x798830, (ctypes.c_int8 * 64)())
        alliance_matrix = np.array(alliance_array).reshape((8, 8))
        gv.mutual_alliance_matrix = np.logical_and(alliance_matrix == 0, alliance_matrix.T == 0)  # (8, 8) symmetric

        # Update teams
        if gv.num_teams > 2:  # Update only when number of teams is greater than 2
            # teamable_matrix = alliance_matrix[np.ix_(gv.non_spectator_player_index, gv.non_spectator_player_index)]
            # alliance_graph = (teamable_matrix == 0) & (teamable_matrix.T == 0)  # symmetrize the matrix
            alliance_graph = gv.mutual_alliance_matrix[np.ix_(gv.non_spectator_player_index, gv.non_spectator_player_index)]
            team_cliques = find_maximal_cliques_with_pivot(alliance_graph)
            gv.num_teams = len(team_cliques)
            for team_idx, player_set in enumerate(team_cliques):
                for teamable_pl_idx in player_set:
                    pl_idx = gv.dict_teamable_index_to_player_index[teamable_pl_idx]
                    gv.player_teams[pl_idx] = team_idx + 1

        # Player stats
        for p in range(gv.number_of_player):
            # Update finishing place
            if not gv.is_defeated[p] and gv.has_nothing[p]:
                gv.is_defeated[p] = True
                if gv.victory_status[p] == VICTORY_STATUS_UNDETERMINED:
                    gv.victory_status[p] = VICTORY_STATUS_DEFEATED
                gv.finishing_place[p] = gv.number_of_remaining_player
                gv.number_of_remaining_player -= 1

            # Update has_quitted
            if not gv.has_quitted[p] and gv.left_game_at[p] >= 0:
                gv.has_quitted[p] = True
                print(f"[{datetime.now().strftime('%H:%M:%S')}]: Player {gv.player_names[p]} has left the game at game tick = {gv.gGameTicks}")

            # Update victory status
            is_ally = gv.mutual_alliance_matrix[p, :]  # (8, ) bool
            non_ally = np.logical_not(is_ally)  # (8, ) bool
            is_opponent = non_ally & gv.is_player & (~gv.is_spectator)  # (8, ) bool, non-spect, non-ally players
            if not gv.game_finished and gv.has_nothing[non_ally].all():  # All opponents have nothing
                gv.game_finished = True
                gv.victory_status[is_ally] = VICTORY_STATUS_WIN
                gv.victory_status[is_opponent] = VICTORY_STATUS_LOSS

            cur_pl_offset = PLAYER_DATA_LENGTH * p
            gv.barracks_owning[p] = global_handle.read_simple_data(
                BUILDINGS_OWNING_TABLE + cur_pl_offset + 1 + BARRACKS_BUILDING_GROUP_INDEX,
                ctypes.c_uint8()
            )
            gv.lightfac_owning[p] = global_handle.read_simple_data(
                BUILDINGS_OWNING_TABLE + cur_pl_offset + 1 + LIGHT_FACTORY_BUILDING_GROUP_INDEX,
                ctypes.c_uint8()
            )
            gv.heavyfac_owning[p] = global_handle.read_simple_data(
                BUILDINGS_OWNING_TABLE + cur_pl_offset + 1 + HEAVY_FACTORY_BUILDING_GROUP_INDEX,
                ctypes.c_uint8()
            )
            if gv.barracks_owning[p] >= 3:
                gv.having_3_barracks_ticks[p] += gv.game_tick_diff
            if gv.lightfac_owning[p] >= 3:
                gv.having_3_light_ticks[p] += gv.game_tick_diff
            if gv.heavyfac_owning[p] >= 3:
                gv.having_3_heavy_ticks[p] += gv.game_tick_diff

            # stats
            gv.spice[p] = global_handle.read_simple_data(0x7BCAC4 + cur_pl_offset, ctypes.c_int32())
            # gv.spice_capacity[p] = global_handle.read_simple_data(0x7BCAC8 + cur_pl_offset, ctypes.c_int32())
            # gv.spice_buffer[p] = global_handle.read_simple_data(0x7BCAD4 + cur_pl_offset, ctypes.c_int32())
            gv.cash[p] = global_handle.read_simple_data(0x7BCACC + cur_pl_offset, ctypes.c_int32())
            gv.spice_harvested[p] = global_handle.read_simple_data(0x7BCFEC + cur_pl_offset, ctypes.c_int32())
            gv.harvester_count[p] = global_handle.read_simple_data(0x7BCE28 + cur_pl_offset, ctypes.c_uint8())

            if gv.gDeadOrder[p] == -1:  # player still in game, update the before-defeated stats
                gv.spice_before_defeated[p] = gv.spice[p]
                if not (gv.harvester_count[p] == 0 and gv.harvester_count_before_defeated[p] > 5):  # not sudden drop
                    gv.harvester_count_before_defeated[p] = gv.harvester_count[p]
            # Spice wasted
            # if gv.spice[p] == gv.spice_capacity[p]:  # silos needed
            #     gv.spice_wasted[p] += gv.spice_harvested[p] - gv.last_spice_harvested[p] - (
            #                 gv.spice_capacity[p] - gv.last_spice[p])
            #     gv.spice_wasted2[p] += (
            #         (gv.spice_harvested[p] - gv.last_spice_harvested[p]) +
            #         (gv.last_spice_buffer[p] - gv.spice_buffer[p]) -
            #         (gv.spice[p] - gv.last_spice[p])
            #     )
            # gv.last_spice_harvested[p] = gv.spice_harvested[p]
            # gv.last_spice[p] = gv.spice[p]
            # gv.last_spice_buffer[p] = gv.spice_buffer[p]

            # low power
            power_supply = global_handle.read_simple_data(
                0x7BCE18 + cur_pl_offset,
                ctypes.c_int32()
            )
            power_load = global_handle.read_simple_data(
                0x7BCE1C + cur_pl_offset,
                ctypes.c_int32()
            )
            if power_supply < power_load:  # low power
                gv.low_power_ticks[p] += gv.game_tick_diff
                gv.low_power_time_actual[p] += gv.real_timestamp_diff_sec

            # buildings killed and lost
            gv.total_buildings_killed_count[p] = global_handle.read_simple_data(
                TOTAL_BUILDINGS_KILLED + cur_pl_offset,
                ctypes.c_int32()
            )
            gv.total_buildings_lost_count[p] = global_handle.read_simple_data(
                TOTAL_BUILDINGS_LOST + cur_pl_offset,
                ctypes.c_int32()
            )

        #########################
        # Efficiency related, capture unit production
        #########################
        capture_production.update_production()  # Must run in each loop! The more frequent, the better!

    #########################
    # Begin: run every loop, even if game is paused / frozen
    #########################
    # Calculate game speed
    if gv.real_second > 0:
        gv.average_game_speed = gv.effective_sec_float / gv.real_second

    # Internet. Update
    wait_time_limit = global_handle.read_simple_data(0x6B93E8, ctypes.c_int32())  # 180
    wait_time = global_handle.read_simple_data(0x6B97A0, ctypes.c_int32())  # wait time
    potential_laggers_names_str = ""
    min_max_diff_game_tick = 0

    gv.received_game_ticks = np.array([
        global_handle.read_simple_data(
            0x6B91F8 + 60 * p,
            ctypes.c_int32()
        ) for p in range(8)
    ])
    gv.received_game_ticks[gv.me] = gv.gGameTicks

    # Need to discard the players who have left game!!!!
    if gv.number_of_human >= 1:  # if failed to connect to game, then gv.number_of_human is 0
        valid_received_game_ticks = gv.received_game_ticks[:gv.number_of_human][~gv.has_quitted[:gv.number_of_human]]
        if len(valid_received_game_ticks) > 0:  # Not zero length, i.e. at least 1 human player hasn't quitted.
            max_game_tick = np.max(gv.received_game_ticks[:gv.number_of_human][~gv.has_quitted[:gv.number_of_human]])
            min_game_tick = np.min(gv.received_game_ticks[:gv.number_of_human][~gv.has_quitted[:gv.number_of_human]])
            min_max_diff_game_tick = max_game_tick - min_game_tick
            gv.potential_laggers = np.where(gv.received_game_ticks[:gv.number_of_human] == min_game_tick)[0]  # 1 dimensional array, player indexes
            potential_laggers_names = [gv.player_names[lag_pl] for lag_pl in gv.potential_laggers]
            potential_laggers_names_str = ', '.join(potential_laggers_names)
        else:
            potential_laggers_names_str = gv.player_names[gv.me]  # I am disconnected
            min_max_diff_game_tick = 0
        if wait_time:
            gv.total_freeze_seconds[gv.potential_laggers] += gv.real_timestamp_diff_sec

    game_end_state_str = game_end_state_dict.get(gv.game_end_state, "Unknown game end state")
    app.set_title(
        f'[Started: {gv.game_start_timestamp.strftime('%Y-%m-%d %H:%M:%S')}] '
        f'Elapsed time: {timedelta(seconds=gv.real_second)}, effective time: {gv.effective_sec}, game ticks: {gv.gGameTicks}, '
        f'Avg Speed: {gv.average_game_speed:.2f}, '
        f'Map: {gv.map_name}. '
        f'Wait time: {wait_time}/{wait_time_limit} ({potential_laggers_names_str}: {min_max_diff_game_tick} game ticks behind.) '
        f'End status: {game_end_state_str}, '
    )
    # f'. Mouse pos: ({gv.mouse_pos_map_tile_x:>3}, {gv.mouse_pos_map_tile_y:>3}), 0x{cur_tile_addr:06X}')
    #########################
    # End: run every loop
    #########################
    #

    if gv.gGameTicks > gv.gGameTicks_prev:  # Game not paused or frozen

        # Table stats don't need to be updated so frequently
        if gv.real_second > gv.real_second_prev:
            # some stats that doesn't need to be updated every loop

            update_stats()
            if gv.MeIsSpectator or debug_mode:
                # Show / update the table on the UI
                app.update_table()

        # Update the last_ variables
        # Not using copy, because the array is guaranteed to be assigned to immutable, and assiged to a new array. It's more computationally and memory efficient
        gv.last_build_slot_progress = gv.build_slot_progress  # gv.last_build_slot_progress points to the same underlying array as gv.build_slot_progress!!!!
        gv.last_build_unit_type = gv.build_unit_type  # gv.last_build_unit_type points to the same underlying array as gv.build_unit_type!!!!
        gv.last_delivery_queues = gv.delivery_queues  # gv.last_delivery_queues points to the same underlying array as gv.delivery_queues!!!!
        gv.last_build_slot_on_hold = gv.build_slot_on_hold
        # gv.gDeadOrder_prev = gv.gDeadOrder  # gv.gDeadOrder_prev points to the same underlying array as gv.gDeadOrder!!!!

        if not gv.first_loop_of_positive_gametick_finished and gv.gGameTicks > 0:
            gv.first_loop_of_positive_gametick_finished = True

def on_game_start():
    """
    Run once on game start, initialized game variables
    """
    import_button.config(state=tk.DISABLED)
    gv.clear()  # reset to default values
    gv.spawner_active = global_handle.read_simple_data(mem.SpawnerActive_ADDR, ctypes.c_bool())
    if gv.spawner_active:
        mem.Actual_GameEndState_ADDR = mem.SpawnerGameEndState_ADDR
        gv.MeIsSpectator = global_handle.read_simple_data(mem.MeIsSpectator_ADDR, ctypes.c_bool())

    gv.is_cnc = True if global_handle.read_simple_data(0x4F2898, ctypes.c_uint8()) else False
    gv.is_multiplayer = True if global_handle.read_simple_data(0x797E34, ctypes.c_bool()) else False  # gGameType
    gv.more_than_1_human = True if global_handle.read_simple_data(NetworkGame, ctypes.c_bool()) else False

    gv.game_width = global_handle.read_simple_data(0x4EB020, ctypes.c_uint32())
    gv.game_height = global_handle.read_simple_data(0x4EB024, ctypes.c_uint32())
    gv.map_width = global_handle.read_simple_data(0x517DE8, ctypes.c_uint32())
    gv.map_height = global_handle.read_simple_data(0x517DEC, ctypes.c_uint32())
    map_name_bytes = global_handle.read_simple_data(mem.CNC_MAP_NAME, ctypes.create_string_buffer(60))
    map_hash_bytes = global_handle.read_simple_data(0x797638, ctypes.create_string_buffer(60))
    map_hash_bytes_cnc = global_handle.read_simple_data(mem.CNC_MAP_HASH, ctypes.create_string_buffer(60))
    gv.map_name = map_name_bytes.decode('utf-8')
    gv.gNetMap = map_hash_bytes.decode('utf-8')
    gv.gNetMap_cnc = map_hash_bytes_cnc.decode('utf-8')
    gv.me = global_handle.read_simple_data(0x798544, ctypes.c_int32())
    gv.my_offset = gv.me * 0x26990
    gv.game_start_timestamp = datetime.now()
    gv.game_start_timestamp_utc = datetime.now(timezone.utc)
    print("====================================")
    print(f"[{gv.game_start_timestamp.strftime('%H:%M:%S')}]: New game detected! Game ticks: {gv.gGameTicks}")
    print(f"[Debug] SpawnerActive = {global_handle.read_simple_data(mem.SpawnerActive_ADDR, ctypes.c_bool())}")
    # print(f"{gv.map_width=}, {gv.map_height=}, {gv.game_width=}, {gv.game_height=}")
    print(f"Map name: {gv.map_name}")
    # print(f"Map hash: {gv.gNetMap}")
    # print(f"Map hash (cnc): {gv.gNetMap_cnc}")

    gv.player_names = []
    gv.number_of_AI = global_handle.read_simple_data(0x4E3B0C, ctypes.c_int32())
    computer_player_names = [f"Computer#{c+1}" for c in range(gv.number_of_AI)]
    gv.number_of_human = 0
    gv.number_of_player = 0
    if gv.more_than_1_human:
        # vs human (possibly with computer)
        # Get player name
        # print("more than 1 human")
        for p in range(8):
            gv.player_numbers[p] = global_handle.read_simple_data(0x6B91F8 + 60 * p + 16, ctypes.c_uint8())
            player_name_bytes = global_handle.read_simple_data(HUMAN_PLAYER_NAME + HUMAN_PLAYER_NAME_SIZE * p,
                                                               ctypes.create_string_buffer(20))
            if player_name_bytes:
                gv.number_of_human += 1
                gv.player_names.append(player_name_bytes.decode('utf-8'))
            else:
                gv.player_names += computer_player_names
                break
    elif gv.is_multiplayer:
        # multiplayer practice (cncnet 1 human or non-cncnet multiplayer)
        gv.number_of_human = 1
        local_player_name_bytes = global_handle.read_simple_data(LOCAL_PLAYER_NAME,
                                                                 ctypes.create_string_buffer(20))
        gv.player_names = [local_player_name_bytes.decode('utf-8')] + computer_player_names
    else:
        # single player (mission / campaign)
        gv.player_names = ['Atreides', 'Harkonnen', 'Ordos', 'Emperor', 'Fremen', 'Smugglers', 'Mercenaries',
                           'Sandworm']
        gv.number_of_human = 1
        gv.number_of_AI = 7
    gv.number_of_player = gv.number_of_human + gv.number_of_AI
    gv.number_of_remaining_player = gv.number_of_player
    gv.is_defeated[gv.number_of_player:] = True
    gv.is_player[:gv.number_of_player] = True

    # print(f"{gv.is_multiplayer=}")
    # print(f"Number of human: {gv.number_of_human}, Number of AI: {gv.number_of_AI}, total: {gv.number_of_player}")

    # Get other info
    cur_team = 0
    for p in range(gv.number_of_player):
        # Side
        gv.player_sides[p] = global_handle.read_simple_data(0x8CD4F0 + p, ctypes.c_uint8())

        # Color
        if gv.is_multiplayer:
            gv.player_colors[p] = global_handle.read_simple_data(0x6B9208 + 60 * p + 0x25, ctypes.c_uint8())
        else:
            # single player
            gv.player_colors[p] = global_handle.read_simple_data(0x5175D8 + p, ctypes.c_uint8())

        # handicap and etc
        if gv.more_than_1_human:
            if gv.player_numbers[p] < 1:  # 0 is Computer
                gv.player_handicaps[p] = 0  # Computer always have handicap 1
            else:
                gv.player_handicaps[p] = global_handle.read_simple_data(
                    0x4F2898 + 40 * (gv.player_numbers[p] - 1) + 0x1A,
                    ctypes.c_uint8()
                )
                # gv.player_handicaps[p] = global_handle.read_simple_data(0x6B9208 + 60 * p + 0x26, ctypes.c_uint8())
                gv.is_spectator[p] = global_handle.read_simple_data(
                    mem.NetPlayersExt_ADDR + 24 * (gv.player_numbers[p] - 1) + 21,
                    ctypes.c_bool()
                )
                gv.start_location[p] = global_handle.read_simple_data(
                    mem.NetPlayersExt_ADDR + 24 * (gv.player_numbers[p] - 1) + 22,
                    ctypes.c_int8()
                )
        else:
            if p == gv.me:
                gv.player_handicaps[p] = global_handle.read_simple_data(0x4E8BF0, ctypes.c_uint8())  # gDifficultyLevel
                # print(f"my handicap={gv.player_handicaps[p] + 1}")
            else:
                gv.player_handicaps[p] = 0  # Computer player always 0

        # Teams and non-spectator:
        if gv.is_spectator[p]:
            gv.player_teams[p] = "Spectator"
            gv.victory_status[p] = VICTORY_STATUS_SPECTATING
        else:
            gv.victory_status[p] = VICTORY_STATUS_UNDETERMINED
            gv.dict_teamable_index_to_player_index[cur_team] = p
            cur_team += 1
            gv.player_teams[p] = cur_team
            gv.non_spectator_player_index += [p]

    game_type_dict = {0: "Single Player", 1: "Skirmish", 2: "LAN", 3: "Serial", 4: "Modem", 5: "WOL"}
    game_type_str = game_type_dict.get(global_handle.read_simple_data(0x797E34, ctypes.c_int32()), "Unknown")
    print(f"gGametype = {game_type_str}")
    print(f"Number of human players: {gv.number_of_human}")
    print(f"Number of AIs: {gv.number_of_AI}")
    print(f"I am spectator? {gv.MeIsSpectator}")
    print(f"Player names: {', '.join(gv.player_names)}")

    # Debug:
    # print(f"Teamable (non-spec) player index: {gv.non_spectator_player_index}")

    # Initialized build time ticks
    gv.max_boost = np.array([
        speed_boost.get_full_production_boost(handi) for handi in gv.player_handicaps
    ])  # dim: (8, )
    gv.max_boost_handicap1 = speed_boost.get_full_production_boost(0)  # Scalar

    # Get units property
    for unit_index in range(NUM_UNITS):
        gv.unit_cost[unit_index] = global_handle.read_simple_data(
            UNITS_PROPERTY_DATA + 256 * unit_index + 0x1C,
            ctypes.c_int32()
        )
        gv.unit_build_speed[unit_index] = global_handle.read_simple_data(
            UNITS_PROPERTY_DATA + 256 * unit_index + 0x20,
            ctypes.c_int32()
        )
    gv.unit_progress_per_tick = np.maximum(np.outer(gv.max_boost, gv.unit_build_speed) // 100, 1)  # dim: (8, 30)
    gv.unit_build_time_ticks_actual = 23040 // gv.unit_progress_per_tick  # dim: (8, 30)

    gv.unit_cost_handicap1 = gv.unit_cost * 3 // 4
    gv.unit_progress_per_tick_handicap1 = np.maximum((gv.max_boost_handicap1 * gv.unit_build_speed) // 100,
                                                     1)  # dim: (30, )
    gv.unit_build_time_ticks_handicap1 = 23040 // gv.unit_progress_per_tick_handicap1  # dim: (30, )

    # Get buildings property
    for building_index in range(NUM_BUILDINGS):
        gv.building_cost[building_index] = global_handle.read_simple_data(
            BUILDINGS_PROPERTY_DATA + 268 * building_index + 0x1C,
            ctypes.c_int32()
        )
        gv.building_build_speed[building_index] = global_handle.read_simple_data(
            BUILDINGS_PROPERTY_DATA + 268 * building_index + 0x2C,
            ctypes.c_int32()
        )
    gv.building_progress_per_tick = np.maximum(
        np.outer(gv.max_boost, gv.building_build_speed) // 100,
        1)  # dim: (8, 62)
    gv.building_build_time_ticks_actual = 23040 // gv.building_progress_per_tick  # dim: (8, 62)

    gv.building_cost_handicap1 = gv.building_cost * 3 // 4
    gv.building_progress_per_tick_handicap1 = np.maximum(
        (gv.max_boost_handicap1 * gv.building_build_speed) // 100,
        1)  # dim: (62, )
    gv.building_build_time_ticks_handicap1 = 23040 // gv.building_progress_per_tick_handicap1  # dim: (62, )

    app.reset_table()
    # Debug:
    # print(f"effi_unit_weights: {effi_unit_weights}")
    # print(f"units_owned_start: {gv.units_owned_at_start}")
    # print(f"unit_build_time_ticks_handicap1: {gv.unit_build_time_ticks_handicap1}")
    # print(f"building_build_time_ticks_handicap1: {gv.building_build_time_ticks_handicap1}")

def on_game_end():
    """
    Run once on game end
    """
    if gv.gGameTicks > app.last_update_gametick:
        update_stats()
        app.update_table()  # Need to update table again when game ends?

    app.set_title_after_game()

    # f'. Mouse pos: ({gv.mouse_pos_map_tile_x:>3}, {gv.mouse_pos_map_tile_y:>3}), 0x{cur_tile_addr:06X}')
    if gv.number_of_player < 2:
        print(f"Failed to connect!")
    n_pl = len(gv.player_names)
    print(f"[{datetime.now().strftime('%H:%M:%S')}]: Game ended.")

    total_freeze_seconds_dict = dict(zip(gv.player_names, gv.total_freeze_seconds[:n_pl]))
    print(f"Total freeze seconds: {total_freeze_seconds_dict}")
    # print(gv.infantry_gameticks_delicated_production)
    # print(gv.light_gameticks_delicated_production)
    # print(gv.heavy_gameticks_delicated_production)

    # Dump data to pickle:
    dump_game_data(gv)
    import_button.config(state=tk.NORMAL)

    # # Dump data to tables
    # if gv.number_of_player > 1:
    #     dump_data_to_csv()

def exec_while_running():
    """
    Runs constantly while d2k process is running
    """
    global in_game, in_game_prev, exe_initialized
    # in_game = global_handle.read_simple_data(0x515BA0, ctypes.c_bool())  # After connecting all player, really into game
    in_game = global_handle.read_simple_data(0x5179D0, ctypes.c_bool())  # After connecting all player, really into game
    gv.gGameState = global_handle.read_simple_data(0x4DFB08, ctypes.c_int32())  # 1: not in game. 2: in game, but might be connecting

    # Initialize exe info, addresses
    if not exe_initialized:
        vars_section_start_addr = 0x6B8818
        vars_section_size = 80
        # noinspection all
        vars_section = global_handle.read_data(vars_section_start_addr, (ctypes.c_ubyte * vars_section_size)())
        if any(vars_section):  # make sure the Mission::LoadVarsFile() function has been run
            exe_initialized = True
            init_at_running()  # Set up basic addresses

    # Debug
    gv.NetPlayerCount = global_handle.read_simple_data(0x7984C0, ctypes.c_uint8())  # number of human players
    if debug_mode and gv.NetPlayerCount != gv.NetPlayerCount_prev:
        print(f"[Debug] {datetime.now().strftime('%H:%M:%S')}: gGameTick = {global_handle.read_simple_data(0x5173F4, ctypes.c_uint32())}, NetPlayerCount = {gv.NetPlayerCount}")

    # Basic key variables
    gv.gGameTicks = global_handle.read_simple_data(0x5173F4, ctypes.c_uint32())
    gv.real_second = global_handle.read_simple_data(0x6B9814, ctypes.c_uint32())
    gv.effective_sec_float = gv.gGameTicks * 0.0167
    gv.effective_sec = timedelta(seconds=int(round(gv.effective_sec_float)))
    gv.game_tick_diff = gv.gGameTicks - gv.gGameTicks_prev
    gv.real_timestamp = datetime.now()
    # gv.elapsed_real_sec = (gv.real_timestamp - gv.game_start_timestamp).total_seconds()  # Should not put here! Should put after game_start
    gv.real_timestamp_diff = gv.real_timestamp - gv.real_timestamp_prev
    gv.real_timestamp_diff_sec = gv.real_timestamp_diff.total_seconds()  # float

    if in_game:
        new_game = False
        if not in_game_prev:
            new_game = True
        # Detect restart game or load saved game
        if gv.gGameTicks < gv.gGameTicks_prev:  # Cannot detect load saved game
            new_game = True
        if new_game:
            # time.sleep(0.5)  # wait for map data to load when game starts? Really need?
            on_game_start()
            # exec_in_game()  # need to consider

    if in_game_prev:  # Can detect restart and load saved game if good luck
        exec_in_game()
        if not in_game:
            on_game_end()

    in_game_prev = in_game
    gv.gGameTicks_prev = gv.gGameTicks
    gv.real_second_prev = gv.real_second
    gv.real_timestamp_prev = gv.real_timestamp

    # Debug
    gv.NetPlayerCount_prev = gv.NetPlayerCount  # number of human players

def init_at_running():
    """
    Run once right after dune2000 exe is started (after Mission::LoadVarsFile()). Initializing all necessary memory addresses
    """
    mem.set_handle(global_handle)
    mem.initialize_addresses()
    # print(f"[Debug] Map Name At 0x{mem.CNC_MAP_NAME:08X}")
    print(f"{datetime.now().strftime('%H:%M:%S')}:")
    # print(f"[Debug] SpawnerActive At 0x{mem.SpawnerActive_ADDR:08X}")
    # print(f"[Debug] UnitTracker At 0x{mem.UNITS_OWNED_TABLE_CNC:08X}")
    # print(f"[Debug] BuildingTracker At 0x{mem.BUILDINGS_OWNED_TABLE_CNC:08X}")
    # print(f"[Debug] SpawnerGameEndState At = 0x{mem.SpawnerGameEndState_ADDR:08X}")
    # # print(f"[Debug] NetPlayersExt_ADDR At 0x{mem.NetPlayersExt_ADDR:08X}")
    # # print(f"[Debug] MCVDeployed_ADDR At 0x{mem.MCVDeployed_ADDR:08X}")
    # print(f"[Debug] SpawnerActive = {global_handle.read_simple_data(mem.SpawnerActive_ADDR, ctypes.c_bool())}")
    # print(f"[Debug] NetPlayerCount = {global_handle.read_simple_data(0x7984C0, ctypes.c_uint8())}")
    # print(f"[Debug] gNetAIPlayers = {global_handle.read_simple_data(0x4E3B0C, ctypes.c_uint8())}")
    # print(f"[Debug] StatsDmpBuffer_ADDR At 0x{mem.StatsDmpBuffer_ADDR:08X}")
    # print(f"[Debug] MeIsSpectator_ADDR At 0x{mem.MeIsSpectator_ADDR:08X}")

    print(f"[Info] EXE info initialized!")

def monitor_process():
    global n, exe_initialized
    if global_handle:  # is running
        if global_handle.get_exit_code() == 259:  # Running
            # if not exe_initialized:
            #     exe_initialized = True
            #     # time.sleep(0.1)
            #     init_at_running()  # Need to have some lag. Sometimes SpawnerActive hasn't become true
            exec_while_running()  # exec when dune2000.exe is running (not necessarily in game)

            # Debug
            # if gv.gGameState != 2 or (gv.gGameState == 2 and gv.gGameTicks < 30):
            #     print(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]}, "
            #           f"SpawnerActive = {global_handle.read_simple_data(mem.SpawnerActive_ADDR, ctypes.c_bool())}, "
            #           f"gGameState = {global_handle.read_simple_data(0x4DFB08, ctypes.c_int32())}, "
            #           f"gGameType = {global_handle.read_simple_data(0x797E34, ctypes.c_int32())}, "
            #           f"0x515BA0 = {global_handle.read_simple_data(0x515BA0, ctypes.c_bool())}, "
            #           f"0x5179D0 = {global_handle.read_simple_data(0x5179D0, ctypes.c_bool())}, "
            #           f"gGameTicks = {global_handle.read_simple_data(0x5173F4, ctypes.c_int32())}, "
            #           f"InitialConnectTimeOut = {global_handle.read_simple_data(0x6B9644, ctypes.c_int32())}, "
            #           # f"gNetStartingCredits = {global_handle.read_simple_data(0x004E3B08, ctypes.c_uint16())}, "  # LoadDune2000Ini()
            #           f"gNetUnitCount = {global_handle.read_simple_data(0x004E3B00, ctypes.c_uint8())}, "  # LoadDune2000Ini()
            #           f"harvestUnloadDelay = {global_handle.read_simple_data(0x6B8818, ctypes.c_int32())}, "  # LoadVars()
            #           # f"SinglePlayerDelay = {global_handle.read_simple_data(0x6B8850, ctypes.c_int32())}, "  # LoadVars()
            #           # f"GameWidth = {global_handle.read_simple_data(0x4EB020, ctypes.c_int32())}, "  # InitHighRes()
            #           f"")

            # Debug end

            root.after(100, monitor_process)  # delay 0.1s
        else:
            global_handle.close_handle()
            n = 0
            root.after(5000, monitor_process)  # delay 5s
    else:  # Handle is closed
        if exe_initialized:
            exe_initialized = False
            mem.set_handle(None)  # clear the handle inside the MemoryAddress
        pid = get_d2k_pid()
        if pid is not None:
            print(f"{datetime.now().strftime('%H:%M:%S')}: Dune2000 process found.")
            global_handle.open_handle(pid)  # open the handle hooked to d2k process
            root.after(100, monitor_process)  # delay 0.1s
        else:
            if n < 1:
                print(f"Searching for d2k process...")
                # Force reset the tk UI and force update
                root.geometry(f'{app_width}x{app_height}')
                root.update_idletasks()

            # app.set_title(f"Searching for Dune2000 process... ({n})")
            n += 1
            root.after(1000, monitor_process)  # delay 1s
            # root.after(100, monitor_process)  # delay 0.1s debug


def update_stats():
    capture_production.update_units_owned()
    capture_production.update_buildings_owned()
    capture_production.update_unit_scores()
    capture_production.update_expenses()  # must be after update_efficiencies_all_players() ?

    capture_production.update_efficiencies()

    gv.total_orders_received = np.array([
        global_handle.read_simple_data(0x6B91F8 + 60 * idx + 0x18, ctypes.c_int32()) for idx in range(8)
    ])
    # Debug: check if the units owned of read and calculated match:
    # units_owned_calculated = gv.units_owned_at_start + gv.units_produced + gv.units_from_starport + gv.reinforcements_from_carryall + gv.harvs_from_ref
    # # When there's no deviator, then the units calculated should match actually units owned for indexes from 1 to 17
    # if (gv.debug_info_repeat_time <= 20 and gv.units_owned[:, DEVIATOR_INDEX] == 0).all() and (gv.units_owned != units_owned_calculated)[:, 1:18].any():
    #     gv.debug_info_repeat_time += 1
    #     print(f"Units owned discrepancy detected at gametick={gv.gGameTicks}")
    #     print(f"Where is the discrepancy: \n{np.where((gv.units_owned != units_owned_calculated)[:, 1:18])}")
    #     print(f"units_owned_calculated: \n{units_owned_calculated}")
    #     print(f"units_owned actual: \n{gv.units_owned}")

def get_data_table():
    """
    Calculate the basic stats based on the updated stats
    :return: A pandas dataframe
    """
    # OPM
    avg_OPM = np.zeros(8) if gv.real_second == 0 else gv.total_orders_received * 60 / gv.real_second

    # Other player info

    df_data = [
        ("Team", gv.player_teams),
        ("Side", [side_idx_to_name.get(pl_sd, "Unknown") for pl_sd in gv.player_sides[:gv.number_of_player]]),
        ("Colour", [color_idx_to_name.get(pl_cl, "Unknown") for pl_cl in gv.player_colors[:gv.number_of_player]]),
        ("Handicap", gv.player_handicaps + 1),
        ("Victory Status", [victory_status_dict.get(pl_vc, "Unknown") for pl_vc in gv.victory_status[:gv.number_of_player]]),
        # ("Dead Order", gv.gDeadOrder + 1),
        ("Finishing Place", gv.finishing_place),
        ("Start Location", gv.start_location + 1),
        # ("Credits", gv.spice + gv.cash),
        ("Credits (before defeated)", gv.spice_before_defeated + gv.cash),
        ("Spice Harvested", gv.spice_harvested),


        # ("Unit Expense (handicap1)", gv.unit_expense_handicap1),
        # ("Building Expense (handicap1)", gv.building_expense_handicap1),
        ("Buildings Destroyed Count", gv.total_buildings_killed_count),
        ("Buildings Lost Count", gv.total_buildings_lost_count),

        ("Units Killed Count", gv.total_units_killed_count),
        ("Units Lost Count", gv.total_units_lost_count),

        ("Units Killed Score", gv.total_units_killed_cost),
        ("Units Lost Score", gv.total_units_lost_cost),
        # ("Units Killed Train Time", gv.total_units_killed_train_time),
        # ("Units Lost Train Time", gv.total_units_lost_train_time),


        ("Low Power (game ticks)", gv.low_power_ticks),
        ("Low Power (real seconds)", gv.low_power_time_actual.astype(int)),
        # ("Player Numbers", gv.player_numbers),
        # ("Left Game At", gv.left_game_at),
        # ("Current Gameticks", gv.received_game_ticks),
        # ("Total Freeze Seconds", gv.total_freeze_seconds.astype(int)),

        ("Harvester Count", gv.harvester_count_before_defeated),
        # ("Harvester Count", gv.harvester_count),
        # ("Harvesters Owned", gv.units_owned[:, HARVESTER_INDEX]),  # including deviated
        ("Harvesters Owned", gv.units_produced[:, HARVESTER_INDEX] + gv.units_from_starport[:, HARVESTER_INDEX] + gv.harvs_from_ref[:, HARVESTER_INDEX]),
        ("Refineries Owned", gv.refineries_owned),
        ("Starport Deliveries", gv.units_owned[:, 26]),
        ("Average OPM", [f"{pl_opm:.2f}" for pl_opm in avg_OPM]),


        # ("Effi Building", [f"{pl_ef:.2f}%" for pl_ef in gv.building_efficiency]),
        ("Effi Building (handicap1)", [f"{pl_ef:.2f}%" for pl_ef in gv.building_efficiency_handicap1]),


        ("Effi Infantry Prod (+Sell)", [f"{ef1:.2f} (+{ef2:.2f})" for ef1, ef2 in zip(gv.prod_infantry_effi, gv.light_infantry_by_selling_building_effi)]),
        ("Effi Light Prod (+Starport)", [f"{ef1:.2f} (+{ef2:.2f})" for ef1, ef2 in zip(gv.prod_light_effi, gv.starport_light_effi)]),
        ("Effi Heavy Prod (+Starport +Refi)", [f"{ef1:.2f} (+{ef2:.2f} +{ef3:.2f})" for ef1, ef2, ef3 in zip(gv.prod_heavy_effi, gv.starport_heavy_effi, gv.harvesters_from_ref_effi)]),


        # ("Total Production Efficiency", [f"{ef:.2f}%" for ef in gv.prod_total_effi]),
        ("Total Production Efficiency (1*)", [f"{ef:.2f}%" for ef in gv.prod_total_effi_handicap1]),
        # ("Total Effi Excluding Refi", [f"{ef:.2f}%" for ef in gv.total_effi_excluding_ref]),
        ("Total Effi Excluding Refi(1*)", [f"{ef:.2f}%" for ef in gv.total_effi_excluding_ref_handicap1]),
        # ("Total Effi Including Refi", [f"{ef:.2f}%" for ef in gv.total_effi_including_ref]),
        ("Total Effi Including Refi (1*)", [f"{ef:.2f}%" for ef in gv.total_effi_including_ref_handicap1]),

        ("[Debug] CNCnet effi", [f"{ef:.2f}" for ef in gv.debug_cncnet_effi]),
    ]

    # Convert to DataFrame
    df = pd.DataFrame.from_records(df_data, columns=["items", "data"]).set_index("items")
    df = pd.DataFrame(df['data'].to_list(), index=df.index)
    df.drop(df.columns[gv.number_of_player:], axis=1, inplace=True)
    df.columns = gv.player_names
    df.index.name = None  # Remove the index name "items"
    return df


class PandasTableApp:
    def __init__(self, rt):
        self.root = rt
        self.root.title('Dune2000 Game Stats Helper')

        # Initialize the pandastable frame
        self.table_frame = tk.Frame(self.root)
        self.table_frame.pack(fill=tk.BOTH, expand=True)

        self.table = None  # Placeholder for the actual table that links to summary_df
        self.summary_df = None  # The pandas dataframe holding the summary data
        self.last_update_gametick = -1  # Game tick when the table was last updated

    def force_redraw(self):
        if self.table is not None and self.summary_df is not None:
            self.table.redraw()

    def set_cells_color(self):
        if 'Colour' in self.summary_df.index:
            color_row_index = self.summary_df.index.get_loc("Colour")
            for p in range(gv.number_of_player):
                p_color_index = gv.player_colors[p]
                if p_color_index in color_idx_to_hex_string:
                    self.table.setRowColors(rows=[color_row_index], clr=color_idx_to_hex_string[gv.player_colors[p]],
                                            cols=[p])
        if "Total Effi Including Refi (1*)" in self.summary_df.index:
            effi_row_index = self.summary_df.index.get_loc("Total Effi Including Refi (1*)")
            # print(f"effi_row_index={effi_row_index}")
            self.table.setRowColors(rows=[effi_row_index], clr="#CCEDFF",
                                    cols="all")
            # Just in case there are also extra units for players that are not in the game
            max_effi_player = np.argmax(
                gv.total_effi_including_ref_handicap1[:gv.number_of_player])  # ignore the tie case
            # print(f"max_effi_player={max_effi_player}")
            self.table.setRowColors(rows=[effi_row_index], clr="#9999CC",
                                    cols=[max_effi_player])
        # self.table.setColumnColors(cols=[0], clr="#9999CC")  # Impossible to set column header colors individually
        # self.table.colheader.bgcolor = "#9999CC"  # Impossible to set column header colors individually

        # Color stripe:
        for rw in [
            "Credits (before defeated)",
            "Spice Harvested",
            "Units Killed Count",
            "Units Lost Count",
            "Low Power (game ticks)",
            "Low Power (real seconds)",
            "Refineries Owned",
            "Starport Deliveries",
        ]:
            if rw in self.summary_df.index:
                row_idx = self.summary_df.index.get_loc(rw)
                self.table.setRowColors(rows=[row_idx], clr="#E0E0E0", cols="all")

    def update_table(self):
        """
        Run every second.
        Can only be called when the get_data_table() returns a DataFrame containing real data!\
        :return:
        """

        self.summary_df = get_data_table()  # Update the related info and get the data

        if self.table is None:
            # If the table hasn't been created, create it
            self.table = Table(self.table_frame, dataframe=self.summary_df, showtoolbar=False, showstatusbar=False)
            # Once the table is linked to a dataframe, then the UI will auto refresh when drag-and-drop the UI, or when functions like redraw() or setRowColors() is called

            self.table.showIndex()
            self.table.show()  # This method will call adjustColumnWidths() which overwrite the custom columnwidths。 Also initialize the related attributes
            self.table.columnwidths = {col: 168 for col in self.summary_df.columns}  # Set default column width
            self.table.rowheader.maxwidth = 240   # Manually set default row header width, suggested by dmnfarrell
            # self.set_cells_color()
            # self.table.redraw()  # See if this is needed
        else:
            # If the table exists, need to manually update it! So weird
            self.table.model.df = self.summary_df

        self.set_cells_color()  # This forces a refresh on the UI, i.e. redraw the table? No!
        self.table.redraw()

        self.last_update_gametick = gv.gGameTicks
        # Schedule the next update in 1 second (1000 milliseconds)
        # self.root.after(1000, self.update_table)

    def reset_table(self):
        if self.table is not None:
            self.table = None  # Reset the table attribute to None
        if self.summary_df is not None:
            self.summary_df = None  # Reset the underlying pandas df
        self.last_update_gametick = -1

    def set_title(self, new_title):
        # Run every loop.
        self.root.title(new_title)

    def set_title_after_game(self):
        game_end_state_str = game_end_state_dict.get(gv.game_end_state, "Unknown game end state")
        self.set_title(
            f'[Started: {gv.game_start_timestamp.strftime('%Y-%m-%d %H:%M:%S')}] '
            f'Elapsed time: {timedelta(seconds=gv.real_second)}, effective time: {gv.effective_sec}, game ticks: {gv.gGameTicks}, '
            f'Avg Speed: {gv.average_game_speed:.2f}, '
            f'Map: {gv.map_name}. '
            f'End status: {game_end_state_str} '
        )


def refresh_UI():
    root.geometry(f'{app_width}x{app_height}')
    root.update()
    app.force_redraw()


if __name__ == "__main__":
    log_file = setup_logging()

    # tk part
    root = tk.Tk()

    exe_path = sys.argv[0]
    icon_path = "app_icon.ico"

    # Set the window icon to app_icon.ico if it exists, else use the exe path icon
    if os.path.exists(icon_path):
        try:
            root.iconbitmap(icon_path)
        except Exception as e:
            print(f"Error setting custom icon: {e}")
    # else:
    #     try:
    #         root.iconbitmap(exe_path)
    #     except Exception as e:
    #         print(f"Error setting executable icon: {e}")

    app_width = 1280
    app_height = 760
    root.geometry(f'{app_width}x{app_height}')
    app = PandasTableApp(root)
    s = ttk.Style()  # Create a ttk style object, to change the font of ttl.Button
    # Set the font size for the style. The name must end with ".TButton"
    s.configure('yahei20.TLabel', font=("Microsoft YaHei", 20))

    # refresh_button = ttk.Button(root, text="Refresh", command=refresh_UI)
    # refresh_button.pack()
    # Create a frame for buttons at the bottom
    button_frame = ttk.Frame(root)
    button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

    # Refresh button
    refresh_button = ttk.Button(button_frame, text="Refresh", command=refresh_UI)
    refresh_button.pack(side=tk.LEFT, padx=5, pady=5)

    # Import button
    import_button = ttk.Button(button_frame, text="Import", command=lambda: import_stats(app))
    import_button.pack(side=tk.LEFT, padx=5, pady=5)

    # Export button
    export_button = ttk.Button(button_frame, text="Export", command=export_stats)
    export_button.pack(side=tk.LEFT, padx=5, pady=5)

    n = 0  # Number of seconds passed when searching for d2k process
    monitor_process()

    try:
        root.mainloop()
    finally:
        global_handle.close_handle()
        close_logging(log_file)
