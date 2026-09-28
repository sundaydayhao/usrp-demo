"""Read USB descriptors and FPGA readback registers via UHD's documented wire protocol."""
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
report = {'usb': {'vid': hex(dev.idVendor), 'pid': hex(dev.idProduct),
                  'serial': dev.serial_number, 'usb_version': hex(dev.bcdUSB),
                  'speed': getattr(dev, 'speed', None)}, 'interfaces': [], 'readback': []}
try:
    for config in dev:
        for interface in config:
            report['interfaces'].append({
                'number': interface.bInterfaceNumber, 'alt': interface.bAlternateSetting,
                'endpoints': [{'address': hex(ep.bEndpointAddress), 'max_packet': ep.wMaxPacketSize}
                              for ep in interface]})
    for trial in range(3):
        row = {'trial': trial}
        # Source: usrp1_iface.cpp peek32(), FPGA SPI slave 1, one MSB header.
        for register in (1, 2, 3, 4):
            data = bytes(dev.ctrl_transfer(0xc0, 0x82, 0x80 | register, 0x0120, 4, timeout=1500))
            if len(data) != 4:
                raise RuntimeError('Short FPGA readback')
            row[f'reg_{register}'] = f'0x{int.from_bytes(data, "big"):08x}'
        report['readback'].append(row)
        time.sleep(0.1)
finally:
    usb.util.dispose_resources(dev)
filename = 'hardware-status-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '.json'
(Path(__file__).resolve().parents[1] / 'logs' / filename).write_text(
    json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
