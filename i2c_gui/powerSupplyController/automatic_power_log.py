import subprocess
import time
import sys
import argparse
from pathlib import Path

# --- Configuration ---
# Please update these values before running the script
wafer_name = "Wafer_N62C72_16G3"
CONFIG_FILE = "20250924-CERN-Wafer.yaml"
OUTPUT_PATH = f"/home/daq/ETROC2/ETROC-History/CERN_Sep2025_Wafer/{wafer_name}"  # IMPORTANT: Change this to your desired output directory

# --- Script settings ---
PYTHON_EXECUTABLE = sys.executable # Use the same python that runs this script
SCRIPT_TO_RUN = "read_current_v2.py"


def generate_toml_config(die_name, wafer_name, toml_path, toml_filename):
    """Generates a TOML configuration file from a template with dynamic values."""
    print(f"--- Generating TOML config file: {toml_filename} ---")

    toml_content = f"""[satellites.ETROC2ClassicWafer]

[satellites.ETROC2ClassicWafer.One]
fast_command_memo = "Start QInj L1A Triggerbit BCR"
polarity = 0x4123
active_channel = 0x0001
timestamp = 0x0000

# fc_delays        = 0b0000000000100100 # register 4
# data_delays_01   = 0b0000000001100011 # register 5
# data_delays_23   = 0b0000111100000000 # register 6
# counter_duration = 0b0000000000000000 # register 7

i2c_port = "/dev/ttyACM4"
chip_addresses = [0x60]
ws_addresses = [0x40]
chip_names = ["{die_name}"]
output_path = "/home/daq/ETROC2/ETROC-Data/CERN_Sep_WaferProbe/{wafer_name}/{die_name}"
do_full_chip = true
power_mode = "high"

[satellites.ETROC2Receiver]

[satellites.ETROC2Receiver.One]
output_path = "/home/daq/ETROC2/ETROC-Data/CERN_Sep_WaferProbe/{wafer_name}/{die_name}"
translate = 1
compressed_binary = 0
skip_fillers = 1
"""

    try:
        with open(Path(toml_path) / toml_filename, "w") as f:
            f.write(toml_content)
        print(f"--- Successfully generated TOML config for {die_name}. ---")
        return True
    except IOError as e:
        print(f"--- ERROR: Could not write TOML file '{toml_filename}': {e} ---")
        return False
    except ImportError:
        print("--- ERROR: The 'toml' library is not installed. ---")
        print("--- Please install it by running: pip install toml ---")
        return False


def run_command(command):
    """Executes a command and waits for it to complete."""
    try:
        print(f"--- Running command: {' '.join(command)} ---")
        # Using check=True to raise an exception if the command returns a non-zero exit code
        subprocess.run(command, check=True, capture_output=True, text=True)
        print("--- Command finished successfully. ---\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"--- ERROR executing command: {' '.join(command)} ---")
        print(f"--- Return Code: {e.returncode} ---")
        print(f"--- STDOUT: ---\n{e.stdout}")
        print(f"--- STDERR: ---\n{e.stderr}")
        return False
    except FileNotFoundError:
        print(f"--- ERROR: The script '{command[1]}' was not found. ---")
        print("--- Please ensure it is in the same directory or in your system's PATH. ---")
        return False


def main(args):
    """Main function to orchestrate the testing process."""
    print("Starting automated wafer testing process...")

    Path(OUTPUT_PATH).mkdir(exist_ok=True, parents=True)

    # 1. Prepare paths and generate the TOML configuration file
    if not generate_toml_config(args.dieName, wafer_name, '/home/daq/ETROC2', 'testslowwafer.toml'):
        print("--- Halting execution due to TOML generation failure. ---")
        sys.exit(1) # Exit the script if config can't be created

    # 1. Start power-on and logging process in the background.
    # This assumes read_current_v2.py can handle both flags in one call.
    DIE_NAME = f"{args.dieName}.sqlite"           # IMPORTANT: Change this to the specific die you are testing
    start_and_log_command = [
        PYTHON_EXECUTABLE,
        SCRIPT_TO_RUN,
        "-c", CONFIG_FILE,
        "--turn-on",
        "--log",
        "-i", "1",
        "-o", OUTPUT_PATH,
        "-f", DIE_NAME,
    ]
    print(f"--- Starting power-on and logging: {' '.join(start_and_log_command)} ---")
    # Popen starts the process without blocking, allowing us to manage it
    active_process = subprocess.Popen(start_and_log_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    print("\n--- Power-on and logging started. Press CTRL+C to stop logging and proceed with shutdown. ---")

    # 2. Wait for keyboard interrupt to stop logging
    try:
        # wait() blocks until the process finishes on its own,
        # or until this script is interrupted by the user (e.g., with Ctrl+C).
        active_process.wait()
    except KeyboardInterrupt:
        print("\n--- Keyboard interrupt received. Stopping the process... ---")
    except Exception as e:
        # Catch other potential exceptions from wait()
        print(f"\n--- An unexpected error occurred while waiting for the process: {e} ---")


    # 3. Terminate the process
    # This will run after the process finishes naturally or after a KeyboardInterrupt
    print("--- Terminating process (if still running)... ---")
    active_process.terminate()

    # Wait a moment to ensure the process has terminated and capture any final output
    try:
        stdout, stderr = active_process.communicate(timeout=5)
        print("--- Process stopped. ---")
        if stdout:
            print(f"--- Logging STDOUT: ---\n{stdout}")
        if stderr:
            print(f"--- Logging STDERR: ---\n{stderr}")

    except subprocess.TimeoutExpired:
        print("--- Process did not terminate gracefully. Forcing kill. ---")
        active_process.kill()

    print("") # Newline for readability

    # 4. Wait for 1 second
    print(f"Waiting for 1 second(s)...")
    time.sleep(1)

    # 5. Turn off power supplies
    turn_off_command = [
        PYTHON_EXECUTABLE,
        SCRIPT_TO_RUN,
        "-c", CONFIG_FILE,
        "--turn-off",
        "--no_reset_inst"
    ]
    if not run_command(turn_off_command):
        print("Failed to turn off power supplies. Please check manually.")
    
    print("Automated process complete.")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
            prog='PlaceHolder',
            description='PlaceHolder',
    )

    parser.add_argument(
        '--dieName',
        metavar = 'NAME',
        type = str,
        help = 'Example: die<number>_RxCy',
        required = True,
        dest = 'dieName',
    )

    args = parser.parse_args()

    # Basic check for placeholder values
    if "/path/to/your/log/output" in OUTPUT_PATH:
        print("!!! WARNING !!!")
        print("Please update the OUTPUT_PATH and DIE_NAME variables in the script before running.")
    else:
        main(args)
