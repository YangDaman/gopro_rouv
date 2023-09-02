# GoPro ROUV
## Overview

The GoPro ROUV is a 5-thruster remote-controlled underwater drone. It is capable of diving to a depth of 30ft and recording video with the attached GoPro. The pilot receives a live feed through the onboard FPV camera. The system is primarily driven by two Raspberry Pi 4B's, one in the floating buoy and one in the main electronics enclosure, connected via an Ethernet cable. Data is sent between the two RPi's using TCP/IP, and the system uses Linux/Python to operate. It is powered by a 14.8V 22,000mAh battery.

![image](https://github.com/YangDaman/gopro_rouv/assets/69991904/4285ed5c-3687-4f91-9572-e621a569097e)

This project was built by Daman Yang, Grant Recker, Elliott Mitchell, Rachel Zou, and Grant Olick-Sutphen.

For further reading, please click [here](https://damanyang.com/gopro-rouv).


## Signal Transmission
Transmitting signals 30ft underwater is a challenge, as conventional wireless signals do not go very far underwater. Furthermore, wired signals can suffer from signal deteoriation dependent on the length of the wire. The GoPro ROUV utilizes a buoy to receive wireless signals from a PS4 DualShock Controller, which is then sent down to the drone through an Ethernet cable. The BUOY_Pi is used to receive wireless signals from the DualShock Controller, and the ROUV_Pi is used to control the thrusters and lights, as well as detecting any leakage.

The live analog feed from the FPV camera is transmitted through a two-strand cable to the VTX transmitter in the buoy. The VTX transmitter then sends the video feed as a 5GHz signal to the Live Feed Receiver.

![image](https://github.com/YangDaman/gopro_rouv/assets/69991904/8aecebad-408a-4954-a40a-f7f265f8c98b)

### Data Packets
A typical command is sent to the drone as such:
1) The pilot presses a button on the Dualshock controller.
2) The DualShock controller relays the input to the BUOY_RPi via Bluetooth.
3) The BUOY_RPi receives the input and formats a data packet using the `create_message()` function. This returns a struct (formatted in short little endian) where the first two bytes are the packet's length, followed by the rest of the message.
4) The BUOY_RPi sends the data packet through the Ethernet cable to the ROUV_RPi.
5) The ROUV_RPi uses the `handle_client()` function and reads the first two bytes of the packet to confirm message length. It continues to receive until all bytes have been accounted for.
6) The ROUV_RPi reads the message and sends the specified PWM signal to the thrusters/lights, performing the commanded maneuver.
7) Once the signal is sent, the ROUV_RPi continues to listen for the next data packet.


## Controller
The DualShock controller's connection to the BUOY_RPi uses ArturSpirin's [pyPS4Controller module](https://github.com/ArturSpirin/pyPS4Controller).

The joystick readings on the DualShock controller have a max/min value of +/- 32767 for each axis. The UP and LEFT values are negative, while the DOWN and RIGHT values are positive. In order to simplify this, the input value is divided by 100 and rounded up to vield a value of +/- 1 ~ 327. This is then separated into 3 levels, corresponding to different thruster speeds: 

- Level 1 is a value between +/- 1 ~ 100
- Level 2 is a value between +/- 101 ~ 200
- Level 3 is a value between +/- 201 ~ 327


## Pulse Width Modulation
After initial testing with the standard RPi.GPIO library failed to activate the thrusters, we realized we needed a more precise PWM signal. This was achieved with joan2937's [pigpio module](https://github.com/joan2937/pigpio/blob/master/pigpio.py), which interfaces with the pigpio daemon to use hardware-timed PWM. 

The PWM frequency is set to 100Hz. (100Hz = 1/100s period = 0.01s = 10,000us). This enables full control of the thrusters and lights between 11% and 19% duty cycle, with 15% DC being the STOP signal for the thrusters. Setting the PWM range from 0 ~ 9999 enables control of the PWM signal down to the microsecond.

The BlueRobotics T200 thrusters, when supplied with 14.8V, are able to produce a maximum forward thrust of ~4.53kgf and a maximum reverse thrust of ~3.52kgf.

<img width="1088" alt="image" src="https://github.com/YangDaman/gopro_rouv/assets/69991904/db210281-577b-479c-9774-60f56848dc64">

Note: Due to the reversed directions of the thruster propellers on thrusters 1 and 4 (in order to balance out the torque and keep the drone level while moving), they receive different PWM signals than their counterparts in order to produce the same thrust.


## Auto-Start
Since the GoPro ROUV needs to start up with the flick of a switch, the various scripts need to boot in the correct order without interfacing with the GUI. This is accomplished with the systemd daemon. See [method 4](https://www.dexterindustries.com/howto/run-a-program-on-your-raspberry-pi-at-startup/).


## Safety Features
In the event of overheating or a leak, an exception is raised and interrupts whatever the drone is currently doing. Before listening for the next command, the system checks the RPi's CPU temp as well as the leak sensor reading.

- If a leak occurs, the ROUV_RPi sends a leak alert message to the BUOY_RPi, which would light up the Leak Indicator LED on the BUOY. The drone then moves upward at full speed for 10 seconds to reach the surface before cutting power to the thrusters.
- If an overheat occurs, the ROUV_RPi sends an overheat alert message to the BUOY_RPi, which would light up the Overheat Indicator LED on the BUOY. The drone then cuts power to the thrusters.


## Potential Improvements
1) Running the system with Arduino + an Ethernet shield, coding in C++ or other compiled language
  - Easier to work with PWM on Arduino systems.
  - Compiled language enables the system to respond faster to real-time events, such as controller inputs or leaks.
2) Implement multithreading to allow for parallel processes (real-time readouts, leak/overheat procedures, etc.).
3) Finish implementing the IMU (originally planned, but scrapped due to difficulties integrating the ICM-20948 DMP with Python and time constraints). This will enable the addition of a control system to maintain depth/heading or pitch/roll angle, further stablizing the video recording.

Thank you for your interest in this project! If you have any further questions, you can contact me at yang.shaoh@northeastern.edu.
