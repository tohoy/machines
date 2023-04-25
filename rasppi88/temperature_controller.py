""" Temperature controller """
import logging
import time
import threading
import socket
import curses
#import pickle
import json
import wiringpi as wp
import PyExpLabSys.auxiliary.pid as PID
import credentials
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.value_logger import LoggingCriteriumChecker

# Set up debug logging
FORMAT = '%(asctime)s -- %(name)s:%(message)s'
logging.basicConfig(filename="log.temperature_controller", format=FORMAT, level=logging.WARNING)
LOGGER = logging.getLogger('temperature_controller')

class CursesTui(threading.Thread):
    """ Text user interface for furnace heating control """
    def __init__(self, heating_class):
        threading.Thread.__init__(self)
        self.start_time = time.time()
        self.quit = False
        self.hc = heating_class
        self.message = ''
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)

    def run(self):
        while not self.quit:
            self.screen.addstr(3, 2, 'Running')
            if self.hc.isAlive():
                self.message = self.hc.pc.msg
            else:
                self.message = 'Controller dead!'
            self.screen.addstr(5, 2, self.message)
            val = self.hc.pc.setpoint
            self.screen.addstr(9, 40, "Setpoint: {0:.2f}C  ".format(val))
            val = self.hc.pc.temperature
            try:
                self.screen.addstr(9, 2, "Temperature: {0:.1f}C  ".format(val))
            except (ValueError, TypeError):
                self.screen.addstr(9, 2, "Temperature: {}         ".format(val))
            val = self.hc.dutycycle
            self.screen.addstr(10, 2, "Wanted dutycycle: {0:.5f} ".format(val))
            val = self.hc.pc.pid.setpoint
            self.screen.addstr(11, 2, "PID-setpint: {0:.2f}C  ".format(val))
            val = self.hc.pc.pid.int_err
            self.screen.addstr(12, 2, "PID-error: {0:.3f} ".format(val))
            val = self.hc.pc.pid.pid_p * self.hc.pc.pid.error
            self.screen.addstr(11, 40, "PID-P term: {0:.6f}    ".format(val))
            val = self.hc.pc.pid.pid_i * self.hc.pc.pid.int_err
            self.screen.addstr(12, 40, "PID-I term: {0:.6f}    ".format(val))

            val = time.time() - self.start_time
            self.screen.addstr(15, 2, "Runtime: {0:.0f}s".format(val))

            key_val = self.screen.getch()
            if key_val == ord('q'):
                self.hc.quit = True
                self.quit = True
            if key_val == ord('i'):
                self.hc.pc.update_setpoint(self.hc.pc.setpoint + 1)
            if key_val == ord('d'):
                self.hc.pc.update_setpoint(self.hc.pc.setpoint - 1)

            self.screen.refresh()
            time.sleep(0.2)

    def stop(self):
        """ Clean up console """
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()


class PowerCalculatorClass(threading.Thread):
    """ Calculate the wanted amount of power """
    def __init__(self, datasocket, pushsocket):
        threading.Thread.__init__(self)
        self.datasocket = datasocket
        self.pushsocket = pushsocket
        self.power = 0
        self.setpoint = 0
        self.pid = PID.PID(pid_p=0.013, pid_i=0.000015, p_max=1)
        self.update_setpoint(self.setpoint)
        self.quit = False
        self.msg = '                                '
        self.last_time = -2
        self.time = -1
        self.temperature = None
        self.ramp = None
        LOGGER.info('PowerCalculatorClass init')

    def read_power(self):
        """ Return the calculated wanted power """
        return self.power

    def update_setpoint(self, setpoint=None, ramp=0):
        """ Update the setpoint
        ´ramp´: Start of ramp sequence (time.time() format)
        ´setpoint´: The setpoint (Celcius) to apply manually
        If both ramp and setpoint are specified, the ramp sequence takes priority!
        """
        if ramp > 0:
            setpoint = self.ramp_calculator(time.time()-ramp)
        self.setpoint = setpoint
        self.pid.update_setpoint(setpoint)
        self.datasocket.set_point_now('setpoint', setpoint)
        return setpoint

    def ramp_calculator(self, current_time):
        """ Return the current valid setpoint calculated from the relevant ramp
        Also includes a default ramp for testing"""
        if self.ramp is None:
            self.ramp = {}
            self.ramp['init'] = True
            self.ramp['temp'] = {}
            self.ramp['time'] = {}
            self.ramp['step'] = {}
            self.ramp['time'][0] = 20.0
            self.ramp['time'][1] = 2500.0
            self.ramp['time'][2] = 10800.0
            self.ramp['time'][3] = 10800.0
            self.ramp['time'][4] = 10800.0
            self.ramp['time'][5] = 10800.0
            self.ramp['temp'][0] = 0.0
            self.ramp['temp'][1] = 450.0
            self.ramp['temp'][2] = 0.0
            self.ramp['temp'][3] = 0.0
            self.ramp['temp'][4] = 0.0
            self.ramp['temp'][5] = 0.0
            self.ramp['step'][0] = True
            self.ramp['step'][1] = True
            self.ramp['step'][2] = True
            self.ramp['step'][3] = True
            self.ramp['step'][4] = False
            self.ramp['step'][4] = False
            self.ramp['step'][4] = False
        self.ramp['temp'][len(self.ramp['time'])] = 0
        self.ramp['step'][len(self.ramp['time'])] = True
        self.ramp['time'][len(self.ramp['time'])] = 999999999
        self.ramp['time'][-1] = 0
        self.ramp['temp'][-1] = 0

        # Figure out which line we're in
        i = 0
        while (current_time > 0) and (i < len(self.ramp['time'])):
            current_time = current_time - self.ramp['time'][i]
            i = i + 1

        # Get the current time (within the line in the temperature program)
        i = i - 1
        current_time = current_time + self.ramp['time'][i]
        if self.ramp['step'][i] is True: # Line is a step function
            return_value = self.ramp['temp'][i]
        else:                            # Line is a ramp function
            time_frac = current_time / self.ramp['time'][i]
            return_value = self.ramp['temp'][i-1] + time_frac * (self.ramp['temp'][i] -
                                                                 self.ramp['temp'][i-1])
        return return_value

    def run(self):
        LOGGER.info('PowerCalculatorClass start')
        ttl = 0
        data_temp = b'fr307_furnace_1_T#raw'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        ramp_time = 0
        paused = False
        #ramp_time = time.time()
        sp_updatetime = 0
        ramp_updatetime = 0
        log_counter = 0
        log_interval = 50
        while not self.quit:
            LOGGER.debug('PowerCalculatorClass beginning of while loop...')
            sock.sendto(data_temp, ('localhost', 9001))
            socketerror = False
            try:
                received = sock.recv(1024).decode()
                received = received.split(',')
                self.msg = '                                '
            except socket.timeout:
                self.msg = 'ERR: Temperature socket down'
                self.temperature = -50
                self.datasocket.set_point_now('temperature', self.temperature)
                self.power = 0
                time.sleep(0.5)
                socketerror = True
                continue
            if received[0] == 'OLD_DATA':
                old_data = True
            else:
                old_data = False
            try:
                self.last_time = float(self.time)
                self.time = float(received[0])
                self.temperature = float(received[1])
            except ValueError:
                pass
            except Exception as e:
                LOGGER.warning('Package received: {}'.format(repr(received)))
                LOGGER.warning(e)
            #self.temperature = float(received[received.find(',') + 1:])
            if (self.time == self.last_time) or old_data:
                ttl += 1
                if ttl > 200:
                    LOGGER.error('Data from pull socket TOO OLD! Breaking out of while loop.')
                    self.msg = 'ERR: Stopped because of old temperature feed.'
                    break
                time.sleep(0.1)
                continue
            ttl = 0
            log_counter += 1
            if log_counter > log_interval:
                LOGGER.info('Time/Temperature from datedatasocket: ({}/{})'.format(self.time, self.temperature))
                log_counter = 0

            self.datasocket.set_point_now('temperature', self.temperature)
            self.power = self.pid.wanted_power(self.temperature)


            #  Handle the setpoint from the network
            try:
                setpoint = self.pushsocket.last[1]['setpoint']
                new_update = self.pushsocket.last[0]
            except (TypeError, KeyError): #  Setpoint has never been sent
                setpoint = None
            if ((setpoint is not None) and setpoint != self.setpoint) and \
               (sp_updatetime < new_update):
                self.update_setpoint(setpoint)
                sp_updatetime = new_update

            #  Handle the ramp from the network
            try:
                ramp = self.pushsocket.last[1]['ramp'] # "ramp" string or dict
                new_update = self.pushsocket.last[0] # time of last command
            except (TypeError, KeyError): #  Ramp has not yet been set
                ramp = None
            if ramp == 'stop': # Last command was stop button being pressed
                ramp_time = 0
                self.stop()
            elif ramp == 'pause':
                paused = not paused
            elif (ramp is not None) and (ramp != 'stop'):
                if new_update > ramp_updatetime:
                    # Convert JSON ramp format to index
                    index_list = list(ramp['time'].keys())
                    if isinstance(index_list[0], str):
                        for key in ['time', 'temp', 'step']:
                            for i in index_list:
                                ramp[key][int(i)] = ramp[key][i]
                                del ramp[key][i]
                    # Update setpoint / ramp settings
                    ramp_updatetime = new_update
                    self.ramp = ramp
                    if ramp['init']:
                        ramp_time = time.time()
                    paused = False
                else:
                    pass

            if ramp_time > 0 and not paused:
                self.update_setpoint(ramp=ramp_time)
            time.sleep(0.5)
        LOGGER.info('PowerCalculatorClass stop!')
        self.stop()

    def stop(self):
        """On stop set the setpoint back to a low temperature"""
        # Make sure it is below room temperature
        self.update_setpoint(0)

class HeaterClass(threading.Thread):
    """ Do the actual heating """
    def __init__(self, power_calculator, datasocket, db_logger, criterium_checker):
        threading.Thread.__init__(self)
        self.pinnumber = 0
        self.pc = power_calculator
        self.datasocket = datasocket
        self.db_logger = db_logger
        self.criterium_checker = criterium_checker
        self.beatperiod = 5 # seconds
        self.beatsteps = 100
        self.dutycycle = 0
        self.quit = False
        wp.pinMode(self.pinnumber, 1)  # Set pin 0 to output

    def run(self):
        prefix = 'fr307_furnace_1_'
        while not self.quit:
            # Get PID output
            self.dutycycle = self.pc.read_power()

            # Log stuff
            for name, value in [('dutycycle', self.dutycycle),
                               ('pid_p', self.pc.pid.proportional_contribution()),
                               ('pid_i', self.pc.pid.integration_contribution())]:
                self.pc.datasocket.set_point_now(name, value)
                if self.criterium_checker.check(prefix+name, value):
                    self.db_logger.save_point_now(prefix+name, value)
            name, value = 'S', self.pc.setpoint
            if self.criterium_checker.check(prefix+name, value):
                self.db_logger.save_point_now(prefix+name, value)

            # Set output
            for i in range(0, self.beatsteps):
                time.sleep(1.0 * self.beatperiod / self.beatsteps)
                if i < self.beatsteps * self.dutycycle:
                    wp.digitalWrite(self.pinnumber, 1)
                else:
                    wp.digitalWrite(self.pinnumber, 0)
        wp.digitalWrite(self.pinnumber, 0)


def main():
    """ Main function """
    wp.wiringPiSetup()
    datasocket = DateDataPullSocket('furnaceroom_controller',
                                    ['temperature', 'setpoint', 'dutycycle', 'pid_p', 'pid_i'],
                                    timeouts=999999, port=9000)
    datasocket.start()

    pushsocket = DataPushSocket('furnaceroom_push_control', action='store_last')
    pushsocket.start()

    power_calculator = PowerCalculatorClass(datasocket, pushsocket)
    power_calculator.daemon = True
    power_calculator.start()

    codenames = ['fr307_furnace_1_dutycycle', 'fr307_furnace_1_S',
                 'fr307_furnace_1_pid_p', 'fr307_furnace_1_pid_i']
    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_furnaceroom307',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    # Criterium checker
    criterium_checker = LoggingCriteriumChecker(
        codenames=codenames,
        types=['lin']*len(codenames),
        criteria=[0.02, 1., 1., 1.],
        time_outs=[60, 120, 300, 300],
        )
    
    heater = HeaterClass(power_calculator, datasocket, db_logger, criterium_checker)
    heater.daemon = True ###
    heater.start()

    tui = CursesTui(heater)
    tui.daemon = True
    tui.start()
    # make sure tui close down properly and the T setpoint is put low.
    try:
        while not heater.quit:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Keyboard Interrupt detected, closing program")
        heater.quit = True
    finally:
        power_calculator.quit = True
        time.sleep(0.1)
        tui.stop()

if __name__ == '__main__':
    main()
