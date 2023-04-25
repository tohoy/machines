""" Data logger for the furnaceroom, 307 """
import threading
import logging
import time
import minimalmodbus
import serial
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket, LiveSocket
import credentials


class TemperatureReader(threading.Thread):
    """ Communicates with the Omega ?? """
    def __init__(self, port, datasocket=None, debugger=None, name='default'):
        threading.Thread.__init__(self)
        self.comm = minimalmodbus.Instrument('/dev/serial/by-id/' + port, 1)
        self.comm.serial.baudrate = 9600
        self.comm.serial.parity = serial.PARITY_EVEN
        self.comm.serial.timeout = 0.25
        self.temperature = -999
        self.logger = debugger
        self.name = name
        self.datasocket = datasocket
        print(self.comm.serial)

        self.quit = False
        if self.logger:
            self.logger.info('{} TemperatureReader initialized'.format(self.name))

    def value(self):
        """ Return current temperature """
        return self.temperature

    def run(self):
        if self.logger:
            self.logger.info('{} TemperatureReader started'.format(self.name))
        while not self.quit:
            time.sleep(0.1)
            try:
                self.temperature = self.comm.read_register(4096, 1)
                print(self.temperature)
                if self.datasocket:
                    self.datasocket.set_point_now(self.name, self.temperature)
                time.sleep(1)
                # Uncomment to force a case of OLD_DATA on DateDataPullSocket:
                #raise KeyboardInterrupt
            except ValueError as e:
                if self.logger:
                    self.logger.warning('{} ValueError: {}'.format(self.name, e))
                print('Error')
            except Exception as e:
                if self.logger:
                    self.logger.error('{} Uncaught exception: {}'.format(self.name, e))
                raise

def main():
    """ Main function """
    # Set up debug logging
    FORMAT = '%(asctime)s -- %(name)s:%(message)s'
    logging.basicConfig(filename="log.data_logger", format=FORMAT, level=logging.WARNING)
    LOGGER = logging.getLogger('data_logger')

    LOGGER.info('Initializing main()')
    # Codenames for database logging
    codenames = ['fr307_furnace_1_T', 'fr307_furnace_2_T']

    datasocket = DateDataPullSocket('furnaceroom_reader', codenames,
                                    timeouts=[3.0, 3.0], port=9001)
    datasocket.start()

    livesocket = LiveSocket('B307_furnace1_monitor', codenames)
    livesocket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_furnaceroom307',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    ports = {}
    ports['fr307_furnace_1_T'] = 'usb-FTDI_USB-RS485_Cable_FTYIZLJV-if00-port0'
    ports['fr307_furnace_2_T'] = 'usb-FTDI_USB-RS485_Cable_FTYJ1V33-if00-port0'
    loggers = {}
    temperature_readers = {}
    for logger_name in codenames:
        temperature_readers[logger_name] = TemperatureReader(ports[logger_name],
                                                             debugger=LOGGER,
                                                             name=logger_name,
                                                             datasocket=datasocket,
        )
        temperature_readers[logger_name].daemon = True
        temperature_readers[logger_name].start()
        loggers[logger_name] = ValueLogger(temperature_readers[logger_name], comp_val=0.09)
        loggers[logger_name].start()

    time.sleep(5)

    values = {}
    while True:
        time.sleep(1)
        for logger_name in codenames:
            values[logger_name] = loggers[logger_name].read_value()
            #datasocket.set_point_now(logger_name, values[logger_name])
            livesocket.set_point_now(logger_name, values[logger_name])
            if loggers[logger_name].read_trigged():
                LOGGER.debug('Saving point: {}: {}'.format(logger_name, values[logger_name]))
                print(logger_name + ': ' + str(values[logger_name]))
                db_logger.save_point_now(logger_name, values[logger_name])
                loggers[logger_name].clear_trigged()


if __name__ == '__main__':
    main()
