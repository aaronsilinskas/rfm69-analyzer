import time
import board
import busio
import digitalio
import displayio
import terminalio
import adafruit_rfm69
from adafruit_debouncer import Debouncer
from adafruit_display_text import label
from i2cdisplaybus import I2CDisplayBus

import adafruit_displayio_sh1107

# Pins

RFM_CS_PIN = board.D12
RFM_RESET_PIN = board.D5
TX_POWER_UP_PIN = board.D9
TX_POWER_DOWN_PIN = board.D6
TX_DELAY_UP_PIN = board.D11
TX_DELAY_DOWN_PIN = board.D10

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
transmit_delay = 1.0  # Seconds between transmissions


# Button Setup
def setup_button(pin: int) -> Debouncer:
    button = digitalio.DigitalInOut(pin)
    button.direction = digitalio.Direction.INPUT
    button.pull = digitalio.Pull.UP
    return Debouncer(button, interval=0.020)


tx_power_up_button = setup_button(TX_POWER_UP_PIN)
tx_power_down_button = setup_button(TX_POWER_DOWN_PIN)
tx_delay_up_button = setup_button(TX_DELAY_UP_PIN)
tx_delay_down_button = setup_button(TX_DELAY_DOWN_PIN)
buttons = [
    tx_power_up_button,
    tx_power_down_button,
    tx_delay_up_button,
    tx_delay_down_button,
]

# OLED Display Setup

# i2c = board.I2C()  # uses board.SCL and board.SDA
i2c = board.STEMMA_I2C()  # Built-in STEMMA QT connector
displayio.release_displays()
display_bus = I2CDisplayBus(i2c, device_address=0x3C)
# SH1107 is vertically oriented 64x128
WIDTH = 128
HEIGHT = 64

display = adafruit_displayio_sh1107.SH1107(
    display_bus, width=WIDTH, height=HEIGHT, rotation=270
)

# Make the display context
splash = displayio.Group()
display.root_group = splash

color_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0xFFFFFF  # White

bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
splash.append(bg_sprite)

# Fill all but the border with black
inner_bitmap = displayio.Bitmap(WIDTH - 2, HEIGHT - 2, 1)
inner_palette = displayio.Palette(1)
inner_palette[0] = 0x000000  # Black
black_background = displayio.TileGrid(
    inner_bitmap, pixel_shader=inner_palette, x=1, y=1
)
splash.append(black_background)

transmit_power_label = label.Label(terminalio.FONT, color=0xFFFFFF, x=4, y=14)
splash.append(transmit_power_label)

high_power_label = label.Label(terminalio.FONT, color=0xFFFFFF, x=4, y=30)
splash.append(high_power_label)

transmit_delay_label = label.Label(terminalio.FONT, color=0xFFFFFF, x=4, y=46)
splash.append(transmit_delay_label)


def update_display():
    transmit_power_label.text = "TX Power: {} dBm".format(rfm69.tx_power)
    high_power_label.text = "High Power: {}".format(rfm69.high_power)
    transmit_delay_label.text = "TX Delay: {:.1f} s".format(transmit_delay)


update_display()

# Print chip state:
print(f"Temperature: {rfm69.temperature}C")
print(f"Frequency: {rfm69.frequency_mhz}mhz")
print(f"Bit rate: {rfm69.bitrate / 1000}kbit/s")
print(f"Frequency deviation: {rfm69.frequency_deviation}hz")
print(f"Transmit power: {rfm69.tx_power}dbm")

last_transmit = 0
transmit_sequence = 1000

while True:
    for button in buttons:
        button.update()

    if tx_power_up_button.fell:
        if rfm69.tx_power < 20:
            if not rfm69.high_power and rfm69.tx_power >= 13:
                rfm69.high_power = True
                print("High power mode enabled")

            rfm69.tx_power += 1

            update_display()
            print(
                f"\nTransmit power increased to {rfm69.tx_power} dBm, high power mode: {rfm69.high_power}"
            )
        else:
            print("\nTransmit power is already at maximum (20 dBm)")

    if tx_power_down_button.fell:
        if rfm69.tx_power > -18:
            if rfm69.high_power and rfm69.tx_power <= 2:
                rfm69.high_power = False
                print("\nHigh power mode disabled")

            rfm69.tx_power -= 1

            update_display()
            print(
                f"\nTransmit power decreased to {rfm69.tx_power} dBm, high power mode: {rfm69.high_power}"
            )
        else:
            print("\nTransmit power is already at minimum (-18 dBm)")

    if tx_delay_up_button.fell:
        transmit_delay += 0.2

        update_display()
        print(f"\nTransmit delay increased to {transmit_delay} seconds")

    if tx_delay_down_button.fell:
        if transmit_delay > 0.2:
            transmit_delay -= 0.2

            update_display()
            print(f"\nTransmit delay decreased to {transmit_delay} seconds")
        else:
            print("\nTransmit delay is already at minimum (0.2 seconds)")

    if time.monotonic() - last_transmit >= transmit_delay:
        last_transmit = time.monotonic()
        data = bytes("Ping {}".format(transmit_sequence), "utf-8")        
        rfm69.send(data, keep_listening=True)

        print(transmit_sequence, rfm69.tx_power, rfm69.high_power, end=" ")
        transmit_sequence += 1
