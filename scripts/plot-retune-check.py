"""Compare existing spectral CSVs at three tuning settings, without hardware I/O."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('initial_plots', type=Path)
parser.add_argument('retuned_plots', type=Path)
args = parser.parse_args()
font = Path('C:/Windows/Fonts/msyh.ttc')
font_manager.fontManager.addfont(str(font))
plt.rcParams.update({'font.family': font_manager.FontProperties(fname=str(font)).get_name(),
                     'axes.unicode_minus': False, 'font.size': 10,
                     'axes.spines.top': False, 'axes.spines.right': False})
fig, axes = plt.subplots(1, 2, figsize=(12, 6), sharey=True)
fig.subplots_adjust(left=0.09, right=0.96, top=0.76, bottom=0.30, wspace=0.20)
fig.suptitle('1890 MHz 附近窄峰 · 小幅移频复测', x=0.09, y=0.95, ha='left', fontsize=18, weight='bold')
fig.text(0.09, 0.85, '中心改变 250 / 500 kHz 后，A、B 的主峰仍位于软件标称约 1890.621 MHz。', fontsize=11)
results = []
for ax, slot in zip(axes, ['A', 'B']):
    for center, color in zip([1890, 1890.25, 1890.5], ['#1478a6', '#d87816', '#763eb0']):
        folder = args.initial_plots if center == 1890 else args.retuned_plots
        path = folder / f'{slot}-{center:g}MHz-g60-spectrum.csv'
        data = np.loadtxt(path, delimiter=',', skiprows=1)
        mask = (data[:, 0] / 1e6 >= 1890.45) & (data[:, 0] / 1e6 <= 1890.8)
        selected = data[mask]
        peak = selected[np.argmax(selected[:, 2])]
        results.append({'slot': slot, 'tune_mhz': center, 'peak_nominal_rf_hz': float(peak[0]),
                        'peak_offset_hz': float(peak[0] - center * 1e6),
                        'peak_median_dbfs_per_hz': float(peak[2]), 'source': str(path.resolve())})
        ax.plot(selected[:, 0] / 1e6, selected[:, 2], color=color, lw=1, alpha=0.82, label=f'中心 {center:g} MHz')
    ax.set_title(slot + ' 槽', loc='left')
    ax.set_xlabel('软件标称射频频率（MHz）')
    ax.set_xlim(1890.45, 1890.8)
    ax.set_ylim(-128, -90)
    ax.ticklabel_format(useOffset=False)
    ax.grid(alpha=0.2)
    ax.legend(loc='upper left', fontsize=9)
axes[0].set_ylabel('中位数功率谱（dBFS/Hz，未经偏差校正）')
fig.text(0.09, 0.14, '这支持峰对应固定射频频率成分；仍不能区分空中信号、外部干扰或设备内部射频杂散。', fontsize=10)
fig.text(0.09, 0.075, '沿用 64 MHz 时钟假设；真实频率未校准，各次录制均有包序号 / overflow 提示。', fontsize=10, color='#637286')
fig.savefig(args.initial_plots / 'retune-check.png', dpi=170)
plt.close(fig)
(args.initial_plots / 'retune-check.json').write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(results, indent=2, ensure_ascii=False))
