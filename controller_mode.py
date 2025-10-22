import time
import adafruit_rfm69
from input import MODE_RELAY, check_serial_input, get_user_input
from packets import (
    InfoRequest,
    InfoResponse,
    RunTestRequest,
    RunTestResponse,
    TestParameters,
    check_for_message,
)
from rfm_util import attempt_send
from rgb_indicator import indicate_processing, indicate_ready


class TestResult:
    def __init__(self):
        self.sequence: int = 0
        self.rssi: float = 0.0


class ControllerMode:

    def __init__(self, rfm69: adafruit_rfm69.RFM69, device_id: str):
        self._rfm69 = rfm69
        self._device_id = device_id
        self._test_params = TestParameters()
        self._distance_A = 35  # Estimated signal strength at 1 meter
        self._test_running = False
        self._test_timeout = 0.0
        self._test_run_results = {}  # device_id -> list of TestResult

    def _calculate_distance(self, tx_power, rssi, n):
        """Calculate distance based on RSSI using path loss model"""
        return 10 ** ((tx_power - rssi - self._distance_A) / (10 * n))

    def _render_results_table(self):
        """Render results as a markdown table"""
        if not self._test_run_results:
            print("No test results yet")
            return

        print("\n" + "=" * 80)
        print("TEST RESULTS TABLE")
        print("=" * 80)

        # Calculate distances for different n values
        print(
            "\n| Device | TX Power | RSSI Min | RSSI Max | RSSI Avg | Packet Loss | Dist(n=2) | Dist(n=3) | Dist(n=4) |"
        )
        print(
            "|--------|----------|-----------|-----------|-----------|-------------|-----------|-----------|-----------|"
        )

        for device_id, results in self._test_run_results.items():
            rssi_min = min(result.rssi for result in results)
            rssi_max = max(result.rssi for result in results)
            rssi_avg = sum(result.rssi for result in results) / len(results)

            packet_loss = 100.0 * (1 - (len(results) / self._test_params.num_packets))

            tx_power = self._test_params.tx_power
            dist_n2 = self._calculate_distance(tx_power, rssi_avg, 2.0)
            dist_n3 = self._calculate_distance(tx_power, rssi_avg, 3.0)
            dist_n4 = self._calculate_distance(tx_power, rssi_avg, 4.0)

            print(
                f"| {device_id:<6} | {tx_power:>8}db | {rssi_min:>9.1f} | {rssi_max:>9.1f} | {rssi_avg:>9.1f} | {packet_loss:>10.1f}% | {dist_n2:>8.1f}m | {dist_n3:>8.1f}m | {dist_n4:>8.1f}m |"
            )

        print("\nDistance calculation parameters:")
        print(f"  A (signal @ 1m): {self._distance_A}db")
        print("=" * 80 + "\n")

    def _show_help(self):
        """Display help menu"""
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
        print("  h - Show this help menu")
        print("=" * 50 + "\n")

        print(f"Current test parameters:")
        print(f"  Packets: {self._test_params.num_packets}")
        print(f"  Delay: {self._test_params.delay_ms}ms")
        print(f"  High Power: {self._test_params.high_power}")
        print(f"  TX Power: {self._test_params.tx_power}db")
        print()

    def run(self):
        """Controller mode - send commands to relays"""
        self._show_help()
        indicate_ready()

        while True:
            # Check for commands
            key = check_serial_input()

            if key == "r":
                print("\n[CONTROLLER] Switching back to relay mode...\n")
                return MODE_RELAY

            elif key == "s":
                # Send test command to relays
                print("\n[CONTROLLER] Sending test command to relays...")
                indicate_processing()

                test_params = self._test_params

                self._test_running = True
                self._test_timeout = time.monotonic() + (
                    test_params.num_packets * (test_params.delay_ms / 1000.0) + 2
                )
                self._test_run_results = {}

                request = RunTestRequest.encode(test_params)
                attempt_send(self._rfm69, request)
                print(f"[CONTROLLER] Test command sent")

            elif key == "c":
                # Configure parameters
                print("\n[CONTROLLER] Configure Test Parameters")
                print("-" * 40)

                num_packets = int(
                    get_user_input("Number of packets", self._test_params.num_packets)
                )
                delay_ms = int(
                    get_user_input(
                        "Delay between packets (ms)", self._test_params.delay_ms
                    )
                )
                stagger_ms = int(
                    get_user_input(
                        "Stagger (random delay) between packets (ms)",
                        self._test_params.stagger_ms,
                    )
                )
                high_power_str = get_user_input(
                    "High power mode (true/false)", self._test_params.high_power
                )
                high_power = high_power_str.lower() in [
                    "true",
                    "t",
                    "1",
                    "yes",
                    "y",
                ]
                tx_power = int(
                    get_user_input("TX power (db)", self._test_params.tx_power)
                )

                self._test_params.num_packets = num_packets
                self._test_params.delay_ms = delay_ms
                self._test_params.stagger_ms = stagger_ms
                self._test_params.high_power = high_power
                self._test_params.tx_power = tx_power

                print("\n[CONTROLLER] Parameters updated:")
                print(f"  Packets: {self._test_params.num_packets}")
                print(f"  Delay: {self._test_params.delay_ms}ms")
                print(f"  Stagger: {self._test_params.stagger_ms}ms")
                print(f"  High Power: {self._test_params.high_power}")
                print(f"  TX Power: {self._test_params.tx_power}db\n")

            elif key == "d":
                # Configure distance calculation parameters
                print("\n[CONTROLLER] Configure Distance Parameters")
                print("-" * 40)

                self._distance_A = float(
                    get_user_input("A value (signal @ 1m)", self._distance_A)
                )

                print("\n[CONTROLLER] Distance parameters updated:")
                print(f"  A: {self._distance_A}db")

            elif key == "p":
                # Show parameters
                print(f"\n[CONTROLLER] Current test parameters:")
                print(f"  Packets: {self._test_params.num_packets}")
                print(f"  Delay: {self._test_params.delay_ms}ms")
                print(f"  Stagger: {self._test_params.stagger_ms}ms")
                print(f"  High Power: {self._test_params.high_power}")
                print(f"  TX Power: {self._test_params.tx_power}db")
                print(f"\nDistance calculation parameters:")
                print(f"  A (signal @ 1m): {self._distance_A}db")

            elif key == "t":
                # Show results table
                self._render_results_table()

            elif key == "q":
                # Request relay device info
                print("\n[CONTROLLER] Requesting device info from relays...")

                request = InfoRequest.encode()
                attempt_send(self._rfm69, request)
                print("[CONTROLLER] Info request sent\n")

            elif key == "i":
                print(
                    f"\n[INFO] Device: {self._device_id} | Temperature: {self._rfm69.temperature}C | TX Power: {self._rfm69.tx_power}dbm | Freq: {self._rfm69.frequency_mhz}mhz\n"
                )
            elif key == "h":
                self._show_help()

            # Listen for packets from relays
            message, rssi = check_for_message(self._rfm69)
            if message is not None:
                if isinstance(message, RunTestResponse):
                    if message.device_id not in self._test_run_results:
                        self._test_run_results[message.device_id] = []

                    result = TestResult()
                    result.sequence = message.packet_num
                    result.rssi = rssi
                    self._test_run_results[message.device_id].append(result)

                    print(
                        f"\n[CONTROLLER] Received test results from {message.device_id} | {result.sequence} | RSSI: {rssi}db"
                    )
                elif isinstance(message, InfoResponse):
                    print(f"\n[CONTROLLER] Received device info | RSSI: {rssi}db")
                    print(f"  Device ID: {message.device_id}")
                    print(f"  High Power: {message.high_power}")
                    print(f"  TX Power: {message.tx_power}dbm")
                    print(f"  Temperature: {message.temperature}C")
                    print(f"  Frequency: {message.frequency_mhz}mhz")
                    print(f"  Bitrate: {message.bitrate_kbps / 1000:.1f}kbit/s")
                    print(f"  Frequency Deviation: {message.frequency_deviation}hz\n")
                else:
                    print(
                        f"[CONTROLLER] Received unhandled message: {message} | RSSI: {rssi}db"
                    )

            if self._test_running and time.monotonic() > self._test_timeout:
                self._test_running = False
                print("\n[CONTROLLER] Test run complete!")
                indicate_ready()

                self._render_results_table()
