import time
import adafruit_rfm69
from input import MODE_CONTROLLER, check_serial_input
from packets import (
    InfoResponse,
    InfoRequest,
    RunTestRequest,
    TestParameters,
    RunTestResponse,
    decode_packet,
)


class RelayMode:
    """Class to handle relay mode operations"""

    def __init__(self, rfm69: adafruit_rfm69.RFM69, device_id: str):
        self._rfm69 = rfm69
        self._device_id = device_id

    def _run_test(self, params: TestParameters):
        """Execute a test with the given parameters"""
        print(f"\n[TEST] Starting test with parameters:")
        print(f"  Packets: {params.num_packets}")
        print(f"  Delay: {params.delay_ms}ms")
        print(f"  High Power: {params.high_power}")
        print(f"  TX Power: {params.tx_power}db")

        # Configure radio
        self._rfm69.high_power = params.high_power
        self._rfm69.tx_power = params.tx_power

        delay_sec = params.delay_ms / 1000.0

        for i in range(params.num_packets):
            # Send test packet
            response = RunTestResponse.encode(self._device_id, i)
            self._rfm69.send(response, keep_listening=True)

            print(f"[TEST] Sent packet {i+1}/{params.num_packets}")

            time.sleep(delay_sec)

        print(f"\n[TEST] Complete:")

    def run(self):
        """Relay mode - listen for commands from controller"""
        print("[RELAY MODE] Listening for commands...")

        while True:
            # Check for mode switch request
            key = check_serial_input()
            if key:
                return MODE_CONTROLLER

            # Listen for packets from controller
            packet = self._rfm69.receive(timeout=0.1)
            if packet is not None:
                rssi = self._rfm69.last_rssi

                request = decode_packet(packet)

                # Check if this is a command
                if isinstance(request, RunTestRequest):
                    print(f"[RELAY] Received test command | RSSI: {rssi}db")
                    self._run_test(request)

                elif isinstance(request, InfoRequest):
                    print(f"[RELAY] Received info request | RSSI: {rssi}db")
                    response = InfoResponse.encode(
                        device_id=self._device_id,
                        high_power=self._rfm69.high_power,
                        tx_power=self._rfm69.tx_power,
                        temperature=self._rfm69.temperature,
                        frequency_mhz=self._rfm69.frequency_mhz,
                        bitrate_kbps=self._rfm69.bitrate,
                        frequency_deviation_hz=self._rfm69.frequency_deviation,
                    )

                    self._rfm69.send(response, keep_listening=True)
                    print("[RELAY] Device info sent to controller")
                else:
                    print(f"[RELAY] Unknown command type: {packet}")

            time.sleep(0.01)
