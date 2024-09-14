import pickle
from tkinter import filedialog, messagebox
from datetime import datetime
from dump_data import dump_game_data
from gamedata.gamevars import game_vars as gv

def export_stats():
    """Handles the export of game stats to a .pkl file."""
    dest_fn = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.pkl")
    file_path = filedialog.asksaveasfilename(
        defaultextension=".pkl",
        filetypes=[("pkl files", "*.pkl")],
        initialfile=dest_fn,
        title="Export stats file as"
    )
    if file_path:
        try:
            dump_game_data(gv, file_path)
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")


def import_stats(app):
    """Handles the import of game stats from a .pkl file and updates the global 'gv'."""
    file_path = filedialog.askopenfilename(
        defaultextension=".pkl",
        filetypes=[("pkl files", "*.pkl")],
        title="Import stats file"
    )
    if file_path:
        try:
            # Load the pickle file
            with open(file_path, 'rb') as f:
                loaded_data = pickle.load(f)

            # Ensure the loaded data is an instance of GameVariable
            if isinstance(loaded_data, type(gv)):
                gv.update_from_instance(loaded_data)  # Update 'gv' attributes with the loaded instance's attributes
                # messagebox.showinfo("Success", "Game stats imported successfully.")
                app.reset_table()
                app.set_title_after_game()
                app.update_table()

            else:
                messagebox.showerror("Error", "Invalid data format. Expected a GameVariable instance.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
