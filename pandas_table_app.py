# import tkinter as tk
from tkinter import ttk
from gamedata.gamevars import game_vars as gv
from memrw import (
    color_idx_to_name,
    side_idx_to_name,
    color_idx_to_hex_string,
    unit_group_idx_to_name,
    building_group_idx_to_name
)
# import numpy as np
import pandas as pd
from pandastable import Table
from enums import *
from gamedata.unitsdata import *


# from datetime import timedelta

def get_groups_stats(values_array, indices_array, num_groups: int):
    """
    :param values_array: 2-d array
    :param indices_array: 1-d array
    :param num_groups: int
    :return:
    """
    groups_stats = np.zeros((8, num_groups), dtype=np.int32)
    np.add.at(
        groups_stats,
        (slice(None), indices_array),
        values_array
    )
    return groups_stats

class PandasTableApp:
    def __init__(self, master: ttk.Frame):
        self.root = master
        # self.root.title('Dune2000 Game Stats Helper')

        # Initialize the pandastable frame
        # self.table_frame = ttk.Frame(self.root)
        # self.table_frame.pack(fill=tk.BOTH, expand=True)

        self.table = None  # Placeholder for the actual table that links to summary_df
        self.summary_df = None  # The pandas dataframe holding the summary data
        self.last_update_gametick = -1  # Game tick when the table was last updated

    def force_redraw(self):
        if self.table is not None and self.summary_df is not None:
            self.table.redraw()

    def set_cells_color(self):
        # This serves as a placeholder
        raise NotImplementedError("Subclasses must implement set_cells_color method!")

    def get_data_table(self):
        # This serves as a placeholder
        raise NotImplementedError("Subclasses must implement get_data_table method!")

    def update_table(self):
        """
        Run every second. Must make sure gv.number_of_player >= 2
        Can only be called when the get_data_table() returns a DataFrame containing real data!\
        :return:
        """
        if gv.number_of_player < 2:  # Failed to connect
            return

        self.summary_df = self.get_data_table()  # Update the related info and get the data

        if self.table is None:
            # If the table hasn't been created, create it
            self.table = Table(self.root, dataframe=self.summary_df, showtoolbar=False, showstatusbar=False)
            # Once the table is linked to a dataframe, then the UI will auto refresh when drag-and-drop the UI, or when functions like redraw() or setRowColors() is called

            self.table.showIndex()
            self.table.show()  # This method will call adjustColumnWidths() which overwrite the custom columnwidths。 Also initialize the related attributes
            self.table.columnwidths = {col: 168 for col in self.summary_df.columns}  # Set default column width
            self.table.rowheader.maxwidth = 240  # Manually set default row header width, suggested by dmnfarrell
            # self.set_cells_color()
            # self.table.redraw()  # See if this is needed
        else:
            # If the table exists, need to manually update it! So weird
            self.table.model.df = self.summary_df

        self.set_cells_color()  # This forces a refresh on the UI, i.e. redraw the table? No!
        self.table.redraw()

        self.last_update_gametick = gv.gGameTicks

    def reset_table(self):
        if self.table is not None:
            self.table = None  # Reset the table attribute to None
        if self.summary_df is not None:
            self.summary_df = None  # Reset the underlying pandas df
        self.last_update_gametick = -1


class SummaryTable(PandasTableApp):
    def set_cells_color(self):
        if gv.number_of_player < 2:  # Game failed to start
            return
        if 'Handicap' in self.summary_df.index:
            handicap_row_index = self.summary_df.index.get_loc("Handicap")

            # Highlight handicap2 in light red
            handicap2_players = list(
                np.where(gv.player_handicaps[:gv.number_of_player] == 1)[0])  # must convert to list
            self.table.setRowColors(rows=[handicap_row_index], clr="#FFCCCC", cols=handicap2_players)
            # Highlight handicap3 in light purple
            handicap3_players = list(np.where(gv.player_handicaps[:gv.number_of_player] > 1)[0])  # must convert to list
            self.table.setRowColors(rows=[handicap_row_index], clr="#E5CCFF", cols=handicap3_players)

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

    def get_data_table(self):
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
            ("Victory Status",
             [victory_status_dict.get(pl_vc, "Unknown") for pl_vc in gv.victory_status[:gv.number_of_player]]),
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
            ("Harvesters Owned",
             gv.units_produced[:, HARVESTER_INDEX] + gv.units_from_starport[:, HARVESTER_INDEX] + gv.harvs_from_ref[:, HARVESTER_INDEX]),
            ("Refineries Owned", gv.refineries_owned),
            ("Starport Deliveries", gv.units_owned[:, 26]),
            ("Average OPM", [f"{pl_opm:.2f}" for pl_opm in avg_OPM]),

            # ("Effi Building", [f"{pl_ef:.2f}%" for pl_ef in gv.building_efficiency]),
            ("Effi Building (handicap1)", [f"{pl_ef:.2f}%" for pl_ef in gv.building_efficiency_handicap1]),

            ("Effi Infantry Prod (+Sell)", [f"{ef1:.2f} (+{ef2:.2f})" for ef1, ef2 in
                                            zip(gv.prod_infantry_effi, gv.light_infantry_by_selling_building_effi)]),
            ("Effi Light Prod (+Starport)",
             [f"{ef1:.2f} (+{ef2:.2f})" for ef1, ef2 in zip(gv.prod_light_effi, gv.starport_light_effi)]),
            ("Effi Heavy Prod (+Starport +Refi)", [f"{ef1:.2f} (+{ef2:.2f} +{ef3:.2f})" for ef1, ef2, ef3 in
                                                   zip(gv.prod_heavy_effi, gv.starport_heavy_effi,
                                                       gv.harvesters_from_ref_effi)]),

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


class DetailsTable(PandasTableApp):
    def set_cells_color(self):
        # print("DetailsTable set_cells_color called!")
        if gv.number_of_player < 2:  # Game failed to start
            return

        # Color stripe:
        for rw in [
            "Buildings Owned Count",
            "Buildings Killed Count",
            "Buildings Lost Count",
            "Buildings Owned Score",
            "Buildings Killed Score",
            "Buildings Lost Score",
        ]:
            if rw in self.summary_df.index:
                row_idx = self.summary_df.index.get_loc(rw)
                self.table.setRowColors(rows=[row_idx], clr="#E0E0E0", cols="all")

    def get_data_table(self):
        """
        :return: A pandas dataframe
        """
        # print("DetailsTable get_data_table called!")

        # debug
        # def print_array(arr):
        #     # Nested loop to print the array in a format similar to print(arr)
        #     for i in range(arr.shape[0]):
        #         print("[")  # Start of a new "slice" along the first dimension
        #         for j in range(arr.shape[1]):
        #             print("  [", end="")  # Start of a new row
        #             for k in range(arr.shape[2]):
        #                 print(f"{arr[i, j, k]:2}", end="")  # Print element with padding
        #                 if k < arr.shape[2] - 1:
        #                     print(",", end=" ")  # Add comma and space if not the last element
        #             print("]", end="")
        #             if j < arr.shape[1] - 1:
        #                 print(",")
        #             else:
        #                 print("")
        #
        #         if i < arr.shape[0] - 1:
        #             print(" ],")  # End of the slice, add comma if not the last slice
        #         else:
        #             print("]")
        #     print("]")  # Close the last bracket
        #
        # print_array(gv.buildings_killed_detail)

        # Use np stack to optimize performance.

        df_data = np.stack([
            gv.units_owned.sum(axis=1),  # Units Owned Count (Raw)
            gv.units_owned_clean.sum(axis=1),  # Units Owned Count (Clean)
            gv.units_killed.sum(axis=1),  # Units Killed Count
            gv.units_lost.sum(axis=1),  # Units Lost Count
            gv.buildings_owned.sum(axis=1),  # Buildings Owned Count
            gv.buildings_killed.sum(axis=1),  # Buildings Killed Count
            gv.buildings_lost.sum(axis=1),  # Buildings Lost Count

            gv.units_owned @ gv.unit_cost_handicap1,  # Units Owned Score (Raw)
            gv.units_owned_clean @ gv.unit_cost_handicap1,  # Units Owned Score (Clean)
            gv.units_killed @ gv.unit_cost_handicap1,  # Units Killed Score
            gv.units_lost @ gv.unit_cost_handicap1,  # Units Lost Score
            gv.buildings_owned @ gv.building_cost_handicap1,  # Buildings Owned Score
            gv.buildings_killed @ gv.building_cost_handicap1,  # Buildings Killed Score
            gv.buildings_lost @ gv.building_cost_handicap1,  # Buildings Lost Score
        ])[:, :gv.number_of_player]

        # Convert to DataFrame
        df = pd.DataFrame(df_data, index=[
            "Units Owned Count (Raw)",
            "Units Owned Count (Clean)",
            "Units Killed Count",
            "Units Lost Count",
            "Buildings Owned Count",
            "Buildings Killed Count",
            "Buildings Lost Count",

            "Units Owned Score (Raw)",
            "Units Owned Score (Clean)",
            "Units Killed Score",
            "Units Lost Score",
            "Buildings Owned Score",
            "Buildings Killed Score",
            "Buildings Lost Score",
        ])
        df.columns = gv.player_names
        return df

class UnitsOwnedCleanTable(PandasTableApp):
    def set_cells_color(self):
        if gv.number_of_player < 2:  # Game failed to start
            return

    def get_data_table(self):
        """
        :return: A pandas dataframe
        """
        df = pd.DataFrame(
            get_groups_stats(gv.units_owned_clean, gv.unit_group_index, NUM_UNIT_GROUPS)[:gv.number_of_player, :].T,
            index=unit_group_idx_to_name.values()
        )
        df.columns = gv.player_names
        return df


class TotalOwnedTable(PandasTableApp):
    def set_cells_color(self):
        if gv.number_of_player < 2:  # Game failed to start
            return

    def get_data_table(self):
        """
        :return: A pandas dataframe
        """
        df_data = np.vstack((
            get_groups_stats(gv.units_owned, gv.unit_group_index, NUM_UNIT_GROUPS)[:gv.number_of_player, :].T,
            get_groups_stats(gv.buildings_owned, gv.building_group_index, NUM_BUILDING_GROUPS)[:gv.number_of_player, :].T,
        ))
        df = pd.DataFrame(
            df_data,
            index=list(unit_group_idx_to_name.values()) + list(building_group_idx_to_name.values())
        )
        df.columns = gv.player_names
        return df


class TotalKilledTable(PandasTableApp):
    def set_cells_color(self):
        if gv.number_of_player < 2:  # Game failed to start
            return

    def get_data_table(self):
        """
        :return: A pandas dataframe
        """
        df_data = np.vstack((
            get_groups_stats(gv.units_killed, gv.unit_group_index, NUM_UNIT_GROUPS)[:gv.number_of_player, :].T,
            get_groups_stats(gv.buildings_killed, gv.building_group_index, NUM_BUILDING_GROUPS)[:gv.number_of_player, :].T,
        ))
        df = pd.DataFrame(
            df_data,
            index=list(unit_group_idx_to_name.values()) + list(building_group_idx_to_name.values())
        )
        df.columns = gv.player_names
        return df


class TotalLostTable(PandasTableApp):
    def set_cells_color(self):
        if gv.number_of_player < 2:  # Game failed to start
            return

    def get_data_table(self):
        """
        :return: A pandas dataframe
        """
        df_data = np.vstack((
            get_groups_stats(gv.units_lost, gv.unit_group_index, NUM_UNIT_GROUPS)[:gv.number_of_player, :].T,
            get_groups_stats(gv.buildings_lost, gv.building_group_index, NUM_BUILDING_GROUPS)[:gv.number_of_player, :].T,
        ))
        df = pd.DataFrame(
            df_data,
            index=list(unit_group_idx_to_name.values()) + list(building_group_idx_to_name.values())
        )
        df.columns = gv.player_names
        return df
