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
# from memrw import color_idx_to_name, side_idx_to_name, color_idx_to_hex_string
import speed_boost

import capture_production

# import pandas as pd
import numpy as np
from pandas_table_app import (
    SummaryTable,
    DetailsTable,
    UnitsOwnedCleanTable,
    TotalOwnedTable,
    TotalKilledTable,
    TotalLostTable,
)
from buttons_right import RightButtons

from find_cliques import find_maximal_cliques_with_pivot

from redirect_output import setup_logging, close_logging

from file_operations import export_stats, import_stats, dump_game_data  # Import the functions from the new module

# Suppress FutureWarning: Downcasting object dtype arrays on .fillna, .ffill, .bfill is deprecated...
warnings.simplefilter(action='ignore', category=FutureWarning)

debug_mode = False
version_list = [1, 0, 4]
version_date_str = "2025-03-24"
version_string = f"Version {version_list[0]}.{version_list[1]}{version_list[2]}"

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
        gv.has_units = np.array(global_handle.read_from_memory(0x6B8268, (ctypes.c_bool * 8)()))
        # noinspection all
        gv.has_buildings = np.array(global_handle.read_from_memory(0x6B87C0, (ctypes.c_bool * 8)()))
        gv.has_nothing = ~(gv.has_units | gv.has_buildings)

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
                    gv.player_team_idx[pl_idx] = team_idx + 1

            # Argsort player team idx
            gv.player_index_by_teams = np.argsort(gv.player_team_idx)

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
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: Player {gv.player_names[p]} has left the game at game tick = {gv.gGameTicks}")

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
                BUILDINGS_EXIST_PER_GROUP + cur_pl_offset + BARRACKS_BUILDING_GROUP_INDEX,
                ctypes.c_uint8()
            )
            gv.lightfac_owning[p] = global_handle.read_simple_data(
                BUILDINGS_EXIST_PER_GROUP + cur_pl_offset + LIGHT_FACTORY_BUILDING_GROUP_INDEX,
                ctypes.c_uint8()
            )
            gv.heavyfac_owning[p] = global_handle.read_simple_data(
                BUILDINGS_EXIST_PER_GROUP + cur_pl_offset + HEAVY_FACTORY_BUILDING_GROUP_INDEX,
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
            gv.power_output[p] = global_handle.read_simple_data(0x7BCE18 + cur_pl_offset, ctypes.c_uint32())
            gv.power_drained[p] = global_handle.read_simple_data(0x7BCE1C + cur_pl_offset, ctypes.c_uint32())

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
    main_ui.set_title(
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
                # main_ui.update_summary_table()
                main_ui.update_all_tables()

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
    main_ui.import_button.config(state=tk.DISABLED)
    main_ui.right_button_instance.disable_all_buttons()

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
    print("=" * 20)  # Delimiter to separate possible load saved game
    print(f"[{gv.game_start_timestamp.strftime('%Y-%m-%d %H:%M:%S')}]: New game detected! Game ticks: {gv.gGameTicks}")
    print(f"[Debug] SpawnerActive = {global_handle.read_simple_data(mem.SpawnerActive_ADDR, ctypes.c_bool())}")
    # print(f"{gv.map_width=}, {gv.map_height=}, {gv.game_width=}, {gv.game_height=}")
    print(f"Map name: {gv.map_name}")
    print(f"Map file name: {gv.gNetMap}")
    print(f"Map file name (cnc): {gv.gNetMap_cnc}")

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
            gv.player_team_idx[p] = TEAM_INDEX_SPECTATOR
            gv.victory_status[p] = VICTORY_STATUS_SPECTATING
        else:
            gv.victory_status[p] = VICTORY_STATUS_UNDETERMINED
            gv.dict_teamable_index_to_player_index[cur_team] = p
            cur_team += 1
            gv.player_teams[p] = cur_team
            gv.player_team_idx[p] = cur_team
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
        gv.unit_group_index[unit_index] = global_handle.read_simple_data(
            UNITS_PROPERTY_DATA + 256 * unit_index + 0x01,
            ctypes.c_uint8()
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
        gv.building_group_index[building_index] = global_handle.read_simple_data(
            BUILDINGS_PROPERTY_DATA + 268 * building_index + 0x88,
            ctypes.c_uint8()
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

    main_ui.reset_all_tables()
    # Debug:
    # print(f"effi_unit_weights: {effi_unit_weights}")
    # print(f"units_owned_start: {gv.units_owned_at_start}")
    # print(f"unit_build_time_ticks_handicap1: {gv.unit_build_time_ticks_handicap1}")
    # print(f"building_build_time_ticks_handicap1: {gv.building_build_time_ticks_handicap1}")

def on_game_end():
    """
    Run once on game end
    """
    if gv.number_of_player < 2:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Failed to connect! Game ended")
    else:
        if gv.gGameTicks > main_ui.get_summary_last_update_gametick():
            update_stats()
            main_ui.update_all_tables()  # Need to update table again when game ends?

        main_ui.set_title_after_game()

        # f'. Mouse pos: ({gv.mouse_pos_map_tile_x:>3}, {gv.mouse_pos_map_tile_y:>3}), 0x{cur_tile_addr:06X}')
        n_pl = len(gv.player_names)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]: Game ended.")

        total_freeze_seconds_dict = dict(zip(gv.player_names, gv.total_freeze_seconds[:n_pl]))
        print(f"Total freeze seconds: {total_freeze_seconds_dict}")
        # print(gv.infantry_gameticks_delicated_production)
        # print(gv.light_gameticks_delicated_production)
        # print(gv.heavy_gameticks_delicated_production)

    # Dump data to pickle:
    dump_game_data(gv)
    main_ui.import_button.config(state=tk.NORMAL)
    main_ui.right_button_instance.enable_all_buttons()

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
        print(f"[Debug] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: gGameTick = {global_handle.read_simple_data(0x5173F4, ctypes.c_uint32())}, NetPlayerCount = {gv.NetPlayerCount}")

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
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:")
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
            #     print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}, "
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
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Dune2000 process found.")
            global_handle.open_handle(pid)  # open the handle hooked to d2k process
            root.after(100, monitor_process)  # delay 0.1s
        else:
            if n < 1:
                print(f"Searching for d2k process...")
                # print("=" * 40)
                # Force reset the tk UI and force update
                root.geometry(f'{app_width}x{app_height}')
                root.update_idletasks()

            # app.set_title(f"Searching for Dune2000 process... ({n})")
            n += 1
            root.after(1000, monitor_process)  # delay 1s
            # root.after(100, monitor_process)  # delay 0.1s debug


def update_stats():
    """
    Called every second (not every loop)
    :return:
    """
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


def refresh_UI():
    root.geometry(f'{app_width}x{app_height}')
    root.update()
    main_ui.force_redraw_all()


# Create a class so that other python files can access its attributes
class MainApp:
    # Symbols: ┌ ┐ └ ┘ ┬ ┴ ├ ┤
    # ┌-------------------------------------------------┐
    # | Main Frame (LabelFrame)                         |
    # |┌-----------------------------------------------┐|
    # || Notebook [Tab:Summary][Tab:..]                ||
    # ||                                               ||
    # ||                                               ||
    # |├-----------------------------------------------┤|
    # || Button Frame                                  ||
    # ||┌--------------┬---------------┬--------------┐||
    # ||| Left buttons | Version Texts | Right buttons|||
    # ||└--------------┴---------------┴--------------┘||
    # |└-----------------------------------------------┘|
    # └-------------------------------------------------┘
    def __init__(self, master):
        self.root = master

        # Create the frame of the table app
        self.main_frame = ttk.LabelFrame(self.root, text="No game data found", style="yahei10.TLabelframe")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create a Notebook on the frame
        self.main_stats_notebook = ttk.Notebook(self.main_frame)
        self.main_stats_notebook.pack(expand=True, fill="both")

        self.all_pandas_tables = []

        self.summary_stats_frame = ttk.Frame(self.main_stats_notebook)
        self.main_stats_notebook.add(self.summary_stats_frame, text="Summary")
        self.app_summary_stats = SummaryTable(self.summary_stats_frame)  # The pandas table app
        self.all_pandas_tables.append(self.app_summary_stats)

        self.detailed_stats_frame = ttk.Frame(self.main_stats_notebook)
        self.main_stats_notebook.add(self.detailed_stats_frame, text="Other Details")
        self.app_detailed_stats = DetailsTable(self.detailed_stats_frame)  # The pandas table app
        self.all_pandas_tables.append(self.app_detailed_stats)

        self.units_owned_clean_stats_frame = ttk.Frame(self.main_stats_notebook)
        self.main_stats_notebook.add(self.units_owned_clean_stats_frame, text="Units Owned Clean")
        self.app_units_owned_clean_stats = UnitsOwnedCleanTable(self.units_owned_clean_stats_frame)  # The pandas table app
        self.all_pandas_tables.append(self.app_units_owned_clean_stats)

        self.total_owned_stats_frame = ttk.Frame(self.main_stats_notebook)
        self.main_stats_notebook.add(self.total_owned_stats_frame, text="Total Owned")
        self.app_total_owned_stats = TotalOwnedTable(self.total_owned_stats_frame)  # The pandas table app
        self.all_pandas_tables.append(self.app_total_owned_stats)

        self.total_killed_stats_frame = ttk.Frame(self.main_stats_notebook)
        self.main_stats_notebook.add(self.total_killed_stats_frame, text="Total Killed")
        self.app_total_killed_stats = TotalKilledTable(self.total_killed_stats_frame)  # The pandas table app
        self.all_pandas_tables.append(self.app_total_killed_stats)

        self.total_lost_stats_frame = ttk.Frame(self.main_stats_notebook)
        self.main_stats_notebook.add(self.total_lost_stats_frame, text="Total Lost")
        self.app_total_lost_stats = TotalLostTable(self.total_lost_stats_frame)  # The pandas table app
        self.all_pandas_tables.append(self.app_total_lost_stats)

        # refresh_button = ttk.Button(master, text="Refresh", command=refresh_UI)
        # refresh_button.pack()
        # Create a frame for buttons at the bottom
        self.button_frame = ttk.Frame(self.root)
        self.button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        self.left_button_frame = ttk.Frame(self.button_frame)
        self.left_button_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.version_text = ttk.Label(
            self.button_frame,
            text=f"{version_string} ({version_date_str})\nMade by Perennie",
            style='yahei10blue.TLabel'
        )
        self.version_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.right_button_frame = ttk.Frame(self.button_frame, borderwidth=1, relief=tk.SOLID)
        self.right_button_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        ###############
        # Left buttons
        ###############
        # Refresh button
        self.refresh_button = ttk.Button(self.left_button_frame, text="Refresh", command=refresh_UI)
        self.refresh_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Import button
        self.import_button = ttk.Button(self.left_button_frame, text="Import", command=lambda: import_stats(main_ui))
        self.import_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Export button
        self.export_button = ttk.Button(self.left_button_frame, text="Export", command=export_stats)
        self.export_button.pack(side=tk.LEFT, padx=5, pady=5)

        ###############
        # Right buttons
        ###############
        self.right_button_instance = RightButtons(root, self.right_button_frame)

    def get_summary_last_update_gametick(self):
        return self.app_summary_stats.last_update_gametick

    def set_title(self, new_title):
        """
        :param new_title: str
        :return:
        """
        # Run every loop.
        # self.root.title(new_title)  # If self.root is the root of tk
        self.main_frame.configure(text=new_title)  # If self.root is a LabelFrame

    def set_title_after_game(self):
        game_end_state_str = game_end_state_dict.get(gv.game_end_state, "Unknown game end state")
        self.set_title(
            f'[Started: {gv.game_start_timestamp.strftime('%Y-%m-%d %H:%M:%S')}] '
            f'Elapsed time: {timedelta(seconds=gv.real_second)}, effective time: {gv.effective_sec}, game ticks: {gv.gGameTicks}, '
            f'Avg Speed: {gv.average_game_speed:.2f}, '
            f'Map: {gv.map_name}. '
            f'End status: {game_end_state_str} '
        )

    def force_redraw_all(self):
        """
        Redraw all the pandas table apps
        :return:
        """
        for pt in self.all_pandas_tables:
            pt.force_redraw()

    def update_all_tables(self):
        """
        Update all the pandas table apps
        :return:
        """
        for pt in self.all_pandas_tables:
            pt.update_table()

    def reset_all_tables(self):
        """
        Reset all the pandas table apps
        :return:
        """
        for pt in self.all_pandas_tables:
            pt.reset_table()

    def update_summary_table(self):
        """
        Update only the Summary
        :return:
        """
        self.app_summary_stats.update_table()


if __name__ == "__main__":
    log_file = setup_logging()

    # tk part
    root = tk.Tk()
    root.title("Dune2000 Statistics Helper")

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

    app_width = 1400
    app_height = 850
    root.geometry(f'{app_width}x{app_height}')

    s = ttk.Style()  # Create a ttk style object, to change the font of ttk.Button
    # Set the font size for the style. The name must end with ".TButton"
    s.configure('yahei20.TLabel', font=("Microsoft YaHei", 20))
    s.configure('yahei10blue.TLabel', foreground='blue', font=("Microsoft YaHei", 10))
    # Configure the style for TLabelFrame.Label
    s.configure('yahei10.TLabelframe')
    s.configure('yahei10.TLabelframe.Label', font=("Microsoft YaHei", 10))

    # Configure the tab style (add padding around text)
    s.configure("TNotebook.Tab", padding=[3, 0])

    main_ui = MainApp(root)

    n = 0  # Number of seconds passed when searching for d2k process
    monitor_process()

    try:
        root.mainloop()
    finally:
        global_handle.close_handle()
        close_logging(log_file)
