# -*- coding: utf-8 -*-
import socket
import json
import time
import code
#from tkinter.filedialog import askopenfile
import threading
from pprint import pprint
import propar

version = 'Script version: 20th Feb. 2024'

mfc_factor = {'O2' :   0.0949,
          'H2' :   1.3716,
          'CH4':   1.064,
          'CO2':   0.5000,#'CO2':   0.6987,
          'N2O':   0.7207,
          'N2O/Ar': 1.4163,
          'CO' :   0.4826,
          'Ar' :   1.4093
          }
mfc_offset = {'O2' :   0.00,
          'H2' :   0.6907,
          'CH4':   -0.26,
          'CO2':   0.000,#'CO2':   0.2582,
          'N2O':   0.7029,
          'N2O/Ar': -0.8819,
          'CO' :   1.7148,
          'Ar' :   1.4674
          }

sock_MFC_comm = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # setting up connection to pi over the IPv4 -> (AF_INET)
sock_MFC_data = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_MFC_data.settimeout(0.5)


sock_pressure = propar.instrument('/dev/ttyUSB0') #connecting to the pressure controller

pi_address ='rasppi72.fysik.dtu.dk' #Use this then AIT changes the address of the Pi's

def hello():
    print(' ')
    print('####################################################################################')
    print(' ')
    print('This is the user-interface for Heimdal')
    print(' ')
    print(' ')
    print('for help, use "list_commands()" or "help_command("command")"')
    print(' ')
    print('have fun!')
    print(' ')
    print('############################################################# '+version)
    print(' ')

hello()

#if True:

def list_commands():
        pprint(['help_command("command")','hello()','MFC(number, percentage_flow)', 'set_flow(gas, flow)', 'set_pressure(pressure)','start_batch_run(data_folder_name)', 'run()','stop()'])

def help_command(command):
    if command == 'help_command' or command == 'help_command()' or command == 'help_command("command")':
        print(' ')
        print('### help: help_command ###')
        print('This is exactly what "help_command" does.')
        print(' ')
    elif command == 'hello' or command == 'hello()':
        print(' ')
        print('### help: hello ###')
        print('hello() prints the greeting of this program to the terminal.')
        print(' ')
    elif command == 'MFC' or command == 'MFC()' or command == 'MFC(number, percentage_flow)':
        print(' ')
        print('### help: MFC ###')
        print('MFC(x,y) takes two arguments: "x" is the number of the mass-flow controller, "y" is the setpoint for that mass-flow controllers flow.')
        print(' ')
    elif command == 'set_flow' or command == 'set_flow()' or command == 'set_flow(gas, flow)':
        print(' ')
        print('### help: set_flow ###')
        print('set_flow(x,y) takes two arguments: "x" is the gas, "y" is the setpoint for the gas flow in Nml/min.')
        print(' ')
    elif command == 'set_pressure' or command == 'set_pressure()' or command == 'set_pressure(pressure)':
        print(' ')
        print('### help: set_flow ###')
        print('set_pressure(x) takes one argument: "x" is the desired reactor pressure.')
        print(' ')
    elif command == 'start_batch_run' or command == 'start_batch_run()' or command == 'start_batch_run(data_folder_name)':
        print(' ')
        print('### help: start_batch_run ###')
        print('start_batch_run(x) takes a string "x" and makes a data-folder of that name, and prompts the user for a batch-script to run.')
        print('Use start_batch_run(x, gas_list=some_gas_list) to define specific gasses different from the standard. Eg. "some_gas_list = ["O2","CH4","N2O","CO","N2"]"')
        print(' ')
    elif command == 'run' or command == 'run()':
        print(' ')
        print('### help: run ###')
        print('run() is identical to "start_batch_run", but creates a data folder named by the current time. It is only used for convenience.')
        print(' ')
    elif command == 'stop' or command == 'stop()':
        print(' ')
        print('### help: stop ###')
        print('stop() will end the currently running experiment.')
        print(' ')
    elif command == 'list_commands' or command == 'list_commands()':
        print(' ')
        print('### help: list_commands ###')
        print('list_commands() will list the available commands. An optional settings is "full=True", which will list additional commands used for utility.')
        print(' ')
    elif command == 'help_command' or command == 'help_command()' or command == 'help_command(command)':
        print(' ')
        print('### help: help_command ###')
        print('This is exactly what this command does.')
        print(' ')
    else:
        print('No command of that name was found in the "help".')

def send_command(sock, data, address, echo=False):
    #used for sending commands to pushserver which controls the MFC's
    if echo:
        print(' ')
    command = 'json_wn#{}'.format(json.dumps(data))
    if echo:
        print('Sending command: {}'.format(command))
    sock.sendto(command.encode('ascii'), address)
    print('Sending command: {}'.format(command))

def MFC(number, flow):
    if number not in [1, 2, 3, 4, 5]:
        raise ValueError('First argument "MFC" should be an integer between 1 and 5')
        return False
    if flow < 0. or flow > 100.:
        raise ValueError('Second argument "flow" should be a float between 0. and 100.')
        return False
    data = {'method': 'update_settings', 'sp'+str(number): flow}
    send_command(sock_MFC_comm, data, (pi_address, 8501))

def ALL_MFC(flow_list):
    if len(flow_list) != 5:
        raise IndexError('Argument should be a list of 5 floats')
        return False
    for flow in flow_list:
        if flow < 0. and flow > 100.:
            raise ValueError('Flows should be floats between 0. and 100.')
            return False
    data = {'method': 'update_settings', 
            'sp1': flow_list[0],
            'sp2': flow_list[1],
            'sp3': flow_list[2],
            'sp4': flow_list[3],
            'sp5': flow_list[4]}
    send_command(sock_MFC_comm, data, (pi_address, 8501))

def from_percentage_to_flow(gas,percentage_flow):
    try:
        flow = mfc_factor[gas]*percentage_flow+mfc_offset[gas]
        if flow < 0:
            flow = 0.
        return flow
    except:
        print('"'+gas+'" is not a calibrated gas')
        return percentage_flow

def from_flow_to_percentage(gas, flow):
    try:
        percentage_flow = (flow-mfc_offset[gas])/mfc_factor[gas]
        if percentage_flow < 0:
            percentage_flow = 0.
        return percentage_flow
    except:
        print('"'+gas+'" is not a calibrated gas')
        return flow

def set_flow(gas, flow):
    gas_MFC_dict = {'CO':  1, 
                    'H2':  2,
                    'CO2': 3,
                    'Ar':  4,
                    'Empty':  5}
    if gas not in gas_MFC_dict.keys():
        raise KeyError(gas+' is not an available gas')
    if flow != 0.:
        percentage_flow = from_flow_to_percentage(gas,flow)
    else:
        percentage_flow = 0
    if percentage_flow > 100:
        percentage_flow = 100
        print('Max flow is '+str(from_percentage_to_flow(gas,100)))
    MFC(gas_MFC_dict[gas], percentage_flow)

def set_all_flow(gas_list, flow_list):
    calibrated_flow_list = [0.,0.,0.,0.,0.]
    gas_MFC_dict = {'CO':  0, 
                    'H2':  1,
                    'CO2': 2,
                    'Ar':  3,
                    'Open':  4,}
    for gas, flow in zip(gas_list, flow_list):
        if flow != 0.:
            calibrated_flow_list[gas_MFC_dict[gas]] = from_flow_to_percentage(gas,flow_list[gas_list.index(gas)])
    ALL_MFC(calibrated_flow_list)

def set_pressure(pressure):
    conversion_factor = 32000/2.5 #32000 is full range and 2.5 bar is = 32000
    print("Changing the pressure to " + str(pressure) + "bar") #printing the pressure as 
    if pressure > 1:
        print("Max pressure is 1 bar, setting the pressure to 1 bar")
        pressure = 1
    elif pressure < 0:
        print("Min pressure is 0 bar, setting the pressure to 0 bar")
        pressure = 0
    print("Raw input " + str(round(pressure*conversion_factor)) + " equil to " + str(pressure*conversion_factor/conversion_factor) + " in bar")
    sock_pressure.writeParameter(9, round(pressure*conversion_factor))
    print(sock_pressure.writeParameter(9, round(pressure*conversion_factor))) #Using brooks module propar to change the setpoint (param 9) note that the setpoint is from 0..32000 with 32000 = 2.5 bar
    print("Current Setpoint: " + str(sock_pressure.readParameter(9,1)) + " Current Pressure: " + str(sock_pressure.readParameter(8))) #measured pressure


def load_program_items(file):
    lines = file.readlines()
    # Filter out lines containing '#'
    filtered_lines = [line for line in lines if '#' not in line]
    
    program = []
    time_dict = {'h': 3600, 'm': 60, 's': 1}
    
    for line in filtered_lines:
        split_line = line.replace(",", "").split()
        item = [time_dict[split_line[0]] * float(split_line[1])]
        for set_point in split_line[2:]:
            item.append(float(set_point))
        if len(item) == 8:
            program.append(item)
        elif len(item) == 7:
            item.append(1.0)
            program.append(item)
        else:
            raise IndexError('Wrong number of items in line '+line+' was found. Check your program')
            return None
    
    for index, item in enumerate(program[1:]):
        program[index + 1][0] = program[index + 1][0] + program[index][0]
    
    # This part adds two more lines with default values
    program.append([program[-1][0] + 1080, 20., 0.0, 0.0, 0.0, 0.0, 5.0, 1.0])
    program.append([program[-1][0] + 1080, 20., 0.0, 0.0, 0.0, 0.0, 5.0, 1.0])
    
    # This part sets the time of the added lines to the same as the last line
    for index, item in enumerate(program[1:]):
        program[-index - 1][0] = program[-index - 2][0]
    
    program[0][0] = 0.
    
    return program

class mfc_thread(threading.Thread):
            
    def __init__(self, start_time = 0, 
                        data_path = '', 
                        gas_list = ['CO','H2','CO2','Ar','Empty'],
                        program = [1, -9999., 0.0, 0.0, 0.0, 5.0, 0.0, 1.0]): # [Unknown, Unknown, MFC1 flow, MFC2 flow, MFC3 flow, MFC4 flow, MFC5 flow, Pressure]
        threading.Thread.__init__(self)
        self._running = True
        self.mfc_sock = sock_MFC_data
        self.mfc_sock_address = (pi_address,9001)
        self.command = 'json_wn'
        self.start_time = start_time
        self.gas_list = gas_list
        self.data_path = data_path
        self.program = program
        self.item = 0
        self.data_recieve_error = False
                
    def stop(self):
        self._running = False
            
    def start_experiment(self):
        self.data_file = open(self.data_path+'/setup_data.txt','w+')
        self.data_file.write('#data file created on '+time.ctime()+' in the folder "'+self.data_path+'".\n')
        self.data_file.write('#time[s], temperature[C], '+self.gas_list[0]+'[Nml/min], '+self.gas_list[1]+'[Nml/min], '+self.gas_list[2]+'[Nml/min], '+self.gas_list[3]+'[Nml/min], '+self.gas_list[4]+'[Nml/min], frontpressure[bar], backpressure[bar], front GC ressure, back GC pressure.\n')
        self.data_file.close()
        self.rel_time = [time.time()-self.start_time]
        self.program_time = self.rel_time[0]
        time.sleep(0.5)
        self.rel_time.append(time.time() - self.start_time)
        
    def read_and_write(self):
        self.rel_time.append(time.time() - self.start_time)
        #for i in [1]:
        try:
            self.mfc_sock.sendto(self.command.encode('ascii'), self.mfc_sock_address)
            data = json.loads(self.mfc_sock.recv(2**20))
            #pressure = round(data['P'][1],2)
            pressure = round(sock_pressure.readParameter(9),2)
        except:
            if not self.data_recieve_error:
                print('\n MFC data could not be recieved from pi. Program will continue \n')
                self.data_recieve_error = True
            data = {'MFC1' : [0,-1000],
                    'MFC2' : [0,-1000],
                    'MFC3' : [0,-1000],
                    'MFC4' : [0,-1000],
                    'MFC5' : [0,-1000]}
            pressure = -1000
        try:
            #self.sock_pressure.sendto(self.command.encode('ascii'), self.pressure_sock_address)
            #pressure = round(json.loads(self.pressure_sock.recv(2048))['pressure'][0],2)
            pressure = round(sock_pressure.readParameter(9),2)
        except:
            if not self.data_recieve_error:
                print('\n Pressure data could not be recieved from pi. Program will continue \n')
                self.data_recieve_error = True
            pressure = -1000
       
        self.data_file = open(self.data_path+'/setup_data.txt','a+')
        self.data_file.write(str(round(self.rel_time[-1],1))
        +'    '+str(round(from_percentage_to_flow(self.gas_list[0],data['MFC1'][1]),1))
        +'    '+str(round(from_percentage_to_flow(self.gas_list[1],data['MFC2'][1]),1))
        +'    '+str(round(from_percentage_to_flow(self.gas_list[2],data['MFC3'][1]),1))
        +'    '+str(round(from_percentage_to_flow(self.gas_list[3],data['MFC4'][1]),1))
        +'    '+str(round(from_percentage_to_flow(self.gas_list[4],data['MFC5'][1]),1))
        +'    '+str(pressure)
        )
        self.data_file.close()
    
    def update_experiment(self):
        try:
            if self.program_time >= self.program[self.item+1][0]:
                self.item += 1
                print('\n')
                print('Executing item '+str(self.item+1)+' of program')
                print('\n')
        except:
            self.item = len(self.program)-1
    #        furnace(self.program[self.item][1])
        set_all_flow(self.gas_list, self.program[self.item][2:7])
        set_pressure(self.program[self.item][7])
            
    def end_experiment(self):
        self._running = False
        self.data_file.close()
        print('Experiment ended')
                
    def run(self):
        self.start_experiment()
        while self.program_time < (self.program[-1][0]+920) and self._running:
            self.read_and_write()
            self.update_experiment()
            time.sleep(0.4)
        self.end_experiment()
        print('\n')
        if self.program_time > (self.program[-1][0]+920):
            print('Experiment ended by itself')
        print('Press [ENTER] to continue')
        print('\n')
           
            
print(' ')  
print('############################################################# '+version)
print('for help, use "list_commands()" or "help_command("command")"')
print(' ')  
code.interact(local=locals())
