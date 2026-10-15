import re, json, os, shutil, zipfile, sys
from PIL import Image
SCR = __file__.rsplit('/', 2)[0]
OUT = sys.argv[1]
TPL = SCR + '/tpl'
sys.path.insert(0, SCR + '/tools')
from runall import CFG, V_DESIGN
from sim import VEH

def esc(s): return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
def box(state):  # state: 'yes'|'no'|'na'
    m = {'yes': '■是<text:s/>□否<text:s/>□不適用', 'no': '□是<text:s/>■否<text:s/>□不適用', 'na': '□是<text:s/>□否<text:s/>■不適用'}
    return m[state]

PROJ = '淡水區新市三路二段周邊人行道改善工程'
AGENCY = '新北市淡水區公所'
DESIGNER = '兩家工程顧問有限公司'
STA = {1: 'A0K+000（T字路口）', 2: '約A0K+329、B0K+236.2、C0K+000（十字路口）', 3: 'A0K+601.4（T字路口）',
       4: 'B0K+000（十字路口，西側為既有道路）', 5: 'C0K+239'}
NOTE = {1: '義山路二段圖面未標繪車道線，以路面寬度（約15.7 m）均分為雙向各2車道設定行車位置。',
        2: '各車道位置依設計圖車道線、中央分隔及島頭實測。',
        3: '沙崙路二段為斜交道路且路中有既有輕軌，圖面未完整標繪車道線；右轉、左轉行車位置參照設計圖之轉向導引線（01-5圖層）設定。',
        4: '新市二路三段圖面未標繪車道線，以中央分隔島兩側路面寬度均分車道設定；西側為既有道路（寬約6.3 m）。',
        5: '新市五路三段圖面未標繪車道線，以中央分隔島兩側路面寬度均分車道設定。'}
CN = '一二三四五六七八'
GRPN = {'thru': '直行', 'left': '左轉', 'right': '右轉'}

x = open(TPL + '/content.xml', encoding='utf-8').read()
head, body = x.split('<office:body>')
# ---- extra automatic styles ----
extra_styles = '''<style:style style:name="PB94" style:parent-style-name="內文" style:family="paragraph"><style:paragraph-properties fo:break-before="page" fo:widows="2" fo:orphans="2" fo:line-height="0.2916in"/></style:style>
<style:style style:name="PB96" style:parent-style-name="內文" style:family="paragraph"><style:paragraph-properties fo:break-before="page" fo:widows="2" fo:orphans="2" fo:line-height="0.2916in"/><style:text-properties style:font-name="標楷體" style:font-name-asian="標楷體" style:font-name-complex="新細明體" fo:font-weight="bold" style:font-weight-asian="bold" style:font-weight-complex="bold" fo:font-size="13.5pt" style:font-size-asian="13.5pt" style:font-size-complex="13.5pt"/></style:style>
<style:style style:name="PCap" style:parent-style-name="內文" style:family="paragraph"><style:paragraph-properties fo:text-align="center" fo:margin-bottom="0.12in" fo:keep-with-next="never"/><style:text-properties style:font-name="標楷體" style:font-name-asian="標楷體" style:font-name-complex="新細明體" fo:font-size="11pt" style:font-size-asian="11pt"/></style:style>
<style:style style:name="frBase" style:family="graphic"><style:graphic-properties style:wrap="none" style:vertical-pos="from-top" style:vertical-rel="paragraph" style:horizontal-pos="from-left" style:horizontal-rel="paragraph" fo:margin-top="0in" fo:margin-bottom="0.04in" fo:margin-left="0in" fo:margin-right="0in" style:run-through="background" fo:border="none" draw:fill="none" fo:background-color="transparent" style:background-transparency="100%" draw:stroke="none"/></style:style>
<style:style style:name="frOvl" style:family="graphic"><style:graphic-properties style:wrap="run-through" style:run-through="foreground" style:vertical-pos="from-top" style:vertical-rel="paragraph" style:horizontal-pos="from-left" style:horizontal-rel="paragraph" fo:margin-top="0in" fo:margin-bottom="0in" fo:margin-left="0in" fo:margin-right="0in" fo:border="none" draw:fill="none" fo:background-color="transparent" style:background-transparency="100%" draw:stroke="none"/></style:style>
<style:style style:name="frTxt" style:family="graphic"><style:graphic-properties style:wrap="run-through" style:run-through="foreground" style:vertical-pos="from-top" style:vertical-rel="paragraph" style:horizontal-pos="from-left" style:horizontal-rel="paragraph" fo:margin-top="0in" fo:margin-bottom="0in" fo:margin-left="0in" fo:margin-right="0in" fo:background-color="#ffffff" draw:fill="solid" draw:fill-color="#ffffff" fo:padding="0.03in" fo:border="0.01in solid #000000" draw:stroke="solid" svg:stroke-color="#000000" svg:stroke-width="0.01in"/></style:style>
<style:style style:name="PLeg" style:family="paragraph"><style:paragraph-properties fo:margin-top="0in" fo:margin-bottom="0in" fo:line-height="115%"/><style:text-properties style:font-name="標楷體" style:font-name-asian="標楷體" style:font-name-complex="新細明體" fo:font-size="7.5pt" style:font-size-asian="7.5pt" style:font-size-complex="7.5pt"/></style:style>
<style:style style:name="PFig" style:parent-style-name="內文" style:family="paragraph"><style:paragraph-properties fo:text-align="start" fo:keep-with-next="always" fo:margin-top="0.05in"/></style:style>
<style:style style:name="TC0" style:family="text"><style:text-properties fo:color="#dc1e1e"/></style:style>
<style:style style:name="TC1" style:family="text"><style:text-properties fo:color="#145ae6"/></style:style>
<style:style style:name="TC2" style:family="text"><style:text-properties fo:color="#00963c"/></style:style>
<style:style style:name="TC3" style:family="text"><style:text-properties fo:color="#c800c8"/></style:style>
<style:style style:name="TC4" style:family="text"><style:text-properties fo:color="#e67800"/></style:style>
<style:style style:name="TC5" style:family="text"><style:text-properties fo:color="#00a0aa"/></style:style>
<style:style style:name="PImg" style:parent-style-name="內文" style:family="paragraph"><style:paragraph-properties fo:text-align="center" fo:keep-with-next="always"/></style:style>
<style:style style:name="PNote" style:parent-style-name="內文" style:family="paragraph"><style:paragraph-properties fo:widows="2" fo:orphans="2" fo:margin-left="0.25in" fo:margin-top="0.04in" fo:margin-bottom="0.04in" fo:line-height="130%"/><style:text-properties style:font-name="標楷體" style:font-name-asian="標楷體" style:font-name-complex="新細明體" fo:font-size="11pt" style:font-size-asian="11pt"/></style:style>
<style:style style:name="PBody" style:parent-style-name="內文" style:family="paragraph"><style:paragraph-properties fo:widows="2" fo:orphans="2" fo:margin-left="0.5in" fo:margin-top="0.04in" fo:margin-bottom="0.04in" fo:line-height="140%" fo:text-align="justify"/><style:text-properties style:font-name="標楷體" style:font-name-asian="標楷體" style:font-name-complex="新細明體" fo:font-size="12pt" style:font-size-asian="12pt"/></style:style>
'''
head = head.replace('</office:automatic-styles>', extra_styles + '</office:automatic-styles>')

b = body
# ---- cover ----
b = b.replace('<text:h text:style-name="P13" text:outline-level="2">計畫名稱：</text:h>',
              f'<text:h text:style-name="P13" text:outline-level="2">計畫名稱：{PROJ}</text:h>')
b = b.replace('<text:span text:style-name="T15">設計單位名稱：</text:span>', f'<text:span text:style-name="T15">設計單位名稱：{DESIGNER}</text:span>')
b = b.replace('<text:h text:style-name="P18" text:outline-level="2">.</text:h>', '<text:h text:style-name="P18" text:outline-level="2"/>')
b = b.replace('<text:h text:style-name="P19" text:outline-level="2">年<text:s text:c="4"/>月</text:h>',
              '<text:h text:style-name="P19" text:outline-level="2">中華民國115年10月</text:h>')
# ---- basic data ----
b = re.sub(r'(<text:p text:style-name="P22">)計畫名稱：＿+', r'\1計畫名稱：' + PROJ, b)
b = re.sub(r'(<text:p text:style-name="P23">)工程主辦機關：＿+', r'\1工程主辦機關：' + AGENCY, b)
b = re.sub(r'(<text:p text:style-name="P24">)設計單位：＿+', r'\1設計單位：' + DESIGNER, b)
# location table rows
t0 = b.index('<table:table-row table:style-name="TableRow38">'); t1 = b.index('</table:table>', t0)
rows = ''
for i, c in CFG.items():
    rows += (f'<table:table-row table:style-name="TableRow38"><table:table-cell table:style-name="TableCell39"><text:p text:style-name="內文Web">'
             f'<text:span text:style-name="T40">路口{i}</text:span></text:p></table:table-cell><table:table-cell table:style-name="TableCell42">'
             f'<text:p text:style-name="內文Web"><text:span text:style-name="T43">{esc(c["name"])}</text:span></text:p>'
             f'<text:p text:style-name="內文Web"><text:span text:style-name="T43">{esc(STA[i])}；{esc(c["sheet"])}</text:span></text:p></table:table-cell></table:table-row>')
b = b[:t0] + rows + b[t1:]
# ---- software / method ----
b = b.replace('<text:p text:style-name="P73">□ AutoTURN　□ Vehicle Tracking　　</text:p>', '<text:p text:style-name="P73">□ AutoTURN　□ Vehicle Tracking　　</text:p>')
m0 = b.index('<text:p text:style-name="P74">'); m1 = b.index('</text:p>', m0) + len('</text:p>')
method = [
    '■ 其他：設計車種幾何參數掃掠軌跡模擬（前軸導引／後軸曳引曲線法），套繪於本案設計平面配置圖。',
]
mp = ''.join(f'<text:p text:style-name="P74"><text:span text:style-name="T76">{esc(t)}</text:span></text:p>' for t in method)
desc = [
    f'1. 設計車種：{VEH["name"]}（依設計規範圖1.3「大客車最小轉向軌跡參考圖」），全長{VEH["L"]:.2f} m、車寬{VEH["W"]:.2f} m、軸距{VEH["WB"]:.2f} m、前懸{VEH["FOH"]:.2f} m、後懸{VEH["ROH"]:.2f} m、左前輪最小轉向半徑{VEH["RMIN"]:.2f} m（換算最大轉向角約{VEH["STEER"]:.1f}°）；輪距圖未標示，採{VEH["TRACK"]:.2f} m。',
    '2. 分析方法：以前軸中心沿導引路徑行駛、後軸依曳引曲線（tractrix）追隨之車輛運動模型，逐點計算車身四角及四輪軌跡，取其包絡範圍為車身掃掠範圍。比例尺依設計圖里程樁號（每20 m）校正。',
    '3. 結構物判定：緣石、轉角綠帶、島頭及中央分隔島等取自設計圖CAD圖層（01-7、中央分隔島等），標線（車道線、停止線、斑馬線、箭頭）不列為結構物；圖層未繪製之既有緣石及中央分隔島依圖面補繪。',
    '4. 轉向路徑：依道路交通安全規則第102條，右轉由外側（右轉）車道轉入目的道路最外側車道（外側轉外側），左轉由內側（左轉）車道轉入目的道路最內側車道（內側轉內側）。車輛於路口範圍外須於車道內行駛（僅允許車道內±0.25 m偏移），路口範圍內可向外側擺頭；於可行路徑中取最小淨距最接近且不小於25公分者繪製（即以25公分淨距為設計條件）。如無可行路徑，則改駛入目的道路相鄰同向車道並加註「＊」。',
    f'5. 檢核標準：（1）轉向軌跡與結構物間距應保持25公分以上；（2）直行車道於路口上下游偏移時，路口內可用漸變長度應不小於 L＝W×V²/155（W：偏移量m，V：速率km/h，V≦60 km/h），本報告採 V＝{V_DESIGN:.0f} km/h 檢核。',
]
dp = ''.join(f'<text:p text:style-name="PBody">{esc(t)}</text:p>' for t in desc)
b = b[:m0] + mp + dp + b[m1:]
# ---- remove blank spacer headings before section 3, add page break ----
s0 = b.index('<text:h text:style-name="P80"'); s1 = b.index('<text:h text:style-name="P94"')
b = b[:s0] + b[s1:]
b = b.replace('<text:h text:style-name="P94" text:outline-level="3">', '<text:h text:style-name="PB94" text:outline-level="3">')
# ---- per-intersection blocks ----
blk0 = b.index('<text:h text:style-name="P96"'); blk1 = b.index('</office:text>')
tpl_blk = b[blk0:blk1]
tbl0 = tpl_blk.index('<table:table '); tbl1 = tpl_blk.index('</table:table>') + len('</table:table>')
table_tpl = tpl_blk[tbl0:tbl1]
line0 = tpl_blk.index('<text:p text:style-name="P140">'); line1 = tpl_blk.index('</text:p>', line0) + len('</text:p>')
hline_tpl = tpl_blk[line0:line1]

media = []
LAY = {}
def fig_xml(i, grp, k, cap):
    if i not in LAY: LAY[i] = json.load(open(f'{SCR}/layers_out/I{i}.json', encoding='utf-8'))
    L = LAY[i][grp]
    os.makedirs(SCR + '/odt/media', exist_ok=True)
    bp, BW, BH = L['base']
    bname = f'media/I{i}_{grp}_base.jpg'
    Image.open(bp).convert('RGB').save(SCR + '/odt/' + bname, quality=88)
    media.append((bname, 'image/jpeg'))
    Win = 6.1; sc = Win / BW; Hin = BH * sc
    if Hin > 6.4: Hin = 6.4; sc = Hin / BH; Win = BW * sc
    z = 100 + i*40 + k*10
    x = (f'<text:p text:style-name="PFig"><draw:frame draw:style-name="frBase" draw:name="圖{i}-{k} 底圖(設計圖)" text:anchor-type="paragraph" '
         f'svg:x="0in" svg:y="0in" svg:width="{Win:.4f}in" svg:height="{Hin:.4f}in" draw:z-index="{z}">'
         f'<draw:image xlink:href="{bname}" xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad"/></draw:frame>')
    for m, (mp, mx, my, mw, mh, c) in enumerate(L['moves']):
        mname = f'media/I{i}_{grp}_mv{m+1}.png'
        shutil.copy(mp, SCR + '/odt/' + mname); media.append((mname, 'image/png'))
        x += (f'<draw:frame draw:style-name="frOvl" draw:name="圖{i}-{k} 軌跡{m+1}" text:anchor-type="paragraph" '
              f'svg:x="{mx*sc:.4f}in" svg:y="{my*sc:.4f}in" svg:width="{mw*sc:.4f}in" svg:height="{mh*sc:.4f}in" draw:z-index="{z+1+m}">'
              f'<draw:image xlink:href="{mname}" xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad"/></draw:frame>')
    # legend text box (top-left) and vehicle spec (bottom-right), editable
    rows = ''.join(f'<text:p text:style-name="PLeg"><text:span text:style-name="TC{m}">■</text:span> {esc(t)}</text:p>' for m, (t, c) in enumerate(L['rows']))
    lw = 3.3 if grp != 'thru' else 3.9
    x += (f'<draw:frame draw:style-name="frTxt" draw:name="圖{i}-{k} 圖例" text:anchor-type="paragraph" svg:x="0.05in" svg:y="0.05in" svg:width="{lw}in" draw:z-index="{z+8}">'
          f'<draw:text-box fo:min-height="0.2in">{rows}</draw:text-box></draw:frame>')
    spec = [f'設計車種：{VEH["name"]}', f'全長{VEH["L"]:.2f}m　車寬{VEH["W"]:.2f}m', f'軸距{VEH["WB"]:.2f}m　輪距{VEH["TRACK"]:.2f}m',
            f'前懸{VEH["FOH"]:.2f}m　後懸{VEH["ROH"]:.2f}m', f'最小轉向半徑{VEH["RMIN"]:.2f}m', '色帶：車身掃掠範圍　細線：輪跡', '黑框：車輛位置　○：最小淨距處', '虛線：25cm淨距線']
    sw, sh = 1.75, 0.11*len(spec)+0.08
    x += (f'<draw:frame draw:style-name="frTxt" draw:name="圖{i}-{k} 車種規格" text:anchor-type="paragraph" svg:x="{Win-sw-0.05:.4f}in" svg:y="{Hin-sh-0.05:.4f}in" svg:width="{sw}in" draw:z-index="{z+9}">'
          f'<draw:text-box fo:min-height="{sh:.3f}in">' + ''.join(f'<text:p text:style-name="PLeg">{esc(t)}</text:p>' for t in spec) + '</draw:text-box></draw:frame>')
    x += '</text:p>'
    x += f'<text:p text:style-name="PCap">{esc(cap)}</text:p>'
    return x

FIGNO = {}
for i, c in CFG.items():
    k = 0
    for g in ('right', 'left', 'thru'):
        if g == 'thru' and c['thru'] is None: continue
        k += 1; FIGNO[(i, g)] = f'圖{i}-{k}'
MODS = []
for i in CFG:
    Rj = json.load(open(f'{SCR}/fig/I{i}.json', encoding='utf-8'))
    for g in ('right', 'left'):
        for r in Rj[g]:
            for md in r.get('mods') or []:
                if md['depth_m'] < 0.05 or md['area_m2'] < 0.1: continue
                md = dict(md, kind='轉角緣石／轉角綠帶' if g == 'right' else '中央分隔島／島頭'); MODS.append(dict(no=len(MODS)+1, i=i, g=g, tag=r['tag'], before=r.get('clr_before'), **md))
THRU_FIX = {}
summary = []
blocks = ''
for i, c in CFG.items():
    R = json.load(open(f'{SCR}/fig/I{i}.json', encoding='utf-8'))
    cells = {}
    # turning rows
    for grp in ('left', 'right'):
        rs = R[grp]; ok = all(r['clr'] >= 0.25 for r in rs)
        items = []
        anymod = False
        for r in rs:
            items.append(f'{r["tag"]}：最小淨距{r["clr"]:.2f} m')
        txt = ('結構物是否與轉向軌跡保持25公分以上之間距<text:line-break/>分析結果：' + esc('；'.join(items)) +
               ('，均保持25公分以上' + ('（＃者依修正建議修正後）。' if anymod else '。') if ok else '，未達25公分。'))
        cells[grp] = (txt, 'yes' if ok else 'no')
        summary.append((i, grp, ok, min(r['clr'] for r in rs)))
    # through row
    if c['thru'] is None:
        cells['thru'] = ('直行路段路口上下游偏移，其漸變是否符合規範<text:line-break/>分析結果：' + esc(c['thru_na']), 'na')
    else:
        rs = R['thru']; ok = all(r['L'] >= r['req'] for r in rs)
        items = [f'{r["tag"]}{"＃" if r["tag"] in THRU_FIX else ""}：{("（" + THRU_FIX[r["tag"]] + "）") if r["tag"] in THRU_FIX else ""}偏移{r["off"]:.2f} m，路口內漸變長{r["L"]:.1f} m（需≧{r["req"]:.1f} m）{"" if r["L"] >= r["req"] else "，不足"}' for r in rs]
        tail = '，均符合。' if ok else '。'
        cells['thru'] = ('直行路段路口上下游偏移，其漸變是否符合規範<text:line-break/>分析結果：' + esc('；'.join(items)) + tail, 'yes' if ok else 'no')
        summary.append((i, 'thru', ok, None))
    t = table_tpl
    # fill vehicle cells
    for p in ('P116', 'P125', 'P134'):
        t = t.replace(f'<text:p text:style-name="{p}"/>', f'<text:p text:style-name="{p}">{VEH["name"]}</text:p>')
    t = t.replace('直行路段路口上下游偏移，其漸變是否符合規範<text:s/><text:s text:c="4"/>', cells['thru'][0])
    parts = t.split('結構物是否與轉向軌跡保持25公分以上之間距')
    t = parts[0] + cells['left'][0] + parts[1] + cells['right'][0] + parts[2]
    chk = t.split('□是<text:s/>□否<text:s/>□不適用')
    t = chk[0] + box(cells['thru'][1]) + chk[1] + box(cells['left'][1]) + chk[2] + box(cells['right'][1]) + chk[3]
    hstyle = 'P96' if i == 1 else 'PB96'
    blk = f'<text:h text:style-name="{hstyle}" text:outline-level="3">({CN[i-1]})路口{i}({esc(c["name"])})</text:h>'
    blk += f'<text:p text:style-name="PNote">位置：{esc(STA[i])}；套繪圖說：{esc(c["sheet"])}。{esc(NOTE[i])}</text:p>'
    blk += '<text:h text:style-name="P97" text:outline-level="3">1.分析項目</text:h>' + t
    blk += '<text:p text:style-name="PNote">註：右轉採外側轉外側、左轉採內側轉內側。</text:p>'
    blk += hline_tpl.replace('draw:id="id1"', f'draw:id="idL{i}"').replace('Horizontal Line 2', f'Horizontal Line {i+10}')
    blk += '<text:p text:style-name="P142">2.軌跡模擬圖(轉向及直行軌跡)</text:p>'
    k = 0
    for grp in ('right', 'left', 'thru'):
        if grp == 'thru' and c['thru'] is None: continue
        k += 1
        blk += fig_xml(i, grp, k, f'圖{i}-{k}　路口{i} {c["name"]}　{VEH["name"]}{GRPN[grp]}軌跡模擬圖')
    blocks += blk

# conclusion
concl = '<text:h text:style-name="PB94" text:outline-level="3"><text:span text:style-name="T95">【四、綜合說明】</text:span></text:h>'
lines = []
VNm = VEH['name']
turns = [t for t in summary if t[1] in ('left', 'right')]
bad_turn = [t for t in turns if not t[2]]
if not bad_turn:
    lines.append(f'1. 轉向軌跡：依外側轉外側（右轉）、內側轉內側（左轉）原則，五處路口之左轉、右轉軌跡與緣石、轉角綠帶、島頭等結構物均保持25公分以上間距。')
else:
    lines.append('1. 轉向軌跡：' + '、'.join(f'路口{i}{GRPN[g]}' for i, g, ok, v in bad_turn) + '未達25公分。')
thru_bad = []
for i, c in CFG.items():
    if c['thru'] is None: continue
    for r in json.load(open(f'{SCR}/fig/I{i}.json', encoding='utf-8'))['thru']:
        if r['L'] < r['req']: thru_bad.append((i, r))
if thru_bad:
    lines.append('2. 直行軌跡：' + '；'.join(f'路口{i}{r["tag"]}偏移{r["off"]:.2f} m，可用漸變長度{r["L"]:.1f} m小於所需{r["req"]:.1f} m' for i, r in thru_bad) + f'（V＝{V_DESIGN:.0f} km/h）；其餘直行車道偏移漸變均符合規範。')
else:
    lines.append(f'2. 直行軌跡：各路口上下游車道偏移漸變均符合規範（V＝{V_DESIGN:.0f} km/h）。')
lines.append('3. 路口1、路口3為T字路口，直行軌跡檢核列為不適用。')
lines.append('4. 本報告之車道位置，於設計圖未標繪車道線之路段（義山路二段、沙崙路二段、新市二路三段、新市五路三段）係依路面寬度或導引線假設，詳各路口說明。')
concl += ''.join(f'<text:p text:style-name="PBody">{esc(t)}</text:p>' for t in lines)

sec5 = '<text:h text:style-name="PB94" text:outline-level="3"><text:span text:style-name="T95">【五、設計修正建議】</text:span></text:h>'
sec5 += '<text:p text:style-name="PBody">下表為使' + esc(VEH['name']) + '轉向軌跡與結構物保持25公分以上間距，須修正（退縮）之結構物範圍；修正範圍以軌跡圖中紅色斜線區標示，退縮量為該範圍內距現況路緣之最大距離。修正時建議將緣石線順接退縮至斜線範圍外緣，並維持原有轉角綠帶、無障礙坡道等設施之功能。</text:p>'
hdr = ['編號', '路口', '車流方向', '修正位置', '原設計最小淨距(m)', '最大退縮(m)', '修正面積(m²)', '圖號']
def cell(t, head=False):
    st, ps = ('TableCell104', 'P105') if head else ('TableCell113', 'P118')
    return f'<table:table-cell table:style-name="{st}"><text:p text:style-name="{ps}">{esc(str(t))}</text:p></table:table-cell>'
tb = '<table:table table:style-name="Table98">' + ''.join('<table:table-column/>' for _ in hdr)
tb += '<table:table-header-rows><table:table-row>' + ''.join(cell(h, True) for h in hdr) + '</table:table-row></table:table-header-rows>'
for m in MODS:
    tb += '<table:table-row>' + ''.join(cell(v) for v in (f'修正{m["no"]}', f'路口{m["i"]}', m['tag'], m['kind'], f'{m["before"]:.2f}', f'{m["depth_m"]:.2f}', f'{m["area_m2"]:.1f}', FIGNO[(m['i'], m['g'])])) + '</table:table-row>'
for tag, fix in THRU_FIX.items():
    tb += '<table:table-row>' + ''.join(cell(v) for v in (f'修正{len(MODS)+1}', '路口4', tag, '車道配置', '—', '—', '—', FIGNO[(4, 'thru')])) + '</table:table-row>'
tb += '</table:table>'
sec5 += tb
for tag, fix in THRU_FIX.items():
    sec5 += f'<text:p text:style-name="PNote">修正{len(MODS)+1}說明：路口4{esc(tag)}，原由外側直行車道直行，上下游偏移約4.94 m，路口內漸變長度不足；建議將{esc(fix)}，使直行車流由內側車道進入西側道路，偏移降為約2.0 m，漸變長度符合 L＝W×V²/155（V＝{V_DESIGN:.0f} km/h）。</text:p>'
b = b[:blk0] + blocks + concl + b[blk1:]
x2 = head + '<office:body>' + b

# ---- write odt ----
od = SCR + '/odt'
for f in ('styles.xml', 'meta.xml', 'settings.xml', 'mimetype'):
    shutil.copy(TPL + '/' + f, od + '/' + f)
os.makedirs(od + '/META-INF', exist_ok=True)
open(od + '/content.xml', 'w', encoding='utf-8').write(x2)
man = open(TPL + '/META-INF/manifest.xml', encoding='utf-8').read()
man = man.replace('<manifest:file-entry manifest:full-path="media/image1.png" manifest:media-type="image/png"/>',
                  ''.join(f'<manifest:file-entry manifest:full-path="{m}" manifest:media-type="{t}"/>' for m, t in media))
open(od + '/META-INF/manifest.xml', 'w', encoding='utf-8').write(man)
with zipfile.ZipFile(OUT, 'w') as z:
    z.write(od + '/mimetype', 'mimetype', compress_type=zipfile.ZIP_STORED)
    for f in ['content.xml', 'styles.xml', 'meta.xml', 'settings.xml', 'META-INF/manifest.xml'] + [m for m, t in media]:
        z.write(od + '/' + f, f, compress_type=zipfile.ZIP_DEFLATED)
print('wrote', OUT, len(media), 'images')
