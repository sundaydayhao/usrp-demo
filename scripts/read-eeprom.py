"""Back up USRP1 daughterboard EEPROMs; only sends EEPROM address-pointer writes.

Protocol and addresses follow Ettus UHD v4.10.0.0 fx2_ctrl.cpp and usrp1_impl.hpp.
No EEPROM data, board IDs, GPIO, or RF configuration are written.
"""
import datetime
import json
from pathlib import Path

import usb.backend.libusb1
import usb.core
import usb.util

root = Path(__file__).resolve().parents[1]
out = root / 'logs' / ('eeprom-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
out.mkdir()
backend = usb.backend.libusb1.get_backend(
    find_library=lambda _: r'C:\Program Files\UHD\bin\libusb-1.0.dll')
devices = list(usb.core.find(find_all=True, idVendor=0xfffe, idProduct=0x0002, backend=backend))
if len(devices) != 1:
    raise RuntimeError(f'Expected exactly one USRP1, found {len(devices)}')
dev = devices[0]
report = {'usb_serial': dev.serial_number, 'eeproms': {}}
try:
    for label, address in [('A-TX', 0x54), ('A-RX', 0x55), ('B-TX', 0x56), ('B-RX', 0x57)]:
        entry = {'i2c_address': hex(address)}
        try:
            data = bytearray()
            for offset in range(0, 256, 32):
                count = dev.ctrl_transfer(0x40, 0x08, address, 0, bytes([offset]), timeout=1500)
                if count != 1:
                    raise RuntimeError(f'Address pointer transfer returned {count}')
                chunk = bytes(dev.ctrl_transfer(0xc0, 0x81, address, 0, 32, timeout=1500))
                if len(chunk) != 32:
                    raise RuntimeError(f'Short EEPROM read: {len(chunk)} bytes')
                data.extend(chunk)
            (out / f'{label}.bin').write_bytes(data)
            entry.update(header_hex=data[:32].hex(' '), magic_valid=data[0] == 0xdb,
                         checksum_valid=sum(data[:32]) % 256 == 0,
                         stored_id=f'0x{int.from_bytes(data[1:3], "little"):04x}')
        except Exception as error:
            entry['error'] = str(error)
        report['eeproms'][label] = entry
        print(label, json.dumps(entry), flush=True)
finally:
    usb.util.dispose_resources(dev)
    (out / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('Backup directory:', out)
