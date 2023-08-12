# GoPro_ROUV
## Overview

The GoPro ROUV is a 5-thruster remote-controlled underwater drone. It is capable of diving to a depth of 30ft and recording video with the attached GoPro. The pilot receives a live feed through the onboard FPV camera. The system is primarily driven by two Raspberry Pi 4B's, one in the floating buoy and one in the main electronics enclosure, connected via an Ethernet cable. Data is sent between the two RPi's using TCP/IP, and the system uses Linux/Python to operate.

This project was built by Daman Yang, Grant Recker, Elliott Mitchell, Rachel Zou, and Grant Olick-Sutphen.

## Signal Transmission
Transmitting signals 30ft underwater is a challenge, as conventional wireless signals do not go very far underwater. Furthermore, wired signals can suffer from signal deteoriation dependent on the length of the wire. The GoPro ROUV utilizes a buoy to receive wireless signals from a PS4 DualShock Controller, which is then sent down to the drone through an Ethernet cable. The BUOY_Pi is used to receive wireless signals from the DualShock Controller, and the ROUV_Pi is used to control the thrusters and lights, as well as detecting any leakage.

### Data Packets
A typical command is sent to the drone as such:
1) The pilot presses a button on the Dualshock controller.
2) The DualShock controller relays the input to the BUOY_RPi via Bluetooth.
3) The BUOY_RPi receives the input and formats a data packet using the `create_message()` function. This returns a struct (formatted in short little endian) where the first two bytes are the packet's length, followed by the rest of the message.
4) The BUOY_RPi sends the data packet through the Ethernet cable to the ROUV_RPi.
5) The ROUV_RPi reads the first two bytes of the packet to confirm message length. It continues to receive until all bytes have been accounted for.
6) The ROUV_RPi reads the message and sends the specified PWM signal to the thrusters/lights, performing the commanded maneuver.

## Controller

## Auto-Start

##
