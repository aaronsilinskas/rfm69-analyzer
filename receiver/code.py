import time
import board
import busio
import digitalio
import adafruit_rfm69

# Pins

RFM_CS_PIN = board.RFM_CS
RFM_RESET_PIN = board.RFM_RST

# RFM69 Radio Setup

RADIO_FREQ_MHZ = 915.0  # Frequency of the radio in Mhz. Must match your RFM module!
# CS = digitalio.DigitalInOut(board.RFM69_CS)
# RESET = digitalio.DigitalInOut(board.RFM69_RST)
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
rfm69 = adafruit_rfm69.RFM69(
    spi,
    cs=digitalio.DigitalInOut(RFM_CS_PIN),
    reset=digitalio.DigitalInOut(RFM_RESET_PIN),
    frequency=RADIO_FREQ_MHZ,
)


# Print chip state:
print(f"Temperature: {rfm69.temperature}C")
print(f"Frequency: {rfm69.frequency_mhz}mhz")
print(f"Bit rate: {rfm69.bitrate / 1000}kbit/s")
print(f"Frequency deviation: {rfm69.frequency_deviation}hz")
print(f"Transmit power: {rfm69.tx_power}dbm")

last_sequence: int = -1

while True:
    packet = rfm69.receive(timeout=0.1)

    if packet is not None:
        rssi = rfm69.last_rssi
        if packet[0:5] == b"Ping ":
            sequence = int(packet[5:])
            if last_sequence > sequence:
                print("Transmitter sequence reset!")        
            elif last_sequence != -1 and sequence != (last_sequence + 1):
                print(f"Lost {sequence - last_sequence - 1} packets!")
            last_sequence = sequence

            print(f"Received: {sequence} with RSSI: {rssi}")
        else:
            print(f"Received (unknown format): {packet} with RSSI: {rssi}")
