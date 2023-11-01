""" The program will check up status of a list of hosts """
import subprocess
import datetime
import telnetlib
import socket
import threading
import time
try:
    import Queue as queue
except ImportError:
    import queue
import json
import MySQLdb
from PyExpLabSys.common.system_status import SystemStatus
from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

default_user = credentials.host['default_user']
default_passwd = credentials.host['default_passwd']

SELF = socket.gethostname()
LOGGER = get_logger('Host Checker', level='debug', file_log=True,
                    file_name='host_checker.log', terminal_log=True,
                    email_on_warnings=False, email_on_errors=False,
                    file_max_bytes=104857, file_backup_count=5)

def host_status(hostname, port):
    """ Report if a host is available on the network """
    host_is_up = True

    if port != '3389':
        try:
            subprocess.check_output(["ping", "-c1", "-W1", hostname])
        except subprocess.CalledProcessError:
            host_is_up = False
    if port == 3389: # RDP
        try:
            _ = telnetlib.Telnet(hostname, 3389)
        except socket.gaierror:
            host_is_up = False
        except socket.error:
            host_is_up = False
    return host_is_up

def uptime(hostname, port, username=default_user, password=default_passwd):
    """ Fetch as much information as possible from a host """
    return_value = {}
    return_value['up'] = ''
    return_value['load'] = ''
    return_value['git_pyexplabsys'] = ''
    return_value['git_machines'] = ''
    return_value['host_temperature'] = ''
    return_value['python_version'] = ''
    return_value['model'] = ''
    return_value['os_version'] = ''
    if hostname == SELF:
        status = SystemStatus()
        return_value['up'] = str(int(int(status.uptime()['uptime_sec']) / (60*60*24)))
        return_value['load'] = status.load_average()['15m']
        apt_up_time= status.last_apt_cache_change_unixtime()
        return_value['apt_up'] = datetime.datetime.fromtimestamp(apt_up_time).strftime('%Y-%m-%d')
        gittime = status.last_git_fetch_unixtime()
        try:
            return_value['git_pyexplabsys'] = datetime.datetime.fromtimestamp(gittime['PyExpLabSys']).strftime('%Y-%m-%d')
            return_value['git_machines'] = datetime.datetime.fromtimestamp(gittime['machines']).strftime('%Y-%m-%d')
        except TypeError:
            # Only for legacy purposes
            return_value['git_pyexplabsys'] = datetime.datetime.fromtimestamp(gittime).strftime('%Y-%m-%d')
            return_value['git_machines'] = None
        return_value['host_temperature'] = status.rpi_temperature()
        return_value['python_version'] = status.python_version()
        return_value['model'] = status.rpi_model()
        return_value['os_version'] = status.os_version()
        return return_value

    # Specifically use SSH
    if port == 22:
        uptime_string = subprocess.check_output(["sshpass",
                                                 "-p",
                                                 password,
                                                 "ssh",
                                                 '-o LogLevel=quiet',
                                                 '-oUserKnownHostsFile=/dev/null',
                                                 '-oStrictHostKeyChecking=no',
                                                 username + "@" + hostname,
                                                 'cat /proc/uptime /proc/loadavg'])
        uptime_raw = uptime_string.split('\n')[0]
        uptime_value = str(int(float(uptime_raw.split()[0]) / (60*60*24)))
        load = uptime_string.split('\n')[1].split()[2]
        return_value['up'] = uptime_value
        return_value['load'] = load

    if not port in [22, 3389]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.5)

        try:
            sock.sendto(b'status', (hostname, port))
            received = sock.recv(4096)
            status = json.loads(received.decode())
            system_status = status['system_status']
            uptime_value = str(int(int(system_status['uptime']['uptime_sec']) / (60*60*24)))
            LOGGER.debug(uptime_value)
            load = str(system_status['load_average']['15m'])
            return_value['up'] = uptime_value
            return_value['load'] = load
        except:
            return_value['up'] = 'Down'
            return_value['load'] = 'Down'

        try:
            if system_status['purpose']['id'] is not None:
                return_value['location'] = system_status['purpose']['id']
                return_value['purpose'] = system_status['purpose']['purpose']
        except (KeyError, UnboundLocalError):
            pass

        # Legacy compatibility: if os_version not available, then SSH to obtain it
        try:
            os_version = system_status['os_version']
            ret = True
        except (KeyError, UnboundLocalError):
            ret = False
        if not ret:
            try:
                os_string = subprocess.check_output([
                    "sshpass",
                    "-p",
                    password,
                    "ssh",
                    '-o LogLevel=quiet',
                    '-oUserKnownHostsFile=/dev/null',
                    '-oStrictHostKeyChecking=no',
                    username + "@" + hostname,
                    'cat /etc/os-release',
                ])
                os_version = os_string.decode().split('\n')
                for os_line in os_version:
                    if os_line.startswith('VERSION='):
                        break
                os_version = os_line.split('=')[1].strip('"') + ' _ssh'
            except subprocess.CalledProcessError:
                os_version = 'Unavailable'

        try:
            model = system_status['rpi_model']
            host_temperature = system_status['rpi_temperature']
        except (KeyError, UnboundLocalError):
            model = ''
            host_temperature = ''

        try:
            python_version = system_status['python_version']
        except (KeyError, UnboundLocalError):
            python_version = ''
        return_value['model'] = model
        return_value['host_temperature'] = host_temperature
        return_value['python_version'] = python_version
        return_value['os_version'] = os_version

        try:
            apt_up_time = system_status['last_apt_cache_change_unixtime']
            apt_up = datetime.datetime.fromtimestamp(apt_up_time).strftime('%Y-%m-%d')
        except UnboundLocalError:
            apt_up = ''
        #except TypeError as exception:
        #    print(exception)
        #    apt_up = ''
        #    print('{} - TypeError: "repr(apt_up_time)" = {}'.format(hostname, repr(apt_up_time)))
        return_value['apt_up'] = apt_up

        git = {}
        try:
            gittime = system_status['last_git_fetch_unixtime']
            try:
                git['PyExpLabSys'] = datetime.datetime.fromtimestamp(gittime['PyExpLabSys']).strftime('%Y-%m-%d')
                git['machines'] = datetime.datetime.fromtimestamp(gittime['machines']).strftime('%Y-%m-%d')
            except TypeError:
                # Legacy purposes only
                git['PyExpLabSys'] = datetime.datetime.fromtimestamp(gittime).strftime('%Y-%m-%d')
                git['machines'] = 'None'
        except TypeError:
            git['PyExpLabSys'] = 'None'
            git['machines'] = 'None'
        except  UnboundLocalError:
            git['PyExpLabSys'] = ''
            git['machines'] = ''
        return_value['git_pyexplabsys'] = git['PyExpLabSys']
        return_value['git_machines'] = git['machines']

    return return_value

class CheckHost(threading.Thread):
    """ Perfom the actual check """

    def __init__(self, hosts_queue, results_queue):
        threading.Thread.__init__(self)
        self.hosts = hosts_queue
        self.results = results_queue

    def run(self):
        suffixes = ["", ".fys.clients.local"]
        while not self.hosts.empty():
            host = self.hosts.get_nowait()
            try:
                attr = json.loads(host[5])
            except TypeError: # Happens if attr is empty
                attr = {}
                attr['git_pyexplabsys'] = ''
                attr['git_machines'] = ''
                attr['model'] = ''
                attr['python_version'] = ''
                attr['apt_up'] = ''
                attr['location'] = host[3]
                attr['purpose'] = host[4]
            for suffix in suffixes:
                host_is_up = host_status(host[1] + suffix, host[2])
                if host_is_up:
                    hostname = host[1] + suffix
                    break

            LOGGER.debug('host_is_up: ' + str(host_is_up))

            if host_is_up:
                username, password = credentials.get_user_and_password(hostname)
                uptime_val = uptime(hostname, host[2], username=username, password=password)
            else:
                uptime_val = {}
                uptime_val['up'] = ''
                uptime_val['load'] = ''
                try:
                    uptime_val['git_pyexplabsys'] = attr['git_pyexplabsys']
                    uptime_val['git_machines'] = attr['git_machines']
                except KeyError: # Legacy support
                    uptime_val['git_pyexplabsys'] = attr['git']
                    uptime_val['git_machines'] = 'None'
                uptime_val['host_temperature'] = ''
                uptime_val['model'] = attr['model']
                try:
                    uptime_val['apt_up'] = attr['apt_up']
                except KeyError:
                    uptime_val['apt_up'] = ''
                uptime_val['python_version'] = attr['python_version']

            uptime_val['db_id'] = host[0]
            uptime_val['hostname'] = host[1]
            uptime_val['up_or_down'] = host_is_up
            uptime_val['port'] = host[2]

            if uptime_val['load'] == 'Down':
                uptime_val['location'] = attr['location']
                uptime_val['purpose'] = attr['purpose']
                try:
                    uptime_val['git'] = attr['git']
                except KeyError:
                    uptime_val['git'] = ''
                try:
                    uptime_val['model'] = attr['model']
                except KeyError:
                    uptime_val['model'] = ''
                try:
                    uptime_val['apt_up'] = attr['apt_up']
                except KeyError:
                    uptime_val['apt_up'] = ''
            if not 'location' in uptime_val:
                uptime_val['location'] = '<i>' + host[3] + '</i>'
                uptime_val['purpose'] = '<i>' + host[4] + '</i>'
            self.results.put(uptime_val)

            self.hosts.task_done()

def main():
    """ Main function """
    hosts = queue.Queue()

    database = MySQLdb.connect(
        host=credentials.sql_host,
        user=credentials.user,
        passwd=credentials.passwd,
        db=credentials.db,
    )
    cursor = database.cursor()
    database.autocommit(True)

    query = 'select id, host, port, location, purpose, attr from host_checker';
    cursor.execute(query)
    results = cursor.fetchall()

    for result in results:
        hosts.put(result)
    LOGGER.debug('Size of hosts-select: ' + str(hosts.qsize()))
    results = queue.Queue()

    host_checkers = {}
    for i in range(0, 5): # number threads, high number will complete faster
        host_checkers[i] = CheckHost(hosts, results)
        host_checkers[i].start()
    hosts.join()

    while not results.empty():
        host = results.get()
        LOGGER.debug('Value of host: ' + str(host))
        query = ("update host_checker set time=now(), attr = '" +
                 json.dumps(host) + "' where id = " + str(host['db_id']))
        LOGGER.debug(query)
        cursor.execute(query)
    database.close()

if __name__ == "__main__":
    minutes_failed = 0
    while True:
        try:
            main()
        except MySQLdb.OperationalError as exception:  # OperationalError
            print("Got '{}'. Try again in 60 sec".format(exception))
            minutes_failed += 1
            # We allow up to 15 min downtime, before finally giving up
            if minutes_failed > 15:
                raise
        else:
            minutes_failed = 0
        time.sleep(60)
