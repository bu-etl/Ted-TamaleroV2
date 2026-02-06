import socket
import time
from datetime import datetime

# --- Configuration ---
# !!! IMPORTANT: Replace with your multimeter's actual IP address !!!
DMM_IP = "192.168.2.61"
DMM_PORT = 5025

# --- The SCPI Command ---
# We will use "READ?" inside the loop, which is slightly more efficient
# than "MEASure?" for repeated readings on an already configured instrument.
config_command = "CONF:VOLT:DC AUTO\n" # Configure once before the loop
read_command = "READ?\n"              # Ask for a reading inside the loop

print(f"Connecting to DMM at {DMM_IP}...")

try:
    # Create a TCP/IP socket and establish the connection
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(5)  # 5 seconds
        s.connect((DMM_IP, DMM_PORT))
        print("Connection successful. Starting continuous measurements.")
        print("Press Ctrl+C to stop.")

        # Configure the instrument for DC Voltage measurement just once
        s.sendall(config_command.encode('ascii'))

        # This is the main loop that runs forever
        while True:
            # Send the command to ask for a reading
            s.sendall(read_command.encode('ascii'))

            # Read the response from the instrument
            response = s.recv(1024).decode('ascii').strip()

            # The response is a number in string format.
            # Convert it to a float for calculations or formatting.
            voltage = float(response)

            # Print the formatted result. The '\r' at the start and end=''
            # causes the line to overwrite itself, creating a live display.
            now = datetime.now().isoformat(sep=' ', timespec='seconds')
            print(f"{now}, Measured DC Voltage: {voltage:+.6f} V", end='\r')

            # Wait for 1 second before the next measurement
            time.sleep(1)

except KeyboardInterrupt:
    # This block runs when the user presses Ctrl+C
    print("\n\nUser stopped the measurement loop.")
    print("Script finished.")

except socket.timeout:
    print("\nError: Connection timed out.")
    print("Please check the IP address and ensure the DMM is connected to the network.")
except ConnectionRefusedError:
    print("\nError: Connection refused.")
    print("Please ensure the 'Sockets' service is enabled on the DMM's I/O menu.")
except Exception as e:
    print(f"\nAn error occurred: {e}")
