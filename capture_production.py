import ctypes
# import numpy as np

from memrw.memory_table import *
from memrw import global_handle, unit_idx_to_name
from memrw.read_tables import read_array, read_u32_table  # Later discard
from gamedata.gamevars import game_vars as gv
from gamedata.unitsdata import *

# debugging
unitnames = [v for v in unit_idx_to_name.values()]

def update_buildings_owned():
    """
    Update the buildings_owned game variable.
    Assuming SpawnerActive is True. So we are reading the UnitTracker PlayerUnitsOwned. int[8][30]
    """
    gv.buildings_owned = np.stack([
        read_array(BUILDINGS_OWNED_TABLE + PLAYER_DATA_LENGTH * i, ctypes.c_uint32, NUM_BUILDINGS) for i in range(8)
    ])
    gv.refineries_owned = \
        gv.buildings_owned[:, ATREIDES_REFINERY_INDEX] + \
        gv.buildings_owned[:, HARKONNEN_REFINERY_INDEX] + \
        gv.buildings_owned[:, ORDOS_REFINERY_INDEX]  # dim (8, )


def update_units_owned():
    """
    Update the units_owned game variable
    """
    # Assuming single player, not using mission launcher
    # for i in range(8):
    #     # 30 types of units
    #     gv.units_owned[i] = read_array(UNITS_OWNED_TABLE + PLAYER_DATA_LENGTH * i, ctypes.c_uint32, NUM_UNITS)
    if not gv.spawner_active:  # Temporarily do not consider mission launcher
        gv.units_owned = np.stack([
            read_array(UNITS_OWNED_TABLE + PLAYER_DATA_LENGTH * i, ctypes.c_uint32, NUM_UNITS) for i in range(8)
        ])
    else:
        gv.units_owned = read_u32_table(mem.UNITS_OWNED_TABLE_CNC, (8, NUM_UNITS))

def update_production():
    """
    Must be run in every loop.
    :return: None
    """
    gv.build_unit_type = np.array([
        global_handle.read_simple_data(0x7BEDA0 + i * PLAYER_DATA_LENGTH + slot * 20, ctypes.c_int16())
        for i in range(8)
        for slot in range(10)
    ]).reshape(8, 10)

    gv.build_slot_progress = np.array([
        global_handle.read_simple_data(0x7BEDA0 + i * PLAYER_DATA_LENGTH + slot * 20 + 2, ctypes.c_int16())
        for i in range(8)
        for slot in range(10)
    ]).reshape(8, 10)

    gv.build_slot_on_hold = np.array([
        global_handle.read_simple_data(0x7BEDA0 + i * PLAYER_DATA_LENGTH + slot * 20 + 16, ctypes.c_bool())
        for i in range(8)
        for slot in range(10)
    ]).reshape(8, 10)

    # Create units increment array
    units_increment_production = np.zeros((8, NUM_UNITS), dtype=int)
    units_increment_harvs_from_ref = np.zeros((8, NUM_UNITS), dtype=int)
    units_increment_starport = np.zeros((8, NUM_UNITS), dtype=int)

    ##############################
    # Detect new units produced
    ##############################
    unit_ready_captured_slots = (  # array shape (8, 10)
            (gv.build_slot_progress == 0x5A00) &  # current progress == 23040
            (gv.build_unit_type == -1) &  # finished building
            (gv.last_build_slot_progress <= 0x5A00) &  # last progress <= 23040
            (gv.last_build_unit_type >= 0)  # was actually building something
    )  # This will fail when a unit is blocked from entrance and then player cancel it: it's counted by this algorithm, but not by d2k.

    # Debug:
    # if unit_ready_captured_slots.any():
    #     print("Captured!")
    #     print(np.where(unit_ready_captured_slots))

    # C: Number of units produced captured
    # N: Number of potential produced
    # n: Number of trully produced with in N
    # Use this mask (unit_ready_slots) to select the relevant player_index and unit_type
    unit_produced_increment_player_index, _ = np.where(unit_ready_captured_slots)  # (C, )
    unit_produced_increment_unit_type = gv.last_build_unit_type[unit_ready_captured_slots]  # (C, )

    unit_ready_potential_slots = (  # (8, 10)
            (
                    gv.build_slot_progress < gv.last_build_slot_progress) &  # Continuously building something, or we missed the game tick when build_unit_type == -1
            (gv.last_build_unit_type >= 0) &  # was actually building something
            (~gv.last_build_slot_on_hold)  # last not on hold
    )  # This will fail when a unit is on hold right before it finishes building, then player quickly click twice to finish the building and then start the next build,
    # and coincidentally we missed both the clicks. In this case, it's not counted by this algorithm, but counted by d2k.

    # See if the unit was canceled:
    unit_ready_potential_slots_player_index, _ = np.where(unit_ready_potential_slots)  # (N, )
    if len(unit_ready_potential_slots_player_index) > 0:
        unit_ready_potential_slots_unit_type_last = gv.last_build_unit_type[unit_ready_potential_slots]  # (N, )
        unit_ready_potential_slots_unit_type_current = gv.build_unit_type[unit_ready_potential_slots]  # (N, )
        handi_boost = np.array([125, 100, 75])
        handicaps = gv.player_handicaps[unit_ready_potential_slots_player_index]  # (N, )
        cur_boost = handi_boost[handicaps] * 200 // 100  # To save time, assume the fastest factory boost
        progress_per_tick_last_unit = np.maximum(
            (cur_boost * gv.unit_build_speed[unit_ready_potential_slots_unit_type_last]) // 100,
            1)
        progress_per_tick_cur_unit = np.maximum(
            (cur_boost * gv.unit_build_speed[unit_ready_potential_slots_unit_type_current]) // 100,
            1)
        game_ticks_needed_for_last_unit = (0x5A00 - gv.last_build_slot_progress[
            unit_ready_potential_slots]) // progress_per_tick_last_unit
        game_ticks_needed_for_cur_unit = gv.build_slot_progress[
                                             unit_ready_potential_slots] // progress_per_tick_cur_unit
        passed_potential_slots = (
                                         game_ticks_needed_for_last_unit + game_ticks_needed_for_cur_unit) <= gv.game_tick_diff  # (N, ) Boolean
        passed_potential_player_index = unit_ready_potential_slots_player_index[
            passed_potential_slots]  # (n, ) player index
        passed_potential_unit_type = unit_ready_potential_slots_unit_type_last[
            passed_potential_slots]  # (n, ) unit type
        unit_produced_increment_player_index = np.concatenate(
            (unit_produced_increment_player_index, passed_potential_player_index))  # (C + n, ) player index
        unit_produced_increment_unit_type = np.concatenate(
            (unit_produced_increment_unit_type, passed_potential_unit_type))  # (C + n, ) unit type

    # To be implemented: check unit_produced <= units_owned
    np.add.at(gv.units_produced, (unit_produced_increment_player_index, unit_produced_increment_unit_type), 1)

    # Add to increment and append
    if len(unit_produced_increment_player_index) > 0:
        np.add.at(units_increment_production, (unit_produced_increment_player_index, unit_produced_increment_unit_type), 1)
        gv.units_increment_buffer_production.append(
            (gv.gGameTicks, units_increment_production)
        )

    # debugging
    # print(f"Gametick: {gv.gGameTicks:>6}, cur_unit_type: {gv.build_unit_type[0, 0]:3}, "
    #       f"cur_prgress: {gv.build_slot_progress[0, 0]:>5}"
    #       f"")
    # debug_unit_produced_increment_unit_type = unit_produced_increment_unit_type[unit_produced_increment_player_index == gv.me]
    # if len(debug_unit_produced_increment_unit_type) > 0:
    #     print(unit_ready_captured_slots)
    #     print(unit_ready_potential_slots)
    #     # print(f"{unit_produced_increment_player_index=}")
    #     print(f"{unit_produced_increment_unit_type=}")
    #     print(f"Player: {gv.player_names[unit_produced_increment_player_index[0]]} "
    #           f"produced: {unitnames[debug_unit_produced_increment_unit_type[0]]}, "
    #           f"Total produced: {gv.units_produced[gv.me, debug_unit_produced_increment_unit_type[0]]}")

    ##############################
    # Detect starport and carryall delivery units
    ##############################
    gv.delivery_queues = np.array([
        global_handle.read_simple_data(0x7BEB5C + i * PLAYER_DATA_LENGTH + q * 56 + 8 + slot, ctypes.c_int8())
        for i in range(8)
        for q in range(10)
        for slot in range(40)
    ]).reshape(8, 10, 40)

    delivery_captured_slots = (  # bool (8, 10, 40)
            (gv.delivery_queues == -2) &
            (gv.last_delivery_queues >= 0)
    )
    if delivery_captured_slots.any():
        unit_delivered_increment_player_index, unit_delivered_increment_queue_index, _ = np.where(
            delivery_captured_slots)  # (C, ), (C, )
        unit_delivered_increment_unit_type = gv.last_delivery_queues[delivery_captured_slots]  # (C, )

        # Read the delivery type:
        delivery_type = np.array([
            global_handle.read_simple_data(int(0x7BEB5C + i * PLAYER_DATA_LENGTH + q * 56 + 0x35), ctypes.c_int8())
            for i, q in zip(unit_delivered_increment_player_index, unit_delivered_increment_queue_index)
        ])
        delivery_sub_type = np.array([
            global_handle.read_simple_data(int(0x7BEB5C + i * PLAYER_DATA_LENGTH + q * 56 + 0x36), ctypes.c_int8())
            for i, q in zip(unit_delivered_increment_player_index, unit_delivered_increment_queue_index)
        ])
        delivery_arriving_time = np.array([
            global_handle.read_simple_data(int(0x7BEB5C + i * PLAYER_DATA_LENGTH + q * 56 + 4), ctypes.c_int32())
            for i, q in zip(unit_delivered_increment_player_index, unit_delivered_increment_queue_index)
        ])
        harv_delivered_increment_player_index = unit_delivered_increment_player_index[
            (delivery_type == 1) & (delivery_sub_type == 4)]
        harv_delivered_increment_unit_type = unit_delivered_increment_unit_type[
            (delivery_type == 1) & (delivery_sub_type == 4)]
        carryall_reinforcement_increment_player_index = unit_delivered_increment_player_index[
            (delivery_type == 1) & (delivery_sub_type != 4)]
        carryall_reinforcement_increment_unit_type = unit_delivered_increment_unit_type[
            (delivery_type == 1) & (delivery_sub_type != 4)]
        np.add.at(gv.harvs_from_ref, (harv_delivered_increment_player_index, harv_delivered_increment_unit_type),
                  1)  # + harvs
        # np.add.at(gv.harvs_from_ref, (harv_delivered_increment_player_index, CARRYALL2_INDEX), 1)  # Can't capture carryall2 like this!
        np.add.at(gv.reinforcements_from_carryall,
                  (carryall_reinforcement_increment_player_index, carryall_reinforcement_increment_unit_type),
                  1)  # + Reinforced units
        # np.add.at(gv.harvs_from_ref, (carryall_reinforcement_increment_player_index, CARRYALL2_INDEX), 1)  # Can't capture carryall2 like this!
        # Currently, ignore all carryall reinforcement deliveries in efficiency calculation!

        # Add to increment array
        if len(harv_delivered_increment_player_index) > 0:
            np.add.at(units_increment_harvs_from_ref, (harv_delivered_increment_player_index, harv_delivered_increment_unit_type),
                      1)  # + harvs
            # np.add.at(units_increment_excl_starport,
            #           (carryall_reinforcement_increment_player_index, carryall_reinforcement_increment_unit_type),
            #           1)  # + Reinforced units
            gv.units_increment_buffer_harvs_from_ref.append(
                (gv.gGameTicks, units_increment_harvs_from_ref)
            )

        starport_delivered_increment_player_index = unit_delivered_increment_player_index[delivery_type == 2]
        if len(starport_delivered_increment_player_index) > 0:
            starport_delivered_increment_unit_type = unit_delivered_increment_unit_type[delivery_type == 2]
            np.add.at(gv.units_from_starport,
                      (starport_delivered_increment_player_index, starport_delivered_increment_unit_type), 1)
            # Add to increment array, and append
            np.add.at(units_increment_starport,
                      (starport_delivered_increment_player_index, starport_delivered_increment_unit_type), 1)
            gv.units_increment_buffer_starport.append(
                (gv.gGameTicks, units_increment_starport)
            )
            # store the delivery time
            delivery_arriving_time_effective = delivery_arriving_time[delivery_type == 2]
            for pl, gt in zip(starport_delivered_increment_player_index, delivery_arriving_time_effective):
                curpl_delivery_list = gv.starport_delivery_times[pl]
                if not curpl_delivery_list:  # empty list
                    curpl_delivery_list.append(gt)
                else:  # compare to last delivery time
                    if gt > curpl_delivery_list[-1]:
                        curpl_delivery_list.append(gt)

def update_efficiencies():
    """
    No need to run every loop. Just need to be run when updating the stats table.
    This function will clear the 3 unit increment buffers:
        units_increment_buffer_production, units_increment_buffer_harvs_from_ref, units_increment_buffer_starport,
    and append to the delicated list
    :return: None
    """
    if gv.gGameTicks == gv.efficiency_stat_last_update_time:
        return
    if gv.gGameTicks == 0:
        # gv.append_data_to_list()
        gv.efficiency_stat_last_update_time = gv.gGameTicks
        return
    # Debug:
    # if gv.real_second > gv.real_second_prev and gv.gGameTicks > gv.gGameTicks_prev:
    #     print("gv.units_produced (me):")
    #     print(gv.units_produced[0, :])

    ########################
    # 1 Unit efficiency
    ########################

    ###################
    # 1.1 Production efficiency
    ###################
    total_time_cost_each_unit_each_player_prod = gv.units_produced * gv.unit_build_time_ticks_actual  # (8, 30) array

    gv.prod_infantry_effi = total_time_cost_each_unit_each_player_prod[:, effi_infantry_index].sum(
        1) * 100 / gv.gGameTicks  # (8, ) array
    gv.prod_light_effi = total_time_cost_each_unit_each_player_prod[:, effi_light_index].sum(
        1) * 100 / gv.gGameTicks  # (8, ) array
    gv.prod_heavy_effi = total_time_cost_each_unit_each_player_prod[:, effi_heavy_index].sum(
        1) * 100 / gv.gGameTicks  # (8, ) array

    # Total production efficiency
    gv.prod_total_effi = gv.prod_infantry_effi * weight_infantry + gv.prod_light_effi * weight_light + gv.prod_heavy_effi * weight_heavy  # (8, ) array

    # Total production efficiency handicap 1
    total_time_cost_each_unit_each_player_prod_handicap1 = gv.units_produced * gv.unit_build_time_ticks_handicap1  # (8, 30) array
    gv.prod_total_effi_handicap1 = total_time_cost_each_unit_each_player_prod_handicap1 @ effi_unit_weights * 100 / gv.gGameTicks
    # gv.prod_total_effi_handicap1 = (
    #                                        total_time_cost_each_unit_each_player_prod_handicap1[:, effi_infantry_index].sum(
    #                                            1) * 100 * weight_infantry +
    #                                        total_time_cost_each_unit_each_player_prod_handicap1[:, effi_light_index].sum(
    #                                            1) * 100 * weight_light +
    #                                        total_time_cost_each_unit_each_player_prod_handicap1[:, effi_heavy_index].sum(
    #                                            1) * 100 * weight_heavy
    #                                ) / gv.gGameTicks

    # Production total time cost delicated handicap 1
    time_cost_details_prod_h1 = gv.units_produced * gv.unit_build_time_ticks_handicap1  # (8, 30) array
    gv.infantry_gameticks_delicated_production.append(time_cost_details_prod_h1[:, effi_infantry_index].sum(1))
    gv.light_gameticks_delicated_production.append(time_cost_details_prod_h1[:, effi_light_index].sum(1))
    gv.heavy_gameticks_delicated_production.append(time_cost_details_prod_h1[:, effi_heavy_index].sum(1))

    ###########################
    # 1.2 Starport efficiency
    ###########################
    total_time_cost_each_unit_each_player_starport = gv.units_from_starport * gv.unit_build_time_ticks_actual  # (8, 30) array

    gv.starport_infantry_effi = total_time_cost_each_unit_each_player_starport[:, effi_infantry_index].sum(
        1) * 100 / gv.gGameTicks  # (8, ) array
    gv.starport_light_effi = total_time_cost_each_unit_each_player_starport[:, effi_light_index].sum(
        1) * 100 / gv.gGameTicks  # (8, ) array
    gv.starport_heavy_effi = total_time_cost_each_unit_each_player_starport[:, effi_heavy_index].sum(
        1) * 100 / gv.gGameTicks  # (8, ) array

    # Starport total time cost delicated handicap 1
    time_cost_details_starport_h1 = gv.units_from_starport * gv.unit_build_time_ticks_handicap1  # (8, 30) array
    # gv.infantry_gameticks_delicated_starport.append(time_cost_details_starport_h1[:, effi_infantry_index].sum(1))
    gv.light_gameticks_delicated_starport.append(time_cost_details_starport_h1[:, effi_light_index].sum(1))
    gv.heavy_gameticks_delicated_starport.append(time_cost_details_starport_h1[:, effi_heavy_index].sum(1))

    ###########################
    # 1.3 Effi of light infantries gained by selling buildings
    ###########################
    light_infantries_from_selling = np.maximum(
        gv.units_owned[:, LIGHT_INFANTRY_INDEX] -
        gv.units_owned_at_start[:, LIGHT_INFANTRY_INDEX] -
        gv.units_produced[:, LIGHT_INFANTRY_INDEX],
        0
    )  # (8, )
    gv.light_infantry_by_selling_building_effi = light_infantries_from_selling * gv.unit_build_time_ticks_actual[:, LIGHT_INFANTRY_INDEX] * 100 / gv.gGameTicks  # (8, )

    # Infantry total time cost delicated handicap 1
    gv.infantry_gameticks_delicated_selling.append(light_infantries_from_selling * gv.unit_build_time_ticks_handicap1[LIGHT_INFANTRY_INDEX])  # (8, )

    ###########################
    # 1.4 Effi of harvesters gained by building refineries
    ###########################
    gv.harvesters_from_ref_effi = gv.harvs_from_ref[:, HARVESTER_INDEX] * gv.unit_build_time_ticks_actual[:, HARVESTER_INDEX] * 100 / gv.gGameTicks  # (8, )

    # Harvesters from refineries total time cost delicated handicap 1
    gv.heavy_gameticks_delicated_harvs_from_ref.append(gv.harvs_from_ref[:, HARVESTER_INDEX] * gv.unit_build_time_ticks_handicap1[HARVESTER_INDEX])  # (8, )

    ###########################
    # 1.5 Total effi
    ###########################
    # Total effi
    total_effi_units_excl_harv = gv.units_produced + gv.units_from_starport  # (8, 10)
    total_effi_units_excl_harv[:, LIGHT_INFANTRY_INDEX] += light_infantries_from_selling  # Enable this line if starting units are excluded
    # total_effi_units_excl_harv[:, LIGHT_INFANTRY_INDEX] = gv.units_owned[:, LIGHT_INFANTRY_INDEX]  # Enable this line if starting units are included
    total_effi_units_incl_harv = total_effi_units_excl_harv + gv.harvs_from_ref  # (8, 10)

    total_gametick_excl_harv = total_effi_units_excl_harv * gv.unit_build_time_ticks_actual  # (8, 30) array
    gv.total_effi_excluding_ref = total_gametick_excl_harv @ effi_unit_weights * 100 / gv.gGameTicks

    total_gametick_incl_harv = total_effi_units_incl_harv * gv.unit_build_time_ticks_actual  # (8, 30) array
    gv.total_effi_including_ref = total_gametick_incl_harv @ effi_unit_weights * 100 / gv.gGameTicks

    # Total effi handicap 1
    total_gametick_excl_harv_handicap1 = total_effi_units_excl_harv * gv.unit_build_time_ticks_handicap1  # (8, 30) array
    gv.weighted_sum_gameticks_excluding_ref_handicap1 = total_gametick_excl_harv_handicap1 @ effi_unit_weights  # (8, )
    gv.total_effi_excluding_ref_handicap1 = gv.weighted_sum_gameticks_excluding_ref_handicap1 * 100 / gv.gGameTicks

    total_gametick_incl_harv_handicap1 = total_effi_units_incl_harv * gv.unit_build_time_ticks_handicap1  # (8, 30) array
    gv.weighted_sum_gameticks_including_ref_handicap1 = total_gametick_incl_harv_handicap1 @ effi_unit_weights  # (8, )
    gv.total_effi_including_ref_handicap1 = gv.weighted_sum_gameticks_including_ref_handicap1 * 100 / gv.gGameTicks

    #
    #######################
    # 2. building efficiency
    #######################
    #
    total_time_cost_each_building_each_player = gv.buildings_owned * gv.building_build_time_ticks_actual  # (8, 62) array
    gv.building_efficiency = total_time_cost_each_building_each_player[:, effi_all_building_index].sum(
        1) * 100 / gv.gGameTicks

    # handicap 1
    total_time_cost_building_each_player_handicap1 = (
            gv.buildings_owned[:, effi_all_building_index] @ gv.building_build_time_ticks_handicap1[effi_all_building_index])
    gv.building_efficiency_handicap1 = (total_time_cost_building_each_player_handicap1 * 100 / gv.gGameTicks)

    ################
    # 3. Debug: check if the calculated units owned matches the cncnet's efficiency if calculated using the old implementation
    ################
    totalunits = gv.starting_units_excluding_mvc + total_effi_units_excl_harv + gv.harvs_from_ref
    totalunits[:, HARVESTER_INDEX] -= gv.refineries_owned  # Decrease harvester owned by refineries owned, but should not be below 0
    np.maximum(totalunits[:, HARVESTER_INDEX], 0, out=totalunits[:, HARVESTER_INDEX])  # Decrease harvester owned by refineries owned, but should not be below 0
    # Get wrong boost
    max_boost_wrong = np.array([
        {0: 250, 1: 225, 2: 200}.get(handi, 250) for handi in gv.player_handicaps  # wrong boost
    ])
    unit_progress_per_tick_wrong = np.maximum(np.outer(max_boost_wrong, gv.unit_build_speed) // 100, 1)  # dim: (8, 30)
    unit_build_time_ticks_actual_wrong = 23040 // unit_progress_per_tick_wrong  # dim: (8, 30)

    max_production = np.where(unit_build_time_ticks_actual_wrong > 0, gv.gGameTicks // unit_build_time_ticks_actual_wrong, 0)  # dim: (8, 30)
    efficiencies = np.zeros((8, NUM_UNITS))  # initialize a placeholder  # dim: (8, 30)
    # vectorized version of:
    # if max_production > 0:
    #     eff = units_owned / max_production
    # else:
    #     eff = 0
    np.divide(totalunits, max_production, out=efficiencies, where=(max_production > 0))
    temp_infantry_effi = efficiencies[:, effi_infantry_index].sum(1) * 100  # (8, ) array
    temp_light_effi = efficiencies[:, effi_light_index].sum(1) * 100  # (8, ) array
    temp_heavy_effi = efficiencies[:, effi_heavy_index].sum(1) * 100  # (8, ) array
    gv.debug_cncnet_effi = temp_infantry_effi * weight_infantry + temp_light_effi * weight_light + temp_heavy_effi * weight_heavy  # (8, ) array

    ##########
    # 4. Append the weighted sum of total time cost to list
    ##########
    # Update the total production time lists
    gv.append_data_to_list()

    ##########
    # 5. Delicated total time cost list update
    ##########
    N = len(gv.game_ticks_list)  # The current sample size: how many data points have already been captured.
    # N = len(gv.infantry_gameticks_delicated_production)  # Equivalent

    # 5.1 units_increment_buffer_production -> delicated production
    for gt, incr in gv.units_increment_buffer_production:
        incremented_prod_time = incr * gv.unit_build_time_ticks_handicap1  # (8, 30) array

        incremented_time_infantry = incremented_prod_time[:, effi_infantry_index].sum(1)  # (8, )
        incremented_time_light = incremented_prod_time[:, effi_light_index].sum(1)  # (8, )
        incremented_time_heavy = incremented_prod_time[:, effi_heavy_index].sum(1)  # (8, )

        for incremented_time, delicated_list in (
                (incremented_time_infantry, gv.infantry_gameticks_delicated_production),
                (incremented_time_light, gv.light_gameticks_delicated_production),
                (incremented_time_heavy, gv.heavy_gameticks_delicated_production),
        ):
            # if gt < incremented_time, then it can only be reinforcements at game start!
            prod_start_time = gt - incremented_time  # (8, ), for example: (gt, gt-100, gt, gt, ..., gt)
            max_incremented_time = incremented_time.max()  # integer
            idx_to_start_with = max(N - 1 - max_incremented_time // 60, 0)  # Maximum 60 gameticks per seconds. Last
            if idx_to_start_with < N - 1:
                for idx, time_cost_array in enumerate(delicated_list[idx_to_start_with: N-1], start=idx_to_start_with):
                    gametick_at_that_time = gv.game_ticks_list[idx]
                    time_cost_array += np.maximum(gametick_at_that_time - prod_start_time, 0)  # (8, )

    gv.units_increment_buffer_production = []  # Clear the buffer

    # 5.2 units_increment_buffer_starport -> delicated starport
    assumed_starport_cooldown = 2000  # game ticks. Distribute the time cost evenly into 2000 game ticks
    for gt, incr in gv.units_increment_buffer_starport:
        incremented_prod_time = incr * gv.unit_build_time_ticks_handicap1  # (8, 30) array

        # incremented_time_infantry = incremented_prod_time[:, effi_infantry_index].sum(1)  # (8, )
        incremented_time_light = incremented_prod_time[:, effi_light_index].sum(1)  # (8, )
        incremented_time_heavy = incremented_prod_time[:, effi_heavy_index].sum(1)  # (8, )

        for incremented_time, delicated_list in (
                # (incremented_time_infantry, gv.infantry_gameticks_delicated_starport),
                (incremented_time_light, gv.light_gameticks_delicated_starport),
                (incremented_time_heavy, gv.heavy_gameticks_delicated_starport),
        ):
            # if gt < incremented_time, then it can only be reinforcements at game start!
            prod_start_time = gt - assumed_starport_cooldown  # (8, ), for example: (gt, gt-100, gt, gt, ..., gt)
            max_incremented_time = assumed_starport_cooldown  # integer
            idx_to_start_with = max(N - 1 - max_incremented_time // 60, 0)  # Maximum 60 gameticks per seconds. Last
            if idx_to_start_with < N - 1:
                for idx, time_cost_array in enumerate(delicated_list[idx_to_start_with: N - 1], start=idx_to_start_with):
                    gametick_at_that_time = gv.game_ticks_list[idx]
                    time_cost_array += np.maximum(
                        gametick_at_that_time - prod_start_time,
                        0) * incremented_time // assumed_starport_cooldown  # (8, )

    gv.units_increment_buffer_starport = []  # Clear the buffer

    # 5.3 infantry gameticks from selling -> delicated infantry from selling
    if N > 1:
        incremented_time = gv.infantry_gameticks_delicated_selling[N - 1] - gv.infantry_gameticks_delicated_selling[N - 2]
        prod_start_time = gv.gGameTicks - incremented_time  # (8, ), for example: (gt, gt-51, gt, gt-102, ..., gt)
        max_incremented_time = incremented_time.max()  # integer
        idx_to_start_with = max(N - 1 - max_incremented_time // 60, 0)  # Maximum 60 gameticks per seconds. Last
        if idx_to_start_with < N - 1:
            for idx, time_cost_array in enumerate(gv.infantry_gameticks_delicated_selling[idx_to_start_with: N - 1], start=idx_to_start_with):
                gametick_at_that_time = gv.game_ticks_list[idx]
                time_cost_array += np.maximum(gametick_at_that_time - prod_start_time, 0)  # (8, )

    # 5.4 units_increment_buffer_harvs_from_ref -> delicated harvs from ref
    for gt, incr in gv.units_increment_buffer_harvs_from_ref:
        incremented_time_heavy = incr[:, HARVESTER_INDEX] * gv.unit_build_time_ticks_handicap1[HARVESTER_INDEX]  # (8, )

        for incremented_time, delicated_list in (
                # (incremented_time_infantry, gv.infantry_gameticks_delicated_harvs_from_ref),
                # (incremented_time_light, gv.light_gameticks_delicated_harvs_from_ref),
                (incremented_time_heavy, gv.heavy_gameticks_delicated_harvs_from_ref),
        ):
            # if gt < incremented_time, then it can only be reinforcements at game start!
            prod_start_time = gt - incremented_time  # (8, ), for example: (gt, gt-100, gt, gt, ..., gt)
            max_incremented_time = incremented_time.max()  # integer
            idx_to_start_with = max(N - 1 - max_incremented_time // 60, 0)  # Maximum 60 gameticks per seconds. Last
            if idx_to_start_with < N - 1:
                for idx, time_cost_array in enumerate(delicated_list[idx_to_start_with: N-1], start=idx_to_start_with):
                    gametick_at_that_time = gv.game_ticks_list[idx]
                    # print(f"increment on [{idx}]: {np.maximum(gametick_at_that_time - prod_start_time, 0)}")
                    time_cost_array += np.maximum(gametick_at_that_time - prod_start_time, 0)  # (8, )

    gv.units_increment_buffer_harvs_from_ref = []  # Clear the buffer

    gv.efficiency_stat_last_update_time = gv.gGameTicks

def _update_units_lost():
    """
    Update the units_lost game variable
    """
    gv.units_lost = np.stack([
        read_array(UNITS_LOST_TABLE + PLAYER_DATA_LENGTH * i, ctypes.c_uint32, NUM_UNITS) for i in range(8)
    ])

def _update_units_killed():
    """
    Update the units_killed_detail game variable
    """
    gv.units_killed_detail = np.stack([
        read_u32_table(UNITS_KILLED_TABLE + PLAYER_DATA_LENGTH * i, shape=(NUM_UNITS, 8)) for i in range(8)
    ])
    gv.units_killed = gv.units_killed_detail.sum(axis=2)


def update_unit_scores():
    """
    Update the
    """
    _update_units_lost()
    _update_units_killed()

    gv.total_units_killed_count = gv.units_killed.sum(axis=1)
    gv.total_units_lost_count = gv.units_lost.sum(axis=1)
    gv.total_units_killed_cost = gv.units_killed @ gv.unit_cost_handicap1
    gv.total_units_lost_cost = gv.units_lost @ gv.unit_cost_handicap1
    gv.total_units_killed_train_time = gv.units_killed @ gv.unit_build_time_ticks_handicap1
    gv.total_units_lost_train_time = gv.units_lost @ gv.unit_build_time_ticks_handicap1


def update_expenses():
    gv.unit_expense_handicap1 = (gv.units_produced + gv.units_from_starport) @ gv.unit_cost_handicap1
    gv.building_expense_handicap1 = gv.buildings_owned[:, effi_all_building_index] @ gv.building_cost_handicap1[effi_all_building_index]
