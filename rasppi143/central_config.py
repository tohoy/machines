# This is a config file for the monitoring of the Vortes gas centrals in B307 basement.
# Access as central[1]['settings']['port'] or central[1]['codenames'][3] for example..
CENTRAL = {
    # Central 1
    1: {
        'name': 'B307_basement_vortex_1',
        'codenames': {# List of (channel, codename)
            1: 'B307_gasalarm_fireloop_basement1',
            2: 'B307_gasalarm_H2_913',
            3: 'B307_gasalarm_O2_913',
            4: 'B307_gasalarm_CO_913',
            #5: 'B307_gasalarm_O2_938',
            #6: 'B307_gasalarm_O2_945',
            #7: 'B307_gasalarm_O2_946',
            #8: 'B307_gasalarm_O2_954',
            #9: 'B307_gasalarm_O2_957',
            #10: 'B307_gasalarm_O2_960',
            #11: 'B307_gasalarm_O2_964',
        },
        'settings': {# USB settings
            'port': '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FT0BVMK5-if00-port0',#'/dev/ttyUSB2',
            'slave': 1,
        },
    },
    # Central 2
    2: {
        'name': 'B307_basement_vortex_2',
        'codenames': {# List of (channel, codename)
            1: 'B307_gasalarm_O2_929',
            2: 'B307_gasalarm_H2_926',
            3: 'B307_gasalarm_O2_926',
            4: 'B307_gasalarm_O2_927',
        },
        'settings': {# USB settings
            'port': '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FT700F0A-if00-port0',#'/dev/ttyUSB1',
            'slave': 1,
        },
    },
    # Central 3
    3: {
        'name': 'B307_basement_vortex_3',
        'codenames': {# List of (channel, codename)
            1: 'B307_gasalarm_fireloop_basement3',
            2: 'B307_gasalarm_H2_908',
            3: 'B307_gasalarm_CO_908',
            4: 'B307_gasalarm_CO2_908',
            5: 'B307_gasalarm_H2_972',
            6: 'B307_gasalarm_CO_972',
            7: 'B307_gasalarm_CO2_972',
            8: 'B307_gasalarm_H2_948',
            9: 'B307_gasalarm_CO_948',
            10: 'B307_gasalarm_CO2_948',
        },
        'settings': {# Port settings
            'port': '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FT0EJ92A-if00-port0',#'/dev/ttyUSB0',
            'slave': 1,
        },
    },
}
