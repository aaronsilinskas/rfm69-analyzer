import board
import busio
import digitalio
import adafruit_rfm69

# Setup RFM69 radio module
RADIO_FREQ_MHZ = 915.0  # Frequency of the radio in Mhz. Must match your RFM module!
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)


def init_onboard_rfm69() -> adafruit_rfm69.RFM69 | None:
    """Initialize embedded RFM69 module"""
    try:
        if not hasattr(board, "RFM_CS") or not hasattr(board, "RFM_RST"):
            print("Onboard RFM69 pins not defined, skipping onboard initialization.")
            return None

        return adafruit_rfm69.RFM69(
            spi,
            cs=digitalio.DigitalInOut(board.RFM_CS),
            reset=digitalio.DigitalInOut(board.RFM_RST),
            frequency=RADIO_FREQ_MHZ,
        )
    except Exception as e:
        print(f"Embedded RFM69 module not detected: {e}")
        return None


def init_external_rfm69() -> adafruit_rfm69.RFM69 | None:
    """Initialize external RFM69 module"""
    try:
        RFM_CS_PIN = board.D10
        RFM_RESET_PIN = board.D9

        return adafruit_rfm69.RFM69(
            spi,
            cs=digitalio.DigitalInOut(RFM_CS_PIN),
            reset=digitalio.DigitalInOut(RFM_RESET_PIN),
            frequency=RADIO_FREQ_MHZ,
            baudrate=1000000,
        )
    except Exception as e:
        print(f"External RFM69 module not detected: {e}")

        return None


def init_rfm69() -> adafruit_rfm69.RFM69 | None:
    """Initialize RFM69 module, trying onboard first then external."""
    rfm69 = init_onboard_rfm69()
    if rfm69 is not None:
        return rfm69

    return init_external_rfm69()


def attempt_send(rfm69: adafruit_rfm69.RFM69, data: bytes):
    """Attempt to send data via RFM69, returning success status."""
    if not rfm69.send(data, keep_listening=True):
        raise RuntimeError("Time out sending data via RFM69.", data)
