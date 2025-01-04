import tkinter as tk
from tkinter import ttk
from plot_graphs import *

class RightButtons:
    def __init__(self, root, master):
        self.root = root
        self.master: ttk.Frame = master
        self.button_list = []

        self.display_graph_label = ttk.Label(self.master, text="Show Graphs", style="yahei20.TLabel")
        self.display_graph_label.pack(side=tk.LEFT, padx=5, pady=5)

        # Refresh button
        self.plot_credits_button = ttk.Button(self.master, text="Credits", command=lambda: plot_credits(self.root))
        self.plot_credits_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.button_list.append(self.plot_credits_button)

        # Import button
        self.plot_harvesters_button = ttk.Button(self.master, text="Harvesters", command=lambda: plot_harvesters(self.root))
        self.plot_harvesters_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.button_list.append(self.plot_harvesters_button)

        # Export button
        self.plot_units_owned_button = ttk.Button(self.master, text="Units Owned", command=lambda: plot_units_owned(self.root))
        self.plot_units_owned_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.button_list.append(self.plot_units_owned_button)

    def enable_all_buttons(self):
        for bt in self.button_list:
            bt.config(state=tk.NORMAL)

    def disable_all_buttons(self):
        for bt in self.button_list:
            bt.config(state=tk.DISABLED)
