"""Repeat RX/TX lock reads without creating RX or TX streams or writing EEPROMs."""
import argparse
import datetime
import json
import time
from pathlib import Path

import uhd


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--args', default='type=usrp1', help='UHD device arguments; use type=usrp1,mcr=52e6 for the measured external clock.')
options = parser.parse_args()
root = Path(__file__).resolve().parents[1]
output = root / 'logs' / ('lo-stability-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '.json')
usrp = uhd.usrp.MultiUSRP(options.args)
usrp.set_rx_subdev_spec(uhd.usrp.SubdevSpec('A:0 B:0'))
usrp.set_tx_subdev_spec(uhd.usrp.SubdevSpec('A:0 B:0'))
paths = [(slot, ch, direction) for ch, slot in enumerate(('A', 'B')) for direction in ('rx', 'tx')]
report = {
    'uhd': uhd.get_version_string(),
    'device_args': options.args,
    'clock_rate_configured_hz': usrp.get_master_clock_rate(),
    'clock_frequency_measured': False,
    'tx_stream_started': False,
    'rx_stream_started': False,
    'boards': {slot: {direction: getattr(usrp, f'get_usrp_{direction}_info')(ch)
                     for direction in ('rx', 'tx')} for ch, slot in enumerate(('A', 'B'))},
    'settle_seconds': 0.25,
    'poll_interval_seconds': 0.1,
    'rounds': [],
}


def save():
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')


try:
    for trial, frequencies in enumerate(((1.55e9, 1.8e9, 2.05e9), (2.05e9, 1.8e9, 1.55e9), (1.8e9,)), start=1):
        for frequency in frequencies:
            row = {'trial': trial, 'requested_hz': frequency, 'paths': {}}
            for slot, ch, direction in paths:
                name = f'{slot}-{direction.upper()}'
                if 'lo_locked' not in getattr(usrp, f'get_{direction}_sensor_names')(ch):
                    raise RuntimeError(f'{name}: no lo_locked sensor')
                getattr(usrp, f'set_{direction}_freq')(uhd.types.TuneRequest(frequency), ch)
                row['paths'][name] = {
                    'configured_hz': getattr(usrp, f'get_{direction}_freq')(ch), 'polls': []}
            time.sleep(0.25)
            started = time.monotonic()
            for poll in range(20):
                for slot, ch, direction in paths:
                    item = row['paths'][f'{slot}-{direction.upper()}']
                    locked = getattr(usrp, f'get_{direction}_sensor')('lo_locked', ch).to_bool()
                    item['polls'].append({'seconds': time.monotonic() - started, 'locked': locked})
                time.sleep(0.1)
            for item in row['paths'].values():
                item['locked_count'] = sum(p['locked'] for p in item['polls'])
                item['total_count'] = len(item['polls'])
            report['rounds'].append(row)
            save()
            print(json.dumps({'trial': trial, 'frequency_mhz': frequency / 1e6,
                              'locks': {name: f"{item['locked_count']}/{item['total_count']}"
                                        for name, item in row['paths'].items()}}), flush=True)
except Exception as error:
    report['error'] = repr(error)
    raise
finally:
    save()
    print('Report:', output, flush=True)
