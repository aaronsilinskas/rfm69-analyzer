import adafruit_rfm69


class TestParameters:
    num_packets: int = 10
    delay_ms: int = 1000
    stagger_ms: int = 100
    high_power: bool = True
    tx_power: int = 13


class RunTestRequest(TestParameters):
    @staticmethod
    def encode(params: TestParameters) -> bytes:
        return bytes(
            f"R:{params.num_packets}:{params.delay_ms}:{params.stagger_ms}:{int(params.high_power)}:{params.tx_power}",
            "utf-8",
        )

    @staticmethod
    def decode(params: list[str]) -> "RunTestRequest":
        request = RunTestRequest()
        request.num_packets = int(params[0])
        request.delay_ms = int(params[1])
        request.stagger_ms = int(params[2])
        request.high_power = bool(int(params[3]))
        request.tx_power = int(params[4])
        return request


class RunTestResponse:
    def __init__(self):
        self.device_id: str = ""
        self.packet_num: int = 0

    @staticmethod
    def encode(device_id: str, packet_num: int) -> bytes:
        return bytes(f"RR:{device_id}:{packet_num}", "utf-8")

    @staticmethod
    def decode(params: list[str]) -> "RunTestResponse":
        response = RunTestResponse()
        response.device_id = params[0]
        response.packet_num = int(params[1])
        return response


class InfoRequest:
    @staticmethod
    def encode() -> bytes:
        return bytes("I", "utf-8")

    @staticmethod
    def decode(params: list[str]) -> "InfoRequest":
        return InfoRequest()


class InfoResponse:
    def __init__(self):
        self.device_id: str = ""
        self.high_power: bool = False
        self.tx_power: int = 0
        self.temperature: float = 0.0
        self.frequency_mhz: float = 0.0
        self.bitrate_kbps: float = 0.0
        self.frequency_deviation: int = 0

    @staticmethod
    def encode(
        device_id: str,
        high_power: bool,
        tx_power: int,
        temperature: float,
        frequency_mhz: float,
        bitrate_kbps: float,
        frequency_deviation_hz: float,
    ) -> bytes:
        return bytes(
            f"IR:{device_id}:{high_power}:{tx_power}:{temperature}:{frequency_mhz}:{bitrate_kbps}:"
            f"{frequency_deviation_hz}",
            "utf-8",
        )

    @staticmethod
    def decode(params: list[str]) -> "InfoResponse":
        response = InfoResponse()
        response.device_id = params[0]
        response.high_power = bool(params[1])
        response.tx_power = int(params[2])
        response.temperature = float(params[3])
        response.frequency_mhz = float(params[4])
        response.bitrate_kbps = float(params[5])
        response.frequency_deviation = float(params[6])

        return response


def decode_packet(packet: bytes):
    """Parse incoming packet and return command and parameters"""
    packet_text = str(packet, "utf-8")
    parts = packet_text.split(":")

    cmd = parts[0]
    params = parts[1:] if len(parts) > 1 else []
    if cmd == "R":
        return RunTestRequest.decode(params)
    if cmd == "RR":
        return RunTestResponse.decode(params)
    if cmd == "I":
        return InfoRequest.decode(params)
    if cmd == "IR":
        return InfoResponse.decode(params)

    return None


def check_for_message(rfm69: adafruit_rfm69.RFM69) -> tuple[any | None, float | None]:
    try:
        packet = rfm69.receive(timeout=0.1, keep_listening=True)
        if packet is not None:
            rssi = rfm69.last_rssi
            message = decode_packet(packet)
            return message, rssi
        return None, None
    except Exception as e:
        print(f"Error decoding packet: {e}")
        return None, None
