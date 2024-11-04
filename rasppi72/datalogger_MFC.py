# -*- coding: utf-8 -*-
from PyExpLabSys.drivers.dataq_comm import DataQ
from drivers_Munin import i2c_communicate, Relay, loading_animation, MFC_setpoint_1volt_shift, MFC_data_1volt_shift, arduino
import time
from socket_server_MFC import MFC_control_socket, MFC_data_socket

"""
#Initiation
"""
#relay = Relay()
i2c_connection_lost = False
shut_down_procedure = False
arduino_control = arduino()

#relay.MFC_powersupply_ON()
#print('Power up mass flow controllers')

#print('\n')
#loading_animation(9) #they take some time to start

#dataq = DataQ('/dev/ttyACM0')
#dataq.add_channel(1)
#dataq.start_measurement()

#Push socket
#MFC_sock = MFC_control_socket() #on port 8501
MFC_control = MFC_control_socket() #on port 8501

#Pull socket
#MFC_data_sock = MFC_data_socket() #on port 9001
MFC_data = MFC_data_socket() #on port 9001

"""
#MFC setpoint reader
#MFC1=CO; MFC2=H2; MFC3=CO2; MFC4=Ar; MFC5=Empty
"""
print('Gas flow started on '+time.ctime())
print('\n\n')
start_time = time.time()
loop_time = time.time()-start_time
update_time = 0.44
try:
    while True:
        if  (update_time-loop_time) > 0:
             #if less than a second has passed, since last loop, wait until a second has passed
            time.sleep(update_time-loop_time)
        for setpoint in ['sp1','sp2','sp3','sp4','sp5']:
            if MFC_control.settings[setpoint] < 0:
                MFC_control.settings[setpoint] = 0.
            elif MFC_control.settings[setpoint] > 100:
                MFC_control.settings[setpoint] = 100.
        sp1, sp2, sp3, sp4, sp5 = MFC_control.settings['sp1'], MFC_control.settings['sp2'], MFC_control.settings['sp3'], MFC_control.settings['sp4'], MFC_control.settings['sp5'] 
        _flow_ = i2c_communicate(0x16, round(sp1*2.55), round(sp2*2.55), round(sp3*2.55), round(sp4*2.55), round(sp5*2.55))
        if _flow_[4] == -1000:
            time.sleep(0.5)
            _flow_ = i2c_communicate(0x16, round(sp1*2.55), round(sp2*2.55), round(sp3*2.55), round(sp4*2.55), round(sp5*2.55))
            if _flow_[4] == -1000:
                print('\n')
                print('Connection to arduino seems lost on '+time.ctime())
                while True:
                    print('Entered reset-mode.')
                    arduino_control.reset_arduino()
                    arduino_control.reset_pres_arduino()
                    time.sleep(0.5)
                    _flow_ = i2c_communicate(0x16, round(sp1*2.55), round(sp2*2.55), round(sp3*2.55), round(sp4*2.55), round(sp5*2.55))
                    if _flow_[4] != -1000:
                        print('Reset succesfull, at '+time.ctime())
                        break
            _flow_ = i2c_communicate(0x16, round(sp1*2.55), round(sp2*2.55), round(sp3*2.55), round(sp4*2.55), round(sp5*2.55))
        if shut_down_procedure:
            time.sleep(5)
            relay.MFC_powersupply_OFF()
            MFC_control.stop()
            MFC_data.stop()
            break 
            
        print('('+str(round(sp1,1))+'[%]/'+str(round(_flow_[0]/10.23,1))+')('+str(round(sp2,1))+'[%]/'+str(round(_flow_[1]/10.23,1))+')('+str(round(sp3,1))+'[%]/'+str(round(_flow_[2]/10.23,1))+')('+str(round(sp4,1))+'[%]/'+str(round(_flow_[3]/10.23,1))+')('+str(round(sp5,1))+'[%]/'+str(round(_flow_[4]/10.23,1))+')       ',end = '\r')
        MFC_data.set_point_now('MFC1', _flow_[0]/10.23)
        MFC_data.set_point_now('SP1', sp1)
        MFC_data.set_point_now('MFC2', _flow_[1]/10.23)
        MFC_data.set_point_now('SP2', sp2)
        MFC_data.set_point_now('MFC3', _flow_[2]/10.23)
        MFC_data.set_point_now('SP3', sp3)
        MFC_data.set_point_now('MFC4', _flow_[3]/10.23)
        MFC_data.set_point_now('SP4', sp4)
        MFC_data.set_point_now('MFC5', _flow_[4]/10.23)
        MFC_data.set_point_now('SP5', sp5)
        loop_time = time.time()-start_time-loop_time
except KeyboardInterrupt:
    print('Script interrupted. Flow stopped on '+time.ctime())
    _flow_ = i2c_communicate(0x16, 0, 0, 0, 0, 0)
    #dataq.stop_measurement()
    MFC_control.stop()
    MFC_data.stop()
    #print('Power down mass flow controllers')
    #loading_animation(5)
    #relay.MFC_powersupply_OFF()
    print('Quitting')
