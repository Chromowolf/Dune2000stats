import pickle
from tkinter import filedialog, messagebox
from datetime import datetime
from gamedata.gamevars import game_vars as gv, GameVariable
import gzip
import os

folder_name = "stats"

def make_filename_safe_replace(s, replacement='_'):
    for char in '<>:"/\\|?*':
        s = s.replace(char, replacement)
    s = s.strip(' .')
    return s or "NONAME"

def dump_game_data(class_instance: GameVariable, path=None):
    """
    Serializes a class instance and saves it to a file using pickle, overwriting any existing file without warning.

    Args:
        class_instance (object): The instance of the class to be serialized.
        path (str, optional): The file path where the pickle will be saved. If not provided, a default path is used.

    Raises:
        IOError: If the file could not be opened or written to.
        pickle.PicklingError: If the object cannot be pickled.
    """
    # Ensure the folder exists
    os.makedirs(folder_name, exist_ok=True)
    stats_timestamp = class_instance.game_start_timestamp if class_instance.game_start_timestamp else datetime.now()
    player_names_str = "+".join([make_filename_safe_replace(nm) for nm in class_instance.player_names])
    default_file_name = f"game_stats_{stats_timestamp.strftime("%Y%m%d_%H%M%S")}_{player_names_str}.pkl"
    file_path = os.path.join(folder_name, default_file_name)
    if path:
        file_path = path

    try:
        # Save the instance to a file
        # with open(file_path, 'wb') as output:
        with gzip.open(file_path, 'wb') as f:
            pickle.dump(class_instance, f, pickle.HIGHEST_PROTOCOL)
        print(f"[Info] Game stats dumped into \"{file_path}\"")
    except IOError as e:
        print(f"[Error] Failed to write to file {file_path}: {e}")
    except pickle.PicklingError as e:
        print(f"[Error] Failed to pickle the object: {e}")


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
            # Convert list of arrays into list of sparce delta matrices
            ...
            dump_game_data(gv, file_path)
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")


def load_pickle(filepath):
    """Loads a pickle file, automatically detecting if it's gzipped or not.

    Args:
        filepath: The path to the pickle file.

    Returns:
        The unpickled object.

    Raises:
        FileNotFoundError: If the file does not exist.
        pickle.UnpicklingError: If the file is not a valid pickle file.
        Exception: For other errors during file reading or decompression.
    """

    # Check if the file exists
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    # 1. Check file extension first (quick check)
    is_gzipped = False
    if filepath.endswith('.gz'):
        is_gzipped = True
    else:
        # 2. Check magic number (more reliable)
        try:
            with open(filepath, 'rb') as f:
                magic_number = f.read(2)
                is_gzipped = magic_number == b'\x1f\x8b'
        except Exception as e:
            raise Exception(f"Error reading file: {e}")

    # Load the pickle based on the detected type
    try:
        if is_gzipped:
            with gzip.open(filepath, 'rb') as f:
                return pickle.load(f)
        else:
            with open(filepath, 'rb') as f:
                return pickle.load(f)
    except pickle.UnpicklingError:
        raise pickle.UnpicklingError("Not a valid pickle file (corrupted or incorrect format).")
    except Exception as e:
        raise Exception(f"Error loading pickle file: {e}")


def import_stats(main_ui):
    """Handles the import of game stats from a .pkl file and updates the global 'gv'."""
    file_path = filedialog.askopenfilename(
        defaultextension=".pkl",
        filetypes=[("pkl files", "*.pkl")],
        title="Import stats file"
    )
    if file_path:
        try:
            # Load the pickle file
            loaded_data = load_pickle(file_path)
            print(f"[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]: Game stats loaded from \"{file_path}\".")

            # Ensure the loaded data is an instance of GameVariable
            if isinstance(loaded_data, type(gv)):
                gv.update_from_instance(loaded_data)  # Update 'gv' attributes with the loaded instance's attributes
                # Recover list of arrays from list of sparce delta matrices
                ...
                # messagebox.showinfo("Success", "Game stats imported successfully.")
                main_ui.reset_all_tables()
                main_ui.set_title_after_game()
                main_ui.update_all_tables()  # MainApp's update_all_tables()

            else:
                messagebox.showerror("Error", "Invalid data format. Expected a GameVariable instance.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
