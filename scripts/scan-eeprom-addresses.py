"""Read-only response survey of the USRP1 EEPROM address range.

Uses only I2C reads, with no EEPROM address-pointer or data writes. Returned
bytes start at each device's current pointer and must not be treated as an
EEPROM header or used to infer that two responses are distinct physical chips.
"""
import datetime
import json
import time
from pathlib import Path

import usb.backend.libusb1
import usb.core
import usb.util

backend = usb.backend.libusb1.get_backend(
    find_library=lambda _: r'C:\Program Files\UHD\bin\libusb-1.0.dll')
devices = list(usb.core.find(find_all=True, idVendor=0xfffe, idProduct=2,
                           backend=backend))
if len(devices) != 1:
    raise RuntimeError(f'Expected one USRP1, got {len(devices)}')
dev = devices[0]
results = []
root = Path(__file__).resolve().parents[1]
filename = 'eeprom-address-responses-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '.json'
try:
    for trial in range(3):
        for address in range(0x50, 0x58):
            row = {'trial': trial, 'address': hex(address)}
            try:
                data = bytes(dev.ctrl_transfer(0xc0, 0x81, address, 0, 8,
                                               timeout=1500))
                row.update(read_completed=len(data) == 8, length=len(data),
                           current_pointer_data_hex=data.hex(' '))
            except usb.core.USBError as error:
                row['error'] = str(error)
            results.append(row)
            print(json.dumps(row), flush=True)
            time.sleep(0.1)
finally:
    usb.util.dispose_resources(dev)
    report = {'operation': 'I2C read only; no pointer or EEPROM data writes',
              'results': results}
    (root / 'logs' / filename).write_text(json.dumps(report, indent=2),
                                         encoding='utf-8')
    print('Report:', root / 'logs' / filename, flush=True)
