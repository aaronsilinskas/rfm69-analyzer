import time
import board
import neopixel
from digitalio import DigitalInOut, Direction

led = DigitalInOut(board.LED)
led.direction = Direction.OUTPUT
led.value = False

onboard_neopixel = neopixel.NeoPixel(
    board.NEOPIXEL, 1, brightness=0.1, auto_write=False
)


def indicate_ready():
    """Set the RGB indicator to green to show the device is ready."""
    onboard_neopixel.fill((0, 255, 0))  # Green color
    onboard_neopixel.show()


def indicate_error(msg: str):
    """Set the RGB indicator to red to show an error state."""
    print(msg)
    for _ in range(3):
        led.value = True
        onboard_neopixel.fill((255, 0, 0))  # Red color
        onboard_neopixel.show()
        time.sleep(1)
        led.value = False
        onboard_neopixel.fill((0, 0, 0))  # Turn off
        onboard_neopixel.show()
        time.sleep(1)
    raise Exception(msg)


def indicate_processing():
    """Set the RGB indicator to blue to show processing state."""
    onboard_neopixel.fill((0, 0, 255))  # Blue color
    onboard_neopixel.show()
