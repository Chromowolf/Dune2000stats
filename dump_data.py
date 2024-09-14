import os
import pickle

folder_name = "stats"

def dump_game_data(class_instance, path=None):
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
    file_path = os.path.join(folder_name, 'last_game.pkl')
    if path:
        file_path = path

    try:
        # Save the instance to a file
        with open(file_path, 'wb') as output:
            pickle.dump(class_instance, output, pickle.HIGHEST_PROTOCOL)
        print(f"[Info] Game stats dumped into \"{file_path}\"")
    except IOError as e:
        print(f"[Error] Failed to write to file {file_path}: {e}")
    except pickle.PicklingError as e:
        print(f"[Error] Failed to pickle the object: {e}")
