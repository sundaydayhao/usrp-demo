"""Repeat only EEPROM header reads, without changing stored bytes."""
import datetime
import json
import time
from pathlib import Path
import usb.backend.libusb1
import usb.core
import usb.util

backend = usb.backend.libusb1.get_backend(
    find_library=lambda _: r'C:\Program Files\UHD\bin\libusb-1.0.dll')
devices = list(usb.core.find(find_all=True, idVendor=0xfffe, idProduct=2, backend=backend))
if len(devices) != 1:
    raise RuntimeError(f'Expected one USRP1, got {len(devices)}')
dev = devices[0]
results = []
try:
    for trial in range(5):
        for address in (0x54, 0x55, 0x56, 0x57):
            row = {'trial': trial, 'address': hex(address), 'stage': 'pointer'}
            try:
                written = dev.ctrl_transfer(0x40, 8, address, 0, bytes([0]), timeout=1500)
                if written != 1:
                    raise RuntimeError(f'Short address transfer: {written}')
                row['stage'] = 'read'
                data = bytes(dev.ctrl_transfer(0xc0, 0x81, address, 0, 32, timeout=1500))
                row.update(length=len(data), header_hex=data.hex(' '),
                           valid=len(data) == 32 and data[0] == 0xdb and sum(data) % 256 == 0)
            except Exception as error:
                row['error'] = str(error)
            results.append(row)
            print(json.dumps(row), flush=True)
            time.sleep(0.1)
finally:
    usb.util.dispose_resources(dev)
    filename = 'eeprom-stability-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '.json'
    (Path(__file__).resolve().parents[1] / 'logs' / filename).write_text(
        json.dumps(results, indent=2), encoding='utf-8')
