import supervisor
import sys
import time

# Device Mode
MODE_RELAY = "relay"
MODE_CONTROLLER = "controller"


def check_serial_input():
    """Check if there's any input available from serial console"""
    if supervisor.runtime.serial_bytes_available:
        return sys.stdin.read(1)
    return None


def get_user_input(prompt, default):
    """Get user input with a default value"""
    print(f"{prompt} [{default}]: ", end="")

    user_input = ""
    start_time = time.monotonic()
    timeout = 30.0  # 30 second timeout

    while True:
        if time.monotonic() - start_time > timeout:
            print("\n[Timeout - using default]")
            return str(default)

        char = check_serial_input()
        if char:
            if char == "\r" or char == "\n":
                print()
                return user_input if user_input else str(default)
            elif char == "\x7f" or char == "\x08":  # Backspace
                if user_input:
                    user_input = user_input[:-1]
                    print("\b \b", end="")
            else:
                user_input += char
                print(char, end="")

        time.sleep(0.01)
