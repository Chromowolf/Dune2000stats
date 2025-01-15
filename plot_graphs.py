from gamedata import NUM_BUILDING_GROUPS
from gamedata.gamevars import game_vars as gv
import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.ticker import MaxNLocator
from enums import color_idx_to_hex_string, TEAM_INDEX_NONE
from gamedata.unitsdata import (
    CARRYALL_INDEX,
    CARRYALL2_INDEX,
    CHOAM_FRIGATE_INDEX,
    HARVESTER_INDEX,
    NUM_UNITS,
    CONSTRUCTION_YARD_BUILDING_GROUP_INDEX,
    BARRACKS_BUILDING_GROUP_INDEX,
    LIGHT_FACTORY_BUILDING_GROUP_INDEX,
    HEAVY_FACTORY_BUILDING_GROUP_INDEX,
    effi_unit_weights,
    effi_infantry_index,
    effi_light_index,
    effi_heavy_index,
)

# debug
def print_2d_array(arr):
    for row in arr:
        print(' '.join(map(str, row)))

def diff_and_fill_np_1d(arr, period=1):
    """
    Rolling difference along axis 1 of a 2-d numpy array
    :param arr: 2-d numpy array
    :param period: values to shift
    :return: The differenced array
    """
    result = arr.copy()

    if period < arr.shape[0]:
        result[period:] = arr[period:] - arr[:-period]
    return result

def diff_and_fill_np_2d(arr, period=1):
    """
    Rolling difference along axis 1 of a 2-d numpy array
    :param arr: 2-d numpy array of shape (n_player, n_obs)
    :param period: values to shift
    :return: The differenced array
    """
    result = arr.copy()

    if period < arr.shape[1]:
        result[:, period:] = arr[:, period:] - arr[:, :-period]
    return result


def create_ts_plot_at_frame(frame, x, y,
                            title=None, xlabel=None, ylabel=None,
                            stacked=False, proportion=False, colors=None, legend_labels=None, integer_yticks=True,
                            **kwargs):
    """
    If proportion is True, then stacked is automatically true
    Args:
        frame: the tk frame
        x: 1d array of shape (n_obs,)
        y: 2d array of shape (n_player, n_obs), a horizontal matrix
        title: Custom title
        xlabel:
        ylabel:
        stacked: Boolean
        proportion: Boolean
        colors: iterable of length y.shape[0], specifying the color code
        legend_labels: iterable of length y.shape[0], specifying the legend texts
        integer_yticks: whether to use only integer as Y ticks for the non-proportion plots

    Returns: Figure object
    """
    fig = plt.Figure(figsize=(6, 4), dpi=100)
    ax = fig.add_subplot(111)  # 1x1 grid, and this is the first (and only) subplot.
    n_line = y.shape[0]

    # if not colors:
    #     colors = [None] * n_line
    if not legend_labels:
        legend_labels = [f"Series {i}" for i in range(n_line)]

    if proportion:  # Proportion
        # stacked = True
        row_sums = y.sum(axis=0)  # Sum across col
        proportions = np.divide(y, row_sums, where=(row_sums != 0),
                                out=np.full_like(y, 0, dtype=float))
        ax.stackplot(x, proportions, colors=colors, labels=legend_labels)  # Stack plot of proportion
        ax.axhline(y=0.5, color='white', linestyle='--', alpha=0.8)
        ax.legend(loc='upper left')
        ax.set_xlabel("Time" if not xlabel else xlabel)
        ax.set_ylabel("Proportion" if not ylabel else ylabel)
        ax.set_ylim(top=1)
        ax.set_title("Time Series Plot (Proportion)" if not title else title)
    else:
        if stacked:  # Stacked
            # ax.stackplot(x, y, baseline='wiggle', colors=colors, labels=legend_labels)  # Stack plot of proportion
            ax.stackplot(x, y, colors=colors, labels=legend_labels)  # Stack plot of proportion
            ax.legend(loc='upper left')
            ax.set_xlabel("Time" if not xlabel else xlabel)
            ax.set_ylabel("Number" if not ylabel else ylabel)
            ax.set_title("Time Series Plot (Stacked)" if not title else title)
            if integer_yticks:
                ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        else:  # Line
            # ax.plot(x, y.T)  # Stack plot of proportion
            # ax.legend([f"Series{i}" for i in range(n_line)], loc='upper left')
            for i in range(n_line):
                ax.plot(x, y[i, :], color=colors[i] if colors else None, label=legend_labels[i])
            ax.legend(loc='upper left')
            ax.set_xlabel("Time" if not xlabel else xlabel)
            ax.set_ylabel("Number" if not ylabel else ylabel)
            ax.set_title("Time Series Plot (Line)" if not title else title)
            if integer_yticks:
                ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    ax.grid(True)
    ax.set_xlim(left=kwargs.get('xlim_left', 0), right=kwargs.get('xlim_right'))
    ax.set_ylim(bottom=kwargs.get('ylim_bottom', 0), top=kwargs.get('ylim_top'))

    hline_y = kwargs.get('hline_y', None)
    if hline_y is not None:
        # noinspection all
        ax.axhline(y=hline_y, color='grey', linestyle='--', alpha=0.3)

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()

    toolbar = NavigationToolbar2Tk(canvas, frame, pack_toolbar=False)
    toolbar.update()
    toolbar.pack(side=tk.BOTTOM, fill=tk.X)

    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)


class Plots:
    def __init__(self):
        self.colors: list = []
        self.labels: list = []
        self.is_real_player = np.zeros(8, dtype=bool)
        self.num_real_players = 0
        self.player_idx_to_plot = np.array([], dtype=np.int8)

    def update_basics(self):
        """
        Update calors and labels according to current gv
        """
        self.is_real_player = gv.is_player & (~gv.is_spectator)  # shape (8, ), bool
        self.num_real_players = self.is_real_player.sum()
        if (gv.player_team_idx == TEAM_INDEX_NONE).all():
            # Old version, gv.player_team_idx not define
            self.player_idx_to_plot = np.where(self.is_real_player)[0]
        else:
            # gv.player_index_by_teams = np.argsort(gv.player_team_idx)  # Debug
            self.player_idx_to_plot = gv.player_index_by_teams[:self.num_real_players]
        self.colors = [
            color_idx_to_hex_string.get(gv.player_colors[i], "#000000")
            for i in self.player_idx_to_plot
        ]
        self.labels = [gv.player_names[i] for i in self.player_idx_to_plot]

    def plot_economy(self, root):
        plot_window = tk.Toplevel(root)
        plot_window.title("Economy Plots")
        plot_window.geometry("1280x720")

        if not hasattr(gv, "game_ticks_list") or not gv.game_ticks_list:
            ttk.Label(plot_window, text="No game data!", style="yahei20.TLabel").pack()
            return

        # Create a Notebook (tabs)
        notebook = ttk.Notebook(plot_window)
        notebook.pack(expand=True, fill="both")
        self.update_basics()

        #############
        # Credits
        #############
        credits_frame_line = ttk.Frame(notebook)
        notebook.add(credits_frame_line, text="Credits (Line)")
        credits_frame_stacked = ttk.Frame(notebook)
        notebook.add(credits_frame_stacked, text="Credits (Stacked)")
        credits_frame_proportion = ttk.Frame(notebook)
        notebook.add(credits_frame_proportion, text="Credits (Proportion)")

        if not hasattr(gv, "credits_list") or not gv.credits_list:
            ttk.Label(credits_frame_line, text="No credits data found!", style="yahei20.TLabel").pack()
            ttk.Label(credits_frame_stacked, text="No credits data found!", style="yahei20.TLabel").pack()
            ttk.Label(credits_frame_proportion, text="No credits data found!", style="yahei20.TLabel").pack()
        else:
            credit_data_2d = np.stack(gv.credits_list, axis=1)[self.player_idx_to_plot, :]  # Stack arrays vertically
            # --- Create the first tab (Normal) ---
            create_ts_plot_at_frame(credits_frame_line, gv.game_ticks_list, credit_data_2d, stacked=False,
                                    proportion=False,
                                    colors=self.colors, legend_labels=self.labels, title="Credits (Line Plot)")

            # --- Create the 2nd tab (Normal stacked) ---
            create_ts_plot_at_frame(credits_frame_stacked, gv.game_ticks_list, credit_data_2d, stacked=True,
                                    proportion=False, colors=self.colors, legend_labels=self.labels,
                                    title="Credits (Stacked Plot)")

            # --- Create the 3rd tab (Proportion Plot) ---
            create_ts_plot_at_frame(credits_frame_proportion, gv.game_ticks_list, credit_data_2d, stacked=True,
                                    proportion=True, colors=self.colors, legend_labels=self.labels,
                                    title="Credits (Stacked Proportion Plot)")

        #############
        # Harvesters
        #############
        harv_frame_line = ttk.Frame(notebook)
        notebook.add(harv_frame_line, text="Harvester Count (Line)")
        harv_frame_stacked = ttk.Frame(notebook)
        notebook.add(harv_frame_stacked, text="Harvester Count (Stacked)")
        harv_frame_proportion = ttk.Frame(notebook)
        notebook.add(harv_frame_proportion, text="Harvester Count (Proportion)")

        if not hasattr(gv, "units_count_list") or not gv.units_count_list:
            ttk.Label(harv_frame_line, text="No harvesters data found!", style="yahei20.TLabel").pack()
            ttk.Label(harv_frame_stacked, text="No harvesters data found!", style="yahei20.TLabel").pack()
            ttk.Label(harv_frame_proportion, text="No harvesters data found!", style="yahei20.TLabel").pack()
        else:
            harv_data_list = [units_data[:, HARVESTER_INDEX] for units_data in gv.units_count_list]
            harv_data_2d = np.stack(harv_data_list, axis=1)[self.player_idx_to_plot, :]  # Stack arrays vertically
            # --- Create the first tab (Normal) ---
            create_ts_plot_at_frame(harv_frame_line, gv.game_ticks_list, harv_data_2d, stacked=False, proportion=False,
                                    colors=self.colors, legend_labels=self.labels,
                                    title="Harvesters Currently Owned (Line Plot)")

            # --- Create the 2nd tab (Normal stacked) ---
            create_ts_plot_at_frame(harv_frame_stacked, gv.game_ticks_list, harv_data_2d, stacked=True,
                                    proportion=False,
                                    colors=self.colors, legend_labels=self.labels,
                                    title="Harvesters Currently Owned (Stacked Plot)")

            # --- Create the 3rd tab (Proportion Plot) ---
            create_ts_plot_at_frame(harv_frame_proportion, gv.game_ticks_list, harv_data_2d, stacked=True,
                                    proportion=True,
                                    colors=self.colors, legend_labels=self.labels,
                                    title="Harvesters Currently Owned (Stacked Proportion Plot)")

    def plot_units_owned(self, root):
        plot_window = tk.Toplevel(root)
        plot_window.title("Units Plot")
        plot_window.geometry("1280x720")
        if not hasattr(gv, "game_ticks_list") or not gv.game_ticks_list:
            ttk.Label(plot_window, text="No game data!", style="yahei20.TLabel").pack()
            return

        # Create a Notebook (tabs)
        notebook = ttk.Notebook(plot_window)
        notebook.pack(expand=True, fill="both")
        self.update_basics()

        units_count_frame_line = ttk.Frame(notebook)
        notebook.add(units_count_frame_line, text="Units Count (Line)")

        units_count_frame_stacked = ttk.Frame(notebook)
        notebook.add(units_count_frame_stacked, text="Units Count (Stacked)")

        units_count_frame_proportion = ttk.Frame(notebook)
        notebook.add(units_count_frame_proportion, text="Units Count (Proportion)")

        units_value_frame_line = ttk.Frame(notebook)
        notebook.add(units_value_frame_line, text="Units Value (Line)")

        units_value_frame_stacked = ttk.Frame(notebook)
        notebook.add(units_value_frame_stacked, text="Units Value (Stacked)")

        units_value_frame_proportion = ttk.Frame(notebook)
        notebook.add(units_value_frame_proportion, text="Units Value (Proportion)")

        if not hasattr(gv, "units_count_list") or not gv.units_count_list:
            ttk.Label(units_count_frame_line, text="No units data found!", style="yahei20.TLabel").pack()
            ttk.Label(units_count_frame_stacked, text="No units data found!", style="yahei20.TLabel").pack()
            ttk.Label(units_count_frame_proportion, text="No units data found!", style="yahei20.TLabel").pack()
            ttk.Label(units_value_frame_line, text="No units data found!", style="yahei20.TLabel").pack()
            ttk.Label(units_value_frame_stacked, text="No units data found!", style="yahei20.TLabel").pack()
            ttk.Label(units_value_frame_proportion, text="No units data found!", style="yahei20.TLabel").pack()
        else:
            units_data_3d = np.stack(gv.units_count_list, axis=1)  # get (8, n, NUM_UNITS)

            unit_cost_arr = gv.unit_cost_handicap1.astype(np.int64)  # shape (NUM_UNITS, ). astype auto creates a copy
            unit_ones = np.ones(NUM_UNITS, dtype=np.int64)
            unit_cost_arr[[CARRYALL_INDEX, CARRYALL2_INDEX, CHOAM_FRIGATE_INDEX]] = 0  # setting irrelevent units to 0
            unit_ones[[CARRYALL_INDEX, CARRYALL2_INDEX, CHOAM_FRIGATE_INDEX]] = 0  # setting irrelevent units to 0

            unit_counts_2d_8p = units_data_3d @ unit_ones  # (8, n)
            unit_counts_2d = unit_counts_2d_8p[self.player_idx_to_plot, :]

            unit_values_2d_8p = units_data_3d @ unit_cost_arr  # (8, n)
            unit_values_2d = unit_values_2d_8p[self.player_idx_to_plot, :]

            # --- Create the first tab (Normal) ---
            create_ts_plot_at_frame(units_count_frame_line, gv.game_ticks_list, unit_counts_2d, stacked=False,
                                    proportion=False,
                                    colors=self.colors, legend_labels=self.labels,
                                    title="Units Currently Owned Count (Line Plot)")

            # --- Create the 2nd tab (Normal stacked) ---
            create_ts_plot_at_frame(units_count_frame_stacked, gv.game_ticks_list, unit_counts_2d, stacked=True,
                                    proportion=False, colors=self.colors, legend_labels=self.labels,
                                    title="Units Currently Owned Count (Stacked Plot)")

            # --- Create the 3rd tab (Proportion Plot) ---
            create_ts_plot_at_frame(units_count_frame_proportion, gv.game_ticks_list, unit_counts_2d, stacked=True,
                                    proportion=True, colors=self.colors, legend_labels=self.labels,
                                    title="Units Currently Owned Count (Stacked Proportion Plot)")

            # --- Create the first tab (Normal) ---
            create_ts_plot_at_frame(units_value_frame_line, gv.game_ticks_list, unit_values_2d, stacked=False,
                                    proportion=False,
                                    colors=self.colors, legend_labels=self.labels,
                                    title="Value of Units Currently Owned (Line Plot)")

            # --- Create the 2nd tab (Normal stacked) ---
            create_ts_plot_at_frame(units_value_frame_stacked, gv.game_ticks_list, unit_values_2d, stacked=True,
                                    proportion=False, colors=self.colors, legend_labels=self.labels,
                                    title="Value of Units Currently Owned (Stacked Plot)")

            # --- Create the 3rd tab (Proportion Plot) ---
            create_ts_plot_at_frame(units_value_frame_proportion, gv.game_ticks_list, unit_values_2d, stacked=True,
                                    proportion=True, colors=self.colors, legend_labels=self.labels,
                                    title="Value of Units Currently Owned (Stacked Proportion Plot)")

    def plot_buildings(self, root):
        plot_window = tk.Toplevel(root)
        plot_window.title("Buildings Plots")
        plot_window.geometry("1280x720")
        if not hasattr(gv, "game_ticks_list") or not gv.game_ticks_list:
            ttk.Label(plot_window, text="No game data!", style="yahei20.TLabel").pack()
            return

        # Create a Notebook (tabs)
        notebook = ttk.Notebook(plot_window)
        notebook.pack(expand=True, fill="both")
        self.update_basics()

        buildings_count_frame_line = ttk.Frame(notebook)
        notebook.add(buildings_count_frame_line, text="Buildings Count (Line)")

        buildings_count_frame_stacked = ttk.Frame(notebook)
        notebook.add(buildings_count_frame_stacked, text="Buildings Count (Stacked)")

        buildings_count_frame_proportion = ttk.Frame(notebook)
        notebook.add(buildings_count_frame_proportion, text="Buildings Count (Proportion)")

        buildings_value_frame_line = ttk.Frame(notebook)
        notebook.add(buildings_value_frame_line, text="Buildings Value (Line)")

        buildings_value_frame_stacked = ttk.Frame(notebook)
        notebook.add(buildings_value_frame_stacked, text="Buildings Value (Stacked)")

        buildings_value_frame_proportion = ttk.Frame(notebook)
        notebook.add(buildings_value_frame_proportion, text="Buildings Value (Proportion)")

        construction_yard_count_frame = ttk.Frame(notebook)
        notebook.add(construction_yard_count_frame, text="Contruction Yard")

        barracks_count_frame = ttk.Frame(notebook)
        notebook.add(barracks_count_frame, text="Barracks")

        light_factory_count_frame = ttk.Frame(notebook)
        notebook.add(light_factory_count_frame, text="Light Factory")

        heavy_factory_count_frame = ttk.Frame(notebook)
        notebook.add(heavy_factory_count_frame, text="Heavy Factory")

        # Test

        if not hasattr(gv, "building_groups_count_list") or not gv.building_groups_count_list:
            ttk.Label(buildings_count_frame_line, text="No buildings data found!", style="yahei20.TLabel").pack()
            ttk.Label(buildings_count_frame_stacked, text="No buildings data found!", style="yahei20.TLabel").pack()
            ttk.Label(buildings_count_frame_proportion, text="No buildings data found!", style="yahei20.TLabel").pack()
            ttk.Label(buildings_value_frame_line, text="No buildings data found!", style="yahei20.TLabel").pack()
            ttk.Label(buildings_value_frame_stacked, text="No buildings data found!", style="yahei20.TLabel").pack()
            ttk.Label(buildings_value_frame_proportion, text="No buildings data found!", style="yahei20.TLabel").pack()

            ttk.Label(construction_yard_count_frame, text="No buildings data found!", style="yahei20.TLabel").pack()
            ttk.Label(barracks_count_frame, text="No buildings data found!", style="yahei20.TLabel").pack()
            ttk.Label(light_factory_count_frame, text="No buildings data found!", style="yahei20.TLabel").pack()
            ttk.Label(heavy_factory_count_frame, text="No buildings data found!", style="yahei20.TLabel").pack()
        else:
            buildings_data_3d = np.stack(gv.building_groups_count_list, axis=1)  # get (8, n, NUM_BUILDING_GROUPS)

            building_cost_arr = gv.building_cost_handicap1.astype(
                np.int64)  # shape (NUM_BUILDINGs, ). astype auto creates a copy
            building_group_avg_cost = np.array(
                [
                    np.sum(building_cost_arr[gv.building_group_index == i]) // np.sum(gv.building_group_index == i)
                    if np.sum(gv.building_group_index == i) > 0 else 0
                    for i in range(NUM_BUILDING_GROUPS)
                ],
                dtype=np.int64
            )  # shape (NUM_BUILDING_GROUPS, ). Calculate the average cost within each building group

            building_ones = np.ones(NUM_BUILDING_GROUPS, dtype=np.int64)

            buildings_counts_2d_8p = buildings_data_3d @ building_ones  # (8, n)
            buildings_counts_2d = buildings_counts_2d_8p[self.player_idx_to_plot, :]

            buildings_values_2d_8p = buildings_data_3d @ building_group_avg_cost  # (8, n)
            buildings_values_2d = buildings_values_2d_8p[self.player_idx_to_plot, :]

            # --- Create the first tab (Normal) ---
            create_ts_plot_at_frame(buildings_count_frame_line, gv.game_ticks_list, buildings_counts_2d, stacked=False,
                                    proportion=False,
                                    colors=self.colors, legend_labels=self.labels,
                                    title="Buildings Currently Owned Count (Line Plot)")

            # --- Create the 2nd tab (Normal stacked) ---
            create_ts_plot_at_frame(buildings_count_frame_stacked, gv.game_ticks_list, buildings_counts_2d,
                                    stacked=True,
                                    proportion=False, colors=self.colors, legend_labels=self.labels,
                                    title="Buildings Currently Owned Count (Stacked Plot)")

            # --- Create the 3rd tab (Proportion Plot) ---
            create_ts_plot_at_frame(buildings_count_frame_proportion, gv.game_ticks_list, buildings_counts_2d,
                                    stacked=True,
                                    proportion=True, colors=self.colors, legend_labels=self.labels,
                                    title="Buildings Currently Owned Count (Stacked Proportion Plot)")

            # --- Create the first tab (Normal) ---
            create_ts_plot_at_frame(buildings_value_frame_line, gv.game_ticks_list, buildings_values_2d, stacked=False,
                                    proportion=False,
                                    colors=self.colors, legend_labels=self.labels,
                                    title="Value of Buildings Currently Owned (Line Plot)")

            # --- Create the 2nd tab (Normal stacked) ---
            create_ts_plot_at_frame(buildings_value_frame_stacked, gv.game_ticks_list, buildings_values_2d,
                                    stacked=True,
                                    proportion=False, colors=self.colors, legend_labels=self.labels,
                                    title="Value of Buildings Currently Owned (Stacked Plot)")

            # --- Create the 3rd tab (Proportion Plot) ---
            create_ts_plot_at_frame(buildings_value_frame_proportion, gv.game_ticks_list, buildings_values_2d,
                                    stacked=True,
                                    proportion=True, colors=self.colors, legend_labels=self.labels,
                                    title="Value of Buildings Currently Owned (Stacked Proportion Plot)")

            # Factories counts
            cy_count_data = buildings_data_3d[self.player_idx_to_plot, :, CONSTRUCTION_YARD_BUILDING_GROUP_INDEX]
            barracks_count_data = buildings_data_3d[self.player_idx_to_plot, :, BARRACKS_BUILDING_GROUP_INDEX]
            light_fac_count_data = buildings_data_3d[self.player_idx_to_plot, :, LIGHT_FACTORY_BUILDING_GROUP_INDEX]
            heavy_fac_count_data = buildings_data_3d[self.player_idx_to_plot, :, HEAVY_FACTORY_BUILDING_GROUP_INDEX]

            create_ts_plot_at_frame(construction_yard_count_frame, gv.game_ticks_list, cy_count_data, stacked=False,
                                    proportion=False,
                                    colors=self.colors, legend_labels=self.labels,
                                    title="Construction Yards Currently Owned Count (Line Plot)")

            create_ts_plot_at_frame(barracks_count_frame, gv.game_ticks_list, barracks_count_data, stacked=False,
                                    proportion=False,
                                    colors=self.colors, legend_labels=self.labels,
                                    title="Barracks Currently Owned Count (Line Plot)")

            create_ts_plot_at_frame(light_factory_count_frame, gv.game_ticks_list, light_fac_count_data, stacked=False,
                                    proportion=False,
                                    colors=self.colors, legend_labels=self.labels,
                                    title="Light Factories Currently Owned Count (Line Plot)")

            create_ts_plot_at_frame(heavy_factory_count_frame, gv.game_ticks_list, heavy_fac_count_data, stacked=False,
                                    proportion=False,
                                    colors=self.colors, legend_labels=self.labels,
                                    title="Heavy Factories Currently Owned Count (Line Plot)")

    def plot_kills(self, root):
        plot_window = tk.Toplevel(root)
        plot_window.title("Kills Plots")
        plot_window.geometry("1280x720")
        if not hasattr(gv, "game_ticks_list") or not gv.game_ticks_list:
            ttk.Label(plot_window, text="No game data!", style="yahei20.TLabel").pack()
            return

        # Create a Notebook (tabs)
        notebook = ttk.Notebook(plot_window)
        notebook.pack(expand=True, fill="both")
        self.update_basics()

        units_killed_count_frame = ttk.Frame(notebook)
        notebook.add(units_killed_count_frame, text="Units Killed Count")

        units_killed_value_frame = ttk.Frame(notebook)
        notebook.add(units_killed_value_frame, text="Units Killed Score")

        if not hasattr(gv, "units_killed_detail_list") or not gv.units_killed_detail_list:
            ttk.Label(units_killed_count_frame, text="Units killed detail data not found!", style="yahei20.TLabel").pack()
            ttk.Label(units_killed_value_frame, text="Units killed detail data not found!", style="yahei20.TLabel").pack()
            return

        units_killed_per_4d = np.stack(gv.units_killed_detail_list)  # (n, 8, NUM_UNITS, 8)
        units_killed_3d = units_killed_per_4d.sum(axis=3)  # (n, 8, NUM_UNITS)

        units_killed_cost_arr = gv.unit_cost_handicap1.astype(np.int64)  # shape (NUM_UNITS, ). astype auto creates a copy

        units_killed_counts_2d = units_killed_3d.sum(axis=2)[:, self.player_idx_to_plot].T  # (n_player, n_obs)
        units_killed_values_2d = (units_killed_3d @ units_killed_cost_arr)[:, self.player_idx_to_plot].T  # (n_player, n_obs)

        create_ts_plot_at_frame(
            units_killed_count_frame,
            gv.game_ticks_list,
            units_killed_counts_2d, stacked=False, proportion=False,
            colors=self.colors, legend_labels=self.labels,
            title="Cumulated Units Killed Count"
        )

        create_ts_plot_at_frame(
            units_killed_value_frame,
            gv.game_ticks_list,
            units_killed_values_2d, stacked=False, proportion=False,
            colors=self.colors, legend_labels=self.labels,
            title="Values of Cumulated Units Killed"
        )

    def plot_powers(self, root):
        plot_window = tk.Toplevel(root)
        plot_window.title("Power Plots")
        plot_window.geometry("1280x720")
        if not hasattr(gv, "game_ticks_list") or not gv.game_ticks_list:
            ttk.Label(plot_window, text="No game data!", style="yahei20.TLabel").pack()
            return

        # Create a Notebook (tabs)
        notebook = ttk.Notebook(plot_window)
        notebook.pack(expand=True, fill="both")
        self.update_basics()

        power_percent_frame = ttk.Frame(notebook)
        notebook.add(power_percent_frame, text="Power Percent")

        power_output_frame = ttk.Frame(notebook)
        notebook.add(power_output_frame, text="Power Output")

        power_drained_frame = ttk.Frame(notebook)
        notebook.add(power_drained_frame, text="Power Drained")

        if not hasattr(gv, "power_output_list") or not gv.power_output_list:
            ttk.Label(power_percent_frame, text="No powers data found!", style="yahei20.TLabel").pack()
            ttk.Label(power_output_frame, text="No powers data found!", style="yahei20.TLabel").pack()
            ttk.Label(power_drained_frame, text="No powers data found!", style="yahei20.TLabel").pack()
        else:
            power_output_2d = np.stack(gv.power_output_list, axis=1)[self.player_idx_to_plot, :]  # get (p, n)
            power_drained_2d = np.stack(gv.power_drained_list, axis=1)[self.player_idx_to_plot, :]  # get (p, n)
            if not hasattr(gv, "has_buildings_list") or not gv.has_buildings_list:
                has_buildings_2d = np.full((self.num_real_players, len(gv.power_drained_list)), True, dtype=bool)
            else:
                has_buildings_2d = np.stack(gv.has_buildings_list, axis=1)[self.player_idx_to_plot, :]

            power_percent_2d = np.floor_divide(
                power_output_2d * 100,
                power_drained_2d,
                where=(power_drained_2d != 0),
                out=np.where(has_buildings_2d, 200, 0)
            )

            create_ts_plot_at_frame(power_percent_frame, gv.game_ticks_list, power_percent_2d, stacked=False,
                                    proportion=False,
                                    colors=self.colors, legend_labels=self.labels, hline_y=100,
                                    title="Power Percent Over Time")

            create_ts_plot_at_frame(power_output_frame, gv.game_ticks_list, power_output_2d, stacked=False,
                                    proportion=False,
                                    colors=self.colors, legend_labels=self.labels, title="Power Output Over Time")

            # --- Create the 3rd tab (Proportion Plot) ---
            create_ts_plot_at_frame(power_drained_frame, gv.game_ticks_list, power_drained_2d, stacked=False,
                                    proportion=False,
                                    colors=self.colors, legend_labels=self.labels, title="Power Drained Over Time")

    def plot_apms(self, root):
        plot_window = tk.Toplevel(root)
        plot_window.title("APM Plots")
        plot_window.geometry("1280x720")
        if not hasattr(gv, "game_ticks_list") or not gv.game_ticks_list:
            ttk.Label(plot_window, text="No game data!", style="yahei20.TLabel").pack()
            return

        # Create a Notebook (tabs)
        notebook = ttk.Notebook(plot_window)
        notebook.pack(expand=True, fill="both")
        self.update_basics()

        instant_apm_frame = ttk.Frame(notebook)
        notebook.add(instant_apm_frame, text="Instant APM")

        avg_apm_frame = ttk.Frame(notebook)
        notebook.add(avg_apm_frame, text="Average APM")

        if not hasattr(gv, "total_orders_received_list") or not gv.total_orders_received_list:
            ttk.Label(instant_apm_frame, text="No instant APM data found!", style="yahei20.TLabel").pack()
            ttk.Label(avg_apm_frame, text="No instant APM data found!", style="yahei20.TLabel").pack()
        else:
            total_actions_2d = np.stack(gv.total_orders_received_list, axis=1)[self.player_idx_to_plot, :]  # (n_player, n_obs)
            elapsed_real_sec_arr = np.array(gv.elapsed_real_sec_list)

            avg_apm_2d = np.divide(
                total_actions_2d * 60, elapsed_real_sec_arr, where=(elapsed_real_sec_arr != 0),
                out=np.full_like(total_actions_2d, 0, dtype=float)
            )
            create_ts_plot_at_frame(avg_apm_frame, gv.game_ticks_list, avg_apm_2d, stacked=False,
                                    proportion=False,
                                    colors=self.colors, legend_labels=self.labels, hline_y=60, title="Average APM Over Time")

            total_actions_2d_roll_diff = diff_and_fill_np_2d(total_actions_2d, period=20)
            elapsed_real_sec_roll_diff = diff_and_fill_np_1d(elapsed_real_sec_arr, period=20)
            instant_apm_2d = np.divide(
                total_actions_2d_roll_diff * 60, elapsed_real_sec_roll_diff, where=(elapsed_real_sec_roll_diff != 0),
                out=np.full_like(total_actions_2d_roll_diff, 0, dtype=float)
            )  # (n_player, n_obs)
            create_ts_plot_at_frame(instant_apm_frame, gv.game_ticks_list, instant_apm_2d, stacked=False,
                                    proportion=False,
                                    colors=self.colors, legend_labels=self.labels, hline_y=60, title="Instant APM Over Time")

    def plot_efficiency(self, root):
        plot_window = tk.Toplevel(root)
        plot_window.title("Efficiency Plots")
        plot_window.geometry("1280x720")
        if not hasattr(gv, "game_ticks_list") or not gv.game_ticks_list:
            ttk.Label(plot_window, text="No game data!", style="yahei20.TLabel").pack()
            return

        # Create a Notebook (tabs)
        notebook = ttk.Notebook(plot_window)
        notebook.pack(expand=True, fill="both")
        self.update_basics()

        average_total_efficiency_frame = ttk.Frame(notebook)
        notebook.add(average_total_efficiency_frame, text="Avg Total Effi")

        cumulated_total_train_time_frame = ttk.Frame(notebook)
        notebook.add(cumulated_total_train_time_frame, text="Cumu Train Time")

        average_infantry_efficiency_frame = ttk.Frame(notebook)
        notebook.add(average_infantry_efficiency_frame, text="Avg Infantry Effi")

        average_light_efficiency_frame = ttk.Frame(notebook)
        notebook.add(average_light_efficiency_frame, text="Avg Light Effi")

        average_heavy_efficiency_frame = ttk.Frame(notebook)
        notebook.add(average_heavy_efficiency_frame, text="Avg Heavy Effi")

        instant_total_efficiency_frame = ttk.Frame(notebook)
        notebook.add(instant_total_efficiency_frame, text="Instant Total Effi")

        # Instant efficiency: not quite usefule
        instant_infantry_efficiency_frame = ttk.Frame(notebook)
        notebook.add(instant_infantry_efficiency_frame, text="Instant Infantry Effi")

        instant_light_efficiency_frame = ttk.Frame(notebook)
        notebook.add(instant_light_efficiency_frame, text="Instant Light Effi")

        instant_heavy_efficiency_frame = ttk.Frame(notebook)
        notebook.add(instant_heavy_efficiency_frame, text="Instant Heavy Effi")

        # weighted_sum_from_gv_2d = np.stack(gv.weighted_sum_gameticks_including_ref_handicap1_list)  # (n, num_player)
        # weighted_sum_gameticks_2d_trimmed = weighted_sum_gameticks_2d[:, :gv.number_of_player]  # (n, num_player)
        #
        # test_diff = weighted_sum_gameticks_2d_trimmed - weighted_sum_from_gv_2d
        # print("test_diff:")
        # print(f"All equal? {(test_diff == 0).all()}")
        # print_2d_array(test_diff[:100, :])

        # print("gv.units_owned_at_start:")
        # print_2d_array(gv.units_owned_at_start)
        #
        # ttt = np.zeros((8, 30), dtype=np.int32)
        # for i in range(4):
        #     cur = units_owned_clean_3d[i, :, :]
        #     print(f"Current game ticks: {gv.game_ticks_list[i]}")
        #     print_2d_array(cur)
        #     print(f"cur == last? {(ttt == cur).all()}")
        #     ttt = cur.copy()
        #     print("\n")

        # print(weighted_sum_gameticks_2d[:, :gv.number_of_player] == weighted_sum_from_gv_2d)

        if not hasattr(gv, "units_owned_clean_list") or not gv.units_owned_clean_list:
            ttk.Label(instant_total_efficiency_frame, text="No efficiency data found!", style="yahei20.TLabel").pack()
            ttk.Label(average_total_efficiency_frame, text="No efficiency data found!", style="yahei20.TLabel").pack()
            ttk.Label(cumulated_total_train_time_frame, text="No efficiency data found!", style="yahei20.TLabel").pack()
            ttk.Label(instant_infantry_efficiency_frame, text="No efficiency data found!", style="yahei20.TLabel").pack()
            ttk.Label(instant_light_efficiency_frame, text="No efficiency data found!", style="yahei20.TLabel").pack()
            ttk.Label(instant_heavy_efficiency_frame, text="No efficiency data found!", style="yahei20.TLabel").pack()
            ttk.Label(average_infantry_efficiency_frame, text="No efficiency data found!", style="yahei20.TLabel").pack()
            ttk.Label(average_light_efficiency_frame, text="No efficiency data found!", style="yahei20.TLabel").pack()
            ttk.Label(average_heavy_efficiency_frame, text="No efficiency data found!", style="yahei20.TLabel").pack()
            return

        units_owned_clean_excl_start_3d = np.stack(gv.units_owned_clean_list) - gv.units_owned_at_start  # (n, 8, 30), need to exclude starting_units
        total_gametick_per_player_per_unit_3d = units_owned_clean_excl_start_3d * gv.unit_build_time_ticks_handicap1  # (n, 8, 30) * (30, ) = (n, 8, 30)
        weighted_sum_gameticks_2d = total_gametick_per_player_per_unit_3d @ effi_unit_weights  # (n, 8, 30) @ (30, ) = (n, 8), float
        create_ts_plot_at_frame(
            cumulated_total_train_time_frame, gv.game_ticks_list, weighted_sum_gameticks_2d[:, self.player_idx_to_plot].T, stacked=False,
            proportion=False,
            colors=self.colors, legend_labels=self.labels, title="Weighted Sum of Cumulated Units Owned Train Time (Total Efficiency = Y/X)"
        )

        game_tick_arr = np.stack(gv.game_ticks_list)
        weighted_sum_gameticks_2d_horizontal = weighted_sum_gameticks_2d[:, self.player_idx_to_plot].T  # (n_player, n_obs)
        avg_total_effi = np.divide(
            weighted_sum_gameticks_2d_horizontal, game_tick_arr, where=(game_tick_arr != 0),
            out=np.full_like(weighted_sum_gameticks_2d_horizontal, 0, dtype=float)
        )
        create_ts_plot_at_frame(
            average_total_efficiency_frame, gv.game_ticks_list,
            avg_total_effi, stacked=False,
            proportion=False,
            colors=self.colors, legend_labels=self.labels,
            title="Total Efficiency Over Time",
            integer_yticks=False
        )

        diff_period = 15
        select_every = 20

        weighted_sum_2d_roll_diff = diff_and_fill_np_2d(weighted_sum_gameticks_2d_horizontal, period=diff_period)  # (n_player, n_obs)
        game_tick_roll_diff = diff_and_fill_np_1d(game_tick_arr, period=diff_period)  # (n_obs, )
        instant_effi_2d = np.divide(
            weighted_sum_2d_roll_diff, game_tick_roll_diff, where=(game_tick_roll_diff != 0),
            out=np.full_like(weighted_sum_2d_roll_diff, 0, dtype=float)
        )
        create_ts_plot_at_frame(
            instant_total_efficiency_frame, gv.game_ticks_list[::select_every],
            instant_effi_2d[:, ::select_every], stacked=False,
            proportion=False,
            colors=self.colors, legend_labels=self.labels,
            title="Instant Efficiency Over Time",
            integer_yticks=False
        )

        if not hasattr(gv, "units_produced_list") or not gv.units_produced_list:
            ttk.Label(instant_infantry_efficiency_frame, text="Units produced time series data not found!", style="yahei20.TLabel").pack()
            ttk.Label(instant_light_efficiency_frame, text="Units produced time series data not found!", style="yahei20.TLabel").pack()
            ttk.Label(instant_heavy_efficiency_frame, text="Units produced time series data not found!", style="yahei20.TLabel").pack()
            ttk.Label(average_infantry_efficiency_frame, text="Units produced time series data not found!", style="yahei20.TLabel").pack()
            ttk.Label(average_light_efficiency_frame, text="Units produced time series data not found!", style="yahei20.TLabel").pack()
            ttk.Label(average_heavy_efficiency_frame, text="Units produced time series data not found!", style="yahei20.TLabel").pack()
            return

        # Efficient of barracks, light, and heavy:
        units_produced_3d = np.stack(gv.units_produced_list)  # (n, 8, 30)
        units_produced_time_cost_per_player_per_unit_3d = units_produced_3d * gv.unit_build_time_ticks_handicap1  # (n, 8, 30) * (30, ) = (n, 8, 30)
        units_produced_time_cost_per_player_per_unit_3d = units_produced_time_cost_per_player_per_unit_3d[:, self.player_idx_to_plot, :]  # (n, n_player, 30)

        infantry_produced_time_cost_2d = units_produced_time_cost_per_player_per_unit_3d[:, :, effi_infantry_index].sum(axis=2).T  # (n_player, n_obs)
        light_produced_time_cost_2d = units_produced_time_cost_per_player_per_unit_3d[:, :, effi_light_index].sum(axis=2).T  # (n_player, n_obs)
        heavy_produced_time_cost_2d = units_produced_time_cost_per_player_per_unit_3d[:, :, effi_heavy_index].sum(axis=2).T  # (n_player, n_obs)

        avg_infantry_effi = np.divide(
            infantry_produced_time_cost_2d, game_tick_arr, where=(game_tick_arr != 0),
            out=np.full_like(infantry_produced_time_cost_2d, 0, dtype=float)
        )
        avg_light_effi = np.divide(
            light_produced_time_cost_2d, game_tick_arr, where=(game_tick_arr != 0),
            out=np.full_like(light_produced_time_cost_2d, 0, dtype=float)
        )
        avg_heavy_effi = np.divide(
            heavy_produced_time_cost_2d, game_tick_arr, where=(game_tick_arr != 0),
            out=np.full_like(heavy_produced_time_cost_2d, 0, dtype=float)
        )
        create_ts_plot_at_frame(
            average_infantry_efficiency_frame, gv.game_ticks_list,
            avg_infantry_effi, stacked=False,
            proportion=False,
            colors=self.colors, legend_labels=self.labels,
            title="Average Infantry Production Efficiency Over Time",
            integer_yticks=False
        )
        create_ts_plot_at_frame(
            average_light_efficiency_frame, gv.game_ticks_list,
            avg_light_effi, stacked=False,
            proportion=False,
            colors=self.colors, legend_labels=self.labels,
            title="Average Light Factory Production Efficiency Over Time",
            integer_yticks=False
        )
        create_ts_plot_at_frame(
            average_heavy_efficiency_frame, gv.game_ticks_list,
            avg_heavy_effi, stacked=False,
            proportion=False,
            colors=self.colors, legend_labels=self.labels,
            title="Average Heavy Factory Production Efficiency Over Time",
            integer_yticks=False
        )

        infantry_produced_time_cost_roll_diff = diff_and_fill_np_2d(infantry_produced_time_cost_2d, period=diff_period)  # (n_player, n_obs)
        light_produced_time_cost_roll_diff = diff_and_fill_np_2d(light_produced_time_cost_2d, period=diff_period)  # (n_player, n_obs)
        heavy_produced_time_cost_roll_diff = diff_and_fill_np_2d(heavy_produced_time_cost_2d, period=diff_period)  # (n_player, n_obs)

        instant_infantry_effi_2d = np.divide(
            infantry_produced_time_cost_roll_diff, game_tick_roll_diff, where=(game_tick_roll_diff != 0),
            out=np.full_like(infantry_produced_time_cost_roll_diff, 0, dtype=float)
        )
        instant_light_effi_2d = np.divide(
            light_produced_time_cost_roll_diff, game_tick_roll_diff, where=(game_tick_roll_diff != 0),
            out=np.full_like(light_produced_time_cost_roll_diff, 0, dtype=float)
        )
        instant_heavy_effi_2d = np.divide(
            heavy_produced_time_cost_roll_diff, game_tick_roll_diff, where=(game_tick_roll_diff != 0),
            out=np.full_like(heavy_produced_time_cost_roll_diff, 0, dtype=float)
        )

        create_ts_plot_at_frame(
            instant_infantry_efficiency_frame, gv.game_ticks_list[::select_every],
            instant_infantry_effi_2d[:, ::select_every], stacked=False,
            proportion=False,
            colors=self.colors, legend_labels=self.labels,
            title="Instant Infantry Production Efficiency Over Time",
            integer_yticks=False
        )
        create_ts_plot_at_frame(
            instant_light_efficiency_frame, gv.game_ticks_list[::select_every],
            instant_light_effi_2d[:, ::select_every], stacked=False,
            proportion=False,
            colors=self.colors, legend_labels=self.labels,
            title="Instant Light Factory Production Efficiency Over Time",
            integer_yticks=False
        )
        create_ts_plot_at_frame(
            instant_heavy_efficiency_frame, gv.game_ticks_list[::select_every],
            instant_heavy_effi_2d[:, ::select_every], stacked=False,
            proportion=False,
            colors=self.colors, legend_labels=self.labels,
            title="Instant Heavy Factory Production Efficiency Over Time",
            integer_yticks=False
        )
