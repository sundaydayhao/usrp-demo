"""Offline PSD and waterfall plots for a capture-shenzhen-bands manifest."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('manifest', type=Path)
args = parser.parse_args()
manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
root = Path(__file__).resolve().parents[1]
out = root / 'plots' / args.manifest.parent.name
out.mkdir(parents=True, exist_ok=True)
font = Path('C:/Windows/Fonts/msyh.ttc')
if font.exists():
    font_manager.fontManager.addfont(str(font))
    plt.rcParams['font.family'] = font_manager.FontProperties(fname=str(font)).get_name()
plt.rcParams.update({'axes.unicode_minus': False, 'font.size': 10,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'text.color': '#253344', 'axes.labelcolor': '#253344'})
nfft, hop = 4096, 2048
window = np.hanning(nfft + 1)[:-1]
energy = np.sum(window ** 2)
tiny = np.finfo(float).tiny
db = lambda x: 10 * np.log10(np.maximum(x, tiny))
analysis = {
    'manifest': str(args.manifest.resolve()), 'configured_master_clock_hz': 64e6,
    'actual_clock_verified': False,
    'method': 'All complete 4096-sample periodic-Hann windows, 50% overlap, per-window DC subtraction. Mean and uncorrected median PSD. No frame rejection.',
    'units': 'dBFS/Hz, I and Q divided by 32768; unit complex tone = 0 dBFS integrated. Not calibrated dBm.',
    'time_axis': 'Sample index / nominal rate, not continuous wall time; no gap reconstruction.',
    'captures': [],
}
datasets = []
for capture in manifest['captures']:
    path = Path(capture['raw_file'])
    if not path.exists() or path.stat().st_size < 4 * nfft:
        analysis['captures'].append({'slot': capture['slot'], 'center_mhz': capture['requested_center_mhz'], 'status': 'no_usable_data'})
        continue
    raw_bytes = path.read_bytes()
    if len(raw_bytes) % 4:
        raise ValueError(f'Incomplete sc16 sample: {path}')
    iq = np.frombuffer(raw_bytes, dtype='<i2').reshape(-1, 2)
    z = (iq[:, 0].astype(float) + 1j * iq[:, 1].astype(float)) / 32768
    fs = capture['reported_rate_msps'] * 1e6
    fc = capture['reported_center_mhz'] * 1e6
    frequency = np.fft.fftshift(np.fft.fftfreq(nfft, 1 / fs))
    frames = np.lib.stride_tricks.sliding_window_view(z, nfft)[::hop]
    spectra = []
    time_power_sum = 0.0
    for start in range(0, len(frames), 64):
        chunk = frames[start:start + 64]
        weighted = (chunk - chunk.mean(axis=1, keepdims=True)) * window
        fft = np.fft.fftshift(np.fft.fft(weighted, axis=1), axes=1)
        spectra.append(np.abs(fft) ** 2 / (fs * energy))
        time_power_sum += float(np.sum(np.abs(weighted) ** 2) / energy)
    psd = np.concatenate(spectra)
    del spectra
    mean = psd.mean(axis=0)
    median = np.median(psd, axis=0)
    spectral_power = float(mean.sum() * fs / nfft)
    time_power = time_power_sum / len(frames)
    normalization_error = abs(spectral_power - time_power) / max(time_power, tiny)
    assert normalization_error < 1e-10
    # Average groups of adjacent windows for display, retaining every full frame.
    groups = np.array_split(np.arange(len(psd)), min(160, len(psd)))
    map_power = np.stack([psd[g].mean(axis=0) for g in groups])
    map_times = np.array([(g.mean() * hop + nfft / 2) / fs for g in groups])
    interior = (np.abs(frequency) < 0.4 * fs) & (np.abs(frequency) > 3000)
    indices = np.flatnonzero(interior)
    peak_index = indices[np.argmax(median[indices])]
    rec = {
        'slot': capture['slot'], 'center_mhz': fc / 1e6, 'gain_db': capture['reported_gain_db'],
        'path': str(path), 'sha256': hashlib.sha256(raw_bytes).hexdigest(),
        'complex_samples': len(z), 'nominal_sample_duration_s': len(z) / fs,
        'receive_wall_s': capture['reported_receive_elapsed_s'],
        'lo_wait_passed': capture['lo_wait_passed'], 'overflow_indication': capture['overflow_indication'],
        'frames': len(frames), 'unused_tail_samples': len(z) - ((len(frames) - 1) * hop + nfft),
        'clipped_components': int(np.count_nonzero((iq == 32767) | (iq == -32768))),
        'ac_rms_adc_counts': float(np.sqrt(np.mean(np.abs(z - z.mean()) ** 2)) * 32768),
        'mean_psd_integral_dbfs': float(db(spectral_power)),
        'median_psd_floor_dbfs_per_hz': float(np.median(db(median[interior]))),
        'median_psd_peak_offset_hz': float(frequency[peak_index]),
        'median_psd_peak_dbfs_per_hz': float(db(median[peak_index])),
        'normalization_relative_error': normalization_error,
    }
    analysis['captures'].append(rec)
    datasets.append({'record': rec, 'frequency': frequency, 'fs': fs,
                     'mean': db(mean), 'median': db(median),
                     'map': db(map_power), 'times': map_times})
    np.savetxt(out / (path.stem + '-spectrum.csv'),
               np.column_stack([fc + frequency, db(mean), db(median)]), delimiter=',',
               header='nominal_rf_hz,mean_dbfs_per_hz,uncorrected_median_dbfs_per_hz', comments='')
    print(json.dumps(rec, ensure_ascii=False), flush=True)
    del psd, iq, z, frames, raw_bytes

centers = sorted(set(c['requested_center_mhz'] for c in manifest['captures']))
rows = (len(centers) + 1) // 2
colors = {'A': '#1478a6', 'B': '#db721e'}
if not datasets:
    raise RuntimeError('No data to plot; inspect capture logs.')
for statistic, filename, description in [('mean', 'spectrum.png', '全部完整窗口的平均功率谱'),
                                          ('median', 'spectrum-median.png', '逐频点中位数功率谱（未经偏差校正）')]:
    fig, axes = plt.subplots(rows, 2, figsize=(13, 2.5 * rows + 2.5), squeeze=False)
    fig.subplots_adjust(left=0.09, right=0.98, top=0.82, bottom=0.16, hspace=0.65, wspace=0.22)
    fig.suptitle('深圳候选蜂窝频段 · A / B 槽接收频谱', x=0.09, y=0.97, ha='left', fontsize=20, weight='bold')
    rate = datasets[0]['fs'] / 1e6
    gain = datasets[0]['record']['gain_db']
    fig.text(0.09, 0.923, f'TX/RX 天线接口  |  软件采样率 {rate:g} MS/s  |  增益约 {gain:.0f} dB  |  A、B 分时录制', fontsize=11)
    fig.text(0.09, 0.882, description + f' · {nfft} 点 Hann / 50% 重叠 / 每窗去直流', fontsize=10, color='#637286')
    limits = np.concatenate([d[statistic] for d in datasets])
    ymin = np.floor((limits.min() - 2) / 5) * 5
    ymax = np.ceil((limits.max() + 2) / 5) * 5
    for ax, center in zip(axes.ravel(), centers):
        for data in datasets:
            rec = data['record']
            if rec['center_mhz'] != center:
                continue
            label = f"{rec['slot']} 槽 · LO {'锁定' if rec['lo_wait_passed'] else '未确认'}"
            ax.plot(center + data['frequency'] / 1e6, data[statistic], color=colors[rec['slot']], lw=0.8, alpha=0.85, label=label)
        kind = '基站下行候选' if center < 1880 else 'TDD 候选'
        ax.set_title(f'{center:g} MHz · {kind}', loc='left', fontsize=12, pad=7)
        ax.set_xlim(center - rate / 2, center + rate / 2)
        ax.set_ylim(ymin, ymax)
        ax.ticklabel_format(useOffset=False)
        ax.set_xlabel('软件标称射频频率（MHz）')
        ax.set_ylabel('dBFS/Hz')
        ax.grid(alpha=0.2)
        ax.legend(loc='upper right', ncol=2, fontsize=8)
    for ax in axes.ravel()[len(centers):]:
        ax.set_visible(False)
    fig.text(0.09, 0.09, '频率轴沿用 64 MHz 时钟假设；此前实测报告为 52 MHz，真实射频频率尚未核实。', fontsize=10)
    fig.text(0.09, 0.047, '录制存在包序号 / overflow 提示；仅观察所选局部窗口，图中峰值不等同于已识别的通信信号。', fontsize=10, color='#637286')
    fig.savefig(out / filename, dpi=160)
    if statistic == 'mean':
        fig.savefig(out / 'spectrum.svg')
    plt.close(fig)

fig, axes = plt.subplots(len(centers), 2, figsize=(11, len(centers) * 1.8 + 2.5), squeeze=False)
fig.subplots_adjust(left=0.10, right=0.86, top=0.90, bottom=0.11, hspace=0.7, wspace=0.22)
fig.suptitle('各频点 IQ 时频图 · 左 A 槽 / 右 B 槽', x=0.1, y=0.97, ha='left', fontsize=17, weight='bold')
fig.text(0.1, 0.936, '共用色标；全部完整 FFT 窗口参与时间分组平均。纵轴为样本累计时间。', fontsize=10)
map_values = np.concatenate([d['map'].ravel() for d in datasets])
vmin = float(np.floor(np.percentile(map_values, 2) / 5) * 5)
vmax = float(np.ceil(np.percentile(map_values, 99.8) / 5) * 5)
analysis['waterfall_color_limits_dbfs_per_hz'] = [vmin, vmax]
for row, center in enumerate(centers):
    for col, slot in enumerate(['A', 'B']):
        ax = axes[row, col]
        data = next((d for d in datasets if d['record']['slot'] == slot and d['record']['center_mhz'] == center), None)
        ax.set_title(f'{slot} 槽 · {center:g} MHz', loc='left', fontsize=10)
        if data is None:
            ax.text(0.5, 0.5, '无可绘制数据', ha='center', transform=ax.transAxes)
            continue
        mesh = ax.pcolormesh(data['frequency'] / 1e6, data['times'], data['map'], shading='auto', cmap='magma', vmin=vmin, vmax=vmax, rasterized=True)
        ax.set_ylim(data['record']['nominal_sample_duration_s'], 0)
        ax.set_xlabel('相对中心的偏移（MHz）', fontsize=9)
        ax.set_ylabel('累计秒', fontsize=9)
cax = fig.add_axes([0.89, 0.21, 0.02, 0.62])
fig.colorbar(mesh, cax=cax, extend='both', label='dBFS/Hz')
fig.text(0.1, 0.065, '频率、时间按 64 MHz 配置假设计算；包序号异常对应的时间缺口没有补齐。', fontsize=9)
fig.text(0.1, 0.035, '天线选择 TX/RX；所有录制均只接收；dBFS 未校准为射频输入功率。', fontsize=9)
fig.savefig(out / 'waterfall.png', dpi=150)
plt.close(fig)
(out / 'analysis.json').write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding='utf-8')
print(f'PLOTS={out}', flush=True)
