"""Receive selected cellular-band windows sequentially with the official UHD tool.

RX only. Keeps the user's explicit 64 MHz clock assumption. The frequency list
is a set of candidate windows, not a verified Shenzhen transmitter directory.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--frequencies-mhz', type=float, nargs='+',
                    default=[1815, 1840, 1865, 1890, 1905, 2017.5])
parser.add_argument('--slots', nargs='+', choices=['A', 'B'], default=['A', 'B'])
parser.add_argument('--gain', type=float, default=60)
parser.add_argument('--rate', type=float, default=2e6)
parser.add_argument('--duration', type=float, default=2)
options = parser.parse_args()
if not all(1500 <= f <= 2100 for f in options.frequencies_mhz):
    parser.error('Keep all requested centers within the RFX1800 RF range.')
if not 0 <= options.gain <= 70 or not 0 < options.duration <= 10 or not 0 < options.rate <= 4e6:
    parser.error('Invalid bounded receive parameters.')
out = ROOT / 'logs' / ('shenzhen-rx-' + dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
out.mkdir(parents=True)
uhd_root = Path('C:/Program Files/UHD')
exe = uhd_root / 'lib/uhd/examples/rx_samples_to_file.exe'
env = os.environ.copy()
env['PATH'] = str(uhd_root / 'bin') + os.pathsep + env['PATH']
env['UHD_IMAGES_DIR'] = str(uhd_root / 'share/uhd/images')
manifest = {
    'created_local': dt.datetime.now().astimezone().isoformat(),
    'device_args': 'type=usrp1,mcr=64e6',
    'actual_clock_verified': False,
    'clock_note': '64 MHz configured per user; earlier scope reading was 52 MHz. Frequency and sample-rate values are nominal.',
    'antenna': 'TX/RX', 'tx_stream_started': False,
    'format': 'little-endian int16 I,Q interleaved (sc16)',
    'frequency_windows_are_candidates_not_confirmed_transmitters': True,
    'captures': [],
}
manifest_path = out / 'manifest.json'
def save():
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
def number(log, pattern):
    match = re.search(pattern, log)
    return float(match.group(1)) if match else None
save()
print(f'OUTPUT={out}', flush=True)
for frequency in options.frequencies_mhz:
    for slot in options.slots:
        name = f'{slot}-{frequency:g}MHz-g{options.gain:g}'
        raw = out / (name + '.dat')
        log_path = out / (name + '.txt')
        command = [str(exe), '--args', manifest['device_args'], '--subdev', slot + ':0',
                   '--channels', '0', '--freq', str(frequency * 1e6),
                   '--rate', str(options.rate), '--gain', str(options.gain),
                   '--ant', 'TX/RX', '--duration', str(options.duration),
                   '--file', str(raw), '--type', 'short', '--stats', '--setup', '1']
        record = {'slot': slot, 'requested_center_mhz': frequency, 'requested_gain_db': options.gain,
                  'requested_rate_sps': options.rate, 'requested_duration_s': options.duration,
                  'raw_file': str(raw), 'log_file': str(log_path), 'command': command,
                  'started_local': dt.datetime.now().astimezone().isoformat()}
        start = time.monotonic()
        with log_path.open('w', encoding='utf-8') as logfile:
            try:
                result = subprocess.run(command, env=env, stdout=logfile, stderr=subprocess.STDOUT, timeout=25)
                record['exit_code'] = result.returncode
            except subprocess.TimeoutExpired:
                record['exit_code'] = None
                record['timed_out'] = True
        record['process_elapsed_s'] = time.monotonic() - start
        log = log_path.read_text(encoding='utf-8', errors='replace')
        record.update({
            'reported_rate_msps': number(log, r'Actual RX Rate:\s+([\d.]+)'),
            'reported_center_mhz': number(log, r'Actual RX Freq:\s+([\d.]+)'),
            'reported_gain_db': number(log, r'Actual RX Gain:\s+([\d.]+)'),
            'reported_receive_elapsed_s': number(log, r'Received \d+ samples in ([\d.]+) seconds'),
            'lo_wait_passed': bool(re.search(r'Waiting for "lo_locked":.* locked\.', log)),
            'overflow_indication': 'overflow indication' in log,
            'packet_D_indications': sum(len(m) for m in re.findall(r'D{2,}', log)),
            'bytes': raw.stat().st_size if raw.exists() else 0,
        })
        record['complex_samples'] = record['bytes'] // 4
        manifest['captures'].append(record)
        save()
        print(json.dumps({k: record[k] for k in ['slot', 'requested_center_mhz', 'exit_code', 'lo_wait_passed', 'complex_samples', 'overflow_indication']}, ensure_ascii=False), flush=True)
        time.sleep(0.3)
manifest['completed_local'] = dt.datetime.now().astimezone().isoformat()
save()
print(f'MANIFEST={manifest_path}', flush=True)
