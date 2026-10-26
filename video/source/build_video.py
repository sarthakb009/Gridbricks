"""Generate the narrated Northstar two-part walkthrough with macOS say and FFmpeg."""
from __future__ import annotations
import html, json, math, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENDER = ROOT / 'rendered'
FPS, WIDTH, HEIGHT = 10, 1600, 900

SCENES = [
  {'part':'PART 1 · CLIENT WALKTHROUGH','title':'A clearer wind decision.','tag':'NORTHSTAR  /  GB POWER DESK','sub':'Day-ahead wind forecast intelligence','narration':'Welcome to Northstar Wind Desk, a day-ahead wind intelligence pilot for a GB electricity buyer. It makes two things clear: which wind forecast was available when the buyer had to decide, and how that forecast compared with the wind delivered. The goal is a more informed residual procurement conversation, with the source and uncertainty visible.', 'visual':'cover'},
  {'part':'PART 1 · CLIENT WALKTHROUGH','title':'Start with the buyer’s question.','tag':'01  /  DECISION CONTEXT','sub':'How much non-wind supply might the portfolio need?','narration':'A buyer needs to cover expected consumer demand. Wind changes with weather, and the day-ahead decision happens before delivery. Forecast uncertainty therefore matters. In this pilot we deliberately isolate national wind generation from Elexon, so the team can inspect forecast availability and error without implying that wind alone determines the portfolio position.', 'visual':'context'},
  {'part':'PART 1 · CLIENT WALKTHROUGH','title':'Freeze what was knowable.','tag':'02  /  FORECAST VINTAGE','sub':'Choose a January delivery date and the desk’s cutoff.','narration':'The delivery date and decision cutoff define the view. Northstar only considers forecast publications no later than that cutoff, then keeps the newest available forecast for each half-hour. This avoids judging a decision with a forecast revision that arrived after the buyer had acted. The illustration on screen is a visual guide; it is not a claim about measured January values.', 'visual':'dashboard'},
  {'part':'PART 1 · CLIENT WALKTHROUGH','title':'See the forecast beside outturn.','tag':'03  /  HALF-HOURLY REVIEW','sub':'Same settlement period. Forecast publication time stays visible.','narration':'The main chart compares the selected day-ahead forecast with actual wind outturn at thirty-minute resolution. A second chart shows signed error, forecast minus actual. Positive bars are an over-forecast; negative bars are an under-forecast. The table makes each period traceable, including its forecast publication time, and the full day can be exported for analysis.', 'visual':'charts'},
  {'part':'PART 1 · CLIENT WALKTHROUGH','title':'Turn error into a planning signal.','tag':'04  /  ACCURACY','sub':'Typical miss · relative miss · systematic bias','narration':'Mean absolute error gives the typical miss in megawatts. Weighted absolute percentage error expresses total absolute miss relative to actual wind volume. Mean bias shows whether forecasts tended to run high or low. These measures describe historic performance for the chosen decision vintage. They help quantify uncertainty; they do not tell the buyer how much to procure without demand and position data.', 'visual':'metrics'},
  {'part':'PART 1 · CLIENT WALKTHROUGH','title':'An auditable pilot, ready to extend.','tag':'05  /  NEXT STEP','sub':'Agree the cutoff. Review the signal. Connect portfolio context next.','narration':'The pilot gives the desk a repeatable historical review: a frozen decision view, a half-hourly comparison, understandable error measures, and a downloadable audit trail. The next step is to agree the actual market decision cutoff. To turn this into a net buying view, connect client demand, contracted generation, current position, and commercial constraints. Those inputs were intentionally excluded here.', 'visual':'close'},
  {'part':'PART 2 · TECHNICAL REVIEW','title':'Implementation and handover.','tag':'NORTHSTAR  /  INTERNAL REVIEW','sub':'Architecture · data contract · selection logic · limitations','narration':'This second part is a technical walkthrough for the lead reviewer. I’ll follow the path from Elexon data into the dashboard, explain how the decision-time vintage is selected, show where the logic lives, and call out the boundary conditions and operational work required before a production rollout.', 'visual':'divider'},
  {'part':'PART 2 · TECHNICAL REVIEW','title':'A small, inspectable architecture.','tag':'01  /  SYSTEM DESIGN','sub':'React dashboard  →  FastAPI service  →  Elexon Insights API','narration':'The frontend is React with Vite. Recharts renders the time series and error bars; the UI owns date and cutoff selection, loading and error states, metrics presentation, and CSV export. FastAPI fetches the two Elexon datasets, applies the time and join rules, and returns one compact response. Docker Compose starts the web and API containers for local review.', 'visual':'architecture'},
  {'part':'PART 2 · TECHNICAL REVIEW','title':'Two datasets. One matching key.','tag':'02  /  DATA CONTRACT','sub':'WINDFOR forecast · FUELHH actual wind generation','narration':'The prototype uses only the requested national Elexon feeds. WINDFOR supplies target start time, publish time, and forecast generation. FUELHH is filtered to fuel type WIND and supplies target start time and generation. The service matches records on start time, which represents the same half-hourly settlement period. Missing actuals stay null and appear as gaps rather than being filled.', 'visual':'datasets'},
  {'part':'PART 2 · TECHNICAL REVIEW','title':'Make the decision vintage reproducible.','tag':'03  /  SELECTION LOGIC','sub':'Previous-day cutoff in Europe/London → UTC API window → per-period latest','narration':'The backend interprets the selected cutoff in the requested timezone, Europe London by default, and converts it to UTC. It queries a bounded publication-time lookback. For each target period it discards anything published after the cutoff, then chooses the latest remaining publish time. Delivery periods are filtered to the selected date and actuals are joined by start time. The response includes the cutoff and publication timestamp for auditability.', 'visual':'timeline'},
  {'part':'PART 2 · TECHNICAL REVIEW','title':'Metrics are explicit and reproducible.','tag':'04  /  ANALYSIS','sub':'error = forecast − actual','narration':'For periods with both forecast and actual, the service computes error as forecast minus actual. MAE is the mean absolute error. RMSE is the square root of mean squared error. WAPE is total absolute error divided by total actual generation, times one hundred. Bias is mean signed error. WAPE is omitted if total actual wind is zero, and all metrics are omitted when there are no matched periods.', 'visual':'formulas'},
  {'part':'PART 2 · TECHNICAL REVIEW','title':'Where to review the code.','tag':'05  /  REPOSITORY MAP','sub':'API logic is isolated from chart presentation.','narration':'The backend main module contains the health route, Elexon request helper, period filtering, forecast selection, matching, and metric calculations. The frontend source contains the React page and visual styling. Dockerfiles define each service, and the root Compose file connects them. README documents the data sources, semantics, local startup, client pitch, and deployment setup. AI assistance is disclosed there as requested.', 'visual':'files'},
  {'part':'PART 2 · TECHNICAL REVIEW','title':'Known limits and production path.','tag':'06  /  REVIEW CHECKLIST','sub':'Validate live API behaviour before operational use.','narration':'This prototype has not been validated against live January responses in this environment. The API query semantics, returned schema, publication coverage, pagination and rate limits must be checked before relying on the result. Production should add caching, retries, request throttling, monitoring, data completeness checks, authentication and stored snapshots. Most importantly, no demand or portfolio inputs are present, so this is forecast intelligence, not a purchase recommendation.', 'visual':'limits'},
]

MINT='#50E0B3'; DARK='#0D201F'; PANEL='#142C2A'; TEXT='#F3F8F5'; MUTED='#A0B9B1'; LINE='#284340'; LIME='#B8F36B'

def esc(s): return html.escape(s, quote=True)
def text(x,y,s,size=24,color=TEXT,weight=400,family='Arial',extra=''):
    return f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="{color}" {extra}>{esc(s)}</text>'
def rect(x,y,w,h,fill=PANEL,rx=18,stroke='none'):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}"/>'
def line(x1,y1,x2,y2,color=LINE,width=2): return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>'
def poly(points,color=MINT,width=4,fill='none'):
    return f'<polyline points="{points}" fill="{fill}" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>'

def visual(kind):
    out=[]
    if kind=='cover':
        out += [rect(820,120,650,650,'url(#card)',30,LINE), text(875,184,'POWER PROCUREMENT   /   UK',15,MUTED,700,'Arial','letter-spacing="2"')]
        out += [text(875,278,'48',86,TEXT,700,'Arial'),text(995,278,'settlement periods',22,MUTED),text(875,330,'ONE DECISION-DAY VIEW',15,MINT,700,'Arial','letter-spacing="1.5"')]
        out += [line(875,380,1405,380),text(875,435,'Latest forecast before cutoff',21,TEXT,600),text(875,474,'Compared with delivered wind',21,TEXT,600),text(875,555,'JANUARY 2026',16,MINT,700,'Arial','letter-spacing="2"')]
        out += [f'<circle cx="1277" cy="646" r="80" fill="none" stroke="{MINT}" stroke-width="2" opacity=".35"/>',f'<circle cx="1277" cy="646" r="48" fill="none" stroke="{MINT}" stroke-width="2" opacity=".55"/>',f'<circle cx="1277" cy="646" r="9" fill="{MINT}"/>']
        for a in range(0,360,45): out.append(f'<line x1="1277" y1="646" x2="{1277+80*math.cos(math.radians(a)):.0f}" y2="{646+80*math.sin(math.radians(a)):.0f}" stroke="{MINT}" opacity=".4" stroke-width="2"/>')
    elif kind=='context':
        out += [rect(840,160,600,535,PANEL,25,LINE),text(890,220,'THE BUYER’S BALANCING QUESTION',15,MINT,700,'Arial','letter-spacing="1.6"')]
        out += [rect(890,260,500,110,'#1D3C38',16),text(925,310,'Consumer demand',22,TEXT,600),text(925,345,'Portfolio requirement',14,MUTED),text(1345,326,'−',32,MINT,700)]
        out += [rect(890,395,500,110,'#1D3C38',16),text(925,445,'Available wind',22,TEXT,600),text(925,480,'Weather dependent',14,MUTED),text(1345,461,'=',32,MINT,700)]
        out += [rect(890,530,500,110,'#254E43',16),text(925,580,'Residual supply need',22,TEXT,600),text(925,615,'This pilot measures wind uncertainty',14,'#A9EBD5')]
    elif kind=='dashboard':
        out += [rect(820,112,680,625,'#102421',24,LINE),text(865,162,'NORTHSTAR   /   WIND INTELLIGENCE',14,MUTED,700,'Arial','letter-spacing="1.2"'),text(865,211,'Thursday, 15 January 2026',25,TEXT,600),rect(865,235,240,47,'#193833',10),text(884,265,'Decision cutoff · 10:00 UK',14,MINT,500),rect(1120,235,180,47,'#203934',10),text(1142,265,'JAN 2026',14,TEXT,500)]
        for i,(lbl,val) in enumerate([('FORECAST VINTAGE','09:48 UK'),('SETTLEMENTS','48 periods'),('RESOLUTION','30 minutes')]):
            x=865+i*198;out += [rect(x,307,180,82,'#18332F',12),text(x+14,336,lbl,10,MUTED,700,'Arial','letter-spacing=".8"'),text(x+14,368,val,18,TEXT,600)]
        out += [rect(865,410,595,275,'#122A27',14),text(892,448,'FORECAST VS ACTUAL  ·  MW',14,MUTED,600,'Arial','letter-spacing="1"')]
        for yy in (495,545,595,645): out.append(line(895,yy,1428,yy,'#29443F',1))
        pts1='895,615 945,588 995,571 1045,582 1095,540 1145,530 1195,550 1245,500 1295,512 1345,482 1395,495 1428,467'
        pts2='895,625 945,598 995,580 1045,592 1095,560 1145,535 1195,568 1245,520 1295,535 1345,500 1395,515 1428,490'
        out += [poly(pts1,MINT,4),poly(pts2,'#E4F4EB',3),text(895,670,'00:00',11,MUTED),text(1380,670,'23:30',11,MUTED),rect(1050,705,400,20,'#493B25',7),text(1062,720,'ILLUSTRATIVE VISUAL · NOT JANUARY OBSERVATIONS',10,'#F0C27E',700,'Arial','letter-spacing=".4"')]
    elif kind=='charts':
        out += [rect(825,130,650,580,PANEL,24,LINE),text(875,195,'FORECAST COMPARED WITH OUTTURN',17,MUTED,700,'Arial','letter-spacing="1.2"')]
        for yy in (258,310,362,414,466): out.append(line(870,yy,1420,yy,'#29443F',1))
        p1='870,424 920,390 970,356 1020,378 1070,325 1120,306 1170,335 1220,276 1270,290 1320,254 1370,272 1420,226'
        p2='870,438 920,401 970,374 1020,389 1070,351 1120,321 1170,357 1220,303 1270,315 1320,281 1370,302 1420,259'
        out += [poly(p1,MINT,4),poly(p2,TEXT,3),text(880,505,'Forecast',13,MINT,600),text(1010,505,'Actual',13,TEXT,600),rect(865,540,550,115,'#193A35',15)]
        out += [text(895,584,'One half-hour = one matched period',18,TEXT,600),text(895,620,'Each forecast publication time remains auditable.',14,MUTED)]
        for i,h in enumerate([30,55,35,80,48,22,67,39,60,44,27,70]):
            x=900+i*39; y=690-h; c='#E4A45C' if i%2==0 else MINT
            out.append(rect(x,y,20,h,c,4))
        out += [line(890,690,1380,690,'#6A8179',1),text(890,735,'Signed error by settlement period',14,MUTED)]
    elif kind=='metrics':
        cards=[('MAE','185 MW','Typical absolute miss',MINT),('WAPE','7.4%','Absolute miss / actual volume',LIME),('BIAS','+42 MW','Positive = over-forecast','#E8A86C')]
        for i,(a,b,c,d) in enumerate(cards):
            y=170+i*166;out += [rect(845,y,590,130,PANEL,18,LINE),text(890,y+40,a,14,MUTED,700,'Arial','letter-spacing="1.6"'),text(890,y+91,b,34,TEXT,700),text(890,y+116,c,14,MUTED),f'<circle cx="1373" cy="{y+65}" r="14" fill="{d}" opacity=".95"/>']
        out += [text(875,718,'ILLUSTRATIVE VALUES ONLY',12,'#F0C27E',700,'Arial','letter-spacing="1.5"')]
    elif kind=='close':
        out += [rect(835,145,620,570,'url(#card)',28,LINE),text(890,210,'THE PILOT DELIVERS',15,MINT,700,'Arial','letter-spacing="1.5"')]
        for i,(a,b) in enumerate([('01','A cutoff-aware wind forecast'),('02','Forecast accuracy in clear units'),('03','Period-level evidence to export')]):
            y=293+i*100;out += [text(890,y,a,15,MINT,700,'Arial'),text(940,y,b,20,TEXT,500),line(890,y+30,1380,y+30,'#29443F',1)]
        out += [text(890,650,'NEXT  →  CONNECT DEMAND + PORTFOLIO POSITION',14,LIME,700,'Arial','letter-spacing=".6"')]
    elif kind=='divider':
        out += [rect(900,145,520,500,'url(#card)',28,LINE),text(970,245,'TECH LEAD',15,MINT,700,'Arial','letter-spacing="2"'),text(970,330,'System',48,TEXT,700),text(970,390,'walkthrough',48,TEXT,700),text(970,475,'Data path  ·  selection logic',18,MUTED),text(970,515,'Metrics  ·  code map  ·  limitations',18,MUTED),line(970,565,1345,565,MINT,3)]
    elif kind=='architecture':
        labels=[('01','REACT + VITE','Selection · charts · export'),('02','FASTAPI','Fetch · vintage · metrics'),('03','ELEXON INSIGHTS','WINDFOR · FUELHH')]
        for i,(n,a,b) in enumerate(labels):
            y=168+i*160; fill='#1D413A' if i==0 else PANEL;out += [rect(850,y,580,108,fill,17,LINE),text(884,y+39,n,13,MINT,700,'Arial'),text(940,y+40,a,19,TEXT,700),text(940,y+73,b,14,MUTED)]
            if i<2: out += [line(1138,y+109,1138,y+151,MINT,2),f'<path d="M1131 {y+144} L1138 {y+154} L1145 {y+144}" fill="none" stroke="{MINT}" stroke-width="2"/>']
        out += [text(870,690,'Docker Compose runs the web and API services locally.',14,MUTED)]
    elif kind=='datasets':
        out += [rect(850,155,585,195,'#193B35',18,LINE),text(895,205,'FORECAST  /  WINDFOR',15,MINT,700,'Arial','letter-spacing="1.2"'),text(895,259,'startTime',20,TEXT,600),text(1110,259,'publishTime',20,TEXT,600),text(895,307,'generation (MW)',17,MUTED)]
        out += [rect(850,390,585,195,PANEL,18,LINE),text(895,440,'ACTUAL  /  FUELHH',15,LIME,700,'Arial','letter-spacing="1.2"'),text(895,494,'fuelType = WIND',20,TEXT,600),text(1110,494,'startTime',20,TEXT,600),text(895,542,'generation (MW)',17,MUTED)]
        out += [line(1140,355,1140,378,MINT,3),text(875,650,'JOIN KEY  →  SAME HALF-HOUR START TIME',15,MINT,700,'Arial','letter-spacing="1"')]
    elif kind=='timeline':
        out += [line(1030,190,1030,666,'#31574E',4)]
        rows=[('Delivery day − 4 days','Forecast lookback begins'),('Previous day · 10:00 UK','Decision cutoff → UTC'),('Each settlement period','Pick latest publishTime ≤ cutoff'),('Delivery day · 00:00–24:00','Match with FUELHH actuals')]
        for i,(a,b) in enumerate(rows):
            y=220+i*135; out += [f'<circle cx="1030" cy="{y-8}" r="10" fill="{MINT if i==2 else LIME}"/>',text(870,y,a,14,MINT if i==2 else LIME,700,'Arial','text-anchor="end"'),text(1080,y,b,18,TEXT,500)]
    elif kind=='formulas':
        formulas=[('MAE','mean(|forecast − actual|)','MW'),('RMSE','√ mean(error²)','MW'),('WAPE','Σ|error| / Σactual × 100','%'),('BIAS','mean(forecast − actual)','MW')]
        for i,(a,b,c) in enumerate(formulas):
            y=164+i*130;out += [rect(850,y,590,98,PANEL,15,LINE),text(882,y+41,a,15,MINT,700,'Arial','letter-spacing="1.2"'),text(1015,y+41,b,17,TEXT,500),text(1385,y+41,c,13,MUTED,600,'Arial','text-anchor="end"')]
    elif kind=='files':
        out += [rect(850,145,600,560,PANEL,22,LINE)]
        tree=[('northstar-wind-desk/',''),('├── backend/','FastAPI data + analysis'),('│   └── main.py',''),('├── frontend/src/','React dashboard + styles'),('├── docker-compose.yml','Local services'),('├── README.md','Runbook + design'),('├── CLIENT_PITCH.md','Customer walkthrough'),('└── video/','Demo source + deliverables')]
        for i,(a,b) in enumerate(tree):
            y=206+i*57;color=MINT if i in (0,1,3,7) else TEXT
            out += [text(890,y,a,17,color,600,'monospace'),text(1160,y,b,13,MUTED,400)]
    elif kind=='limits':
        out += [rect(840,135,610,600,PANEL,25,LINE),text(885,200,'BEFORE PRODUCTION',15,'#E8A86C',700,'Arial','letter-spacing="1.5"')]
        items=['Validate Elexon query parameters and schema','Confirm full January publication coverage','Handle pagination, throttling and upstream retries','Add monitoring and durable vintage snapshots','Connect demand and portfolio position']
        for i,t in enumerate(items):
            y=270+i*82;out += [f'<circle cx="900" cy="{y-7}" r="5" fill="{MINT if i<4 else LIME}"/>',text(925,y,t,17,TEXT,500)]
        out += [line(885,652,1400,652,'#3D5A50',1),text(885,696,'Forecast review only · no purchase recommendation',14,MUTED,500)]
    return ''.join(out)

def make_svg(scene, i):
    body=scene['narration']
    subtitle=scene['sub']
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
    <defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#0A1919"/><stop offset=".6" stop-color="#102725"/><stop offset="1" stop-color="#17332F"/></linearGradient><linearGradient id="card" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#1A3C36"/><stop offset="1" stop-color="#112A27"/></linearGradient><radialGradient id="glow"><stop stop-color="#1C8368" stop-opacity=".25"/><stop offset="1" stop-color="#112321" stop-opacity="0"/></radialGradient></defs>
    <rect width="1600" height="900" fill="url(#bg)"/><ellipse cx="1450" cy="55" rx="500" ry="400" fill="url(#glow)"/><path d="M0 820 Q360 690 760 840 T1600 800 V900 H0Z" fill="#0A1919" opacity=".55"/>
    <rect x="70" y="58" width="36" height="36" rx="10" fill="{MINT}"/><path d="M88 66 C85 74 85 82 88 88 M88 79 C95 75 97 70 97 66 M88 82 C82 80 78 76 78 72" fill="none" stroke="{DARK}" stroke-width="2.5" stroke-linecap="round"/>
    {text(120,82,'NORTHSTAR',18,TEXT,700,'Arial','letter-spacing="2.2"')}{text(120,104,'ENERGY TRADING  /  GB POWER DESK',9,MUTED,600,'Arial','letter-spacing="1.4"')}
    {text(70,161,scene['part'],14,MINT,700,'Arial','letter-spacing="2.0"')}
    {text(70,270,scene['title'],54,TEXT,700,'Arial','letter-spacing="-1.2"')}
    {text(70,322,scene['sub'],20,MUTED,400)}
    {text(70,392,'ELEXON WINDFOR  +  FUELHH',12,'#87A99F',600,'Arial','letter-spacing="1.6"')}
    {visual(scene['visual'])}
    <rect x="70" y="760" width="1460" height="1" fill="#29443F"/>
    {text(70,808,scene['tag'],13,'#B9CFC7',600,'Arial','letter-spacing="1.5"')}
    {text(1530,808,f'{i+1:02d}  /  {len(SCENES):02d}',13,'#89A79E',600,'monospace','text-anchor="end"')}
    {text(70,857,'NORTHSTAR WIND DESK',10,'#638078',500,'Arial','letter-spacing="2"')}{text(1530,857,'ILLUSTRATIVE SCREEN VISUALS · VERIFY LIVE ELEXON DATA BEFORE USE',9,'#708D83',500,'Arial','text-anchor="end" letter-spacing=".8"')}
    </svg>'''

def run(args):
    result=subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace'))
def probe(path):
    q=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(path)],capture_output=True,text=True,check=True)
    return float(json.loads(q.stdout)['format']['duration'])

def srt_time(seconds):
    ms=round(seconds*1000);h=ms//3600000;ms%=3600000;m=ms//60000;ms%=60000;sec=ms//1000;ms%=1000
    return f'{h:02d}:{m:02d}:{sec:02d},{ms:03d}'

def main():
    import textwrap
    RENDER.mkdir(parents=True,exist_ok=True)
    videos=[]; durations=[]; captions=[]
    font='/System/Library/Fonts/Supplemental/Arial.ttf'
    bold='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
    if not Path(bold).exists(): bold=font
    cursor=0
    for i,scene in enumerate(SCENES):
        mp4=RENDER/f'part-{i+1:02d}.mp4'
        d=max(14.0,len(scene['narration'].split())/2.2+5.0)
        durations.append(d)
        captions.append((cursor,cursor+d,scene['narration']))
        cursor+=d
        # Render a branded guide card. The complete talk track appears on the card and in SRT captions.
        filters=["drawbox=x=0:y=0:w=1600:h=900:color=0x0D201F:t=fill",
                 "drawbox=x=1360:y=0:w=240:h=700:color=0x122D28@0.75:t=fill",
                 "drawbox=x=0:y=840:w=1600:h=60:color=0x091716@0.8:t=fill",
                 "drawbox=x=70:y=58:w=36:h=36:color=0x50E0B3:t=fill"]
        text_items=[(70,82,'N',21,'0D201F',bold),(120,81,'NORTHSTAR',18,'F3F8F5',bold),(120,103,'ENERGY TRADING / GB POWER DESK',9,'A0B9B1',font),
                    (70,158,scene['part'],14,'50E0B3',bold),(70,250,scene['title'],40,'F3F8F5',bold),(70,305,scene['sub'],19,'A0B9B1',font),
                    (70,378,'ELEXON WINDFOR  +  FUELHH',12,'87A99F',bold),(70,784,scene['tag'],13,'B9CFC7',bold),
                    (70,865,'NORTHSTAR WIND DESK',10,'638078',font),(830,865,'ILLUSTRATIVE VISUALS · VERIFY LIVE ELEXON DATA BEFORE USE',9,'708D83',font),
                    (1510,784,f'{i+1:02d} / {len(SCENES):02d}',12,'89A79E',font)]
        def box(x,y,w,h,color='142C2A'):
            filters.append(f'drawbox=x={x}:y={y}:w={w}:h={h}:color=0x{color}:t=fill')
        def txt(x,y,value,size=18,color='F3F8F5',fontfile=font): text_items.append((x,y,str(value),size,color,fontfile))
        def card(x,y,w,h,title,sub=''):
            box(x,y,w,h,'173833');txt(x+20,y+32,title,12,'50E0B3',bold)
            if sub: txt(x+20,y+64,sub,16,'F3F8F5',bold)
        def panel_title(x,y,label): txt(x,y,label,13,'A0B9B1',bold)
        kind=scene['visual']
        if kind=='cover':
            box(820,120,650,630,'142C2A');panel_title(875,165,'POWER PROCUREMENT / UK')
            txt(875,280,'48',78,'F3F8F5',bold);txt(995,279,'settlement periods',22,'A0B9B1',font)
            txt(875,360,'ONE DECISION-DAY VIEW',14,'50E0B3',bold);txt(875,430,'Latest forecast before cutoff',20,'F3F8F5',bold);txt(875,476,'Compared with delivered wind',20,'F3F8F5',bold)
            txt(875,570,'JANUARY 2026',15,'50E0B3',bold)
            for rr in (42,76,110): box(1230,615,rr,3,'50E0B3')
        elif kind=='context':
            card(850,165,575,140,'THE BUYER’S QUESTION','How much supply might remain?')
            card(850,340,575,120,'PORTFOLIO REQUIREMENT','Consumer demand')
            card(850,490,575,120,'WIND CONTRIBUTION','Weather dependent')
            box(1050,640,380,68,'254E43');txt(1080,684,'Residual supply need · uncertainty first',16,'B8F36B',bold)
        elif kind=='dashboard':
            box(820,112,680,625,'102421');panel_title(865,160,'NORTHSTAR / WIND INTELLIGENCE');txt(865,211,'Thursday, 15 January 2026',24,'F3F8F5',bold)
            card(865,235,240,90,'DECISION CUTOFF','10:00 UK');card(1120,235,180,90,'SETTLEMENTS','48 periods');card(1315,235,150,90,'RESOLUTION','30 min')
            box(865,350,595,310,'122A27');panel_title(895,385,'FORECAST VS ACTUAL · MW')
            for yy in (430,480,530,580,630): box(895,yy,530,1,'29443F')
            for j in range(11):
                x=900+j*47; h1=35+((j*37)%115);h2=h1-5+(j%3*7)
                box(x,625-h1,5,h1,'50E0B3');box(x+9,625-h2,5,h2,'E4F4EB')
            box(1050,690,410,23,'493B25');txt(1060,707,'ILLUSTRATIVE VISUAL · NOT OBSERVED JANUARY VALUES',10,'F0C27E',bold)
        elif kind=='charts':
            box(825,130,650,580,'142C2A');panel_title(875,190,'FORECAST COMPARED WITH OUTTURN')
            for yy in (240,292,344,396,448): box(875,yy,550,1,'29443F')
            for j in range(11):
                x=882+j*48; h1=160+((j*37)%115);h2=h1-(j%3*9)+4
                box(x,465-h1,7,h1,'50E0B3');box(x+11,465-h2,7,h2,'E4F4EB')
            txt(875,505,'Forecast  /  Actual',13,'50E0B3',font);box(865,545,550,105,'193A35');txt(890,584,'One half-hour = one matched period',17,'F3F8F5',bold);txt(890,620,'Publication time remains auditable.',14,'A0B9B1',font)
            panel_title(875,695,'SIGNED ERROR BY SETTLEMENT PERIOD')
        elif kind=='metrics':
            for j,(lab,val,sub,col) in enumerate([('MAE','185 MW','Typical absolute miss','50E0B3'),('WAPE','7.4%','Absolute miss / actual volume','B8F36B'),('BIAS','+42 MW','Positive = over-forecast','E8A86C')]):
                y=160+j*170;box(845,y,590,135,'142C2A');txt(890,y+40,lab,14,'A0B9B1',bold);txt(890,y+87,val,32,'F3F8F5',bold);txt(890,y+115,sub,14,'A0B9B1',font)
            txt(875,715,'ILLUSTRATIVE VALUES ONLY',12,'F0C27E',bold)
        elif kind=='close':
            box(835,145,620,570,'142C2A');txt(890,210,'THE PILOT DELIVERS',15,'50E0B3',bold)
            for j,label in enumerate(['A cutoff-aware wind forecast','Forecast accuracy in clear units','Period-level evidence to export']):
                yy=293+j*100;txt(890,yy,f'0{j+1}',15,'50E0B3',bold);txt(950,yy,label,20,'F3F8F5',font);box(890,yy+26,490,1,'29443F')
            txt(890,650,'NEXT → CONNECT DEMAND + PORTFOLIO POSITION',14,'B8F36B',bold)
        elif kind=='divider':
            box(900,145,520,500,'142C2A');txt(970,245,'TECH LEAD',15,'50E0B3',bold);txt(970,335,'System',45,'F3F8F5',bold);txt(970,390,'walkthrough',45,'F3F8F5',bold);txt(970,475,'Data path · selection logic',18,'A0B9B1',font);txt(970,515,'Metrics · code map · limitations',18,'A0B9B1',font);box(970,565,375,3,'50E0B3')
        elif kind=='architecture':
            for j,(a,b) in enumerate([('REACT + VITE','Selection · charts · export'),('FASTAPI','Fetch · vintage · metrics'),('ELEXON INSIGHTS','WINDFOR · FUELHH')]):
                yy=168+j*160;box(850,yy,580,108,'1D413A' if j==0 else '142C2A');txt(884,yy+39,f'0{j+1}',13,'50E0B3',bold);txt(940,yy+40,a,19,'F3F8F5',bold);txt(940,yy+73,b,14,'A0B9B1',font)
                if j<2: box(1137,yy+109,3,37,'50E0B3')
            txt(870,690,'Docker Compose runs both services locally.',14,'A0B9B1',font)
        elif kind=='datasets':
            card(850,155,585,195,'FORECAST / WINDFOR','startTime      publishTime');txt(895,307,'generation (MW)',17,'A0B9B1',font)
            card(850,390,585,195,'ACTUAL / FUELHH','fuelType = WIND');txt(1110,494,'startTime',20,'F3F8F5',bold);txt(895,542,'generation (MW)',17,'A0B9B1',font)
            txt(875,650,'JOIN KEY → SAME HALF-HOUR START TIME',15,'50E0B3',bold)
        elif kind=='timeline':
            box(1028,190,4,476,'31574E')
            for j,(a,b) in enumerate([('Delivery day − 4 days','Lookback begins'),('Previous day · 10:00 UK','Decision cutoff → UTC'),('Each settlement period','Latest publishTime ≤ cutoff'),('Delivery day · 00:00–24:00','Join with actuals')]):
                yy=220+j*135;box(1018,yy-12,24,24,'50E0B3' if j==2 else 'B8F36B');txt(870,yy,a,14,'50E0B3' if j==2 else 'B8F36B',bold);txt(1080,yy,b,18,'F3F8F5',font)
        elif kind=='formulas':
            for j,(a,b,c) in enumerate([('MAE','mean(|forecast − actual|)','MW'),('RMSE','√ mean(error²)','MW'),('WAPE','Σ|error| / Σactual × 100','%'),('BIAS','mean(forecast − actual)','MW')]):
                yy=164+j*130;box(850,yy,590,98,'142C2A');txt(882,yy+41,a,15,'50E0B3',bold);txt(1015,yy+41,b,17,'F3F8F5',font);txt(1385,yy+41,c,13,'A0B9B1',bold)
        elif kind=='files':
            box(850,145,600,560,'142C2A')
            for j,(a,b) in enumerate([('northstar-wind-desk/',''),('├── backend/','FastAPI data + analysis'),('│   └── main.py',''),('├── frontend/src/','React dashboard + styles'),('├── docker-compose.yml','Local services'),('├── README.md','Runbook + design'),('├── CLIENT_PITCH.md','Customer walkthrough'),('└── video/','Demo source + deliverables')]):
                yy=206+j*57;txt(890,yy,a,16,'50E0B3' if j in (0,1,3,7) else 'F3F8F5',font);txt(1160,yy,b,12,'A0B9B1',font)
        elif kind=='limits':
            box(840,135,610,600,'142C2A');txt(885,200,'BEFORE PRODUCTION',15,'E8A86C',bold)
            for j,label in enumerate(['Validate API parameters and schema','Confirm January publication coverage','Handle pagination, throttling and retries','Add monitoring and stored snapshots','Connect demand and portfolio position']):
                yy=270+j*82;box(895,yy-10,10,10,'50E0B3' if j<4 else 'B8F36B');txt(925,yy,label,16,'F3F8F5',font)
            box(885,652,515,1,'3D5A50');txt(885,696,'Forecast review only · no purchase recommendation',13,'A0B9B1',font)
        # The complete voiceover script is displayed as readable on-screen talk track.
        body='\n'.join(textwrap.wrap(scene['narration'],width=48))
        body_path=RENDER/f'talktrack-{i+1:02d}.txt';body_path.write_text(body,encoding='utf-8')
        text_items.append((70,448,str(body_path),18,'D5E3DD',font))
        for x,y,value,size,color,fontfile in text_items:
            text_path=value if value.endswith('.txt') else None
            if text_path is None:
                text_path=str(RENDER/f'text-{i+1:02d}-{len(filters):03d}.txt');Path(text_path).write_text(value,encoding='utf-8')
            filters.append(f"drawtext=fontfile='{fontfile}':textfile='{text_path}':expansion=none:fontcolor=0x{color}:fontsize={size}:line_spacing=9:x={x}:y={y}")
        vf=','.join(filters)+f",fade=t=in:st=0:d=0.35,fade=t=out:st={max(0,d-0.4):.3f}:d=0.4,format=yuv420p"
        run(['ffmpeg','-y','-loglevel','error','-f','lavfi','-i',f'color=c=0x0D201F:s=1600x900:r={FPS}:d={d:.3f}','-vf',vf,'-frames:v',str(math.ceil(d*FPS)),'-an','-c:v','libx264','-preset','veryfast','-crf','26',str(mp4)])
        videos.append(mp4)
        print(f'{i+1:02d}. {scene["part"]}: {d:.1f}s — {scene["title"]}')
    inputs=[]
    for p in videos: inputs += ['-i',str(p)]
    filt=''.join(f'[{i}:v]' for i in range(len(videos)))+f'concat=n={len(videos)}:v=1:a=0[vout]'
    out=ROOT/'northstar-wind-desk-demo.mp4'
    run(['ffmpeg','-y','-loglevel','error',*inputs,'-filter_complex',filt,'-map','[vout]','-an','-c:v','libx264','-preset','medium','-crf','22','-movflags','+faststart',str(out)])
    total=probe(out)
    print(f'Output: {out} ({total/60:.2f} min)')
    print(f'Part 1 duration: {sum(durations[:6])/60:.2f} minutes')
    print(f'Part 2 duration: {sum(durations[6:])/60:.2f} minutes')
    srt='';cursor=0
    for i,(start,end,caption) in enumerate(captions,1):
        srt+=f'{i}\n{srt_time(start)} --> {srt_time(end)}\n{caption}\n\n'
    (ROOT/'northstar-wind-desk-demo.srt').write_text(srt,encoding='utf-8')
    (ROOT/'source'/'narration.json').write_text(json.dumps([{'part':s['part'],'title':s['title'],'narration':s['narration'],'seconds':round(d,2)} for s,d in zip(SCENES,durations)],indent=2),encoding='utf-8')

if __name__=='__main__': main()
