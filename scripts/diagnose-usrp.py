"""Check daughterboard identification, synthesizer locks, and RX data transport.

Does not write EEPROMs or start a TX stream. RX samples on an unrecognized
frontend only exercise the motherboard data path, not RF reception.
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
parser.add_argument('--rate', type=float, default=1e6, help='Requested RX samples per second per channel.')
parser.add_argument('--slots', nargs='+', choices=('A', 'B'), default=['A', 'B'],
                    help='Installed slots to test, e.g. --slots B for one board.')
options = parser.parse_args()
if not np.isfinite(options.rate) or options.rate <= 0:
    parser.error('Rate must be finite and positive.')
slots = options.slots
if len(slots) != len(set(slots)):
    parser.error('Each slot may be specified only once.')
subdevices = [f'{slot}:0' for slot in slots]
root = Path(__file__).resolve().parents[1]
out = root / 'logs' / ('diagnostic-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
out.mkdir()
usrp = uhd.usrp.MultiUSRP(options.args)
usrp.set_rx_subdev_spec(uhd.usrp.SubdevSpec(' '.join(subdevices)))
usrp.set_tx_subdev_spec(uhd.usrp.SubdevSpec(' '.join(subdevices)))
report = {'uhd': uhd.get_version_string(), 'selected_slots': slots,
          'device_args': options.args, 'clock_rate_configured_hz': usrp.get_master_clock_rate(),
          'boards': {}, 'tx_stream_started': False}
print(usrp.get_pp_string(), flush=True)
for ch, slot in enumerate(slots):
    board = {'rx_info': usrp.get_usrp_rx_info(ch), 'tx_info': usrp.get_usrp_tx_info(ch)}
    report['boards'][slot] = board
    for direction in ('rx', 'tx'):
        sensors = getattr(usrp, f'get_{direction}_sensor_names')(ch)
        span = getattr(usrp, f'get_{direction}_freq_range')(ch)
        item = {'sensors': sensors, 'freq_range_hz': [span.start(), span.stop()], 'tuning': []}
        board[direction] = item
        if 'lo_locked' not in sensors:
            item['status'] = 'frontend_not_initialized'
            continue
        for frequency in (1.55e9, 1.8e9, 2.05e9):
            if not span.start() <= frequency <= span.stop():
                continue
            getattr(usrp, f'set_{direction}_freq')(uhd.types.TuneRequest(frequency), ch)
            time.sleep(0.12)
            locked = getattr(usrp, f'get_{direction}_sensor')('lo_locked', ch).to_bool()
            item['tuning'].append({'requested_hz': frequency,
                                   'actual_hz': getattr(usrp, f'get_{direction}_freq')(ch),
                                   'lo_locked': locked})
        item['status'] = 'lock_pass' if item['tuning'] and all(t['lo_locked'] for t in item['tuning']) else 'lock_fail'
    usrp.set_rx_rate(options.rate, ch)
    if board['rx']['status'] != 'frontend_not_initialized':
        usrp.set_rx_freq(uhd.types.TuneRequest(1.8e9), ch)
        usrp.set_rx_gain(0, ch)
        if 'RX2' in usrp.get_rx_antennas(ch):
            usrp.set_rx_antenna('RX2', ch)
    print(slot, json.dumps(board), flush=True)

report['rx_transport'] = {'status': 'not_completed'}
(out / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
args = uhd.usrp.StreamArgs('fc32', 'sc16')
args.channels = list(range(len(slots)))
stream = usrp.get_rx_stream(args)
buffer = np.zeros((len(slots), 8192), dtype=np.complex64)
metadata = uhd.types.RXMetadata()
command = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
command.stream_now = True  # USRP1 has no PPS timing facility.
capture = []
count = 0
errors = []
started = time.monotonic()
try:
    stream.issue_stream_cmd(command)
    while time.monotonic() - started < 5:
        received = stream.recv(buffer, metadata, 1.0)
        if metadata.error_code != uhd.types.RXMetadataErrorCode.none:
            errors.append(str(metadata.strerror()))
        if received:
            if count < 65536:
                capture.append(buffer[:, :min(received, 65536-count)].copy())
            count += received
finally:
    stop = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
    stream.issue_stream_cmd(stop)
report['rx_transport'] = {'channels': subdevices, 'rate_per_channel': usrp.get_rx_rate(0),
                          'samples_per_channel': count, 'elapsed_seconds': time.monotonic()-started,
                          'metadata_errors': errors,
                          'limitation': 'USRP1 lacks hardware timestamps and robust loss accounting; unknown frontends do not validate RF reception.'}
if capture:
    data = np.concatenate(capture, axis=1)
    np.savez_compressed(out / 'rx-sample.npz', iq=data, sample_rate=usrp.get_rx_rate(0))
    report['rx_transport']['signal_stats'] = [
        {'slot': slot, 'rms': float(np.sqrt(np.mean(np.abs(data[ch])**2))),
         'peak': float(np.max(np.abs(data[ch]))), 'nonzero': int(np.count_nonzero(data[ch])),
         'std': float(np.std(data[ch]))} for ch, slot in enumerate(slots)]
report['identification_and_lo_checks_passed'] = all(board[direction]['status'] == 'lock_pass'
                                   for board in report['boards'].values() for direction in ('rx','tx'))
report['rf_performance_verified'] = False  # Requires an external calibrated signal/loopback setup.
(out / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report['rx_transport'], indent=2), flush=True)
print('Report:', out, flush=True)
raise SystemExit(0 if report['identification_and_lo_checks_passed'] and count > 0 and not errors else 2)
