import time
import supervisor
import sys
import json
import rfm_init


rfm69 = rfm_init.init_rfm69()
if rfm69 is None:
    print("Failed to initialize any RFM69 module. Exiting.")
    sys.exit(1)


# Device Mode
MODE_RELAY = "relay"
MODE_CONTROLLER = "controller"
current_mode = MODE_RELAY


# Test parameters (defaults)
class TestParameters:
    num_packets: int = 10
    delay_ms: int = 100
    high_power: bool = True
    tx_power: int = 20


test_params = TestParameters()

# Distance calculation parameters
distance_params = {
    "A": -27,  # Signal strength at 1 meter
    "n": 1.8,  # Path loss exponent (indoor line of sight)
}

# Test results storage for relay devices
relay_results = {}

# Print chip state:
print("\n" + "=" * 50)
print("RFM69 Analyzer - Device Info")
print("=" * 50)
print(f"Temperature: {rfm69.temperature}C")
print(f"Frequency: {rfm69.frequency_mhz}mhz")
print(f"Bit rate: {rfm69.bitrate / 1000}kbit/s")
print(f"Frequency deviation: {rfm69.frequency_deviation}hz")
print(f"Transmit power: {rfm69.tx_power}dbm")
print("=" * 50)
print(f"\nStarting in RELAY mode...")
print("Press any key to switch to CONTROLLER mode")
print("=" * 50 + "\n")


def check_serial_input():
    """Check if there's any input available from serial console"""
    if supervisor.runtime.serial_bytes_available:
        return sys.stdin.read(1)
    return None


def calculate_distance(tx_power, rssi, A, n):
    """Calculate distance based on RSSI using path loss model"""
    return 10 ** ((tx_power - rssi - A) / (10 * n))


def run_test(params: TestParameters):
    """Execute a test with the given parameters"""
    print(f"\n[TEST] Starting test with parameters:")
    print(f"  Packets: {params.num_packets}")
    print(f"  Delay: {params.delay_ms}ms")
    print(f"  High Power: {params.high_power}")
    print(f"  TX Power: {params.tx_power}db")

    # Configure radio
    rfm69.high_power = params.high_power
    rfm69.tx_power = params.tx_power

    results = {
        "sent": 0,
        "received": 0,
        "rssi_values": [],
        "start_time": time.monotonic(),
    }

    delay_sec = params.delay_ms / 1000.0

    for i in range(params.num_packets):
        # Send packet
        data = bytes(f"TEST:{i}", "utf-8")
        start = time.monotonic()
        rfm69.send(data, keep_listening=True)
        send_time = time.monotonic() - start
        results["sent"] += 1

        print(
            f"[TEST] Sent packet {i+1}/{params.num_packets} (took {send_time:.4f}s)"
        )

        time.sleep(delay_sec)

    # Calculate results
    duration = time.monotonic() - results["start_time"]
    packet_loss = (
        ((results["sent"] - results["received"]) / results["sent"]) * 100
        if results["sent"] > 0
        else 0
    )

    print(f"\n[TEST] Complete:")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Sent: {results['sent']}")
    print(f"  Received: {results['received']}")
    print(f"  Packet Loss: {packet_loss:.1f}%")

    # Send results back to controller
    result_msg = {
        "type": "result",
        "sent": results["sent"],
        "received": results["received"],
        "packet_loss": packet_loss,
        "duration": duration,
        "temperature": rfm69.temperature,
        "tx_power": params.tx_power,
        "high_power": params.high_power,
    }

    try:
        result_data = bytes(json.dumps(result_msg), "utf-8")
        rfm69.send(result_data, keep_listening=True)
        print("[TEST] Results sent to controller")
    except Exception as e:
        print(f"[TEST] Error sending results: {e}")


def relay_mode():
    """Relay mode - listen for commands from controller"""
    print("[RELAY MODE] Listening for commands...")

    while True:
        # Check for mode switch request
        key = check_serial_input()
        if key:
            return MODE_CONTROLLER

        # Listen for packets from controller
        packet = rfm69.receive(timeout=0.1)
        if packet is not None:
            try:
                packet_text = str(packet, "utf-8")
                rssi = rfm69.last_rssi

                # Check if this is a command
                if packet_text.startswith("{"):
                    try:
                        cmd = json.loads(packet_text)
                        cmd_type = cmd.get("type")

                        if cmd_type == "test":
                            print(f"[RELAY] Received test command | RSSI: {rssi}db")
                            run_test(cmd)

                        elif cmd_type == "info_request":
                            print(f"[RELAY] Received info request | RSSI: {rssi}db")
                            info_msg = {
                                "type": "info",
                                "temperature": rfm69.temperature,
                                "frequency": rfm69.frequency_mhz,
                                "bitrate": rfm69.bitrate,
                                "tx_power": rfm69.tx_power,
                                "high_power": rfm69.high_power,
                            }
                            try:
                                info_data = bytes(json.dumps(info_msg), "utf-8")
                                rfm69.send(info_data, keep_listening=True)
                                print("[RELAY] Device info sent to controller")
                            except Exception as e:
                                print(f"[RELAY] Error sending info: {e}")

                        else:
                            print(f"[RELAY] Unknown command type: {cmd_type}")
                    except Exception as e:
                        print(f"[RELAY] Error parsing command: {e}")
                else:
                    print(f"[RELAY] Received: {packet_text} | RSSI: {rssi}db")
            except Exception as e:
                print(f"[RELAY] Error decoding packet: {e}")

        time.sleep(0.01)


def get_user_input(prompt, default):
    """Get user input with a default value"""
    print(f"{prompt} [{default}]: ", end="")
    sys.stdout.flush()

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
                    sys.stdout.flush()
            else:
                user_input += char
                print(char, end="")
                sys.stdout.flush()

        time.sleep(0.01)


def render_results_table():
    """Render results as a markdown table"""
    if not relay_results:
        print("\n[CONTROLLER] No test results yet\n")
        return

    print("\n" + "=" * 80)
    print("TEST RESULTS TABLE")
    print("=" * 80)

    # Calculate distances for different n values
    print(
        "\n| Device | TX Power | RSSI (db) | Packet Loss | Dist(n=2) | Dist(n=3) | Dist(n=4) |"
    )
    print(
        "|--------|----------|-----------|-------------|-----------|-----------|-----------|"
    )

    for device_id, result in relay_results.items():
        tx_power = result.get("tx_power", 0)
        rssi = result.get("rssi", 0)
        packet_loss = result.get("packet_loss", 0)

        dist_n2 = calculate_distance(tx_power, rssi, distance_params["A"], 2.0)
        dist_n3 = calculate_distance(tx_power, rssi, distance_params["A"], 3.0)
        dist_n4 = calculate_distance(tx_power, rssi, distance_params["A"], 4.0)

        print(
            f"| {device_id:<6} | {tx_power:>8}db | {rssi:>9.1f} | {packet_loss:>10.1f}% | {dist_n2:>8.1f}m | {dist_n3:>8.1f}m | {dist_n4:>8.1f}m |"
        )

    print("\nDistance calculation parameters:")
    print(f"  A (signal @ 1m): {distance_params['A']}db")
    print(f"  n (path loss): {distance_params['n']}")
    print("=" * 80 + "\n")


def controller_mode():
    """Controller mode - send commands to relays"""
    print("\n" + "=" * 50)
    print("CONTROLLER MODE ACTIVATED")
    print("=" * 50)
    print("Commands:")
    print("  r - Return to relay mode")
    print("  s - Start test (send command to relays)")
    print("  c - Configure test parameters")
    print("  d - Configure distance calculation parameters")
    print("  p - Show current parameters")
    print("  t - Show results table")
    print("  q - Request relay device info")
    print("  i - Show local device info")
    print("=" * 50 + "\n")

    print(f"Current test parameters:")
    print(f"  Packets: {test_params.num_packets}")
    print(f"  Delay: {test_params.delay_ms}ms")
    print(f"  High Power: {test_params.high_power}")
    print(f"  TX Power: {test_params.tx_power}db")
    print()

    transmit_sequence = 0
    next_device_id = 1

    while True:
        # Check for commands
        key = check_serial_input()

        if key == "r":
            print("\n[CONTROLLER] Switching back to relay mode...\n")
            return MODE_RELAY

        elif key == "s":
            # Send test command to relays
            print("\n[CONTROLLER] Sending test command to relays...")

            cmd = {
                "type": "test",
                "num_packets": test_params.num_packets,
                "delay_ms": test_params.delay_ms,
                "high_power": test_params.high_power,
                "tx_power": test_params.tx_power,
            }

            try:
                cmd_data = bytes(json.dumps(cmd), "utf-8")
                rfm69.send(cmd_data, keep_listening=True)
                print(f"[CONTROLLER] Test command sent")
            except Exception as e:
                print(f"[CONTROLLER] Error sending command: {e}")

        elif key == "c":
            # Configure parameters
            print("\n[CONTROLLER] Configure Test Parameters")
            print("-" * 40)

            try:
                num_packets = int(
                    get_user_input("Number of packets", test_params.num_packets)
                )
                delay_ms = int(
                    get_user_input(
                        "Delay between packets (ms)", test_params.delay_ms
                    )
                )
                high_power_str = get_user_input(
                    "High power mode (true/false)", test_params.high_power
                )
                high_power = high_power_str.lower() in ["true", "t", "1", "yes", "y"]
                tx_power = int(get_user_input("TX power (db)", test_params.tx_power))

                test_params.num_packets = num_packets
                test_params.delay_ms = delay_ms
                test_params.high_power = high_power
                test_params.tx_power = tx_power

                print("\n[CONTROLLER] Parameters updated:")
                print(f"  Packets: {test_params.num_packets}")
                print(f"  Delay: {test_params.delay_ms}ms")
                print(f"  High Power: {test_params.high_power}")
                print(f"  TX Power: {test_params.tx_power}db\n")
            except Exception as e:
                print(f"\n[CONTROLLER] Error updating parameters: {e}\n")

        elif key == "d":
            # Configure distance calculation parameters
            print("\n[CONTROLLER] Configure Distance Parameters")
            print("-" * 40)

            try:
                A = float(get_user_input("A value (signal @ 1m)", distance_params["A"]))
                n = float(
                    get_user_input("n value (path loss exponent)", distance_params["n"])
                )

                distance_params["A"] = A
                distance_params["n"] = n

                print("\n[CONTROLLER] Distance parameters updated:")
                print(f"  A: {distance_params['A']}db")
                print(f"  n: {distance_params['n']}\n")
            except Exception as e:
                print(f"\n[CONTROLLER] Error updating distance parameters: {e}\n")

        elif key == "p":
            # Show parameters
            print(f"\n[CONTROLLER] Current test parameters:")
            print(f"  Packets: {test_params.num_packets}")
            print(f"  Delay: {test_params.delay_ms}ms")
            print(f"  High Power: {test_params.high_power}")
            print(f"  TX Power: {test_params.tx_power}db")
            print(f"\nDistance calculation parameters:")
            print(f"  A (signal @ 1m): {distance_params['A']}db")
            print(f"  n (path loss): {distance_params['n']}\n")

        elif key == "t":
            # Show results table
            render_results_table()

        elif key == "q":
            # Request relay device info
            print("\n[CONTROLLER] Requesting device info from relays...")
            cmd = {"type": "info_request"}
            try:
                cmd_data = bytes(json.dumps(cmd), "utf-8")
                rfm69.send(cmd_data, keep_listening=True)
                print("[CONTROLLER] Info request sent\n")
            except Exception as e:
                print(f"[CONTROLLER] Error sending info request: {e}\n")

        elif key == "i":
            print(
                f"\n[INFO] Temperature: {rfm69.temperature}C | TX Power: {rfm69.tx_power}dbm | Freq: {rfm69.frequency_mhz}mhz\n"
            )

        # Listen for responses
        packet = rfm69.receive(timeout=0.1)
        if packet is not None:
            try:
                packet_text = str(packet, "utf-8")
                rssi = rfm69.last_rssi

                # Check if this is a result message
                if packet_text.startswith("{"):
                    try:
                        msg = json.loads(packet_text)
                        msg_type = msg.get("type")

                        if msg_type == "result":
                            # Store result with device ID
                            device_id = f"dev{next_device_id:02d}"
                            relay_results[device_id] = {
                                "rssi": rssi,
                                "tx_power": msg.get(
                                    "tx_power", test_params.tx_power
                                ),
                                "packet_loss": msg["packet_loss"],
                                "sent": msg["sent"],
                                "received": msg["received"],
                                "duration": msg["duration"],
                                "temperature": msg.get("temperature", 0),
                                "high_power": msg.get("high_power", False),
                            }

                            print(
                                f"\n[CONTROLLER] Received test results from {device_id} | RSSI: {rssi}db"
                            )
                            print(f"  Sent: {msg['sent']}")
                            print(f"  Received: {msg['received']}")
                            print(f"  Packet Loss: {msg['packet_loss']:.1f}%")
                            print(f"  Duration: {msg['duration']:.2f}s")
                            print(f"  Temperature: {msg.get('temperature', 'N/A')}C\n")

                            next_device_id += 1

                        elif msg_type == "info":
                            print(
                                f"\n[CONTROLLER] Received device info | RSSI: {rssi}db"
                            )
                            print(f"  Temperature: {msg.get('temperature', 'N/A')}C")
                            print(f"  Frequency: {msg.get('frequency', 'N/A')}mhz")
                            print(
                                f"  Bitrate: {msg.get('bitrate', 0) / 1000:.1f}kbit/s"
                            )
                            print(f"  TX Power: {msg.get('tx_power', 'N/A')}dbm")
                            print(f"  High Power: {msg.get('high_power', 'N/A')}\n")

                        else:
                            print(
                                f"[CONTROLLER] Received JSON: {packet_text} | RSSI: {rssi}db"
                            )
                    except Exception as e:
                        print(f"[CONTROLLER] Error parsing JSON: {e}")
                        print(f"[CONTROLLER] Received: {packet_text} | RSSI: {rssi}db")
                else:
                    print(f"[CONTROLLER] Received: {packet_text} | RSSI: {rssi}db")
            except Exception as e:
                print(f"[CONTROLLER] Error decoding packet: {e}")

        time.sleep(0.01)


# Main loop
while True:
    if current_mode == MODE_RELAY:
        current_mode = relay_mode()
    elif current_mode == MODE_CONTROLLER:
        current_mode = controller_mode()
