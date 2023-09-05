import time
import threading
import socket
from PyExpLabSys.drivers.se_galaxy_vs import GalaxyVS
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket

import credentials_ups as credentials

class UpsReader(threading.Thread):
    """ Run the ups-instance and keep status updated """
    def __init__(self, ups):
        threading.Thread.__init__(self)
        self.ups = ups
        self.status = ups.status
        self.ttl = 100
        self.quit = False
        self.live_socket = LiveSocket('UPS Status', self.ups.codenames,
                                      internal_data_pull_socket_port=8001)
        self.live_socket.start()

    def value(self, stat):
        """ Return the value of the reader """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
        return_val = self.ups.status[stat]
        return return_val

    def stop(self):
        self.quit = True
        self.live_socket.stop()
        time.sleep(3)

    def run(self):
        while not self.quit:
            print(self.ttl)
            self.ups.get_all_status()
            for stat in self.ups.codenames:
                self.live_socket.set_point_now(stat, self.ups.status[stat])
            self.ttl = 100
            time.sleep(1)
        self.stop()


class main(object):
    """ Main function """
    
    def __init__(self, auth):
        self.ups = GalaxyVS(credentials=auth)
        self.reader = UpsReader(self.ups)
        self.reader.daemon = True
        self.reader.start()
        time.sleep(5)

        self.codenames = {# DB_codename: GalaxyVS.status[codename]
            'b312_ups_temperature': 'battery_temperature',
            'b312_ups_kVAPh1': 'phase_output_apparent_power_1',
            'b312_ups_kVAPh2': 'phase_output_apparent_power_2',
            'b312_ups_kVAPh3': 'phase_output_apparent_power_3',
            'b312_ups_output_current_Ph1': 'phase_output_current_1',
            'b312_ups_output_current_Ph2': 'phase_output_current_2',
            'b312_ups_output_current_Ph3': 'phase_output_current_3',
            'b312_ups_input_frequency': 'input_frequency',
            'b312_ups_input_voltage_Ph1': 'phase_input_voltage_main_1',
            'b312_ups_input_voltage_Ph2': 'phase_input_voltage_main_2',
            'b312_ups_input_voltage_Ph3': 'phase_input_voltage_main_3',
            'b312_ups_output_voltage_Ph1': 'phase_output_voltage_1',
            'b312_ups_output_voltage_Ph2': 'phase_output_voltage_2',
            'b312_ups_output_voltage_Ph3': 'phase_output_voltage_3',
            'b312_ups_battery_voltage': 'battery_actual_voltage',
            'b312_ups_battery_current': 'battery_current',
            'b312_ups_battery_state_of_charge': 'battery_capacity',
            'b312_ups_output_frequency': 'phase_output_frequency',
         }

        self.loggers = {}
        for codename, stat in self.codenames.items():
            self.loggers[codename] = ValueLogger(self.reader, comp_val=0.11, channel=stat, pre_trig=True)
            self.loggers[codename].start()
        self.socket = DateDataPullSocket('UPS status', list(self.codenames.keys()),
                                         port=9001, timeouts=[5.0] * len(self.codenames))
        self.socket.start()

        self.db_logger = ContinuousDataSaver(continuous_data_table='dateplots_ups_b312',
                                        username=credentials.user,
                                        password=credentials.passwd,
                                        measurement_codenames=list(self.codenames.keys()))
        self.db_logger.start()
        time.sleep(5)

    def stop(self):
        self.socket.stop()
        self.db_logger.stop()

    def start(self):
        while self.reader.is_alive():
            time.sleep(1)
            for name in self.codenames:
                value = self.loggers[name].read_value()
                self.socket.set_point_now(name, value)
                if self.loggers[name].read_trigged():
                    print(value)
                    self.db_logger.save_point_now(name, value)
                    self.loggers[name].clear_trigged()
        self.stop()

if __name__ == '__main__':
    auth = {
        'ups_user': credentials.ups_user,
        'authSecret': credentials.authSecret,
        'authProtocol': credentials.authProtocol,
        'privSecret': credentials.privSecret,
        'privProtocol': credentials.privProtocol,
    }
    while True:
        try:
            ups = main(auth)
            ups.start()
        except (ConnectionResetError, socket.gaierror) as exception:
            print("Got '{}'. Wait 300 sec and try again".format(exception))
            ups.stop()
            time.sleep(300)
            continue
        except KeyboardInterrupt:
            ups.stop()
            break
        except:
            raise
