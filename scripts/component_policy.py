"""Current procurement choices; never change electrical values or geometry."""
EEPROM_SOURCE = 'https://ww1.microchip.com/downloads/en/DeviceDoc/AT24C01C-AT24C02C-I2C-Compatible-Two-Wire-Serial-EEPROM-1Kbit-2Kbit-20006111A.pdf'
EEPROM_REFS = {'BasicRX':['U1'], 'BasicTX':['U52'], 'LFRX':['U1'], 'LFTX':['U52'], 'TVRX':['U1'], 'TVRX2':['U1'], 'WBX':['U202','U403']}
DECOUPLING = {
    'TVRX2': 'C181 C182 C280 C283 C285'.split(),
    'WBX': 'C216 C217 C219 C221 C307 C308 C311 C313 C314 C316 C318 C335 C338 C350 C351 C352 C353 C354 C355 C356 C416 C417 C419 C421 C514 C525 C535 C536 C537 C538 C539 C540 C541'.split(),
}
RESISTORS = {'TVRX2':'R111 R151'.split(), 'WBX':'R302 R303 R304 R305 R306 R307 R317 R330 R333 R334'.split()}
BRANDS = {
    'R': 'YAGEO / Vishay / Panasonic / UNI-ROYAL / FH',
    'C': 'Murata / TDK / Samsung Electro-Mechanics / Walsin / FH / EYANG',
    'L': 'Murata / TDK / Coilcraft / Sunlord / FH',
}

def passive_kind(ref, value):
    if value.lower() in ('none', 'dnp'):
        return None
    # Some source capacitors have R designators; their units take precedence.
    if any(unit in value for unit in ('pF', 'nF', 'uF', 'µF')):
        return 'C'
    if ref.startswith('FB'):
        return 'L'
    return ref[0] if ref and ref[0] in 'RCL' else None

def update_row(name, source, package=''):
    row = dict(source)
    ref, value = row['Reference'], row['Value']
    row['Approved_brands'] = ''
    row['Sourcing_policy'] = ''
    if ref in EEPROM_REFS[name]:
        row.update(Value='AT24C02', Manufacturer='Microchip', MPN='AT24C02C-SSHM-T', LCSC='C6203',
                   Sourcing_status='已核对引脚/封装/电压/目录；8-byte页写；待实机写入及识别',
                   Specification='SOIC-8 3.9x4.9 mm, P1.27 mm; 1.7–5.5 V; 2 Kbit (256x8); 8-byte page; WP=0; write <=5 ms; ACK polling; 不跨8字节页边界',
                   Evidence=EEPROM_SOURCE, Approved_brands='Microchip',
                   Sourcing_policy='按完整MPN和厂家采购，不能仅按AT24C02通用名下单')
        return row
    kind = passive_kind(ref, value)
    if not kind:
        return row
    row['Approved_brands'] = BRANDS[kind]
    row['Sourcing_policy'] = '国产与国际品牌均可；满足参数后比较含税到手价、起订量、库存和交期；换料须复核封装及电气指标'
    if not row['MPN']:
        row['Manufacturer'] = '候选：' + BRANDS[kind]
        row['Sourcing_status'] = row['Sourcing_status'].replace('国产 0402', '0402')
    if 'Polarized bulk' in package:
        row['Approved_brands'] = 'KEMET / KYOCERA AVX / Vishay / 同规格钽电容'
        row['Manufacturer'] = '候选：' + row['Approved_brands']
    if kind == 'C' and ref.startswith('R') and '0402' in package:
        row['Specification'] = '0402; 按原容值及容差；RF/调谐/PLL用C0G；普通去耦X7R >=16 V'
    if ref in RESISTORS.get(name, []):
        assert value == '1K' and '0402' in package, (name, ref, value, package)
        row.update(Manufacturer='YAGEO', MPN='RC0402FR-071KL', LCSC='C106235',
                   Sourcing_status='已核对厂家规格和库存目录；控制/AGC/偏置电阻',
                   Specification='0402; 1 kohm; +/-1%; 1/16 W at 70 C; +/-100 ppm/C; 50 V（功率限制优先）',
                   Evidence='https://www.yageogroup.com/component-documentation/download/specsheet/RC0402FR-071KL')
    if ref in DECOUPLING.get(name, []):
        assert value == '0.1uF' and '0402' in package, (name, ref, value, package)
        row.update(Manufacturer='Samsung Electro-Mechanics', MPN='CL05B104KO5NNNC', LCSC='C1525',
                   Sourcing_status='已核对0402与电源对地去耦连接；待实机电源噪声验证',
                   Specification='0402; 100 nF; X7R; 16 V; +/-10%; 电源去耦；需考虑直流偏压降容',
                   Evidence='https://datasheet.lcsc.com/datasheet/pdf/02336ea48ea44ca18c72517dd3cb7b47.pdf?productCode=C1525')
    return row
