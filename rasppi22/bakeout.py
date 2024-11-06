"""Program for showing and controling the bakeout box rasppi22
conencted to stm312"""
# -*- coding: utf-8 -*-
import time
import sys
import threading
import curses
import wiringpi as wp
from importlib import reload
import datetime

#from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket


class CursesTui(threading.Thread):
    """ Tui for controlling the bakeout boxx"""
    def __init__(self, baker_instance,stdscr):
        threading.Thread.__init__(self)
        self.baker = baker_instance
        self.watchdog = baker_instance.watchdog
        self.screen=stdscr # get this from the curses wrapper
        #self.screen = curses.initscr()
        #curses.noecho()
        #curses.cbreak()
        curses.curs_set(False)
        #self.screen.keypad(1)
        self.screen.nodelay(1)

    def run(self):
        while not self.baker.quit:
            text_line=0
            self.screen.addstr(text_line := text_line + 2, 2, 'Running')
            status_line=text_line

            self.screen.addstr(text_line := text_line + 2, 2,
                               "Watchdog TTL: {0:.0f}  ".format(
                    self.watchdog.time_to_live))
            self.screen.addstr(text_line := text_line + 1, 2,
                               "Watchdog Timer: {0:.1f}".format(
                    time.time() - self.watchdog.timer))
            self.screen.addstr(text_line := text_line + 1, 2,
                               "Watchdog safe: {}    ".format(
                    self.watchdog.watchdog_safe))

            self.screen.addstr(text_line := text_line + 2, 2,
                               'Current channel status:')
            text_line= text_line + 1
            for i in range(1, 7):
                self.screen.addstr(text_line, 6*i,
                                   str(wp.digitalRead(i)))

            self.screen.addstr(text_line := text_line + 3, 2,
                               "Channel duty cycles")
            text_line= text_line + 1
            for i in range(1, 7):
                self.screen.addstr(text_line, 6*i,
                                   str(round(self.baker.dutycycles[i-1],2)))
            
            if self.baker.run_ramp == True:
                time_tuple_back = time.localtime(self.baker.ramp.end_time)
                date_str = time.strftime("%Y-%m-%d %H:%M:%S", time_tuple_back)
                
                seconds_diff=self.baker.ramp.end_time-time.time()
                if self.baker.ramp.finished:
                    seconds_diff=-seconds_diff
                    
                time_diff = datetime.timedelta(seconds=seconds_diff)

                # Extract days, hours, minutes, and seconds
                days = time_diff.days
                hours, remainder = divmod(time_diff.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)

                # Print the result in a user-friendly format
                if self.baker.ramp.finished:
                    ramp_status_text=f'Ramp finished on {date_str}, which is {days} days, {hours} hours, {minutes} minutes, and {seconds} seconds ago'
                else:
                    ramp_status_text=f'Ramp running until {date_str}, which is {days} days, {hours} hours, {minutes} minutes, and {seconds} seconds from now'
                
                self.screen.addstr(text_line := text_line + 2, 2, ramp_status_text)
                self.screen.addstr(text_line := text_line + 1, 2, f'Currently requested dutycycles:')
                self.screen.addstr(text_line := text_line + 1, 7, str(self.baker.ramp.present()))
            else:
                text_line= text_line + 1
                for i in range(3): # clear the lines created for ramping
                    self.screen.move(text_line := text_line + 1, 0)
                    self.screen.clrtoeol()
                #self.screen.addstr(text_line := text_line + 1, 2,
                #                   "                                ")  
            
            self.screen.addstr(text_line := text_line + 3, 2,
                               "l: load ramp from ramp.py, ")
            self.screen.addstr(text_line := text_line + 1, 2,
                               "c: clear from ramp state(checks if done)")
            self.screen.addstr(text_line := text_line + 1, 2,
                               "s: forcefully stop the ramp       ")
            self.screen.addstr(text_line := text_line + 1, 2,
                               "q: quit program       ")
            n = self.screen.getch()

            self.screen.addstr(text_line := text_line + 1, 2,
                               "Last key stroke: {}     ".format(n))

            if n == ord('1'):
                self.baker.modify_dutycycle(1, 0.1)
            elif n == ord('!'):
                self.baker.modify_dutycycle(1, -0.1)
            elif n == ord('2'):
                self.baker.modify_dutycycle(2, 0.1)
            elif n == ord('"'):
                self.baker.modify_dutycycle(2, -0.1)
            elif n == ord('3'):
                self.baker.modify_dutycycle(3, 0.1)
            elif n == ord('#'):
                self.baker.modify_dutycycle(3, -0.1)
            elif n == ord('4'):
                self.baker.modify_dutycycle(4, 0.1)
            elif n == 194: #... '¤':
                self.baker.modify_dutycycle(4, -0.1)
            elif n == ord('5'):
                self.baker.modify_dutycycle(5, 0.1)
            elif n == ord('%'):
                self.baker.modify_dutycycle(5, -0.1)
            elif n == ord('6'):
                self.baker.modify_dutycycle(6, 0.1)
            elif n == ord('&'):
                self.baker.modify_dutycycle(6, -0.1)
            elif n == ord('l'):
                self.baker.load_ramp()
            elif n == ord('c'):
                if self.baker.ramp.finished:
                    self.baker.run_ramp=False
            elif n == ord('s'):
                self.baker.run_ramp=False
                self.baker.dutycycles = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            elif n == ord('q'):
                self.baker.quit = True
                self.screen.addstr(status_line, 2, 'Quitting....')

            self.screen.refresh()
            time.sleep(0.2)

    def stop(self):
        """An attempt of a clean exit"""
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()



class Watchdog(threading.Thread):
    """ timer for ensuring that 100% power
    is not posible even if the program fails"""
    def __init__(self):
        threading.Thread.__init__(self)
        wp.pinMode(0, 1)
        self.timer = time.time()
        self.cycle_time = 120
        self.safety_margin = 3
        self.watchdog_safe = True
        self.quit = False
        self.time_to_live = 0
        self.reactivate()#Watchdog is initially activated
        self.reset_ttl()

    def reset_ttl(self):
        """ reseting the countdown"""
        self.time_to_live = 100

    def decrease_ttl(self):
        """ decrease the time to live with one"""
        self.time_to_live = self.time_to_live - 1

    def reactivate(self):
        """ Reactiviating """
        wp.digitalWrite(0, 1)
        time.sleep(0.1)
        wp.digitalWrite(0, 0)
        return None

    def run(self):
        while not self.quit:
            self.decrease_ttl()
            if self.time_to_live < 0:
                self.quit = True
            dt = time.time() - self.timer
            allowed_time = self.cycle_time - self.safety_margin
            reactivate_time = self.cycle_time + self.safety_margin
            if dt < allowed_time:
                self.watchdog_safe = True
            else:
                self.watchdog_safe = False
            if dt > reactivate_time:
                self.reactivate()
                self.timer = time.time()
            time.sleep(0.2)
        self.watchdog_safe = False


class Bakeout(threading.Thread):
    """ Class for controling the 6 port of the bakeout box"""
    def __init__(self, watchdog, datasocket):
        threading.Thread.__init__(self)
        self.watchdog = watchdog
        self.datasocket = datasocket
        self.quit = False
        for i in range(0, 7): #Set GPIO pins to output
            wp.pinMode(i, 1)
        self.dutycycles = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.run_ramp = False

    def activate(self, pin):
        """ set pin/port to On"""
        if self.watchdog.watchdog_safe:
            wp.digitalWrite(pin, 1)
        else:
            wp.digitalWrite(pin, 0)

    def deactivate(self, pin):
        """Set pin/port to Off"""
        wp.digitalWrite(pin, 0)

    def modify_dutycycle(self, channel, amount):
        """ change the power on time with amount on channel"""
        self.dutycycles[channel-1] =  self.dutycycles[channel-1] + amount
        if  self.dutycycles[channel-1] > 1:
            self.dutycycles[channel-1] = 1.0
        if self.dutycycles[channel-1] < 0.01:
            self.dutycycles[channel-1] = 0.0
        return  self.dutycycles[channel-1]

    def set_dutycycle(self, channel, value):
        """Set a single dutycycle
        input channel number fx 5
        input new value fx 0.2"""
        self.dutycycles[channel-1] = value
        if  self.dutycycles[channel-1] > 1:
            self.dutycycles[channel-1] = 1.0
        if self.dutycycles[channel-1] < 0.01:
            self.dutycycles[channel-1] = 0.0
        return  self.dutycycles[channel-1]


    def set_all_dutycycles(self, value_list):
        """ set new values in dutycyles"""
        if len(value_list) == 6:
            for index, value in enumerate(value_list):
                channel = index + 1
                self.set_dutycycle(channel, value)
        return self.dutycycles

    def load_ramp(self,):
        """ load a ramp defined in external script"""
        import ramp
        reload(ramp)
        self.ramp = ramp.ramp()
        self.run_ramp = True
        
    def run(self):
        totalcycles = 10

        self.quit = False
        cycle = 0
        while not self.quit:
            self.watchdog.reset_ttl()
            self.datasocket.set_point_now('stm312_bakeoutbox', self.dutycycles)
            if self.run_ramp == True:
                self.set_all_dutycycles(self.ramp.present())
                    
            try:
                for i in range(1, 7):
                    if (1.0*cycle/totalcycles) < self.dutycycles[i-1]:
                        self.activate(i)
                    else:
                        self.deactivate(i)
                cycle = cycle + 1
                cycle = cycle % totalcycles
                time.sleep(1)
            except:
                self.quit = True
                print("Program terminated by user")
                print(sys.exc_info()[0])
                print(sys.exc_info()[1])
                print(sys.exc_info()[2])
                for i in range(0, 7):
                    self.deactivate(i)


def main(stdscr):
    """ main function"""
    wp.wiringPiSetup()
    watchdog = Watchdog()
    watchdog.daemon = True
    watchdog.start()
    time.sleep(1)
    datasocket = DateDataPullSocket(
        'stm312_bakeoutbox',
        ['stm312_bakeoutbox'],
        timeouts=[1.0])
    datasocket.start()
    baker = Bakeout(watchdog, datasocket)
    baker.start()
    tui = CursesTui(baker,stdscr)
    #tui.daemon = True
    tui.start()
    while not baker.quit:
        time.sleep(1)
    watchdog.quit = True
    time.sleep(2)
    baker.quit = True

if __name__ == '__main__':
    curses.wrapper(main) # the wrapper helps ensure that "If the application raises an exception, this function will restore the terminal to a sane state before re-raising the exception and generating a traceback"
