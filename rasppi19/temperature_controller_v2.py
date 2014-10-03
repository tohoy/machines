# -*- coding: utf-8 -*-
"""
Spyder Editor

Author:
Anders Nierhoff

changed:
2014-10-01
"""


import time
import threading
#import subprocess
import curses
import socket
import serial 
from datetime import datetime
import MySQLdb

import sys
sys.path.append('../../')
import PyExpLabSys.drivers.cpx400dp as CPX
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
import credentials


#output = 'print'
#output = 'curses'

class PID():
    """Implementation of a PID routine

    Iterates over all devices in /dev/input/event?? and looks for one that has
    'Barcode Reader' in its description.

    Returns:
        str: The Barcode Scanner device path
    """
    
    def __init__(self, case=None):
        """The input parameter case is used to simplify that several system is sharing the software, each with it own parametors."""
        if case == None:
            self.gain = {'Kp':0.15,'Ki':0.0025,'Kd':0.0,'Pmax':54.0, 'Pmin':0.0}
            pass
        elif case == 'stm312 hpc':
            self.gain = {'Kp':0.15, 'Ki':0.0025, 'Kd':0.0, 'Pmax':54.0, 'Pmin':0.0}
            
        """ Provid a starting setpoit to ensure that the PID does not apply any power before an actual setpoit is set."""
        self.setpoint = -9999
        self.Kp = self.gain['Kp']
        self.Ki = self.gain['Ki']
        self.Kd = self.gain['Kd']
        self.Pmax = self.gain['Pmax']
        self.Pmin = self.gain['Pmin']
        self.initialize()
        """datasocket = DateDataPullSocket('furnaceroom_reader',
                                    ['T1', 'T2', 'S1', 'S2'],
                                    timeouts=[3.0, 3.0, 9999999, 99999999], port=9001)
        """
    def initialize(self,):
        """ Initialize delta t variables. """
        self.currtm = time.time()
        self.prevtm = self.currtm

        self.prev_err = 0
        self.prev_P = 0

        # term result variables
        self.Cp = 0
        self.Ci = 0
        self.Cd = 0
        self.P = 0

    def reset_integrated_error(self):
        """ Reset the I value, integrated error. """
        self.Ci = 0

    def update_setpoint(self, setpoint):
        """ Update the setpoint."""
        self.setpoint = setpoint
        return setpoint

    def get_new_Power(self,T):
        """ Get new power for system, P_i+1 

        :param T: Actual temperature
        :type T: float
        :returns: best guess of need power
        :rtype: float
        """
        error = self.setpoint - T
        self.currtm = time.time()               # get t
        dt = self.currtm - self.prevtm          # get delta t
        de = error - self.prev_err  
        
        """ Calculate proportional gain. """
        self.Cp = error
        
        """ Calculate integral gain, including limits """
        if self.prev_P > self.Pmax and error > 0:
            pass
        elif self.prev_P < self.Pmin and error < 0:
            pass
        else:
            self.Ci += error * dt
        
        """ Calculate derivative gain. """
        if dt > 0:                              # no div by zero
            self.Cd = de/dt 
        else:
            self.Cd = 0
            
        """ Adjust times, and error for next iteration. """
        self.prevtm = self.currtm               # save t for next pass
        self.prev_err = error                   # save t-1 error
        
        """ Calculate Output. """
        P = self.Kp * self.Cp + self.Ki * self.Ci + self.Kd * self.Cd
        self.prev_P = P
        
        """ Check if output is valid. """
        if P > self.Pmax:
            P = self.Pmax
        if P < 0:
            P = 0 
        return P

class CursesTui(threading.Thread):
    def __init__(self,powercontrolclass):
        threading.Thread.__init__(self)
        self.pcc = powercontrolclass
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)
        self.time = time.time()
        self.countdown = False
        self.last_key = None
        self.running = True
        
    def run(self,):
        while self.running:
            try:
                self.screen.addstr(3, 2, "Power Supply for HPC stm312, ID: {}".format(self.pcc.status['ID']))
            except Exception, e:
                self.screen.addstr(3, 2, 'Power Supply for HPC stm312, ID: {}'.format(e))
                pass
            if self.pcc.status['Output']:
                self.screen.addstr(4, 2, 'Power Output: '+str(self.pcc.status['Output']))
                self.screen.addstr(5, 2, 'Control mode: '+str(self.pcc.status['Mode'])+'      ')
            try:
                self.screen.addstr(6, 2, "Current:    {0:+.1f}A  -  {0:+.1f}A     ".format(self.pcc.status['Current'], self.pcc.status['Wanted Current']))
                self.screen.addstr(7, 2, "Voltage:    {0:+.1f}V  -  {0:+.1f}V     ".format(self.pcc.status['Voltage'], self.pcc.status['Wanted Voltage']))
                self.screen.addstr(8, 2, "Power:      {0:+.1f}W  -  {0:+.1f}W     ".format(self.pcc.status['Actual Power'],self.pcc.status['Wanted Power']))
                self.screen.addstr(9, 2, "Resistance: {0:+.1f}Ohm     ".format(self.pcc.status['Resistance']))
                self.screen.addstr(11, 2, "Temperature: {0:+.1f}C     ".format(self.pcc.status['Temperature']))
                self.screen.addstr(12, 2, "Setpoint: {0:+.1f}     ".format(self.pcc.status['Setpoint']))
            except:
                pass
            if self.pcc.status['error'] != None:
                self.screen.addstr(17,2, 'Latest error message: ' + str(self.pcc.status['error']) + ' at time: ' + str(self.pcc.status['error time']-self.time))
            #if self.pcc.status['error'] != None:
            #    self.screen.addstr(17,2, 'Latest error message: ' + str(self.pcc.status['error']) + ' at time: ' + str(self.pcc.status['error time']))
            self.screen.addstr(16,2,"Runtime: {0:.0f}s     ".format(time.time() - self.time))
            if self.last_key != None:
                self.screen.addstr(18,2, ' Latest key: ' + str(self.last_key))
            self.screen.addstr(21,2,"q: quit program, z: increas setpoint, x: decrease setpoint     ")
            self.screen.addstr(22,2,"t: PID temperature control, i, fixed current, v: fixed voltage, p: fixed power     ")
            
            n = self.screen.getch()
            if n == ord("q"):
                self.pcc.running = False
                self.running = False
                self.last_key = chr(n)
            elif n == ord('t'):
                self.pcc.change_mode('Temperature Control')
                self.last_key = chr(n)
            elif n == ord('i'):
                self.pcc.change_mode('Current Control')
                self.last_key = chr(n)
            elif n == ord('v'):
                self.pcc.change_mode('Voltage Control')
                self.last_key = chr(n)
            elif n == ord('p'):
                self.pcc.change_mode('Power Control')
                self.last_key = chr(n)
            elif n == ord('z'):
                self.pcc.increase_setpoint()
                self.last_key = chr(n)
            elif n == ord('x'):
                self.pcc.decrease_setpoint()
                self.last_key = chr(n)
            self.screen.refresh()
        time.sleep(5)
        self.stop()
        #print EXCEPTION

    def stop(self):
        self.pcc.stop()
        #print(str(self.running))
        #print(str(self.pcc.running))
        #print(str(self.pcc.temp_class.running))
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()

def sqlTime():
    sqltime = datetime.now().isoformat(' ')[0:19]
    return(sqltime)


def sqlInsert(query):
    try:
        cnxn = MySQLdb.connect(host="servcinf",user="stm312",passwd="stm312",db="cinfdata")
        cursor = cnxn.cursor()
    except:
	print "Unable to connect to database"
	return()
    try:
        cursor.execute(query)
        cnxn.commit()
    except:
        print "SQL-error, query written below:"
        print query
    cnxn.close()

def network_comm(host, port, string):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(string + "\n", (host, port))
    received = sock.recv(1024)
    return received

def read_hp_temp():
    received = network_comm('rasppi19',9990, 'read_hp_temp')
    temp = float(received)
    return(temp)

def read_setpoint():
    received = network_comm('rasppi19',9990, 'read_setpoint')
    temp = float(received)
    return(temp)

def write_setpoint(setpoint):
    #print "write_setpoint {}".format(setpoint)
    received = network_comm('rasppi19',9990, 'set_setpoint '+str(setpoint))
    #temp = float(received)
    #return(temp)

class TemperatureClass(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.temperature = -999
        self.running = True
        self.error = False
        self.debug_level = 0
        
    def run(self):
        while self.running:
            #data_temp = 'T1#raw'
            #sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            #sock.settimeout(1)
            try:
                #sock.sendto(data_temp, ('localhost', 9001))
                #received = sock.recv(1024)
                #self.temperature = float(received[received.find(',') + 1:])
                self.temperature = float(read_hp_temp())
            except:
                self.error = True
            if self.debug_level > 0:
                print(str(self.temperature))
            #temperature = self.temperature
            time.sleep(0.25)
    def stop(self,):
        self.running = False
        pass

class PowerControlClass(threading.Thread):
    
    def __init__(self):#,datasocket,pushsocket
        #self.datasocket = datasocket
        #self.pushsocket = pushsocket
        threading.Thread.__init__(self)
        #self.PowerCalculatorClass = PID_class
        self.running = True
        self.status = {}
        self.status['Mode'] = 'Voltage Control' #, 'Power Control'
        
        self.init_status()
        self.init_PID_class()
        #self.init_temp_class()
        self.init_heater_class()
    
    def init_status(self,):
        self.status['error'] = None
        self.status['Setpoint'] = 0.0
        
        self.status['Current'] = 0.0
        self.status['Wanted Current'] = 0.0
        
        self.status['Voltage'] = 0.0
        self.status['Wanted Voltage'] = 0.0
        
        self.status['Actual Power'] = 0.0
        self.status['Wanted power'] = 0.0
        
        self.status['Resistance'] = 1.0
        
        self.status['ID'] = '0'
    
    def init_temp_class(self,temp_class):
        self.temp_class = temp_class
        
    def init_PID_class(self,):
        self.power = 0.0
        self.setpoint = -200.0
        self.pid = PID()
        self.pid.Kp = 0.035
        self.pid.Ki = 0.00022
        self.pid.Kd = 0.0
        self.pid.Pmax = 8.0
        self.pid.update_setpoint(self.setpoint)
        self.status['Wanted Power'] = self.power
        self.status['Setpoint'] = self.setpoint
        
    def init_heater_class(self,):
        for i in range(0,10):
            self.heater = CPX.CPX400DPDriver(1,usbchannel=i)
            if not self.heater.debug:
                break
        print self.heater.debug
        self.status['ID'] = self.heater.read_software_version()
        print 'ID: ' + self.status['ID']
        #print 'Type: ' + type(self.status['ID'])
        
    def init_resistance(self,):
        self.heater.set_voltage(2)
        self.heater.output_status(on=True)
        time.sleep(1)
        I_calib = self.heater.read_actual_current()
        self.heater.output_status(on=False)
        self.R_calib = 2.0/I_calib
        
    def OutputOn(self,):
        self.status['Output'] = True
        self.heater.output_status(on=True)
        
    def OutputOff(self,):
        self.status['Output'] = False
        self.heater.output_status(on=False)
        
    def update_output(self,):
        self.status['Current'] = self.heater.read_actual_current()
        self.status['Voltage'] = self.heater.read_actual_voltage()
        self.status['Actual Power'] = self.status['Current']* self.status['Voltage']
        self.status['Resistance'] = self.status['Voltage'] / self.status['Current']
        
    def change_setpoint(self,setpoint):
        try:
            write_setpoint(setpoint)
        except:
            self.status['error'] = 'COM error with socket server'
            self.status['error time'] = time.time()
        self.status['Setpoint'] = read_setpoint()
            
    def increase_setpoint(self,):
        setpoint = read_setpoint()
        if self.status['Mode'] == 'Temperature Control':
            setpoint += 1
        elif self.status['Mode'] in ['Power Control','Current Control','Voltage Control']:
            setpoint += 0.1
        self.change_setpoint(setpoint)
        
    def decrease_setpoint(self,):
        setpoint = read_setpoint()
        if self.status['Mode'] == 'Temperature Control':
            setpoint -= 1
        elif self.status['Mode'] in ['Power Control','Current Control','Voltage Control']:
            setpoint -= 0.1
        self.change_setpoint(setpoint)
        
    def change_mode(self,new_mode):
        if new_mode in ['Temperature Control','Power Control','Current Control','Voltage Control']:
            if new_mode in ['Power Control','Current Control','Voltage Control']:
                self.change_setpoint(0.0)
            elif new_mode in  ['Temperature Control']:
                self.change_setpoint(-998.0)
            self.status['Mode'] = new_mode
        else:
            self.status['error'] = 'Mode does not exsist'
            self.status['error time'] = time.time()
    
    def run(self,):
        self.heater.set_voltage(0)
        self.OutputOn()
        while self.running:
            self.status['Setpoint'] = read_setpoint()
            self.status['Temperature'] = self.temp_class.temperature
            if self.status['Mode'] == 'Temperature Control':
                self.pid.update_setpoint(self.status['Setpoint'])
                self.status['Wanted Power'] = self.pid.get_new_Power(self.status['Temperature'])
                self.status['Wanted Voltage'] = ( self.status['Wanted Power']* self.status['Resistance'] )**0.5
            elif self.status['Mode'] == 'Power Control':
                if self.status['Setpoint'] > 0 or self.status['Setpoint'] < 100:
                    self.status['Wanted Power'] = self.status['Setpoint']
                    self.status['Wanted Voltage'] = ( self.status['Wanted Power']* self.status['Resistance'] )**0.5
            elif self.status['Mode'] == 'Current Control':
                if self.status['Setpoint'] > 0 or self.status['Setpoint'] < 10:
                    self.status['Wanted Current'] = self.status['Setpoint']
                    self.status['Wanted Voltage'] = self.status['Resistance']* self.status['Wanted Current']
            elif self.status['Mode'] == 'Voltage Control':
                if self.status['Setpoint'] > 0 or self.status['Setpoint'] < 10:
                    self.status['Wanted Voltage'] = self.status['Setpoint']
            time.sleep(0.25)            
            try:
                self.heater.set_voltage(self.status['Wanted Voltage'])
                if self.heater.debug:
                    raise serial.serialutil.SerialException
            except serial.serialutil.SerialException:
                self.init_heater()
            self.update_output()
        self.pid.update_setpoint(-200)
        self.OutputOff()
        self.stop()
        
    def stop(self,):
        self.running = False
        try:
            self.temp_class.stop()
        except:
            pass


if __name__ == '__main__':
    print('Program start')
    
    """datasocket = DateDataPullSocket('stm312_hpc_temperature_control',
                                    ['global_temperature', 'global_pressure', 'hp_temp', 'setpoint'],
                                    timeouts=[3.0, 3.0, 9999999, 99999999], port=9001)
    datasocket.start()
    
    pushsocket = DataPushSocket('stm312_hpc_temperature_control_push', action='store_last')
    pushsocket.start()
    """
    
    #read_hp_temp()
    
    #classes: 
    TempClass = TemperatureClass()
    #TempClass.debug_level = 1
    #TempClass.run()
    TempClass.start()
    time.sleep(2)
    pcc = PowerControlClass()#datasocket,pushsocket
    pcc.init_temp_class(TempClass)
    pcc.start()
    
    time.sleep(2)
    tui = CursesTui(pcc)
    tui.daemon = True
    tui.start()
    
    
    print('Program End')
