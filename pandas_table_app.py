import tkinter as tk
from tkinter import ttk
from gamedata.gamevars import game_vars as gv
from memrw import color_idx_to_name, side_idx_to_name, color_idx_to_hex_string
# import numpy as np
import pandas as pd
from pandastable import Table
from enums import *
from gamedata.unitsdata import *
from datetime import timedelta


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
        self.table_frame = ttk.Frame(self.root)
        self.table_frame.pack(fill=tk.BOTH, expand=True)

        self.table = None  # Placeholder for the actual table that links to summary_df
        self.summary_df = None  # The pandas dataframe holding the summary data
        self.last_update_gametick = -1  # Game tick when the table was last updated

    def force_redraw(self):
        if self.table is not None and self.summary_df is not None:
            self.table.redraw()

    def set_cells_color(self):
        if gv.number_of_player < 2:  # Game failed to start
            return
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
        Run every second. Must make sure gv.number_of_player >= 2
        Can only be called when the get_data_table() returns a DataFrame containing real data!\
        :return:
        """
        if gv.number_of_player < 2:  # Failed to connect
            return

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
