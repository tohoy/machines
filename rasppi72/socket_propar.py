# -*- coding: utf-8 -*-
"""
Created on Tue Mar  5 10:17:21 2024

@author: jofsch
"""
import time
import propar

sock_pressure = propar.instrument('/dev/ttyUSB0')

print("Connected to Pressure Controller: " + str(sock_pressure.id))
print("Checking Control Mode")
print(str(sock_pressure.readParameter(12)))

#if str(sock_pressure.readParameter(12)) == 18:
#	print("Hello 18")
print("Setting Control Mode to accept RS 232 communication ")
sock_pressure.writeParameter(12,18)
print(str(sock_pressure.readParameter(12)))

def get_setpoint():
   while True:
      value = sock_pressure.setpoint
      if not value is None:
         return value

def set_setpoint(setpoint):
   print('Setting new setpoint: {} int...'.format(setpoint))
   while True:
      sock_pressure.setpoint = setpoint
      value = get_setpoint()
      if value == setpoint:
         print('New setpoint set successfully')
         return
      else:
         print(value, setpoint)

def measure():
   while True:
      value = sock_pressure.measure
      if not value is None:
         return value

#sock_pressure.setpoint = 100
# Now, to access the setpoint value, you can simply print the property
#print("Current setpoint value:", sock_pressure.setpoint)


def log():
   while True:
      time.sleep(0.5)
      #instrument.writeParameter(9, 0) #setting new setpoint
      #print("Current Setpoint: " + str(sock_pressure.readParameter(9,1)) + " Current Pressure: " + str(sock_pressure.readParameter(8))) #measured pressure
      print("Current Setpoint: " + str(get_setpoint()) + " Current Pressure: " + str(measure())) #measured pressure


log()
