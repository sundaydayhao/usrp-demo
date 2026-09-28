"""Test USRP1 FPGA-to-host RX transport using its internal counter, without RF TX.

UHD v4.10.0.0 usrp_std.v defines FR_MODE (13) bit 1 as the RX counter.
The counter is restored to off and streaming stopped in finally.
"""
import argparse
import datetime
import json
import time
from pathlib import Path
import numpy as np
import uhd

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--args', default='type=usrp1', help='UHD device arguments, e.g. type=usrp1,mcr=52e6.')
options = parser.parse_args()
usrp = uhd.usrp.MultiUSRP(options.args)
usrp.set_rx_subdev_spec(uhd.usrp.SubdevSpec('A:0'))
usrp.set_rx_rate(1e6)
args = uhd.usrp.StreamArgs('fc32', 'sc16')
args.channels = [0]
stream = usrp.get_rx_stream(args)
buffer = np.zeros((1, 8192), dtype=np.complex64)
metadata = uhd.types.RXMetadata()
report = {'mode': 'FPGA internal counter, not RF samples', 'sample_rate': usrp.get_rx_rate(),
          'device_args': options.args, 'clock_rate_configured_hz': usrp.get_master_clock_rate(),
          'samples': 0, 'errors': [], 'first_samples': [], 'tx_stream_started': False}
try:
    usrp.set_user_register(13, 2)
    command = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
    command.stream_now = True
    stream.issue_stream_cmd(command)
    started = time.monotonic()
    while time.monotonic() - started < 3:
        count = stream.recv(buffer, metadata, 0.5)
        if metadata.error_code != uhd.types.RXMetadataErrorCode.none:
            report['errors'].append(str(metadata.strerror()))
        if count and not report['first_samples']:
            report['first_samples'] = [[float(x.real), float(x.imag)] for x in buffer[0, :min(count, 12)]]
        report['samples'] += count
finally:
    stop = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
    try:
        stream.issue_stream_cmd(stop)
    finally:
        usrp.set_user_register(13, 0)
        report['counter_mode_restored_off'] = True
print(json.dumps(report, indent=2))
filename = 'fpga-counter-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '.json'
(Path(__file__).resolve().parents[1] / 'logs' / filename).write_text(json.dumps(report, indent=2), encoding='utf-8')
raise SystemExit(0 if report['samples'] > 0 and not report['errors'] else 2)
