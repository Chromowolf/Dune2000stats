import sys
import os
import datetime


def get_log_file_path():
    # Get today's date
    today = datetime.date.today()
    # Format the filename with today's date
    filename = f"console_output_{today.strftime('%Y-%m-%d')}.txt"
    # Construct the full path
    return os.path.join("logs", filename)


def setup_logging():
    # Get the path to the log file
    path = get_log_file_path()
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Open the log file in append mode
    log_file = open(path, "a", buffering=1)  # Line buffering

    # Add a timestamp separator
    now = datetime.datetime.now()
    log_file.write(f"======= {now.strftime('%H:%M:%S')} =========\n")
    log_file.flush()

    # Redirect stdout and stderr to the log file
    sys.stdout = log_file
    sys.stderr = log_file

    return log_file


def close_logging(log_file):
    # Reset stdout and stderr
    log_file.write(f"\n======= End of log =========\n")
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

    # Close the log file
    log_file.close()

