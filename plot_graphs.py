from gamedata.gamevars import game_vars as gv
import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from enums import color_idx_to_hex_string

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
    ax = fig.add_subplot(111)
    n_line = y.shape[0]

    # if not colors:
    #     colors = [None] * n_line
    if not legend_labels:
        legend_labels = [f"Series {i}" for i in range(n_line)]

    if proportion:
        # stacked = True
        row_sums = y.sum(axis=0)  # Sum across col
        proportions = np.divide(y, row_sums, where=(row_sums != 0),
                                out=np.full_like(y, 1 / n_line, dtype=float))
        ax.stackplot(x, proportions, colors=colors, labels=legend_labels)  # Stack plot of proportion
        ax.legend(loc='upper left')
        ax.set_xlabel("Time")
        ax.set_ylabel("Proportion")
        ax.set_title("Time Series Plot (Proportion)")
    else:
        if stacked:
            ax.stackplot(x, y, baseline='wiggle', colors=colors, labels=legend_labels)  # Stack plot of proportion
            ax.legend(loc='upper left')
            ax.set_xlabel("Time")
            ax.set_ylabel("Number")
            ax.set_title("Time Series Plot (Stacked)")
        else:
            # ax.plot(x, y.T)  # Stack plot of proportion
            # ax.legend([f"Series{i}" for i in range(n_line)], loc='upper left')
            for i in range(n_line):
                ax.plot(x, y[i, :], color=colors[i] if colors else None, label=legend_labels[i])
            ax.legend(loc='upper right')
            ax.set_xlabel("Time")
            ax.set_ylabel("Number")
            ax.set_title("Time Series Plot (Normal)")

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()

    toolbar = NavigationToolbar2Tk(canvas, frame, pack_toolbar=False)
    toolbar.update()
    toolbar.pack(side=tk.BOTTOM, fill=tk.X)

    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)


def plot_credits(root):
    plot_window = tk.Toplevel(root)
    plot_window.title("Credits Plot")
    plot_window.geometry("960x720")

    if not hasattr(gv, "credits_list"):
        not_found_label = ttk.LabelFrame(plot_window, text="No credits data found!", style="yahei10.TLabelframe")
        not_found_label.pack(fill=tk.BOTH, expand=True)
        return

    # Create a Notebook (tabs)
    notebook = ttk.Notebook(plot_window)
    notebook.pack(expand=True, fill="both")

    # Efficiently convert to a 2D NumPy array
    data_2d = np.stack(gv.credits_list, axis=1)[:gv.number_of_player, :]  # Stack arrays vertically

    # colors:
    colors = [color_idx_to_hex_string.get(c, "#000000") for c in gv.player_colors[:gv.number_of_player]]
    labels = gv.player_names

    # --- Create the first tab (Normal) ---
    frame_normal = ttk.LabelFrame(notebook)
    notebook.add(frame_normal, text="Normal")
    create_ts_plot_at_frame(frame_normal, gv.game_ticks_list, data_2d, stacked=False, proportion=False, colors=colors, legend_labels=labels)

    # --- Create the 2nd tab (Normal stacked) ---
    frame_stacked = ttk.Frame(notebook)
    notebook.add(frame_stacked, text="Normal Stacked")
    create_ts_plot_at_frame(frame_stacked, gv.game_ticks_list, data_2d, stacked=True, proportion=False, colors=colors, legend_labels=labels)

    # --- Create the 3rd tab (Proportion Plot) ---
    frame_proportion = ttk.Frame(notebook)
    notebook.add(frame_proportion, text="Proportion")
    create_ts_plot_at_frame(frame_proportion, gv.game_ticks_list, data_2d, stacked=True, proportion=True, colors=colors, legend_labels=labels)

def plot_harvesters(root):
    ...

def plot_units_owned(root):
    ...
