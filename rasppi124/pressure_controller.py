""" Pressure xgs600 controller for microreactors """
import time
import credentials
from PyExpLabSys.common.pressure_controller_xgs600 import XGS600Control
import PyExpLabSys.common.utilities
from PyExpLabSys.common.database_saver import ContinuousDataSaver
PyExpLabSys.common.utilities.ERROR_EMAIL = 'jejsor@fysik.dtu.dk'

MICRO = chr(0x03BC)

#### UPDATE  PRESSURE CONTROL LOGGING ####
def main():
    """ Main function """
    port = '/dev/ttyUSB0'
    codenames = ['pressure', 'state']
    socket_name = MICRO + '-reactorANH_xgs600_pressure_control'
    setpoint_channel_userlabel_on_off = {
        'T1': [1, 'NGBUF', '1.333E-04', '2.000E+00'],
        'T2': [2, 'IGMC', '1.000E-11', '1.000E-05'],
        'T3': [3, 'NGBUF', '1.333E-04', '1.000E+00'],
        }
    user_labels = ['IGMC', 'CNV1', 'CNV2', 'CNV3', 'NGBUF', 'OLDBF', 'MAIN']
    db_saver = ContinuousDataSaver(
        continuous_data_table='dateplots_microreactorNG',
        username=credentials.username,
        password=credentials.password,
        measurement_codenames=\
            ['microreactorng_valve_'+valve_names for valve_names \
            in list(setpoint_channel_userlabel_on_off.keys())],
    )

    pressure_control = XGS600Control(port=port,
                                     socket_name=socket_name,
                                     codenames=codenames,
                                     user_labels=user_labels,
                                     valve_properties=setpoint_channel_userlabel_on_off,
                                     db_saver=db_saver,
                                     )
    pressure_control.start()
    time.sleep(1)

    # Main activity loop
    while pressure_control.isAlive():
        time.sleep(0.25)


if __name__ == '__main__':
    main()
