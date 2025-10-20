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
        RFM_CS_PIN = board.D12
        RFM_RESET_PIN = board.D5

        return adafruit_rfm69.RFM69(
            spi,
            cs=digitalio.DigitalInOut(RFM_CS_PIN),
            reset=digitalio.DigitalInOut(RFM_RESET_PIN),
            frequency=RADIO_FREQ_MHZ,
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
