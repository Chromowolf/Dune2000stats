# Dune 2000 stats helper by Pere

## Introduction
Greetings commander!

## Prerequisites
- You must be using a Windows operating system.

## Installation

### Step 1: Download the Project
Download this project to your local machine:
- Click on the green `Code` button and then select `Download ZIP`.

### Step 2: Unzip the Files
Locate the downloaded ZIP file on your computer and extract it to a desired location. We'll refer to this location as the "project folder" from now on.

### Step 3: Install Python
1. Download the latest version of Python 3.12 from the official Python website: [Python Downloads](https://www.python.org/downloads/).
2. Run the installer. Make sure to check the box that says **Add Python 3.12 to PATH** at the beginning of the installation process.

### Step 4: Verify Python Installation
1. Open Command Prompt (cmd) by typing `cmd` in the search bar.
2. In the Command Prompt, type:
   ```
   python --version
   ```
   This should display the Python version number. If you see a version number starting with 3.12, Python has been installed correctly.

### Step 5: Install Required Packages
1. Navigate to the project folder and open Command Prompt. Ensure that Command Prompt displays the directory path, similar to:
`D:\path\to\the\folder>`
2. Once you are in the folder, install all required packages by running:
   ```
   python -m pip install -r requirements.txt
   ```

## Running the Application

After you have set up everything, you can run the application by following these steps:

1. Open Command Prompt.
2. Navigate to the project folder if you are not already there:
   ```
   cd path\to\the\folder
   ```
3. Run the application:
   ```
   python main_app.py
   ```
   This will start the application based on the `main_app.py` Python script.
   


## Usage Manual

### General Usage
- Run the program once after starting your PC. You do not need to reopen it between gameplays. The program automatically detects any Dune 2000 process and attaches to it.
- The application shows live stats only when you are a spectator in the game. Otherwise it will display only the summary stats after the game ends.

### Interface and Controls
- **Refresh Button**: Click this button to refresh the current UI. Use this feature if there is a visual glitch, such as the stats not being fully displayed.
- **Export Button**: Saves the stats from the last game. This allows you to keep a record of game statistics for later review.
