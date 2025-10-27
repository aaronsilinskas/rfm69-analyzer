import microcontroller
from controller_mode import ControllerMode
from input import MODE_CONTROLLER, MODE_RELAY
from rfm_util import init_rfm69
from relay_mode import RelayMode
from rgb_indicator import indicate_error

DEVICE_ID = microcontroller.cpu.uid.hex().upper()

rfm69 = init_rfm69()
if rfm69 is None:
    indicate_error("Failed to initialize any RFM69 module. Exiting.")

current_mode = MODE_RELAY
relay_mode = RelayMode(rfm69, DEVICE_ID)
controller_mode = ControllerMode(rfm69, DEVICE_ID)


# Print device state:
print("\n" + "=" * 50)
print("RFM69 Analyzer - Device Info")
print("=" * 50)
print(f"Device ID: {DEVICE_ID}")
print(f"Temperature: {rfm69.temperature}C")
print(f"Frequency: {rfm69.frequency_mhz}mhz")
print(f"Bit rate: {rfm69.bitrate / 1000}kbit/s")
print(f"Frequency deviation: {rfm69.frequency_deviation}hz")
print(f"Transmit power: {rfm69.tx_power}dbm")
print("=" * 50)
print(f"\nStarting in RELAY mode...")
print("Press any key to switch to CONTROLLER mode")
print("=" * 50 + "\n")

# Main loop
while True:
    try:
        if current_mode == MODE_RELAY:
            current_mode = relay_mode.run()
        elif current_mode == MODE_CONTROLLER:
            current_mode = controller_mode.run()
    except Exception as e:
        indicate_error(f"Error in main loop: {e}")
