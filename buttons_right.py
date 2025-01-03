import tkinter as tk
from tkinter import ttk

def plot_credits():
    ...

def plot_harvesters():
    ...

def plot_units_owned():
    ...

class RightButtons:
    def __init__(self, root):
        self.root: ttk.Frame = root
        display_graph_label = ttk.Label(self.root, text="Show Graphs", style="yahei20.TLabel")
        display_graph_label.pack(side=tk.LEFT, padx=5, pady=5)

        # Refresh button
        plot_credits_button = ttk.Button(self.root, text="Credits", command=plot_credits)
        plot_credits_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Import button
        plot_harvesters_button = ttk.Button(self.root, text="Harvesters", command=plot_harvesters)
        plot_harvesters_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Export button
        plot_units_owned_button = ttk.Button(self.root, text="Units Owned", command=plot_units_owned)
        plot_units_owned_button.pack(side=tk.LEFT, padx=5, pady=5)
