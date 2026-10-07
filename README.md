# rfm69-analyzer

A range and reliability test tool for RFM69HCW radios, written in CircuitPython.

Put the same code on two or more boards. One board is the controller: it tells the others to send a burst of test packets, then reports signal strength (RSSI), packet loss, and a rough distance estimate for each of them.

It was built for [Aura](https://mindwidgets.com), a real-world adventure game platform, to find out whether this radio is a good fit for devices that players carry and wear.

## What you need

- Two or more CircuitPython boards with an RFM69HCW radio:
  - [Adafruit Feather RP2040 RFM69](https://www.adafruit.com/product/5712), which has the radio on board, or
  - another CircuitPython board wired to an [RFM69HCW breakout](https://www.adafruit.com/product/3070) over SPI, with chip select on `D10` and reset on `D9`.
- An antenna on each radio.
- A battery on each board. On USB power alone, transmitting can draw enough current to cause random "Operation Mode failed to set" errors.
- A computer with a serial console for the controller board.

The code expects the board to have an on-board NeoPixel and LED (`board.NEOPIXEL`, `board.LED`), which it uses to show status.

The radio frequency is set to 915 MHz in `rfm_util.py`. Change `RADIO_FREQ_MHZ` to match your module and what is legal where you live.

## Install

Copy the `.py` files and the `lib` folder to the `CIRCUITPY` drive of every board. The libraries the tool needs are included in `lib`.

## Run a test

1. Power up every board. Each one starts in relay mode, listening for commands. The NeoPixel is green when a board is ready, blue while it is busy, and blinks red on an error.
2. Connect one board to a serial console and press any key. That board is now the controller.
3. Type a command and press Enter:

| Command | What it does |
| ------- | ------------ |
| `s` | Start a test: every relay in range sends its packets |
| `c` | Set the test parameters |
| `d` | Set the "A" value used for the distance estimate |
| `p` | Show the current parameters |
| `t` | Show the results table again |
| `q` | Ask the relays for their radio settings |
| `i` | Show this board's radio settings |
| `r` | Go back to relay mode |
| `h` | Show the command list |

The test parameters, with their defaults:

| Parameter | Default | Notes |
| --------- | ------- | ----- |
| Number of packets | 10 | Sent by each relay |
| Delay between packets | 1000 ms | |
| Stagger | 100 ms | A random extra delay, so relays don't all send at once |
| High power mode | on | |
| TX power | 13 dBm | |

When the test ends, the controller prints a table with one row for each relay that answered:

- **RSSI min / max / avg**: the signal strength of that relay's packets, as heard by the controller.
- **Packet loss**: the share of that relay's packets the controller did not receive.
- **Dist (n=2, 3, 4)**: a distance estimate from the average RSSI, for three kinds of surroundings (see below).

Move the relays, change the parameters, and run it again.

### The distance estimate

The estimate uses the log-distance path loss model:

```
distance = 10 ^ ((TX power - RSSI - A) / (10 × n))
```

`A` is the signal loss at 1 meter and `n` describes the surroundings: about 2 in open space, higher with walls and furniture in the way. Both have to be tuned for your radios and your space, so treat the result as a rough guide only.

## What we learned

These are observations from tests indoors, in an apartment, in October 2025, with RFM69HCW radios at 915 MHz. They are not specifications, and no outdoor or maximum-range test has been done yet.

Signal strength and packet loss at 10 meters, high power mode on:

| TX power | Average RSSI | Packet loss |
| -------- | ------------ | ----------- |
| 13 dBm | -70.0 dBm | under 5% |
| 14 dBm | -67.5 dBm | under 5% |
| 15 dBm | -61.5 dBm | under 5% |
| 16 dBm | -57.0 dBm | under 5% |
| 17 dBm | -55.0 dBm | under 5% |
| 20 dBm | -42.0 dBm | under 5% |

Other things we saw:

- From one corner of the apartment to the opposite corner, through walls, at 20 dBm: about -80.5 dBm average RSSI and under 5% packet loss.
- At 16 meters, high power mode on: about -62.5 dBm average RSSI with 5 to 10% packet loss at -2 dBm TX power, and about -43.4 dBm with 10% packet loss at 20 dBm.
- The radio can also be turned down for very short range. With high power mode off, the signal was already weak (about -65 dBm) at 10 to 15 centimeters.
- A closed door or a wall between two radios showed up clearly, usually as a drop of 10 dB or more.
- Packets are sometimes lost even when the signal is strong, and even with a large stagger. Anything that must arrive needs an acknowledgement and a retry.
- The distance estimate matched a measured 4.5 meters with `A` = 35 and `n` = 4 (13 dBm, high power mode on, -48.8 dBm average RSSI). It is good enough to tell near from far, not to measure.
- The antenna worked best standing perpendicular to the board.
- Each send blocks CircuitPython for roughly 10 milliseconds.
- TX power can't usefully be changed packet by packet while also listening: the radio stops receiving while it transmits.

## License

MIT. See [LICENSE](LICENSE).
