# import numpy as np
from .unitsdata import *
from datetime import timedelta, datetime

class GameVariable:
    def __init__(self):
        # Need to divide the vars into 2 categories:
        # (1) vars initialized when program starts
        # (2) vars initialized/refreshed/reset when game starts
        self._initialize_attributes()

    def _initialize_attributes(self):
        self.gGameState = 1
        self.game_finished = False  # True when some player wins

        self.spawner_active = False  # SpawnerActive, set at game start
        self.game_end_state = 0  # GameEndState or SpawnerGameEndState, set at game start

        # True: Using cncnet lobby to start game, implying isMultiplayer is True
        # False: Not using cncnet to start game
        self.is_cnc = False

        # True: Pratice/vs Human, using GameSave\Pxx.SAV
        # False: mission/campaign, using GameSave\Sxx.SAV
        self.is_multiplayer = False

        # True: CNCnet game, more than 1 human when game start, will use 0x798630 to store player names
        # False: not True
        self.more_than_1_human = False

        self.MeIsSpectator = False

        self.map_width = 0
        self.map_height = 0
        self.game_width = 0  # local resolution x
        self.game_height = 0  # local resolution y

        self.map_name = ""
        self.gNetMap = ""  # map hash
        self.gNetMap_cnc = ""  # map hash (cnc)

        self.me = 0  # local_player_index
        self.my_offset = 0  # local_player_offset = local_player_index * 0x26990

        self.first_loop_of_positive_gametick_finished = False  # Run 1 time when game ticks > 0
        # Times
        self.game_start_timestamp = 0  # datetime object
        self.game_start_timestamp_utc = 0  # datetime object (UTC)
        self.elapsed_real_sec = 0  # float, in seconds, = (real_timestamp - game_start_timestamp).total_seconds()
        self.real_second = 0
        self.real_second_prev = 0
        self.gGameTicks = 0
        self.gGameTicks_prev = 0
        self.game_tick_diff = 0

        self.real_timestamp = datetime.now()  # datetime object
        self.real_timestamp_prev = datetime.now()  # datetime object (previous loop)
        self.real_timestamp_diff = timedelta(seconds=0)  # timedelta object
        self.real_timestamp_diff_sec = 0  # float, in seconds

        self.effective_sec_float = 0  # Derived from gGameTicks, integer
        self.effective_sec = 0  # Derived from gGameTicks, timedelta
        self.average_game_speed = 1  # Derived from gGameTicks, real_sec

        self.number_of_AI = 0  # 0x4E3B0C, gNetAIPlayers
        self.number_of_human = 0  # 0x7984C0, NetPlayerCount
        self.number_of_player = 0  # playerCount = NetPlayerCount + gNetAIPlayers
        self.number_of_remaining_player = 0  # Players that are not yet winned, defeated.

        self.NetPlayerCount = -1  # debug. 0x7984C0, NetPlayerCount
        self.NetPlayerCount_prev = -1  # debug. 0x7984C0, NetPlayerCount
        ############################
        # Local info (mouse ...)
        ############################
        # self.mouse_is_at_map = False
        # self.mouse_pos_map_pixel_x = 0  # Mouse pos relative to the whole map
        # self.mouse_pos_map_pixel_y = 0  # Mouse pos relative to the whole map
        # self.mouse_pos_view_pixel_x = 0  # Mouse pos relative to the current view
        # self.mouse_pos_view_pixel_y = 0  # Mouse pos relative to the current view
        # self.mouse_pos_map_tile_x = 0
        # self.mouse_pos_map_tile_y = 0

        ############################
        # Player info
        ############################
        self.player_numbers = [0] * 8
        self.player_names = []
        self.is_player = np.full(8, False, dtype=bool)   # initialized once. First n elements are True, n being total number of players
        self.is_spectator = np.full(8, False, dtype=bool)   # initialized once
        self.has_nothing = np.full(8, True, dtype=bool)   # True: no unit or building. Used for victory checking
        self.is_defeated = np.full(8, False, dtype=bool)  # True: not in game, False: in game. True when first time has_nothing, but might still be spectating. Used for finishing place.
        self.has_quitted = np.full(8, False, dtype=bool)   # True: has quitted program, game ticks no longer increases. False: hasn't quitted yet. Only apply to humna players.
        self.finishing_place = np.full(8, 1, dtype=np.int8)
        self.gDeadOrder = np.full(8, -1, dtype=np.int8)  # 0x797B70 char array
        # self.gDeadOrder_prev = np.full(8, -1, dtype=np.int8)  # 0x797B70 char array
        self.mutual_alliance_matrix = np.full((8, 8), False, dtype=bool)  # type: np.ndarray
        self.victory_status = np.zeros(8, dtype=np.int8)
        self.start_location = np.full(8, -1, dtype=np.int8)  # initialized once
        self.player_handicaps = np.zeros(8, dtype=int)  # initialized once
        self.player_colors = [0] * 8  # initialized once
        self.player_sides = [0] * 8  # initialized once
        self.player_teams = [0] * 8
        self.non_spectator_player_index = []  # initialized once
        self.dict_teamable_index_to_player_index = {}  # initialized once
        self.num_teams = 8

        ############################
        # Efficiency related
        ############################
        self.max_boost = np.zeros(8, dtype=int)  # initialized once
        self.max_boost_handicap1 = 100  # initialized once

        ############################
        # Basic units and building stats
        ############################
        self.building_cost = np.zeros(NUM_BUILDINGS, dtype=int)  # initialized once
        self.building_build_speed = np.zeros(NUM_BUILDINGS, dtype=int)  # initialized once
        self.building_progress_per_tick = np.zeros((8, NUM_UNITS), dtype=int)  # initialized once
        self.building_build_time_ticks_actual = np.zeros((8, NUM_BUILDINGS), dtype=int)  # initialized once

        self.unit_cost = np.zeros(NUM_UNITS, dtype=int)  # initialized once
        self.unit_build_speed = np.zeros(NUM_UNITS, dtype=int)  # initialized once
        self.unit_progress_per_tick = np.zeros((8, NUM_UNITS), dtype=int)  # initialized once
        self.unit_build_time_ticks_actual = np.zeros((8, NUM_UNITS), dtype=int)  # initialized once
        # handicap 1 stat:
        self.building_cost_handicap1 = np.zeros(NUM_BUILDINGS, dtype=int)  # initialized once
        self.unit_cost_handicap1 = np.zeros(NUM_UNITS, dtype=int)  # initialized once
        self.building_progress_per_tick_handicap1 = np.zeros(NUM_UNITS, dtype=int)  # initialized once
        self.building_build_time_ticks_handicap1 = np.zeros(NUM_BUILDINGS, dtype=int)  # initialized once
        self.unit_progress_per_tick_handicap1 = np.zeros(NUM_UNITS, dtype=int)  # initialized once
        self.unit_build_time_ticks_handicap1 = np.zeros(NUM_UNITS, dtype=int)  # initialized once

        self.buildings_owned = np.zeros((8, NUM_BUILDINGS), dtype=int)  # 8 players, 62 types of buildings
        self.units_owned = np.zeros((8, NUM_UNITS), dtype=int)  # 8 players, 30 types of units
        self.units_owned_at_start = np.zeros((8, NUM_UNITS), dtype=int)  # initialized once when game tick > 0
        self.starting_units_excluding_mvc = np.zeros((8, NUM_UNITS), dtype=int)  # initialized once when game tick > 0, together with units_owned_at_start, used to calculate cncnet effi

        self.units_lost = np.zeros((8, NUM_UNITS), dtype=int)  # 8 players, 62 types of buildings
        self.units_killed_detail = np.zeros((8, NUM_UNITS, 8), dtype=int)  # 8 players, 30 types of units, 8 p
        self.units_killed = np.zeros((8, NUM_UNITS), dtype=int)  # 8 players, 30 types of units, 8 p

        self.refineries_owned = np.zeros(8, dtype=int)  # Updated when _update_buildings_owned() is called
        # Used for calculating efficiency
        # Only limited types of units are counted
        # self.units_owned_effi = np.zeros((8, NUM_UNITS), dtype=int)  # later unused
        #
        # self.infantry_effi = np.zeros(8)  # later unused
        # self.light_effi = np.zeros(8)  # later unused
        # self.heavy_effi = np.zeros(8)  # later unused
        # self.total_effi = np.zeros(8)  # later unused
        #
        # self.total_effi_handicap1 = np.zeros(8)  # later unused

        # Unused?
        self.last_units_owned = np.zeros((8, NUM_UNITS), dtype=int)  # 8 players, 30 types of units

        #######################
        # Begin: Must be run in every loop!
        ######################
        # Actual efficiency, tracking all build slots
        self.build_slot_progress = np.zeros((8, 10), dtype=int)  # 8 players, 10 slots
        self.last_build_slot_progress = np.zeros((8, 10), dtype=int)  # 8 players, 10 slots
        self.build_unit_type = np.full((8, 10), -1, dtype=np.int16)  # 8 players, 10 slots
        self.last_build_unit_type = np.full((8, 10), -1, dtype=np.int16)  # 8 players, 10 slots
        self.build_slot_on_hold = np.zeros((8, 10), dtype=bool)  # 8 players, 10 slots
        self.last_build_slot_on_hold = np.zeros((8, 10), dtype=bool)  # 8 players, 10 slots

        # Units from delivery
        self.delivery_queues = np.full((8, 10, 40), -1, dtype=int)  # 8 players, 10 queues, 40 slots per queue
        self.last_delivery_queues = np.full((8, 10, 40), -1, dtype=int)  # 8 players, 10 queues, 40 slots per queue

        # Store the units owned from different sources:
        # (1) Directly produced
        self.units_produced = np.zeros((8, NUM_UNITS), dtype=int)  # 8 players, 30 types of units
        # (2) From starport delivery
        self.units_from_starport = np.zeros((8, NUM_UNITS), dtype=int)  # starport purchase + reinforments
        # (3) From carryall delivery
        self.reinforcements_from_carryall = np.zeros((8, NUM_UNITS), dtype=int)  # Carryall reinforcement (excluding from ref)
        self.harvs_from_ref = np.zeros((8, NUM_UNITS), dtype=int)  # Harvesters delivered when refineries are built
        # (1)+(2)+(3) should equal to units_owned - units_owned_at_start, at index [1:18].
        # For index 0 (light infantry), the latter contains light infantries obtained from selling buildings
        # For index after 18, they might not match. For example: carryall2, choamfrigate, Ornithopter (x3), Fremen (x2)

        # If no Ordos deviators, then (For units index 1 to 18):
        # units_owned = units_owned_at_start + units_produced + units_from_starport + reinforcements_from_carryall + harvs_from_ref

        # Buffers: list of tuples, where each tuple is (gameticks, numpy array of size (8, 30)), all integers, number of units
        self.units_increment_buffer_production = []  # production increment
        self.units_increment_buffer_harvs_from_ref = []  # harvs from ref increment
        self.units_increment_buffer_starport = []  # a starport units increment
        # # # No "units_increment_buffer_infantry_from_selling", this increment can be obtained from the infantry_gameticks_delicated_selling

        self.starport_delivery_times = [
            [], [], [], [], [], [], [], []
        ]  # list of list, each player's star port delivery game ticks list
        ######################
        # End.
        ######################

        ######################
        # Efficiency Statistics (used when updating the stats), run once when update_efficiencies is called
        ######################
        self.efficiency_stat_last_update_time = -1  # game ticks
        # Always use the production time (game ticks) according to the current player's handicap, unless otherwise stated.
        # Units
        self.prod_infantry_effi = np.zeros(8)
        self.prod_light_effi = np.zeros(8)
        self.prod_heavy_effi = np.zeros(8)
        self.prod_total_effi = np.zeros(8)  # total production efficiency
        self.prod_total_effi_handicap1 = np.zeros(8)  # total production efficiency (Using production time of handicap1)

        self.starport_infantry_effi = np.zeros(8)  # not used
        self.starport_light_effi = np.zeros(8)
        self.starport_heavy_effi = np.zeros(8)

        self.light_infantry_by_selling_building_effi = np.zeros(8)
        self.harvesters_from_ref_effi = np.zeros(8)

        self.total_effi_excluding_ref = np.zeros(8)  # prod + starport + light infantries from selling
        self.total_effi_including_ref = np.zeros(8)  # prod + starport + light infantries from selling + harvesters from refineries

        self.total_effi_excluding_ref_handicap1 = np.zeros(8)  # prod + starport + light infantries from selling (Using production time of handicap1)
        self.total_effi_including_ref_handicap1 = np.zeros(8)  # prod + starport + light infantries from selling + harvesters from refineries (Using production time of handicap1)

        self.debug_cncnet_effi = np.zeros(8)  # Check against cncnet's efficiency. Will be removed.

        # Data lists used by plot
        self.weighted_sum_gameticks_excluding_ref_handicap1 = np.zeros(8)  # / gameticks = total_effi_excluding_ref_handicap1
        self.weighted_sum_gameticks_including_ref_handicap1 = np.zeros(8)  # / gameticks = total_effi_including_ref_handicap1

        self.weighted_sum_gameticks_excluding_ref_handicap1_list = []  # list version, appended every second
        self.weighted_sum_gameticks_including_ref_handicap1_list = []  # list version, appended every second
        self.game_ticks_list = []  # list of game ticks, appended every second
        self.elapsed_real_sec_list = []  # list of game ticks, appended every second

        self.harvester_count_list = []  # list of current harvesters owned
        self.credits_list = []  # list of credits

        # Delicated production weighted sums, list of np.array of length 8, each element being the weighted sum of production time
        # self.total_prod_gameticks_delicated_excl_starport_list = []  # appended every second, with backward increment, in handicap 1
        # self.total_prod_gameticks_delicated_starport_list = []  # appended every second, with backward increment, in handicap 1

        self.infantry_gameticks_delicated_production = []  # production - infantry  # list of (8, 30)
        self.light_gameticks_delicated_production = []  # production - light  # list of (8, 30)
        self.heavy_gameticks_delicated_production = []  # production - heavy  # list of (8, 30)

        # self.infantry_gameticks_delicated_starport = []  # starport - infantry
        self.light_gameticks_delicated_starport = []  # starport - light  # list of (8, 30)
        self.heavy_gameticks_delicated_starport = []  # starport - heavy  # list of (8, 30)

        # self.infantry_gameticks_delicated_harvs_from_ref= []  # harvs_from_ref - infantry
        # self.light_gameticks_delicated_harvs_from_ref = []  # harvs_from_ref - light
        self.heavy_gameticks_delicated_harvs_from_ref = []  # harvs_from_ref - heavy  # list of (8, )

        self.infantry_gameticks_delicated_selling = []  # selling - infantry  # list of (8, )
        # # self.light_gameticks_delicated_selling = []  # selling - light
        # self.heavy_gameticks_delicated_selling = []  # selling - heavy

        # Buildings
        self.building_efficiency = np.zeros(8)
        self.building_efficiency_handicap1 = np.zeros(8)

        # Other calculated
        self.total_units_killed_count = np.zeros(8, dtype=int)
        self.total_units_lost_count = np.zeros(8, dtype=int)
        self.total_units_killed_cost = np.zeros(8, dtype=int)
        self.total_units_lost_cost = np.zeros(8, dtype=int)
        self.total_units_killed_train_time = np.zeros(8, dtype=int)
        self.total_units_lost_train_time = np.zeros(8, dtype=int)

        self.unit_expense_handicap1 = np.zeros(8, dtype=int)
        self.building_expense_handicap1 = np.zeros(8, dtype=int)

        # Manually calculate efficiency (tracking units produced)
        self.units_produced = np.zeros((8, NUM_UNITS), dtype=int)
        self.producing_slots_unit_type = np.zeros((8, 10), dtype=int)
        self.producing_slots_unit_type = np.zeros((8, 10), dtype=int)

        ############################
        # Other live stats
        ############################
        self.barracks_owning = [0] * 8
        self.lightfac_owning = [0] * 8
        self.heavyfac_owning = [0] * 8
        self.having_3_barracks_ticks = [0] * 8
        self.having_3_light_ticks = [0] * 8
        self.having_3_heavy_ticks = [0] * 8
        self.low_power_ticks = [0] * 8
        self.low_power_time_actual = np.zeros(8, dtype=float)

        self.spice = np.zeros(8, dtype=int)  # credits = cash + spice
        self.spice_before_defeated = np.zeros(8, dtype=int)  # credits_before_defeated = cash + spice_before_defeated
        self.spice_capacity = np.zeros(8, dtype=int)
        self.spice_buffer = np.zeros(8, dtype=int)
        self.cash = np.zeros(8, dtype=int)  # credits = cash + spice
        self.spice_harvested = np.zeros(8, dtype=int)

        self.last_spice = np.zeros(8, dtype=int)
        self.last_spice_harvested = np.zeros(8, dtype=int)
        self.last_spice_buffer = np.zeros(8, dtype=int)
        self.spice_wasted = [0] * 8
        self.spice_wasted2 = [0] * 8  # a difference algorithm

        self.harvester_count_before_defeated = np.zeros(8, dtype=int)  # Current harvesters owned, before defeated
        self.harvester_count = np.zeros(8, dtype=int)  # Current harvesters owned

        self.total_orders_received = np.zeros(8, dtype=int)  # OPM related
        self.left_game_at = np.zeros(8, dtype=int)  # Game tick when the player left game

        # Internet related
        self.received_game_ticks = np.zeros(8, dtype=int)  # Current game ticks of player. 0x6B91F8
        self.potential_laggers = np.array([])  # The players having the lowest current game ticks
        self.total_freeze_seconds = np.zeros(8, dtype=float)  # Cumulative Network-Induced Freeze Duration per Player (seconds)

        ############################
        # Developing
        ############################
        self.uncaptured_command_number_last = [0] * 8

        #############
        # Debugging
        #############
        self.debug_info_repeat_time = 0

    def append_data_to_list(self):
        """
        Only upto number of players
        :return:
        """
        self.game_ticks_list.append(self.gGameTicks)
        self.elapsed_real_sec_list.append(self.elapsed_real_sec)
        self.weighted_sum_gameticks_excluding_ref_handicap1_list.append(self.weighted_sum_gameticks_excluding_ref_handicap1[:self.number_of_player])
        self.weighted_sum_gameticks_including_ref_handicap1_list.append(self.weighted_sum_gameticks_including_ref_handicap1[:self.number_of_player])

        self.harvester_count_list.append(self.harvester_count)
        self.credits_list.append(self.spice + self.cash)

    def clear(self):
        self._initialize_attributes()


game_vars = GameVariable()  # The global game variables instance
