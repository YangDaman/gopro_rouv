#Continuous Listening Mode
import socket
import struct
import pigpio
import time
import os
import math

ROUV_ADDRESS = ('', 42069)                 


#Thrusters controlled by varying PWM duty cycle.
#12% DC = Max Reverse (Actual max is 11%, limited due to current)
#15% DC = STOP
#18% DC = Max Forward (Actual max is 19%, limited due to current)

#In order to balance torque, thrusters 1 and 4 are run in the opposite direction of the other thrusters
#18% DC = 3kgf = 11.5% DC

#Joysticks broken up into 3 "levels"
#UP and LEFT values are negative while DOWN and RIGHT values are positive.
#Max joystick value is +/- 32767 for each axis
#Input value is divided by 100 and rounded up to yield +/- 1~327
#Level 1: Input value between +/- 1 and 100
#Level 2: Input value between +/- 101 and 200
#Level 3: Input value between +/- 201 and 327

#-----------CONSTANTS-----------
overheat = False                                #Assume temp is under 75 deg C
leak_detected = False                           #Assume there is no leak present
left_light_on = False                           #Left light initially off
right_light_on = False                          #Right light initially off
hover_on = False                                #Hovering initially off
up_speed = 1600                                 #Setting baseline upward speed to 16% DC
up_speed_14 = 1386                              #Baseline upward speed for thrusters 1 & 4
down_speed = 1400                               #Setting baseline downward speed to 14% DC
down_speed_14 = 1588                            #Baseline upward speed for thrusters 1 & 4

fwd_1 = 1600                                    #Joystick forward level 1 is 16% DC
fwd_1_14 = 1386                                 #fwd_1 for thrusters 1 & 4
fwd_2 = 1700                                    #Joystick forward level 2 is 17% DC
fwd_2_14 = 1268                                 #fwd_2 for thrusters 1 & 4
fwd_3 = 1800                                    #Joystick forward level 3 is 18% DC
fwd_3_14 = 1148                                 #fwd_3 for thrusters 1 & 4
rev_1 = 1400                                    #Joystick reverse level 1 is 14% DC
rev_1_14 = 1588                                 #rev_1 for thrusters 1 & 4
rev_2 = 1300                                    #Joystick reverse level 2 is 13% DC
rev_2_14 = 1672                                 #rev_2 for thrusters 1 & 4
rev_3 = 1200                                    #Joystick reverse level 3 is 12% DC
rev_3_14 = 1764                                 #rev_3 for thrusters 1 & 4

#-----------PIN DEFINITIONS-----------
thrust1 = 12                                    #Thruster 1 (left offset) using pin 26 (SOFTWARE PWM)
thrust2 = 16                                    #Thruster 2 (right offset) using pin 16 (SOFTWARE PWM)
thrust3 = 13                                    #Thruster 3 (center vertical) using pin 13 (HARDWARE PWM)
thrust4 = 25                                    #Thruster 4 (left rear) using pin 25 (SOFTWARE PWM)
thrust5 = 18                                    #Thruster 5 (right rear) using pin 24 (SOFTWARE PWM)
left_light = 27                                 #Left light using pin 22 (SOFWTWARE PWM)
right_light = 17                                #Right light using pin 17 (SOFTWARE PWM)
leak_sensor = 23

#-----------PIGPIO SETUP-----------
pi1 = pigpio.pi()
#Set mode for each pin:
pi1.set_mode(thrust1, pigpio.OUTPUT)
pi1.set_mode(thrust2, pigpio.OUTPUT)
pi1.set_mode(thrust3, pigpio.OUTPUT)
pi1.set_mode(thrust4, pigpio.OUTPUT)
pi1.set_mode(thrust5, pigpio.OUTPUT)
pi1.set_mode(left_light, pigpio.OUTPUT)
pi1.set_mode(right_light, pigpio.OUTPUT)
pi1.set_mode(leak_sensor, pigpio.INPUT)

#Set frequency for each pin:
pi1.set_PWM_frequency(thrust1, 100)             #100Hz = 1/100s period = 0.01s = 10,000us
pi1.set_PWM_frequency(thrust2, 100)             #This enables full control of thrusters and lights between 11% and 19% DC
pi1.set_PWM_frequency(thrust3, 100)             #with 15% DC being the STOP signal for the thrusters
pi1.set_PWM_frequency(thrust4, 100)
pi1.set_PWM_frequency(thrust5, 100)
pi1.set_PWM_frequency(left_light, 100)
pi1.set_PWM_frequency(right_light, 100)

#Set range for each pin:
pi1.set_PWM_range(thrust1, 9999)                  #Scaling the range to 0-9999 (instead of 0-255)
pi1.set_PWM_range(thrust2, 9999)                  #This enables control of thrusters accurate to 0.01% DC
pi1.set_PWM_range(thrust3, 9999)                  #PWM DC should be set to 0 or between 1100 and 1900
pi1.set_PWM_range(thrust4, 9999)
pi1.set_PWM_range(thrust5, 9999)
pi1.set_PWM_range(left_light, 9999)
pi1.set_PWM_range(right_light, 9999)

#-----------MISC. FUNCTIONS-----------
def check_temp():
    global overheat
    temp_read = os.popen('vcgencmd measure_temp').readline()
    cpu_temp = float(temp_read.replace("temp=","").replace("'C\n", ""))
    if (cpu_temp > 75):
        overheat = True
        
def check_leak():
    global leak_detected
    if (pi1.read(leak_sensor) == 1):
        leak_detected = True

def hover():
    print("Hovering")
    pi1.set_PWM_dutycycle(thrust1, 1402)
    pi1.set_PWM_dutycycle(thrust2, 1586)
    pi1.set_PWM_dutycycle(thrust3, 1618)
    pi1.set_PWM_dutycycle(thrust4, 1500)
    pi1.set_PWM_dutycycle(thrust5, 1500)
    print("Thruster 1: " + str(pi1.get_PWM_dutycycle(thrust1)))
    print("Thruster 2: " + str(pi1.get_PWM_dutycycle(thrust2)))
    print("Thruster 3: " + str(pi1.get_PWM_dutycycle(thrust3)))
    print("Thruster 4: " + str(pi1.get_PWM_dutycycle(thrust4)))
    print("Thruster 5: " + str(pi1.get_PWM_dutycycle(thrust5)))        
        
class LeakDetectedException(Exception):
    pass

class OverheatException(Exception):
    pass

#-----------SOCKET FUNCTIONS-----------
def create_message(text):
    return struct.pack("<H", len(text)) + bytes(text, 'utf-8')      #Struct is a bytes object. "<H" is for formatting (< for little endian, H denotes short). 
                                                                    #This function provides the fully formatted message.

def recv_all(socket, packet_size):                                  #Receive until all bytes have been accounted for.
    data = bytes()
    while len(data) < packet_size:
        data += socket.recv(packet_size - len(data))
    return data

def handle_client(csock):
    packet_len = csock.recv(2)                                      #Receive 2 bytes of data. First two bytes of every packet will contain packet length.
    print(int.from_bytes(packet_len, "little"))                     #Print number of bytes of message
    msg = recv_all(csock, int.from_bytes(packet_len, "little"))     #Little endian, most significant bit on the right
    print(msg)
    
    #Controller inputs & their respective functions
    if (bytes("PS press", 'utf-8') in msg):                                         #Emergency shutdown
        pi1.set_PWM_dutycycle(thrust1, 0)                                           #Cut power to everything
        pi1.set_PWM_dutycycle(thrust2, 0)
        pi1.set_PWM_dutycycle(thrust3, 0)
        pi1.set_PWM_dutycycle(thrust4, 0)
        pi1.set_PWM_dutycycle(thrust5, 0)
        pi1.set_PWM_dutycycle(left_light, 0)
        pi1.set_PWM_dutycycle(right_light, 0)
        print("Emergency shutdown")
        print("Thruster 1: " + str(pi1.get_PWM_dutycycle(thrust1)))                 #Confirm power is 0
        print("Thruster 2: " + str(pi1.get_PWM_dutycycle(thrust2)))
        print("Thruster 3: " + str(pi1.get_PWM_dutycycle(thrust3)))
        print("Thruster 4: " + str(pi1.get_PWM_dutycycle(thrust4)))
        print("Thruster 5: " + str(pi1.get_PWM_dutycycle(thrust5)))
        print("Left Light: " + str(pi1.get_PWM_dutycycle(left_light)))
        print("Right Light: " + str(pi1.get_PWM_dutycycle(right_light)))

    elif(bytes("X press", 'utf-8') in msg):
        print("Running thruster 3 only")
        pi1.set_PWM_dutycycle(thrust3, 1652)
        print("Thruster 3: " + str(pi1.get_PWM_dutycycle(thrust3)))
        
    elif(bytes("X release", 'utf-8') in msg):
        print("Stopping thruster 3 only")
        pi1.set_PWM_dutycycle(thrust3, 1500)
        
    elif(bytes("Square press", 'utf-8') in msg):
        print("Running thruster 4 only")
        pi1.set_PWM_dutycycle(thrust4, 1324)
        print("Thruster 4: " + str(pi1.get_PWM_dutycycle(thrust4)))
    
    elif(bytes("Square release", 'utf-8') in msg):
        print("Stopping thruster 4 only")
        pi1.set_PWM_dutycycle(thrust4, 1500)
        
    elif(bytes("Circle press", 'utf-8') in msg):
        print("Running thruster 5 only")
        pi1.set_PWM_dutycycle(thrust5, 1652)
        print("Thruster 5: " + str(pi1.get_PWM_dutycycle(thrust5)))
    
    elif(bytes("Circle release", 'utf-8') in msg):
        print("Stopping thruster 5 only")
        pi1.set_PWM_dutycycle(thrust5, 1500)

    elif(bytes("Triangle press", 'utf-8') in msg):
        #ADJUST AFTER POOL TEST
        global hover_on
        if not hover_on:
            hover()
            hover_on = True
        else:
            print("Stopping hover")
            pi1.set_PWM_dutycycle(thrust1, 1500)
            pi1.set_PWM_dutycycle(thrust2, 1500)
            pi1.set_PWM_dutycycle(thrust3, 1500)
            pi1.set_PWM_dutycycle(thrust4, 1500)
            pi1.set_PWM_dutycycle(thrust5, 1500)
            hover_on = False

    #elif(bytes("Triangle release", 'utf-8') in msg):
   
    elif (bytes("Share press", 'utf-8') in msg):
        global left_light_on
        if not left_light_on:
            print("Let there be light! On the left side.")
            pi1.set_PWM_dutycycle(left_light, 1700)                   #If left light is off, turn it on
            left_light_on = True                                      #Left light is now on
        else:
            print("Nighty night")
            pi1.set_PWM_dutycycle(left_light, 1100)                   #If left light is on, turn it off
            left_light_on = False                                     #Left light is now off

    elif (bytes("Options press", 'utf-8') in msg):
        global right_light_on
        if not right_light_on:
            print("Let there be light! On the right side.")
            pi1.set_PWM_dutycycle(right_light, 1700)                  #If left light is off, turn it on
            right_light_on = True                                     #Right light is now on
        else:
            print("Righty night")
            pi1.set_PWM_dutycycle(right_light, 1100)                  #If left light is on, turn it off        
            right_light_on = False                                    #Right light is now off

    elif (bytes("UpArrow press", 'utf-8') in msg):
        print("Going up!")
        pi1.set_PWM_dutycycle(thrust1, 1290)
        pi1.set_PWM_dutycycle(thrust2, 1682)
        pi1.set_PWM_dutycycle(thrust3, 1760)

    elif (bytes("DownArrow press", 'utf-8') in msg):
        print("Going down!")
        pi1.set_PWM_dutycycle(thrust1, 1624)
        pi1.set_PWM_dutycycle(thrust2, 1358)
        pi1.set_PWM_dutycycle(thrust3, 1300)

    elif (bytes("UpDownArrow release", 'utf-8') in msg):
        if hover_on:
            hover()
        else:
            print("Stopping thrusters")
            pi1.set_PWM_dutycycle(thrust1, 1500)
            pi1.set_PWM_dutycycle(thrust2, 1500)
            pi1.set_PWM_dutycycle(thrust3, 1500)

    elif (bytes("LeftArrow press", 'utf-8') in msg):
        print("Left Roll")
        pi1.set_PWM_dutycycle(thrust2, 1600)

    elif (bytes("RightArrow press", 'utf-8') in msg):
        print("Right Roll")
        pi1.set_PWM_dutycycle(thrust1, 1386)

    elif (bytes("LeftRightArrow release", 'utf-8') in msg):
        if hover_on:
            hover()
        else:
            print("Stopping thrusters")
            pi1.set_PWM_dutycycle(thrust1, 1500)
            pi1.set_PWM_dutycycle(thrust2, 1500)

    elif (bytes("L1 press", 'utf-8') in msg):
        print("Left turn")
        pi1.set_PWM_dutycycle(thrust1, 1700)
        pi1.set_PWM_dutycycle(thrust2, 1700)
        pi1.set_PWM_dutycycle(thrust5, 1600)

    elif (bytes("L1 release", 'utf-8') in msg):
        if hover_on:
            hover()
        else:
            print("Stopping thrusters.")
            pi1.set_PWM_dutycycle(thrust1, 1500)
            pi1.set_PWM_dutycycle(thrust2, 1500)
            pi1.set_PWM_dutycycle(thrust5, 1500)

    elif (bytes("R1 press", 'utf-8') in msg):
        print("Right turn")
        pi1.set_PWM_dutycycle(thrust1, 1268)
        pi1.set_PWM_dutycycle(thrust2, 1268)
        pi1.set_PWM_dutycycle(thrust4, 1386)

    elif (bytes("R1 release", 'utf-8') in msg):
        if hover_on:
            hover()
        else:
            print("Stopping thrusters.")
            pi1.set_PWM_dutycycle(thrust1, 1500)
            pi1.set_PWM_dutycycle(thrust2, 1500)
            pi1.set_PWM_dutycycle(thrust4, 1500)
    
    elif (bytes("L2 press", 'utf-8') in msg):
        print("Pitch up")
        pi1.set_PWM_dutycycle(thrust1, up_speed_14)                   
        pi1.set_PWM_dutycycle(thrust2, up_speed)                                            

    elif (bytes("L2 release", 'utf-8') in msg):
        if hover_on:
            hover()
        else:
            print("Stopping thrusters.")                   
            pi1.set_PWM_dutycycle(thrust1, 1500)
            pi1.set_PWM_dutycycle(thrust2, 1500)

    elif (bytes("R2 press", 'utf-8') in msg):
        print("Pitch down")                 
        pi1.set_PWM_dutycycle(thrust1, down_speed_14)                   
        pi1.set_PWM_dutycycle(thrust2, down_speed)                                            

    elif (bytes("R2 release", 'utf-8') in msg):
        if hover_on:
            hover()
        else:
            print("Stopping thrusters.")                   
            pi1.set_PWM_dutycycle(thrust1, 1500)
            pi1.set_PWM_dutycycle(thrust2, 1500)
                          
    elif (bytes("L3 up 1", 'utf-8') in msg):                    #Level 1 Forward
        print("Moving forward. Level 1.")
        pi1.set_PWM_dutycycle(thrust4, fwd_1_14)
        pi1.set_PWM_dutycycle(thrust5, fwd_1)

    elif(bytes("L3 up 2", 'utf-8') in msg):                     #Level 2 Forward
        print("Moving forward. Level 2.")
        pi1.set_PWM_dutycycle(thrust4, fwd_2_14)
        pi1.set_PWM_dutycycle(thrust5, fwd_2)

    elif(bytes("L3 up 3", 'utf-8') in msg):                     #Level 3 Forward
        print("Moving forward. Level 3.")
        pi1.set_PWM_dutycycle(thrust4, fwd_3_14)
        pi1.set_PWM_dutycycle(thrust5, fwd_3)

    elif (bytes("L3 down 1", 'utf-8') in msg):                    #Level 1 Reverse
        print("Moving forward. Level 1.")
        pi1.set_PWM_dutycycle(thrust4, rev_1_14)
        pi1.set_PWM_dutycycle(thrust5, rev_1)

    elif(bytes("L3 down 2", 'utf-8') in msg):                     #Level 2 Reverse
        print("Moving forward. Level 2.")
        pi1.set_PWM_dutycycle(thrust4, rev_2_14)
        pi1.set_PWM_dutycycle(thrust5, rev_2)

    elif(bytes("L3 down 3", 'utf-8') in msg):                     #Level 3 Reverse
        print("Moving forward. Level 3.")
        pi1.set_PWM_dutycycle(thrust4, rev_3_14)
        pi1.set_PWM_dutycycle(thrust5, rev_3)

    elif (bytes("L3 y rest", 'utf-8') in msg):
        if hover_on:
            hover()
        else:
            print("Stopping thrusters.")
            pi1.set_PWM_dutycycle(thrust4, 1500)                          
            pi1.set_PWM_dutycycle(thrust5, 1500)

    elif (bytes("L3 x rest", 'utf-8') in msg):
        if hover_on:
            hover()
        else:
            print("Stopping thrusters.")
            pi1.set_PWM_dutycycle(thrust4, 1500)                          
            pi1.set_PWM_dutycycle(thrust5, 1500)


#-----------MAIN-----------
def main():
    try:
        #Initialize socket connection
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)           #Socket setup
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)         #Hopefully prevents the "Address already in use" error
        s.bind(ROUV_ADDRESS)                                            #"Unlocking the door"
        s.listen()                                                      #Poll for message
        (clientsock, client_addr) = s.accept()                          #"Come on in!"
        print("Connection Established")                                 #Confirm connection
        
        #Initialize thrusters + lights
        pi1.set_PWM_dutycycle(thrust1, 1500)                              #Send STOP signal to thruster 1
        print("Thruster 1 @ 15% DC")
        pi1.set_PWM_dutycycle(thrust2, 1500)                              #Send STOP signal to thruster 2
        print("Thruster 2 @ 15% DC")
        pi1.set_PWM_dutycycle(thrust3, 1500)                              #Send STOP signal to thruster 3
        print("Thruster 3 @ 15% DC")
        pi1.set_PWM_dutycycle(thrust4, 1500)                              #Send STOP signal to thruster 4
        print("Thruster 4 @ 15% DC")
        pi1.set_PWM_dutycycle(thrust5, 1500)                              #Send STOP signal to thruster 5
        print("Thruster 5 @ 15% DC")
        pi1.set_PWM_dutycycle(left_light, 1100)                           #Send OFF signal to left light
        print("Left Light @ 11% DC")
        pi1.set_PWM_dutycycle(right_light, 1100)                          #Send OFF signal to right light
        print("Right Light @ 11% DC")
        time.sleep(10)

        while True:
            check_temp()
            check_leak()
            if leak_detected:
                raise LeakDetectedException
            if overheat:
                raise OverheatException
            handle_client(clientsock)


    except KeyboardInterrupt: 
        pi1.set_PWM_dutycycle(thrust1, 0)                                           #Cut power to thruster 1
        pi1.set_PWM_dutycycle(thrust2, 0)                                           #Cut power to thruster 2
        pi1.set_PWM_dutycycle(thrust3, 0)                                           #Cut power to thruster 3
        pi1.set_PWM_dutycycle(thrust4, 0)                                           #Cut power to thruster 4
        pi1.set_PWM_dutycycle(thrust5, 0)                                           #Cut power to thruster 5
        pi1.set_PWM_dutycycle(left_light, 0)                                        #Cut power to left light
        pi1.set_PWM_dutycycle(right_light, 0)                                       #Cut power to right light
        print("KeyboardInterrupt detected")
        print("Thruster 1: " + str(pi1.get_PWM_dutycycle(thrust1)))
        print("Thruster 2: " + str(pi1.get_PWM_dutycycle(thrust2)))
        print("Thruster 3: " + str(pi1.get_PWM_dutycycle(thrust3)))
        print("Thruster 4: " + str(pi1.get_PWM_dutycycle(thrust4)))
        print("Thruster 5: " + str(pi1.get_PWM_dutycycle(thrust5)))
        print("Left Light: " + str(pi1.get_PWM_dutycycle(left_light)))
        print("Right Light: " + str(pi1.get_PWM_dutycycle(right_light)))
    
    except LeakDetectedException:
        csock.send(create_message("LEAK"))                                          #Send leak alert to BUOY, BUOY will then light up leak LED
        pi1.set_PWM_dutycycle(thrust1, 1800)                                        #Go up!!!
        pi1.set_PWM_dutycycle(thrust2, 1800)
        pi1.set_PWM_dutycycle(thrust3, 1800)
        pi1.set_PWM_dutycycle(thrust4, 1500)                                         
        pi1.set_PWM_dutycycle(thrust5, 1500)
        time.sleep(10)
        pi1.set_PWM_dutycycle(thrust1, 0)                                           #Cut power to thruster 1
        pi1.set_PWM_dutycycle(thrust2, 0)                                           #Cut power to thruster 2
        pi1.set_PWM_dutycycle(thrust3, 0)                                           #Cut power to thruster 3
        pi1.set_PWM_dutycycle(thrust4, 0)                                           #Cut power to thruster 4
        pi1.set_PWM_dutycycle(thrust5, 0)                                           #Cut power to thruster 5
        pi1.set_PWM_dutycycle(left_light, 0)                                        #Cut power to left light
        pi1.set_PWM_dutycycle(right_light, 0)                                       #Cut power to right light
        print("Thruster 1: " + str(pi1.get_PWM_dutycycle(thrust1)))
        print("Thruster 2: " + str(pi1.get_PWM_dutycycle(thrust2)))
        print("Thruster 3: " + str(pi1.get_PWM_dutycycle(thrust3)))
        print("Thruster 4: " + str(pi1.get_PWM_dutycycle(thrust4)))
        print("Thruster 5: " + str(pi1.get_PWM_dutycycle(thrust5)))
        print("Left Light: " + str(pi1.get_PWM_dutycycle(left_light)))
        print("Right Light: " + str(pi1.get_PWM_dutycycle(right_light)))


if __name__ == '__main__':
    main()


