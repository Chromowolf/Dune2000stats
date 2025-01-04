# import tkinter as tk
# from tkinter import ttk
from plot_graphs import *

# Important note: the app could be started when Dune2000 is at the score page after a game is finished!
class RightButtons:
    def __init__(self, root, master):
        self.root = root
        self.master: ttk.Frame = master
        self.button_list = []

        self.display_graph_label = ttk.Label(self.master, text="Show Graphs", style="yahei20.TLabel")
        self.display_graph_label.pack(side=tk.LEFT, padx=5, pady=5)

        # Economy
        self.plot_economy_button = ttk.Button(self.master, text="Economy", command=lambda: plot_economy(self.root))
        self.plot_economy_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.button_list.append(self.plot_economy_button)

        # Units
        self.plot_harvesters_button = ttk.Button(self.master, text="Harvesters", command=lambda: plot_harvesters(self.root))
        self.plot_harvesters_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.button_list.append(self.plot_harvesters_button)

        # Buildings
        self.plot_units_owned_button = ttk.Button(self.master, text="Units Owned", command=lambda: plot_units_owned(self.root))
        self.plot_units_owned_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.button_list.append(self.plot_units_owned_button)

    def enable_all_buttons(self):
        for bt in self.button_list:
            bt.config(state=tk.NORMAL)

    def disable_all_buttons(self):
        for bt in self.button_list:
            bt.config(state=tk.DISABLED)
