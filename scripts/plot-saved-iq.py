"""Plot saved TX/RX captures without accessing the USRP.

Input: little-endian signed int16, interleaved I,Q. Frequency/time axes use
the requested 64 MHz clock assumption, 250 kS/s, and 1800 MHz tuning setting.
All full FFT windows are retained, including transients and suspect data.
"""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--comparison', choices=('b-gain', 'a-b'), default='b-gain',
                    help='Compare B gain settings, or the reseated A with B at 40 dB.')
options = parser.parse_args()
FS = 250000.0
FC = 1800000000.0
NFFT = 4096
HOP = NFFT // 2
SOURCES = [
    ('0 dB', '#1478a6', ROOT / 'logs/antenna-64MHz-B-TXRX-g0-20260928-211550.dat', 3.004949),
    ('40 dB', '#d76c18', ROOT / 'logs/antenna-64MHz-B-TXRX-g40-20260928-211516.dat', 5.001313),
]
OUT = ROOT / 'plots' / 'iq-spectrum-20260928-211516'
TITLE = 'B 槽 · TX/RX 接口 — 保存 IQ 的频谱'
MAP_TITLE = 'B 槽 · TX/RX 接口 — IQ 时频图'
SUBTITLE = '软件中心频率 1800 MHz  |  采样率 250 kS/s  |  0 dB 与 40 dB 增益录制'
COMPARISON_NOTE = '录制包含包序号/溢出提示；不同时间的两次录制不能用于校准增益，纵轴也不是 dBm。'
TIME_NOTE = '采样率采用 250 kS/s；文件对应约 2.425 / 4.047 秒样本，实际录制历时约 3 / 5 秒。'
CSV_LABELS = ['gain0', 'gain40']
GAINS = [0, 40]
if options.comparison == 'a-b':
    SOURCES = [
        ('A 槽 · 40 dB', '#1478a6', ROOT / 'logs/A-reseat-64MHz-TXRX-g40-20260928-212612.dat', 5.001286),
        ('B 槽 · 40 dB', '#d76c18', ROOT / 'logs/antenna-64MHz-B-TXRX-g40-20260928-211516.dat', 5.001313),
    ]
    OUT = ROOT / 'plots' / 'iq-spectrum-A-20260928-212612'
    TITLE = 'A 槽 IQ 频谱 — 与 B 槽同增益录制对比'
    MAP_TITLE = 'A 槽与 B 槽 — TX/RX 接口 IQ 时频图'
    SUBTITLE = '软件中心频率 1800 MHz  |  采样率 250 kS/s  |  均为 40 dB 增益、TX/RX 接口'
    COMPARISON_NOTE = 'A、B 为不同时间的录制；均有包序号/溢出提示，比较结果不能替代射频接收校验。'
    TIME_NOTE = '每份文件均有 1,011,712 个 IQ 采样；按 250 kS/s 累计约 4.047 秒，录制历时约 5 秒。'
    CSV_LABELS = ['A_gain40', 'B_gain40']
    GAINS = [40, 40]
OUT.mkdir(parents=True, exist_ok=True)
font_path = Path('C:/Windows/Fonts/msyh.ttc')
if font_path.exists():
    font_manager.fontManager.addfont(str(font_path))
    plt.rcParams['font.family'] = font_manager.FontProperties(fname=str(font_path)).get_name()
plt.rcParams.update({'axes.unicode_minus': False, 'font.size': 10,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.labelcolor': '#253344', 'text.color': '#253344',
                     'xtick.color': '#455469', 'ytick.color': '#455469',
                     'savefig.facecolor': 'white'})
window = np.hanning(NFFT + 1)[:-1]  # Periodic Hann.
window_energy = np.sum(window ** 2)
frequency = np.fft.fftshift(np.fft.fftfreq(NFFT, 1.0 / FS))
floor = np.finfo(float).tiny
datasets = []
summary = {
    'comparison': options.comparison,
    'configured_master_clock_hz': 64e6,
    'configured_center_frequency_hz': FC,
    'configured_sample_rate_hz': FS,
    'actual_rf_frequency_verified': False,
    'source_format': 'sc16, little-endian int16, interleaved I then Q',
    'normalization': 'Each I/Q component divided by 32768; a unit-amplitude complex tone has 0 dBFS total power. No dBm calibration.',
    'method': 'Two-sided periodogram, periodic Hann, each frame mean removed, 50% overlap. Arithmetic mean PSD and uncorrected median PSD shown separately. No frames clipped or rejected.',
    'nfft': NFFT, 'hop_samples': HOP,
    'bin_spacing_hz': FS / NFFT,
    'hann_enbw_hz': FS * window_energy / np.sum(window) ** 2,
    'limitations': [
        'User requested 64 MHz assumption; earlier user measurement was 52 MHz. Axes are nominal.',
        'Both captures reported overflow/out-of-sequence indications; file sample indices do not preserve wall-clock gaps.',
        'Captures at different times are not a calibrated gain comparison.',
        'DC removed per frame; center bin is not evidence of a radio signal.',
        'An incomplete final FFT window is omitted; no complete window is rejected.',
    ],
    'captures': [],
}

for source_index, (label, color, path, elapsed) in enumerate(SOURCES):
    raw_bytes = path.read_bytes()
    if len(raw_bytes) % 4:
        raise ValueError(f'Incomplete complex int16 sample in {path}')
    iq = np.frombuffer(raw_bytes, dtype='<i2').reshape(-1, 2)
    z = (iq[:, 0].astype(np.float64) + 1j * iq[:, 1].astype(np.float64)) / 32768.0
    frames = np.lib.stride_tricks.sliding_window_view(z, NFFT)[::HOP]
    centered = frames - frames.mean(axis=1, keepdims=True)
    fft = np.fft.fftshift(np.fft.fft(centered * window, axis=1), axes=1)
    psd = np.abs(fft) ** 2 / (FS * window_energy)
    mean_psd = psd.mean(axis=0)
    median_psd = np.median(psd, axis=0)
    # Validate FFT density normalization against the weighted time-domain power.
    spectral_power = mean_psd.sum() * FS / NFFT
    time_power = np.mean(np.sum(np.abs(centered * window) ** 2, axis=1) / window_energy)
    if not np.isclose(spectral_power, time_power, rtol=1e-10, atol=1e-20):
        raise RuntimeError('PSD normalization check failed')
    mean_db = 10 * np.log10(np.maximum(mean_psd, floor))
    median_db = 10 * np.log10(np.maximum(median_psd, floor))
    map_db = 10 * np.log10(np.maximum(psd, floor))
    used_samples = (len(frames) - 1) * HOP + NFFT
    peak_index = int(np.argmax(mean_psd))
    typical_index = int(np.argmax(median_psd))
    record = {
        'capture_label': label, 'configured_gain_db': GAINS[source_index],
        'path': str(path.relative_to(ROOT)),
        'sha256': hashlib.sha256(raw_bytes).hexdigest(),
        'complex_samples': len(z), 'recording_elapsed_seconds': elapsed,
        'sample_index_duration_seconds_nominal': len(z) / FS,
        'fft_frames': len(frames), 'unused_tail_samples': len(z) - used_samples,
        'full_scale_component_clips': int(np.count_nonzero((iq == 32767) | (iq == -32768))),
        'global_iq_mean': [float(z.real.mean()), float(z.imag.mean())],
        'mean_psd_integral_dbfs': float(10 * np.log10(spectral_power)),
        'median_psd_floor_dbfs_per_hz': float(np.median(median_db)),
        'mean_psd_peak_offset_hz': float(frequency[peak_index]),
        'mean_psd_peak_dbfs_per_hz': float(mean_db[peak_index]),
        'median_psd_peak_offset_hz': float(frequency[typical_index]),
        'median_psd_peak_dbfs_per_hz': float(median_db[typical_index]),
        'normalization_relative_error': float(abs(spectral_power - time_power) / time_power),
    }
    summary['captures'].append(record)
    datasets.append({'label': label, 'color': color, 'mean_db': mean_db,
                     'median_db': median_db, 'map_db': map_db, 'record': record})

fig, axes = plt.subplots(2, 1, figsize=(12, 8.2), sharex=True)
fig.subplots_adjust(top=0.82, bottom=0.20, left=0.11, right=0.97, hspace=0.27)
fig.suptitle(TITLE, x=0.11, y=0.96, ha='left', fontsize=19, fontweight='bold')
fig.text(0.11, 0.905, SUBTITLE, fontsize=11)
fig.text(0.11, 0.87, '4096 点 FFT · Hann 窗 · 50% 重叠 · 每段去直流 · 频点间隔 61.0 Hz', fontsize=10, color='#637286')
for ax, key, title in zip(axes, ['mean_db', 'median_db'],
                          ['完整数据的平均功率谱（包含瞬态异常）', '逐窗功率谱中位数（辅助观察持续成分，未经偏差校正）']):
    for data in datasets:
        ax.plot(frequency / 1000, data[key], color=data['color'], linewidth=1.0,
                alpha=0.86, label=data['label'])
    ax.set_title(title, loc='left', fontsize=11, pad=9)
    ax.set_ylabel('功率谱密度（dBFS/Hz）')
    ax.set_xlim(-125, 125)
    ax.grid(True, alpha=0.18)
    ax.legend(loc='upper right', framealpha=0.95, ncol=2)
    vals = np.concatenate([data[key] for data in datasets])
    ax.set_ylim(np.floor((np.min(vals)-3)/5)*5, np.ceil((np.max(vals)+3)/5)*5)
axes[-1].set_xlabel('相对软件中心频率的偏移（kHz）')
fig.text(0.11, 0.115, '说明：频率轴按用户指定的 64 MHz 时钟配置计算；实际时钟/射频频率尚未核实。', fontsize=10)
fig.text(0.11, 0.079, COMPARISON_NOTE, fontsize=10)
fig.text(0.11, 0.043, '上图保留全部完整窗口；下图是同一批窗口的中位数统计，没有删除或修补原始 IQ。', fontsize=9, color='#637286')
fig.savefig(OUT / 'spectrum.png', dpi=180)
fig.savefig(OUT / 'spectrum.svg')
plt.close(fig)

fig, axes = plt.subplots(1, 2, figsize=(12, 6.8))
fig.subplots_adjust(top=0.78, bottom=0.22, left=0.09, right=0.86, wspace=0.27)
fig.suptitle(MAP_TITLE, x=0.09, y=0.96, ha='left', fontsize=19, fontweight='bold')
fig.text(0.09, 0.902, '两图共用色标；亮线表示较强的频率成分，横向亮带可能对应瞬态或数据异常。', fontsize=10)
fig.text(0.09, 0.865, '频率轴采用软件参数；纵轴按文件样本累计，不是录制现场的连续时间。', fontsize=10, color='#637286')
all_values = np.concatenate([data['map_db'].ravel() for data in datasets])
vmin = float(np.floor(np.percentile(all_values, 5) / 5) * 5)
vmax = float(np.ceil(np.percentile(all_values, 99.8) / 5) * 5)
summary['waterfall_color_limits_dbfs_per_hz'] = [vmin, vmax]
for ax, data in zip(axes, datasets):
    times = (np.arange(len(data['map_db'])) * HOP + NFFT / 2) / FS
    mesh = ax.pcolormesh(frequency / 1000, times, data['map_db'], shading='auto',
                         cmap='magma', vmin=vmin, vmax=vmax, rasterized=True)
    rec = data['record']
    ax.set_title(f"{data['label']} · {rec['complex_samples']:,} 个采样", fontsize=11, pad=11)
    ax.set_xlabel('频率偏移（kHz）')
    ax.set_ylabel('样本累计时间（秒，名义值）')
    ax.set_xlim(-125, 125)
    ax.set_ylim(rec['sample_index_duration_seconds_nominal'], 0)
    ax.set_xticks([-125, -62.5, 0, 62.5, 125])
cax = fig.add_axes([0.885, 0.22, 0.018, 0.56])
fig.colorbar(mesh, cax=cax, extend='both', label='功率谱密度（dBFS/Hz）')
fig.text(0.09, 0.12, TIME_NOTE, fontsize=10)
fig.text(0.09, 0.077, '时钟值尚未核实，且录制报告包序号异常；不对缺失时间作插值，也不据此推算精确丢样率。', fontsize=9, color='#637286')
fig.savefig(OUT / 'waterfall.png', dpi=180)
plt.close(fig)

np.savetxt(OUT / 'spectrum.csv',
           np.column_stack([frequency, FC + frequency, datasets[0]['mean_db'],
                            datasets[1]['mean_db'], datasets[0]['median_db'], datasets[1]['median_db']]),
           delimiter=',', header=','.join(['offset_hz', 'nominal_rf_hz'] +
                 [f'{stat}_{label}_dbfs_per_hz' for stat in ('mean', 'median') for label in CSV_LABELS]), comments='')
(OUT / 'analysis.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'output': str(OUT), 'captures': summary['captures']}, ensure_ascii=False, indent=2))
