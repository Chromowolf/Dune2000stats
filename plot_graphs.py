from gamedata import NUM_BUILDING_GROUPS
from gamedata.gamevars import game_vars as gv
import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from enums import color_idx_to_hex_string
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
)


def create_ts_plot_at_frame(frame, x, y, stacked=False, proportion=False, colors=None, legend_labels=None):
    """
    If proportion is True, then stacked is automatically true
    Args:
        frame: the tk frame
        x:
        y: 2d array
        stacked:
        proportion:
        colors: iterable of length y.shape[0], specifying the color code
        legend_labels: iterable of length y.shape[0], specifying the legend texts

    Returns: Figure object
    """
    fig = plt.Figure(figsize=(6, 4), dpi=100)
    ax = fig.add_subplot(111)  # 1x1 grid, and this is the first (and only) subplot.
    n_line = y.shape[0]

    # if not colors:
    #     colors = [None] * n_line
    if not legend_labels:
        legend_labels = [f"Series {i}" for i in range(n_line)]

    if proportion:
        # stacked = True
        row_sums = y.sum(axis=0)  # Sum across col
        proportions = np.divide(y, row_sums, where=(row_sums != 0),
                                out=np.full_like(y, 0, dtype=float))
        ax.stackplot(x, proportions, colors=colors, labels=legend_labels)  # Stack plot of proportion
        ax.legend(loc='upper left')
        ax.set_xlabel("Time")
        ax.set_ylabel("Proportion")
        ax.set_ylim(top=1)
        ax.set_title("Time Series Plot (Proportion)")
    else:
        if stacked:
            # ax.stackplot(x, y, baseline='wiggle', colors=colors, labels=legend_labels)  # Stack plot of proportion
            ax.stackplot(x, y, colors=colors, labels=legend_labels)  # Stack plot of proportion
            ax.legend(loc='upper left')
            ax.set_xlabel("Time")
            ax.set_ylabel("Number")
            ax.set_title("Time Series Plot (Stacked)")
        else:
            # ax.plot(x, y.T)  # Stack plot of proportion
            # ax.legend([f"Series{i}" for i in range(n_line)], loc='upper left')
            for i in range(n_line):
                ax.plot(x, y[i, :], color=colors[i] if colors else None, label=legend_labels[i])
            ax.legend(loc='upper left')
            ax.set_xlabel("Time")
            ax.set_ylabel("Number")
            ax.set_title("Time Series Plot (Line)")

    ax.grid(True)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()

    toolbar = NavigationToolbar2Tk(canvas, frame, pack_toolbar=False)
    toolbar.update()
    toolbar.pack(side=tk.BOTTOM, fill=tk.X)

    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)


def plot_economy(root):
    plot_window = tk.Toplevel(root)
    plot_window.title("Economy Plots")
    plot_window.geometry("1280x720")

    if not hasattr(gv, "game_ticks_list") or not gv.game_ticks_list:
        ttk.Label(plot_window, text="No game data!", style="yahei20.TLabel").pack()
        return

    # Create a Notebook (tabs)
    notebook = ttk.Notebook(plot_window)
    notebook.pack(expand=True, fill="both")
    is_real_player = gv.is_player & (~gv.is_spectator)  # shape (8, ), bool

    # colors:
    colors = [color_idx_to_hex_string.get(c, "#000000")
              for i, c in enumerate(gv.player_colors)
              if is_real_player[i]
              ]
    labels = [
        nm
        for i, nm in enumerate(gv.player_names)
        if is_real_player[i]
    ]

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
        credit_data_2d = np.stack(gv.credits_list, axis=1)[is_real_player, :]  # Stack arrays vertically
        # --- Create the first tab (Normal) ---
        create_ts_plot_at_frame(credits_frame_line, gv.game_ticks_list, credit_data_2d, stacked=False, proportion=False,
                                colors=colors, legend_labels=labels)

        # --- Create the 2nd tab (Normal stacked) ---
        create_ts_plot_at_frame(credits_frame_stacked, gv.game_ticks_list, credit_data_2d, stacked=True,
                                proportion=False, colors=colors, legend_labels=labels)

        # --- Create the 3rd tab (Proportion Plot) ---
        create_ts_plot_at_frame(credits_frame_proportion, gv.game_ticks_list, credit_data_2d, stacked=True,
                                proportion=True, colors=colors, legend_labels=labels)

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
        harv_data_2d = np.stack(harv_data_list, axis=1)[is_real_player, :]  # Stack arrays vertically
        # --- Create the first tab (Normal) ---
        create_ts_plot_at_frame(harv_frame_line, gv.game_ticks_list, harv_data_2d, stacked=False, proportion=False,
                                colors=colors, legend_labels=labels)

        # --- Create the 2nd tab (Normal stacked) ---
        create_ts_plot_at_frame(harv_frame_stacked, gv.game_ticks_list, harv_data_2d, stacked=True, proportion=False,
                                colors=colors, legend_labels=labels)

        # --- Create the 3rd tab (Proportion Plot) ---
        create_ts_plot_at_frame(harv_frame_proportion, gv.game_ticks_list, harv_data_2d, stacked=True, proportion=True,
                                colors=colors, legend_labels=labels)


def plot_units_owned(root):
    plot_window = tk.Toplevel(root)
    plot_window.title("Units Plot")
    plot_window.geometry("1280x720")
    if not hasattr(gv, "game_ticks_list") or not gv.game_ticks_list:
        ttk.Label(plot_window, text="No game data!", style="yahei20.TLabel").pack()
        return

    # Create a Notebook (tabs)
    notebook = ttk.Notebook(plot_window)
    notebook.pack(expand=True, fill="both")
    is_real_player = gv.is_player & (~gv.is_spectator)  # shape (8, ), bool

    # colors:
    colors = [color_idx_to_hex_string.get(c, "#000000")
              for i, c in enumerate(gv.player_colors)
              if is_real_player[i]
              ]
    labels = [
        nm
        for i, nm in enumerate(gv.player_names)
        if is_real_player[i]
    ]

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
        unit_counts_2d = unit_counts_2d_8p[is_real_player, :]

        unit_values_2d_8p = units_data_3d @ unit_cost_arr  # (8, n)
        unit_values_2d = unit_values_2d_8p[is_real_player, :]

        # --- Create the first tab (Normal) ---
        create_ts_plot_at_frame(units_count_frame_line, gv.game_ticks_list, unit_counts_2d, stacked=False,
                                proportion=False,
                                colors=colors, legend_labels=labels)

        # --- Create the 2nd tab (Normal stacked) ---
        create_ts_plot_at_frame(units_count_frame_stacked, gv.game_ticks_list, unit_counts_2d, stacked=True,
                                proportion=False, colors=colors, legend_labels=labels)

        # --- Create the 3rd tab (Proportion Plot) ---
        create_ts_plot_at_frame(units_count_frame_proportion, gv.game_ticks_list, unit_counts_2d, stacked=True,
                                proportion=True, colors=colors, legend_labels=labels)

        # --- Create the first tab (Normal) ---
        create_ts_plot_at_frame(units_value_frame_line, gv.game_ticks_list, unit_values_2d, stacked=False,
                                proportion=False,
                                colors=colors, legend_labels=labels)

        # --- Create the 2nd tab (Normal stacked) ---
        create_ts_plot_at_frame(units_value_frame_stacked, gv.game_ticks_list, unit_values_2d, stacked=True,
                                proportion=False, colors=colors, legend_labels=labels)

        # --- Create the 3rd tab (Proportion Plot) ---
        create_ts_plot_at_frame(units_value_frame_proportion, gv.game_ticks_list, unit_values_2d, stacked=True,
                                proportion=True, colors=colors, legend_labels=labels)


def plot_buildings(root):
    plot_window = tk.Toplevel(root)
    plot_window.title("Buildings Plot")
    plot_window.geometry("1280x720")
    if not hasattr(gv, "game_ticks_list") or not gv.game_ticks_list:
        ttk.Label(plot_window, text="No game data!", style="yahei20.TLabel").pack()
        return

    # Create a Notebook (tabs)
    notebook = ttk.Notebook(plot_window)
    notebook.pack(expand=True, fill="both")
    is_real_player = gv.is_player & (~gv.is_spectator)  # shape (8, ), bool

    # colors:
    colors = [color_idx_to_hex_string.get(c, "#000000")
              for i, c in enumerate(gv.player_colors)
              if is_real_player[i]
              ]
    labels = [
        nm
        for i, nm in enumerate(gv.player_names)
        if is_real_player[i]
    ]

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
        buildings_counts_2d = buildings_counts_2d_8p[is_real_player, :]

        buildings_values_2d_8p = buildings_data_3d @ building_group_avg_cost  # (8, n)
        buildings_values_2d = buildings_values_2d_8p[is_real_player, :]

        # --- Create the first tab (Normal) ---
        create_ts_plot_at_frame(buildings_count_frame_line, gv.game_ticks_list, buildings_counts_2d, stacked=False,
                                proportion=False,
                                colors=colors, legend_labels=labels)

        # --- Create the 2nd tab (Normal stacked) ---
        create_ts_plot_at_frame(buildings_count_frame_stacked, gv.game_ticks_list, buildings_counts_2d, stacked=True,
                                proportion=False, colors=colors, legend_labels=labels)

        # --- Create the 3rd tab (Proportion Plot) ---
        create_ts_plot_at_frame(buildings_count_frame_proportion, gv.game_ticks_list, buildings_counts_2d, stacked=True,
                                proportion=True, colors=colors, legend_labels=labels)

        # --- Create the first tab (Normal) ---
        create_ts_plot_at_frame(buildings_value_frame_line, gv.game_ticks_list, buildings_values_2d, stacked=False,
                                proportion=False,
                                colors=colors, legend_labels=labels)

        # --- Create the 2nd tab (Normal stacked) ---
        create_ts_plot_at_frame(buildings_value_frame_stacked, gv.game_ticks_list, buildings_values_2d, stacked=True,
                                proportion=False, colors=colors, legend_labels=labels)

        # --- Create the 3rd tab (Proportion Plot) ---
        create_ts_plot_at_frame(buildings_value_frame_proportion, gv.game_ticks_list, buildings_values_2d, stacked=True,
                                proportion=True, colors=colors, legend_labels=labels)

        # Factories counts
        cy_count_data = buildings_data_3d[is_real_player, :, CONSTRUCTION_YARD_BUILDING_GROUP_INDEX]
        barracks_count_data = buildings_data_3d[is_real_player, :, BARRACKS_BUILDING_GROUP_INDEX]
        light_fac_count_data = buildings_data_3d[is_real_player, :, LIGHT_FACTORY_BUILDING_GROUP_INDEX]
        heavy_fac_count_data = buildings_data_3d[is_real_player, :, HEAVY_FACTORY_BUILDING_GROUP_INDEX]

        create_ts_plot_at_frame(construction_yard_count_frame, gv.game_ticks_list, cy_count_data, stacked=False,
                                proportion=False,
                                colors=colors, legend_labels=labels)

        create_ts_plot_at_frame(barracks_count_frame, gv.game_ticks_list, barracks_count_data, stacked=False,
                                proportion=False,
                                colors=colors, legend_labels=labels)

        create_ts_plot_at_frame(light_factory_count_frame, gv.game_ticks_list, light_fac_count_data, stacked=False,
                                proportion=False,
                                colors=colors, legend_labels=labels)

        create_ts_plot_at_frame(heavy_factory_count_frame, gv.game_ticks_list, heavy_fac_count_data, stacked=False,
                                proportion=False,
                                colors=colors, legend_labels=labels)
