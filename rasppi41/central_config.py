# This is a config file for the monitoring of the Vortes gas centrals on B307 2nd floor.
# Access as central[1]['settings']['port'] or central[1]['codenames'][3] for example..
CENTRAL = {
    # Central 1
    1: {
        'name': 'B307_209_vortex_1',
        'codenames': {# List of (channel, codename)
            1: 'B307_gasalarm_H2_201',
            2: 'B307_gasalarm_CO_201',
            3: 'B307_gasalarm_CO2_201',
            4: 'B307_gasalarm_H2_205',
            5: 'B307_gasalarm_CO_205',
            6: 'B307_gasalarm_CO2_205',
            7: 'B307_gasalarm_H2_209',
            8: 'B307_gasalarm_CO_209',
            9: 'B307_gasalarm_fireloop_2ndfloor',
            10: 'B307_gasalarm_CO2_209',
            11: 'B307_gasalarm_CO2_215',
        },
        'settings': {# USB settings
            'port': '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_AU0586I5-if00-port0',
            'slave': 1,
        },
    },
}
