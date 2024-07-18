import time
from PyExpLabSys.drivers.omega_cn7800 import CN7800

def main(): 
    # Settings
    port = '/dev/ttyUSB0'
    sleep_time = 3 # Update every X seconds
    logger_timeout = 300 # 5 minutes
    value_trigger = 1 # Force a temperature log at X degrees C
    logfile = 'temperature_log_{}.csv'.format(time.asctime().replace(':', ''))
    t_start = time.time()
    old_temperature = -9999
    last_temperature = -9999
    
    # Connect to temperature reader
    cn = CN7800(port)

    # Initialize CSV file
    with open(logfile, 'w') as f:
        f.write('Created: {}\r\n'.format(time.asctime()))
        f.write('Time (s),Temperature (C)\r\n')

    trig = False
    t0 = time.time()
    while True:
        # Get new reading
        temperature = cn.read_temperature()
        t = time.time()

        # Check if we should save a measurement
        if temperature > old_temperature + value_trigger:
            trig = True
        elif temperature < old_temperature - value_trigger:
            trig = True
        elif t - t0 > logger_timeout:
            trig = True

        # Save data point to file and update reference data
        if trig:
            with open(logfile, 'a') as f:
                f.write('{},{}\r\n'.format(t - t_start, temperature))
            trig = False
            print('{} s, {} C'.format(t - t_start, temperature))
            
            old_temperature = temperature
            t0 = t
        else:
            print('{} C'.format(temperature))

        # Wait a while
        time.sleep(sleep_time)

if __name__ == '__main__':
    while True:
        try:
            main()
        except KeyboardInterrupt:
            break

