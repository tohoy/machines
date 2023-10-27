# pylint: disable=R0913, C0103
import threading
import time
import PyExpLabSys.drivers.bronkhorst as bronkhorst
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.sockets import DateDataPullSocket, DataPushSocket
from PyExpLabSys.common.sockets import LiveSocket
import credentials


class FlowControl(threading.Thread):
    """ Keep updated values of the current flow """

    def __init__(self, mfcs, pullsocket, pushsocket, livesocket):
        threading.Thread.__init__(self)
        self.mfcs = mfcs
        print(mfcs)
        self.pullsocket = pullsocket
        self.pushsocket = pushsocket
        self.livesocket = livesocket
        self.running = True
        self.reactor_pressure = float('NaN')

    def value(self, channel):
        """ Helper function for the reactor logger functionality """
        if channel == 1:
            return self.reactor_pressure

    def run(self):
        while self.running:
            time.sleep(0.1)
            qsize = self.pushsocket.queue.qsize()
            print("Qsize: " + str(qsize))
            while qsize > 0:
                element = self.pushsocket.queue.get()
                mfc = element.keys()[0]
                self.mfcs[mfc].set_flow(element[mfc])
                qsize = self.pushsocket.queue.qsize()

            for mfc in self.mfcs:
                flow = self.mfcs[mfc].read_flow()
                self.pullsocket.set_point_now(mfc, flow)
                self.livesocket.set_point_now(mfc, flow)
                if mfc == 'M11210022A':
                    print("Pressure: " + str(flow))
                    self.reactor_pressure = flow


devices = ['M11210022A']
ranges = {}
ranges['M11210022A'] = 2.5  # Sniffer

names = {}

MFCs = {}
t0 = time.time()
print('Identifying MFCs')
for i in range(0, 8):
    print('Trying port {}'.format(i))
    try:
        bronk = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), 1)
        names[i] = bronk.read_serial()
        names[i] = names[i].strip()
        print('Found: {}'.format(names[i]))
    except Exception as exc:
        print(exc)
        continue
    if names[i] in devices:
        MFCs[names[i]] = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), ranges[names[i]])
        MFCs[names[i]].set_control_mode()  # Accept setpoint from rs232
    if len(names) == len(devices):
        print('All MFCs identified!')
        break
print('Initialized in: {:1.1f}s'.format(time.time() - t0))

Datasocket = DateDataPullSocket(
    'sniffer_mfc_control', devices, timeouts=[3.0], port=9000
)
Datasocket.start()

Pushsocket = DataPushSocket('sniffer_mfc_control', action='enqueue')
Pushsocket.start()
Livesocket = LiveSocket('sniffer_mfc_control', devices)
Livesocket.start()

fc = FlowControl(MFCs, Datasocket, Pushsocket, Livesocket)
fc.start()

Logger = ValueLogger(fc, comp_val=1, comp_type='log', low_comp=0.0001, channel=1)
Logger.start()

db_logger = ContinuousLogger(
    table='dateplots_sniffer',
    username=credentials.user,
    password=credentials.passwd,
    measurement_codenames=['sniffer_chip_pressure'],
)
db_logger.start()

time.sleep(5)
while True:
    time.sleep(0.25)
    v = Logger.read_value()
    if Logger.read_trigged():
        print(v)
        db_logger.enqueue_point_now('sniffer_chip_pressure', v)
        Logger.clear_trigged()
