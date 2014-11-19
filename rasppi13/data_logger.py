""" Pressure and temperature logger """
# pylint: disable=C0301,R0904, C0103

import threading
import time
import logging
import socket
import curses

from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
#from PyExpLabSys.common.sockets import LiveSocket

""" driver """
import PyExpLabSys.drivers.mks_925_pirani as mks_pirani
import PyExpLabSys.drivers.mks_pi_pc as mks_pipc

import credentials

"""
name = 'stm312 HPC pressure'
codenames = ['pressure','setpoint']
socket = DateDataPullSocket(name, codenames)


db_logger_stm312 = ContinuousLogger(table='dateplots_stm312',# stm312 pressure controller pressure
                             username='dummy', password='dummy', # get from credentials
                             measurement_codenames = ['pressure'])
db_logger_ocs = ContinuousLogger(table='dateplots_oldclustersource',# oldclustersource pirani
                                 username='dummy', password='dummy', # get from credentials
                                 measurement_codenames = ['pressure'])
"""

class CursesTui(threading.Thread):
    def __init__(self, pressure_control, pirani, pullsocket):
        threading.Thread.__init__(self)
        self.pullsocket = pullsocket
        self.pc = pressure_control
        self.pirani = pirani
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
                self.screen.addstr(3, 2, "Pressure Controller for HPC stm312,")# ID: {}".format(self.pc.status['ID']))
                self.screen.addstr(4, 2, "Pirani for old cluster source")
            except Exception, e:
                self.screen.addstr(3, 2, "Pressure Controller for HPC stm312, {}".format(e))# ID: {}".format(self.pc.status['ID']))
                self.screen.addstr(4, 2, "Pirani for old cluster source, {}".format(e))
                pass
            """if self.pcc.status['Output']:
                self.screen.addstr(4, 2, 'Power Output: '+str(self.pcc.status['Output']))
                self.screen.addstr(5, 2, 'Control mode: '+str(self.pcc.status['Mode'])+'      ')
            """
            try:
                self.screen.addstr(6, 2, "HPC pressure, pressure control:     {0:+.1f}mbar     ".format(self.pc.pressure))
                self.screen.addstr(7, 2, "HPC pressure, setpoint:             {0:+.1f}mbar     ".format(self.pc.setpoint))
            except Exception, e:
                self.screen.addstr(6, 2, "HPC pressure, pressure control:     {}               ".format(e))
                self.screen.addstr(7, 2, "HPC pressure, setpoint:             {}               ".format(e))
            try:
                self.screen.addstr(10, 2, "Old cluster source pirani:         {0:+.5f}mbar     ".format(self.pirani.pressure))
            except Exception, e:
                self.screen.addstr(10, 2, "Old cluster source pirani:         {}               ".format(e))
            if self.pc.ERROR != None:
                self.screen.addstr(12, 2, 'Latest error message: ' + str(self.pc.ERROR) + ' at time: ')# + str(self.pcc.status['error time']-self.time))
            if self.pirani.ERROR != None:
                self.screen.addstr(13, 2, 'Latest error message: ' + str(self.pirani.ERROR))# + ' at time: ' + str(self.pcc.status['error time']))
            self.screen.addstr(16, 2, "Runtime: {0:.0f}s     ".format(time.time() - self.time))
            if self.last_key != None:
                self.screen.addstr(18, 2, " Latest key: {}       ".format(self.last_key))
            self.screen.addstr(21, 2, "q: quit program, z: increment setpoint, x: decrement setpoint     ")
            #self.screen.addstr(22, 2, "t: PID temperature control, i, fixed current, v: fixed voltage, p: fixed power     ")
            
            n = self.screen.getch()
            if n == ord("q"):
                self.pc.running = False
                self.pirani.running = False
                self.running = False
                self.last_key = chr(n)
            elif n == ord('z'):
                self.pc.increment_setpoint()
                self.last_key = chr(n)
            elif n == ord('x'):
                self.pc.decrement_setpoint()
                self.last_key = chr(n)
            """elif n == ord('v'):
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
            """
            self.screen.refresh()
        time.sleep(5)
        self.stop()
        
    def stop(self):
        print('Tui is stopping')
        try:
            self.pc.stop()
        except Exception, e:
            print(e)
            pass
        try:
            self.pirani.stop()
        except Exception, e:
            print(e)
            pass
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()

class PcClass(threading.Thread):
    """ Analog reader """
    def __init__(self):
        threading.Thread.__init__(self)
        port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWDW3A2-if00-port0'
        self.pc = mks_pipc.Mks_Pi_Pc(port = port)
        self.pressure = None
        self.setpoint = 200
        self.quit = False
        self.last_recorded_time = 0
        self.last_recorded_value = 0
        self.trigged = False
        self.running = True
        self.ERROR = None
        self.socket_avalible = False
        self.db_logger_avalible = False

    def add_socket_server(self,pullsocket,pushsocket):
        self.pullsocket = pullsocket
        self.pushsocket = pushsocket
        self.socket_avalible = True
    
    def read_pressure(self):
        """ Read the pressure """
        return(self.pressure)

    def read_setpoint(self):
        """ Read the setpoint """
        return(self.setpoint)

    def increment_setpoint(self,):
        self.update_setpoint(self.setpoint + 10)
        #self.setpoint += 10
        #self.set_setpoint(self.setpoint)
        return(True)
    
    def decrement_setpoint(self,):
        self.update_setpoint(self.setpoint - 10)
        #self.set_setpoint(self.setpoint)
        return(True)

    #def update_setpoint(self):
    #    """ Read the setpoint from external socket server """
    """    HOST, PORT = "130.225.86.182", 9999
        data = "read_setpoint_pressure"
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(data + "\n", (HOST, PORT))
        received = sock.recv(1024)
        setpoint = int(float(received))
        self.set_setpoint(setpoint)
        return(setpoint)
    """

    def set_setpoint(self, setpoint):
        """ Set the setpoint """
        self.setpoint = int(setpoint)
        try:
            self.pc.set_setpoint(self.setpoint)
        except Exception, e:
            self.ERROR = e
        if self.socket_avalible:
            self.pullsocket.set_point_now('setpoint',self.setpoint)
        return(True)

    def update_setpoint(self, setpoint=None):
        """ Update the setpoint """
        self.setpoint = setpoint
        self.pullsocket.set_point_now('setpoint', setpoint)
        return setpoint

    def run(self):
        sp_updatetime = 0
        while self.running:
            time.sleep(0.5)
            self.pressure = self.pc.read_pressure()
            self.pc.set_setpoint(self.setpoint)
            if self.socket_avalible:
                self.pullsocket.set_point_now('pressure',self.pressure)
            #self.update_setpoint()
            try:
                setpoint = self.pushsocket.last[1]['setpoint']
                new_update = self.pushsocket.last[0]
                self.message = str(new_update)
            except (TypeError, KeyError): # Setpoint has never been sent
                setpoint = None
            if ((setpoint is not None) and
                (setpoint != self.setpoint) and (sp_updatetime < new_update)):
                self.update_setpoint(setpoint)
                sp_updatetime = new_update
            if self.db_logger_avalible:
                time_trigged = (time.time() - self.last_recorded_time) > 120
                val_trigged = not ((self.last_recorded_value * 0.9) <= self.pressure <= (self.last_recorded_value * 1.1))
                if (time_trigged or val_trigged):
                    self.trigged = True
                    self.last_recorded_time = time.time()
                    self.last_recorded_value = self.pressure
                    self.db_logger.enqueue_point_now('',self.pressure)
        self.stop()
        
    def stop(self,):
        self.running = False
        #self.socket.stop()
        print('PcClass is stopping')


class PiraniClass(threading.Thread):
    """ Pressure reader """
    def __init__(self):
        threading.Thread.__init__(self)
        port = '/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0'
        self.pirani = mks_pirani.mks_comm(port = port)
        self.pressure = None
        self.quit = False
        self.last_recorded_time = 0
        self.last_recorded_value = 0
        self.trigged = False
        self.running = True
        self.ERROR = None
        self.socket_avalible = False
        self.db_logger_avalible = False

    #def add_socket_server(self,socket):
    #    self.socket = socket
    #    self.socket_avalible = True

    def add_logger(self,db_logger):
        self.db_logger = db_logger
        #self.db_logger_avalible = True

    def read_pressure(self):
        """ Read the pressure """
        return(self.pressure)

    def run(self):
        while self.running:
            time.sleep(1)
            try:
                self.pressure = float(self.pirani.read_pressure())
            except Exception, e:
                self.ERROR = e
            if self.db_logger_avalible:
                time_trigged = (time.time() - self.last_recorded_time) > 120
                val_trigged = not (self.last_recorded_value * 0.9 < self.pressure < self.last_recorded_value * 1.1)
                if (time_trigged or val_trigged) and (self.pressure > 0):
                    self.trigged = True
                    self.last_recorded_time = time.time()
                    self.last_recorded_value = self.pressure
                    self.db_logger.engueue_point_now('pirani',self.pressure)
        self.stop()

    def stop(self,):
        self.running = False
        print('PiraniClass is stopping')

class Baratron(threading.Thread):
    def __init__(self,):
        pass

#logging.basicConfig(filename="logger.txt", level=logging.ERROR)
#logging.basicConfig(level=logging.ERROR)

#pc_measurement = PcClass()
#pc_measurement.start()

#pressure_measurement = PiraniClass()
#pressure_measurement.start()

#time.sleep(2)

"""
datasocket = DateDataPullSocket(['pirani', 'pc'], timeouts=[1.0, 1.0])
datasocket.start()

db_logger = ContinuousLogger(table='dateplots_stm312', username='stm312', password='stm312', measurement_codenames=['stm312_pirani', 'stm312_pc'])
db_logger.start()
"""

"""
while True:
    pirani = pressure_measurement.read_pressure()
    pc = pc_measurement.read_pressure()
    #datasocket.set_point_now('pirani', pirani)
    #datasocket.set_point_now('pc', pc)
    
    print(pirani)
    if pressure_measurement.trigged:
        print(pirani)
        #db_logger.enqueue_point_now('stm312_pirani', pirani)
        pressure_measurement.trigged = False
    
    print(pc)
    if pc_measurement.trigged:
        print(pc)
        #db_logger.enqueue_point_now('stm312_pc', pc)
        pc_measurement.trigged = False
    time.sleep(0.5)
"""

Pullsocket = DateDataPullSocket('stm312 hpc pressure control', ['pressure', 'setpoint'])
Pushsocket = DataPushSocket('stm312 hpc pressure control', action='store_last')


if __name__ == '__main__':
    print('program start')
    Pullsocket.start()
    Pushsocket.start()
    #socket.start()
    #db_logger_stm312.start()
    #db_logger_ocs.start()
    time.sleep(1)

    pc = PcClass()
    pc.add_socket_server(Pullsocket,Pushsocket)
    pirani = PiraniClass()
    time.sleep(2)
    
    pc.start()
    pc.set_setpoint(2000)
    pirani.start()
    time.sleep(2)
    #print(pirani.pressure)
    
    tui = CursesTui(pc, pirani, Pullsocket)
    tui.deamon = True
    tui.start()
    
    print('Program End')
