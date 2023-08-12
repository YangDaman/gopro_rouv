#Continuous Listening Mode
import socket
import struct
import RPi.GPIO as GPIO
import time
import math
import threading
from pyPS4Controller.controller import Controller

ROUV_ADDR = ('169.254.186.103', 42069)       

#-------CONSTANTS-------
L2_press = False                             #L2 has not been pressed yet
R2_press = False                             #R2 has not been pressed yet


#-------SOCKET FUNCTIONS-------
def create_message(text):                                       #Message format: 2 bytes for packet length, the rest is the actual message
    return struct.pack("<H", len(text)) + bytes(text, 'utf-8')  #Struct is a bytes object. "<H" is for formatting (< for little endian, H denotes short). 
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
    return msg
    
def send_recv(msg, socket):
    socket.send(create_message(msg))
    recv_msg = handle_client(socket)
    print(recv_msg)
    return recv_msg

#------CONTROLLER CLASS & FUNCTIONS------
class MyController(Controller):

    def __init__(self, socket, *args, **kwargs):
        Controller.__init__(self, *args, **kwargs)
        self.s = socket
        
    def on_x_press(self):
        print("X press detected on BUOY")
        self.s.send(create_message("X press"))
        #send_recv("X press", self.s)

    def on_x_release(self):
        print("X release detected on BUOY")
        self.s.send(create_message("X release"))
        #send_recv("X release", self.s)
        
    def on_square_press(self):
        print("Square press detected on BUOY")
        self.s.send(create_message("Square press"))
                    
    def on_square_release(self):
        print("Square release detected on BUOY")
        self.s.send(create_message("Square release"))

    def on_triangle_press(self):
        print("Triangle press detected on BUOY")
        self.s.send(create_message("Triangle press"))
        
    def on_triangle_release(self):
        print("Triangle release detected on BUOY")
        self.s.send(create_message("Triangle release"))

    def on_circle_press(self):
        print("Circle press detected on BUOY")
        self.s.send(create_message("Circle press"))
                    
    def on_circle_release(self):
        print("Circle release detected on BUOY")
        self.s.send(create_message("Circle release"))

    def on_L1_press(self):
        print("L1 press detected on BUOY")
        self.s.send(create_message("L1 press"))
        
    def on_L1_release(self):
        print("L1 release detected on BUOY")
        self.s.send(create_message("L1 release"))

    def on_L2_press(self, value):
        global L2_press
        if (L2_press == False):
            print("L2 press detected on BUOY")
            self.s.send(create_message("L2 press"))
            L2_press = True
    
    def on_L2_release(self):
        global L2_press
        print("L2 release detected on BUOY")
        self.s.send(create_message("L2 release"))
        L2_press = False

    def on_R1_press(self):
        print("R1 press detected on BUOY")
        self.s.send(create_message("R1 press"))
        
    def on_R1_release(self):
        print("R1 release detected on BUOY")
        self.s.send(create_message("R1 release"))

    def on_R2_press(self, value):
        global R2_press
        if (R2_press == False):
            print("R2 press detected on BUOY")
            self.s.send(create_message("R2 press"))
            R2_press = True
    
    def on_R2_release(self):
        global R2_press
        print("R2 release detected on BUOY")
        self.s.send(create_message("R2 release"))
        R2_press = False

    def on_up_arrow_press(self):
        print("UpArrow press detected on BUOY")
        self.s.send(create_message("UpArrow press"))
        
    def on_down_arrow_press(self):
        print("DownArrow press detected on BUOY")
        self.s.send(create_message("DownArrow press"))

    def on_up_down_arrow_release(self):
        print("UpDownArrow release detected on BUOY")
        self.s.send(create_message("UpDownArrow release"))
        
    def on_left_arrow_press(self):
        print("LeftArrow press detected on BUOY")
        self.s.send(create_message("LeftArrow press"))

    def on_right_arrow_press(self):
        print("RightArrow press detected on BUOY")
        self.s.send(create_message("RightArrow press"))

    def on_left_right_arrow_release(self):
        print("LeftRightArrow release detected on BUOY")
        self.s.send(create_message("LeftRightArrow release"))

    def on_playstation_button_press(self):
        print("PS press detected on BUOY")
        self.s.send(create_message("PS press"))
        
    def on_share_press(self):
        print("Share press detected on BUOY")
        self.s.send(create_message("Share press"))    
        
    def on_options_press(self):
        print("Options press detected on BUOY")
        self.s.send(create_message("Options press"))
        
    def on_L3_up(self, value):
        print("L3 up detected on BUOY, value: " + str(value))
        c_value = math.ceil(abs(value)/100)
        print("Converted value: " + str(c_value))
        if (c_value >= 1 and c_value <= 100):
            self.s.send(create_message("L3 up 1"))
        if (c_value > 100 and c_value <= 200):
            self.s.send(create_message("L3 up 2"))
        if (c_value > 200):
            self.s.send(create_message("L3 up 3"))

    def on_L3_down(self, value):
        print("L3 down detected on BUOY, value: " + str(value))
        c_value = math.ceil(abs(value)/100)
        print("Converted value: " + str(c_value))
        if (c_value >= 1 and c_value <= 100):
            self.s.send(create_message("L3 down 1"))
        if (c_value > 100 and c_value <= 200):
            self.s.send(create_message("L3 down 2"))
        if (c_value > 200):
            self.s.send(create_message("L3 down 3"))
    
    def on_L3_y_at_rest(self):
        print("L3 Y at rest detected on BUOY")
        self.s.send(create_message("L3 y rest"))

    def on_L3_x_at_rest(self):
        print("L3 X at rest detected on BUOY")
        self.s.send(create_message("L3 x rest"))
    
            
#-----------MAIN-----------
def main():
    time.sleep(20)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)       #Using TCP/IP, generic socket setup
    s.settimeout(300)
    s.connect(ROUV_ADDR)                                        #Connect to this address "Opening the door"
    s.settimeout(None)
    msg = create_message("Hello World!")                        #Message, self-explanatory
    s.send(msg)                                                 #Send
    print(msg)

    controller = MyController(s, interface="/dev/input/js0", connecting_using_ds4drv=False)
    controller.listen(timeout = 300)

if __name__ == "__main__":
    main()


