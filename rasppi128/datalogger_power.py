import time
import threading

import PyExpLabSys.drivers.netio_powerbox as netio_powerbox

from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DateDataPullSocket

from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver

import credentials

PREFIX = 'SunLab_netio'
CODENAMES = {
    'Voltage': 1.5,
    'TotalLoad': 30,
    'Frequency': 0.3,
    '1_Load': 30,
    '1_Phase': 15,
    '1_PowerFactor': 0.2,
    '2_Load': 30,
    '2_Phase': 15,
    '2_PowerFactor': 0.2,
    '3_Load': 30,
    '3_Phase': 15,
    '3_PowerFactor': 0.2,
    '4_Load': 30,
    '4_Phase': 15,
    '4_PowerFactor': 0.2,
}
CODENAMES = {f'{PREFIX}_{codename}': comp_val for codename, comp_val in CODENAMES.items()}

class Comm(threading.Thread):
    """ Read values from the power strip """
    def __init__(self):
        threading.Thread.__init__(self)
        self.name = 'NetioReader Thread'
        self.netio = netio_powerbox.NetioPowerBox('10.54.10.232')
        self.total_interest = [
            'Voltage',
            'TotalCurrent',
            'OverallPowerFactor',
            'TotalPowerFactor',
            'OverallPhase',
            'TotalPhase',
            'Frequency',
            'TotalEnergy',
            'TotalLoad',
        ]
        self.channel_interest = [
            'State',
            'Current',
            'PowerFactor',
            'Phase',
            'Load',
        ]
        self.values = {f'{PREFIX}_{i+1}_{ci}': -1 for i in range(4)
                       for ci in self.channel_interest}
        self.values.update(
            {f'{PREFIX}_{ti}': -1 for ti in self.total_interest}
        )
        print(self.values) ###
        self.pullsocket = DateDataPullSocket(
            'SunLabPowerMonitor',
            list(self.values.keys()),
            timeouts=[3] * len(self.values),
            port=9000
        )
        self.pullsocket.start()
        self.livesocket = LiveSocket(
            'SunLab PowerMonitor Live', list(self.values.keys())
        )
        self.livesocket.start()

        self.quit = False
        self.ttl = 5000

    def value(self, codename):
        """ Read power readings """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            print('TTL is out! Stopping')
            self.quit = True
            return_val = None
        return_val = self.values[codename]
        return return_val

    def _update_values(self):
        success = False
        try:
            
            # Should we also record phase???
            power_status = self.netio.output_status([1, 2, 3, 4])
            for key, value in power_status[0].items():
                codename = f'{PREFIX}_{key}'
                if codename in self.values:
                    self.values[codename] = value
            for i in range(4):
                j = i + 1
                for key, value in power_status[j].items():
                    codename = f'{PREFIX}_{j}_{key}'
                    if codename in self.values:
                        self.values[codename] = value
            for key, value in self.values.items():
                self.pullsocket.set_point_now(key, value)
                self.livesocket.set_point_now(key, value)
            success = True
        except Exception as e:
            print()
            print('Unable to connect to power strip - exception is: {}'.format(e))
        return success

    def run(self):
        while not self.quit:
            success = self._update_values()
            if success:
                self.ttl = 5000
            time.sleep(0.75)


class Logger(object):
    def __init__(self):
        self.loggers = {}
        self.reader = Comm()
        self.reader.start()

        self.db_logger = ContinuousDataSaver(
            continuous_data_table='dateplots_sunlab',
            username=credentials.user,
            password=credentials.passwd,
            measurement_codenames=CODENAMES.keys()
        )
        self.db_logger.name = 'DB Logger Thread'
        self.db_logger.start()

        for codename, comp_val in CODENAMES.items():
            self.loggers[codename] = ValueLogger(
                self.reader,
                comp_val=comp_val,
                comp_type='lin',
                maximumtime=600,
                channel=codename,
                model='event',
            )
            self.loggers[codename].name = 'Logger_thread_{}'.format(codename)
            self.loggers[codename].start()

    def main(self):
        """
        Main function
        """
        msg = '{} is logging value: {}'
        time.sleep(20)
        while self.reader.is_alive():
            time.sleep(2)
            for name in self.loggers.keys():
                value = self.loggers[name].read_value()
                if self.loggers[name].read_trigged():
                    for point in self.loggers[name].get_data():
                        print(msg.format(name, point))
                        self.db_logger.save_point(name, point)


if __name__ == '__main__':
    logger = Logger()
    logger.main()
