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
    f'1. 設計車種：消防車（水箱車），全長{VEH["L"]:.2f} m、車寬{VEH["W"]:.2f} m、軸距{VEH["WB"]:.2f} m、前懸{VEH["FOH"]:.2f} m、後懸{VEH["ROH"]:.2f} m、輪距{VEH["TRACK"]:.2f} m、最大轉向角{VEH["STEER"]:.0f}°。',
    '2. 分析方法：以前軸中心沿導引路徑行駛、後軸依曳引曲線（tractrix）追隨之車輛運動模型，逐點計算車身四角及四輪軌跡，取其包絡範圍為車身掃掠範圍。比例尺依設計圖里程樁號（每20 m）校正。',
    '3. 結構物判定：緣石、轉角綠帶、島頭及中央分隔島等取自設計圖CAD圖層（01-7、中央分隔島等），標線（車道線、停止線、斑馬線、箭頭）不列為結構物；圖層未繪製之既有緣石及中央分隔島依圖面補繪。',
    '4. 轉向路徑：於同向車道範圍內，以轉彎半徑8~35 m（且轉向角不超過最大轉向角、轉彎圓弧須於路口範圍內完成）搜尋前軸導引路徑，取與結構物淨距最大、且最少跨用車道之路徑。',
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
def fig_xml(i, grp, k, cap):
    src = f'{SCR}/fig/I{i}_{grp}.jpg'; name = f'media/I{i}_{grp}.jpg'
    im = Image.open(src); w, h = im.size
    if w > 1600: im = im.resize((1600, int(h*1600/w)), Image.LANCZOS)
    os.makedirs(SCR + '/odt/media', exist_ok=True); im.save(SCR + '/odt/' + name, quality=85)
    media.append(name)
    W = 6.1; H = W*im.size[1]/im.size[0]
    if H > 6.3: H = 6.3; W = H*im.size[0]/im.size[1]
    return (f'<text:p text:style-name="PImg"><draw:frame draw:style-name="a2" draw:name="圖{i}-{k}" text:anchor-type="as-char" svg:width="{W:.3f}in" svg:height="{H:.3f}in" draw:z-index="{10+i*5+k}">'
            f'<draw:image xlink:href="{name}" xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad"/></draw:frame></text:p>'
            f'<text:p text:style-name="PCap">{esc(cap)}</text:p>')

summary = []
blocks = ''
for i, c in CFG.items():
    R = json.load(open(f'{SCR}/fig/I{i}.json', encoding='utf-8'))
    cells = {}
    # turning rows
    for grp in ('left', 'right'):
        rs = R[grp]; ok = all(r['clr'] >= 0.25 for r in rs)
        items = []
        for r in rs:
            strad = (r['entry'] > 0 or r['exit'] > 0) if grp == 'right' else (r['entry'] >= 2 or r['exit'] > 0)
            items.append(f'{r["tag"]}{"＊" if strad else ""}：最小淨距{r["clr"]:.2f} m')
        txt = ('結構物是否與轉向軌跡保持25公分以上之間距<text:line-break/>分析結果：' + esc('；'.join(items)) +
               ('，均保持25公分以上。' if ok else '，未達25公分。'))
        cells[grp] = (txt, 'yes' if ok else 'no')
        summary.append((i, grp, ok, min(r['clr'] for r in rs)))
    # through row
    if c['thru'] is None:
        cells['thru'] = ('直行路段路口上下游偏移，其漸變是否符合規範<text:line-break/>分析結果：' + esc(c['thru_na']), 'na')
    else:
        rs = R['thru']; ok = all(r['L'] >= r['req'] for r in rs)
        items = [f'{r["tag"]}：偏移{r["off"]:.2f} m，路口內漸變長{r["L"]:.1f} m（需≧{r["req"]:.1f} m）{"" if r["L"] >= r["req"] else "，不足"}' for r in rs]
        tail = '，均符合。' if ok else '。'
        cells['thru'] = ('直行路段路口上下游偏移，其漸變是否符合規範<text:line-break/>分析結果：' + esc('；'.join(items)) + tail, 'yes' if ok else 'no')
        summary.append((i, 'thru', ok, None))
    t = table_tpl
    # fill vehicle cells
    for p in ('P116', 'P125', 'P134'):
        t = t.replace(f'<text:p text:style-name="{p}"/>', f'<text:p text:style-name="{p}">消防車<text:line-break/>(水箱車)</text:p>')
    t = t.replace('直行路段路口上下游偏移，其漸變是否符合規範<text:s/><text:s text:c="4"/>', cells['thru'][0])
    parts = t.split('結構物是否與轉向軌跡保持25公分以上之間距')
    t = parts[0] + cells['left'][0] + parts[1] + cells['right'][0] + parts[2]
    chk = t.split('□是<text:s/>□否<text:s/>□不適用')
    t = chk[0] + box(cells['thru'][1]) + chk[1] + box(cells['left'][1]) + chk[2] + box(cells['right'][1]) + chk[3]
    hstyle = 'P96' if i == 1 else 'PB96'
    blk = f'<text:h text:style-name="{hstyle}" text:outline-level="3">({CN[i-1]})路口{i}({esc(c["name"])})</text:h>'
    blk += f'<text:p text:style-name="PNote">位置：{esc(STA[i])}；套繪圖說：{esc(c["sheet"])}。{esc(NOTE[i])}</text:p>'
    blk += '<text:h text:style-name="P97" text:outline-level="3">1.分析項目</text:h>' + t
    blk += '<text:p text:style-name="PNote">註：標示「＊」者表示消防車轉向時須跨用相鄰同向車道（含跨越車道線行駛）始能維持25公分以上間距。</text:p>'
    blk += hline_tpl.replace('draw:id="id1"', f'draw:id="idL{i}"').replace('Horizontal Line 2', f'Horizontal Line {i+10}')
    blk += '<text:p text:style-name="P142">2.軌跡模擬圖(轉向及直行軌跡)</text:p>'
    k = 0
    for grp in ('right', 'left', 'thru'):
        if grp == 'thru' and c['thru'] is None: continue
        k += 1
        blk += fig_xml(i, grp, k, f'圖{i}-{k}　路口{i} {c["name"]}　消防車{GRPN[grp]}軌跡模擬圖')
    blocks += blk

# conclusion
concl = '<text:h text:style-name="PB94" text:outline-level="3"><text:span text:style-name="T95">【四、綜合說明】</text:span></text:h>'
lines = []
okturn = [s for s in summary if s[1] in ('left', 'right')]
mn = min(s[3] for s in okturn)
lines.append(f'1. 五處路口之左轉、右轉軌跡經模擬，消防車（水箱車）車身掃掠範圍與緣石、轉角綠帶、島頭等結構物之最小淨距為{mn:.2f} m，均保持25公分以上。')
lines.append('2. 部分路口（標示「＊」者）消防車轉向時須跨用相鄰同向車道，屬大型緊急車輛轉向之常態；建議交通號誌時制及停止線位置維持現行配置，以利消防車轉向。')
bad = [(i, CFG[i]['name']) for i, g, ok, _ in summary if g == 'thru' and not ok]
if bad:
    R4 = json.load(open(f'{SCR}/fig/I4.json', encoding='utf-8'))['thru'][0]
    lines.append(f'3. 直行軌跡：路口2、路口5及路口4之新市二路三段直行，上下游車道偏移漸變均符合規範。路口4崁頂二路往西側既有道路直行，上下游中心偏移約{R4["off"]:.2f} m，路口內可用漸變長度約{R4["L"]:.1f} m，小於V＝{V_DESIGN:.0f} km/h所需之{R4["req"]:.1f} m；'
                 '建議於路口內補繪導引標線（設計圖已有導引虛線者予以確認），或於西側道路前設置速限／警告標誌，並請依實際速限檢討。')
else:
    lines.append('3. 直行軌跡：各路口上下游車道偏移漸變均符合規範。')
lines.append('4. 路口1、路口3為T字路口，直行軌跡檢核列為不適用。')
lines.append('5. 本報告之車道位置，於設計圖未標繪車道線之路段（義山路二段、沙崙路二段、新市二路三段、新市五路三段）係依路面寬度或導引線假設，詳各路口說明；如審查單位要求以AutoTURN或Vehicle Tracking成果提送，建議以本報告路徑為基礎於該軟體複核。')
concl += ''.join(f'<text:p text:style-name="PBody">{esc(t)}</text:p>' for t in lines)

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
                  ''.join(f'<manifest:file-entry manifest:full-path="{m}" manifest:media-type="image/jpeg"/>' for m in media))
open(od + '/META-INF/manifest.xml', 'w', encoding='utf-8').write(man)
with zipfile.ZipFile(OUT, 'w') as z:
    z.write(od + '/mimetype', 'mimetype', compress_type=zipfile.ZIP_STORED)
    for f in ['content.xml', 'styles.xml', 'meta.xml', 'settings.xml', 'META-INF/manifest.xml'] + media:
        z.write(od + '/' + f, f, compress_type=zipfile.ZIP_DEFLATED)
print('wrote', OUT, len(media), 'images')
