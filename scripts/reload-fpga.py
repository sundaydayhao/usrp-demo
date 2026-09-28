"""Invalidate only the volatile USRP1 FPGA hash, then use the official loader.

UHD v4.10.0.0 fx2_ctrl.hpp defines USRP_HASH_SLOT_1_ADDR = 0xe1f0;
fx2_ctrl.cpp uses FX2 RAM request 0xa0 to read/write this four-byte slot.
This does not write EEPROM, reset the CPU, or modify the firmware hash.
"""
import json
import subprocess
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
try:
    old = bytes(dev.ctrl_transfer(0xc0, 0xa0, 0xe1f0, 0, 4, timeout=1500))
    if len(old) != 4:
        raise RuntimeError('Cannot read the volatile FPGA hash')
    written = dev.ctrl_transfer(0x40, 0xa0, 0xe1f0, 0, bytes(4), timeout=1500)
    if written != 4:
        raise RuntimeError('Short volatile FPGA hash write')
    current = bytes(dev.ctrl_transfer(0xc0, 0xa0, 0xe1f0, 0, 4, timeout=1500))
    if current != bytes(4):
        raise RuntimeError('Volatile FPGA hash clear failed')
    print(json.dumps({'previous_volatile_hash': old.hex(), 'cleared_hash': current.hex()}), flush=True)
finally:
    usb.util.dispose_resources(dev)
result = subprocess.run([r'C:\Program Files\UHD\bin\uhd_usrp_probe.exe', '--args', 'type=usrp1'],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
log = Path(__file__).resolve().parents[1] / 'logs' / 'usrp-probe-after-fpga-reload.txt'
log.write_bytes(result.stdout)
print(result.stdout.decode('utf-8', errors='replace'), flush=True)
raise SystemExit(result.returncode)
