#!/usr/bin/env python3
"""Render the faster, graph-first competition demo for GEO autoresearch."""

from __future__ import annotations

import math
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import render_autoresearch_demo_video as ui


W, H, FPS, DURATION = 1920, 1080, 30, 42
ROOT = Path(__file__).resolve().parents[1] / "instances/eau/runs/live-5-round/visualization/demo"
BG, PANEL, TEXT, MUTED = ui.BG, ui.PANEL, ui.TEXT, ui.MUTED
PINK, TEAL, YELLOW, BLUE = ui.PINK, ui.TEAL, ui.YELLOW, ui.BLUE


def header(draw: ImageDraw.ImageDraw, n: int, label: str, progress: float) -> None:
    ui.text(draw, (74, 55), "AUTORESEARCH / DEPENDENCY GRAPH", 22, MUTED, bold=True)
    ui.text(draw, (1846, 55), f"0{n}  {label}", 21, MUTED, anchor="ra")
    draw.line((74, 92, 1846, 92), fill="#272d37", width=2)
    draw.rectangle((74, 90, 74 + int(1772 * progress), 94), fill=PINK)


def node(draw, x, y, title, kind, color, alpha=1.0, w=224, h=86, alert=False):
    ui.rr(draw, (x-w/2, y-h/2, x+w/2, y+h/2), 20, PANEL, color, 3)
    if alert:
        draw.ellipse((x+w/2-21, y-h/2-11, x+w/2+11, y-h/2+21), fill=PINK)
        ui.text(draw, (x+w/2-5, y-h/2+5), "!", 18, TEXT, anchor="mm", bold=True)
    ui.text(draw, (x, y-12), title, 23, TEXT, anchor="mm", alpha=alpha, bold=True)
    ui.text(draw, (x, y+21), kind, 15, color, anchor="mm", alpha=alpha, bold=True)


def edge(draw, a, b, color="#3a424d", width=4, label=None, progress=1.0):
    x1,y1=a; x2,y2=b
    x=x1+(x2-x1)*ui.ease(progress); y=y1+(y2-y1)*ui.ease(progress)
    ui.line(draw, (x1,y1,x,y), color, width)
    if label and progress>.75:
        ui.text(draw, ((x1+x2)/2,(y1+y2)/2-15),label,14,color,anchor="mm",bold=True)


def hook(t, draw):
    p=ui.appear(t,.05,.3)
    ui.text(draw,(960,305),"GEO 优化，不是改一个页面。",69,TEXT,anchor="mm",alpha=p,bold=True)
    ui.text(draw,(960,410),"是找到整张图里的阻塞点。",69,PINK,anchor="mm",alpha=ui.appear(t,.45,.35),bold=True)
    # Rapidly construct a graph under the title.
    pts=[(440,720),(720,610),(720,825),(1040,610),(1040,825),(1410,720)]
    links=[(0,1),(0,2),(1,3),(2,3),(2,4),(3,5),(4,5)]
    for i,(a,b) in enumerate(links):
        edge(draw,pts[a],pts[b],"#35404a",4,progress=ui.appear(t,.9+i*.09,.25))
    for i,(x,y) in enumerate(pts):
        a=ui.appear(t,.75+i*.08,.25)
        draw.ellipse((x-14,y-14,x+14,y+14),fill=TEAL if i<5 else PINK)
        if a<1: draw.ellipse((x-24*(1-a),y-24*(1-a),x+24*(1-a),y+24*(1-a)),outline=TEAL,width=2)
    ui.text(draw,(960,970),"BUILD  →  DIAGNOSE  →  MUTATE  →  MEASURE  →  REPEAT",22,MUTED,
            anchor="mm",alpha=ui.appear(t,1.6,.3),bold=True)


def build_graph(t, draw):
    header(draw,1,"BUILD",min(1,t/5.8))
    ui.text(draw,(74,155),"① 扫描仓库，把文件抽象成可优化节点",45,TEXT,bold=True)
    ui.text(draw,(74,210),"页面、结构化数据、外部证据、查询结果进入同一张图。",25,MUTED)
    # Files
    ui.rr(draw,(74,300,490,900),30,"#10141b",TEAL,3)
    ui.text(draw,(112,345),"REPOSITORY",18,TEAL,bold=True)
    files=[("index.html","page"),("paper.html","page"),("schema.json","entity"),("llms.txt","crawler"),("README.md","evidence")]
    for i,(name,kind) in enumerate(files):
        y=420+i*82; a=ui.appear(t,.2+i*.13,.25)
        ui.rr(draw,(108,y-27,454,y+27),13,"#161c25","#2c3540",1)
        ui.text(draw,(130,y),name,20,TEXT,anchor="lm",alpha=a,bold=True)
        ui.text(draw,(430,y),kind,14,MUTED,anchor="rm",alpha=a)
        # scanning beam
        bx=108+346*((t*.75+i*.1)%1)
        draw.line((bx,y-24,bx,y+24),fill=TEAL,width=2)
    # Extracted graph
    coords=[(730,410),(730,690),(1080,410),(1080,690),(1440,550)]
    defs=[("首页","IDENTITY",TEAL),("论文页","EVIDENCE",YELLOW),("JSON-LD","ENTITY",PINK),("GitHub","AUTHORITY",BLUE),("Agent 搜索","OUTCOME",PINK)]
    links=[(0,2,"contains"),(1,2,"describes"),(1,3,"cites"),(2,4,"retrieves"),(3,4,"verifies")]
    for i,(a,b,label) in enumerate(links):
        edge(draw,coords[a],coords[b],"#39434e",4,label,ui.appear(t,1.25+i*.18,.35))
    for i,(pos,d) in enumerate(zip(coords,defs)):
        node(draw,*pos,*d,alpha=ui.appear(t,.85+i*.15,.3))
    ui.rr(draw,(610,865,1760,940),20,"#0f1319","#303844",2)
    ui.text(draw,(650,902),"NODE",16,TEAL,bold=True)
    ui.text(draw,(760,902),"可修改实体",20,TEXT,bold=True)
    ui.text(draw,(1040,902),"EDGE",16,PINK,bold=True)
    ui.text(draw,(1140,902),"影响与可达关系",20,TEXT,bold=True)
    ui.text(draw,(1510,902),"OUTPUT",16,YELLOW,bold=True)
    ui.text(draw,(1625,902),"dependency graph",19,TEXT,bold=True)


def connect_graph(t, draw):
    header(draw,2,"CONNECT",min(1,t/5.5))
    ui.text(draw,(74,155),"② 不只看链接：识别四类依赖关系",45,TEXT,bold=True)
    ui.text(draw,(74,210),"静态引用、生成关系、语义支撑、真实检索共同决定可达路径。",25,MUTED)
    coords=[(230,480),(590,330),(590,650),(980,330),(980,650),(1420,480),(1710,480)]
    defs=[("首页","PAGE",TEAL),("JSON-LD","ENTITY",PINK),("论文页","EVIDENCE",YELLOW),("作者 ID","AUTHORITY",BLUE),("GitHub","AUTHORITY",BLUE),("搜索索引","RETRIEVAL",TEAL),("回答引用","OUTCOME",PINK)]
    links=[(0,1,"contains",TEAL),(0,2,"links",MUTED),(2,3,"attributes",YELLOW),(2,4,"cites",YELLOW),(1,5,"describes",PINK),(3,5,"verifies",BLUE),(4,5,"verifies",BLUE),(5,6,"retrieves",PINK)]
    for i,(a,b,label,color) in enumerate(links):
        edge(draw,coords[a],coords[b],color,4,label,ui.appear(t,.15+i*.17,.3))
    for i,(pos,d) in enumerate(zip(coords,defs)):
        node(draw,*pos,*d,w=190,h=78,alpha=ui.appear(t,.05+i*.08,.25))
    # moving signal along the end-to-end path
    path=[coords[i] for i in (0,2,4,5,6)]
    q=min(.999,(t*.24)%1); seg=q*(len(path)-1); si=int(seg); f=seg-si
    x=path[si][0]+(path[si+1][0]-path[si][0])*f; y=path[si][1]+(path[si+1][1]-path[si][1])*f
    draw.ellipse((x-12,y-12,x+12,y+12),fill=TEXT,outline=PINK,width=4)
    ui.rr(draw,(210,840,1710,935),22,"#10141b","#303844",2)
    tags=[("STATIC","HTML / JSON-LD",TEAL),("GENERATES","build pipeline",BLUE),("SUPPORTS","semantic evidence",YELLOW),("OBSERVED","live search",PINK)]
    for i,(cap,sub,color) in enumerate(tags):
        x=255+i*365
        ui.text(draw,(x,875),cap,16,color,bold=True)
        ui.text(draw,(x,908),sub,18,TEXT,bold=True)


def diagnose(t, draw):
    header(draw,3,"DIAGNOSE",min(1,t/5.5))
    ui.text(draw,(74,155),"③ 沿依赖路径排查：哪个节点真正阻塞曝光？",45,TEXT,bold=True)
    ui.text(draw,(74,210),"缺口 × 下游影响 × 路径阻塞 ÷ 修改成本，得到全局优先级。",25,MUTED)
    coords=[(190,520),(530,370),(530,670),(900,370),(900,670),(1300,520),(1660,520)]
    defs=[("首页","OK",TEAL),("JSON-LD","OK",TEAL),("论文页","GAP 0.82",PINK),("作者 ID","OK",TEAL),("引用簇","MISSING",PINK),("搜索索引","BLOCKED",YELLOW),("回答引用","0 / 4",PINK)]
    links=[(0,1),(0,2),(1,3),(2,4),(3,5),(4,5),(5,6)]
    for a,b in links:
        broken=(a,b)==(4,5)
        edge(draw,coords[a],coords[b],PINK if broken else "#39434e",7 if broken else 4,progress=1)
        if broken:
            mx=(coords[a][0]+coords[b][0])/2; my=(coords[a][1]+coords[b][1])/2
            ui.text(draw,(mx,my-18),"PATH BREAK",17,PINK,anchor="mm",bold=True)
    for i,(pos,d) in enumerate(zip(coords,defs)):
        alert=i in (2,4,5,6)
        node(draw,*pos,*d,w=190,h=80,alert=alert)
    # ranked issue panel slides in quickly
    a=ui.appear(t,1.0,.4)
    ui.rr(draw,(250,825,1670,960),24,"#10141b",PINK,3)
    ui.text(draw,(295,865),"PRIORITY #1",17,PINK,bold=True,alpha=a)
    ui.text(draw,(295,914),"引用簇 → 搜索索引",29,TEXT,bold=True,alpha=a)
    metrics=[("GAP","0.94",PINK),("REACH","4 nodes",TEAL),("BLOCK","critical",YELLOW),("COST","2h",MUTED),("SCORE","9.1",PINK)]
    for i,(k,v,c) in enumerate(metrics):
        x=720+i*185
        ui.text(draw,(x,856),k,14,MUTED,bold=True,alpha=a)
        ui.text(draw,(x,908),v,25,c,bold=True,alpha=a)
    # pulse the selected node
    x,y=coords[4]; pulse=18+10*(.5+.5*math.sin(t*7))
    draw.ellipse((x-110-pulse,y-58-pulse,x+110+pulse,y+58+pulse),outline=PINK,width=3)


def mutate(t, draw):
    header(draw,4,"MUTATE",min(1,t/5.4))
    ui.text(draw,(74,155),"④ 操作节点和边，生成可比较的候选图",45,TEXT,bold=True)
    ui.text(draw,(74,210),"增加证据节点、重写节点内容、移动关系边；每个候选独立测量。",25,MUTED)
    cards=[
        (90,"A  ADD NODE","新增引用簇",BLUE,"27.50","DISCARD"),
        (650,"B  REWIRE","连接论文 → 权威源",TEAL,"28.61","KEEP"),
        (1210,"C  REWRITE","强化实体描述",YELLOW,"26.90","DISCARD"),
    ]
    for i,(x,cap,title,color,score,status) in enumerate(cards):
        a=ui.appear(t,.15+i*.22,.35)
        ui.rr(draw,(x,300,x+510,800),28,PANEL,color,4)
        ui.text(draw,(x+36,345),cap,18,color,bold=True,alpha=a)
        ui.text(draw,(x+36,395),title,27,TEXT,bold=True,alpha=a)
        # mini graph
        pts=[(x+90,565),(x+250,470),(x+250,660),(x+415,565)]
        edge(draw,pts[0],pts[1],"#3a424d",3,progress=a)
        edge(draw,pts[0],pts[2],"#3a424d",3,progress=a)
        edge(draw,pts[1],pts[3],color,5,progress=a)
        edge(draw,pts[2],pts[3],color if i==1 else "#3a424d",5,progress=a)
        if i==0:
            extra=(x+330,690); edge(draw,pts[2],extra,color,4,progress=a); edge(draw,extra,pts[3],color,4,progress=a)
            draw.ellipse((extra[0]-11,extra[1]-11,extra[0]+11,extra[1]+11),fill=color)
        for px,py in pts: draw.ellipse((px-12,py-12,px+12,py+12),fill=color if (i==1 and px>x+200) else MUTED)
        ui.text(draw,(x+36,750),score,37,color,bold=True,alpha=a)
        ui.text(draw,(x+474,750),status,18,TEAL if status=="KEEP" else MUTED,anchor="rm",bold=True,alpha=a)
    ui.text(draw,(960,910),"candidate worktree  →  graph mutation  →  same evaluator",23,MUTED,anchor="mm",bold=True)
    if t>2.6:
        draw.rounded_rectangle((635,285,1175,815),34,outline=TEAL,width=5)


def iterate(t, draw):
    header(draw,5,"ITERATE",min(1,t/5.2))
    ui.text(draw,(74,150),"⑤ 测分、保留最佳图，再从它继续下一轮",45,TEXT,bold=True)
    ui.text(draw,(74,205),"Inner 快速筛选；真实搜索 Outer 决定 KEEP / DISCARD。",25,MUTED)
    # upper graph snapshots
    for r in range(4):
        x=160+r*440; y=375
        active=r <= int(min(3,t*.75))
        color=TEAL if active else "#333a45"
        ui.text(draw,(x,y-100),f"R{r}",18,color,bold=True)
        pts=[(x,y),(x+110,y-55),(x+110,y+55),(x+220,y)]
        for a,b in ((0,1),(0,2),(1,3),(2,3)): edge(draw,pts[a],pts[b],color,3,progress=1)
        for px,py in pts: draw.ellipse((px-8,py-8,px+8,py+8),fill=color)
        if r<3:
            edge(draw,(x+245,y),(x+390,y),PINK,3,progress=ui.appear(t,.35+r*.55,.25))
            ui.text(draw,(x+315,y-28),"MEASURE",13,MUTED,anchor="mm",bold=True)
    # lower autoresearch frontier
    x0,y0,x1,y1=170,875,1750,610
    draw.line((x0,y0,x1,y0),fill="#39414b",width=2)
    values=[27.97,28.08,28.25,27.50,25.42,25.50]
    best=np.maximum.accumulate(values); lo,hi=25,29
    xs=[x0+i*(x1-x0)/5 for i in range(6)]; yy=lambda v:y0-(v-lo)/(hi-lo)*(y0-y1)
    visible=max(1,min(6,int(ui.ease(t/4.2)*6)+1))
    pts=[(xs[i],yy(values[i])) for i in range(visible)]
    if len(pts)>1: ui.line(draw,pts,MUTED,3)
    stair=[]
    for i in range(visible):
        if i==0: stair.append((xs[i],yy(best[i])))
        else: stair += [(xs[i],yy(best[i-1])),(xs[i],yy(best[i]))]
    if len(stair)>1: ui.line(draw,stair,PINK,8)
    for i,(x,y) in enumerate(pts):
        keep=i==0 or values[i]>best[i-1]
        draw.ellipse((x-11,y-11,x+11,y+11),fill=TEAL if keep else MUTED)
        ui.text(draw,(x,y+31),f"R{i}",15,MUTED,anchor="mm",bold=True)
    if visible>=3: ui.text(draw,(xs[2]+20,yy(best[2])-30),"BEST 28.25",19,PINK,bold=True)
    ui.text(draw,(960,955),"图在变，候选在变，查询也可以扩展；唯一不变的是统一评测。",23,TEXT,anchor="mm",bold=True)


def close(t, draw):
    labels=[("SCAN",TEAL),("BUILD",BLUE),("DIAGNOSE",PINK),("MUTATE",YELLOW),("MEASURE",TEAL),("KEEP",PINK)]
    cx,cy=960,540
    for i,(label,color) in enumerate(labels):
        angle=-math.pi/2+i*2*math.pi/6+t*.12
        x=cx+390*math.cos(angle); y=cy+260*math.sin(angle)
        draw.line((cx,cy,x,y),fill="#303844",width=3)
        draw.ellipse((x-51,y-51,x+51,y+51),fill=PANEL,outline=color,width=4)
        ui.text(draw,(x,y),str(i+1),22,color,anchor="mm",bold=True)
        ui.text(draw,(x,y+76),label,16,color,anchor="mm",bold=True)
    draw.ellipse((cx-130,cy-130,cx+130,cy+130),fill="#10141b",outline=PINK,width=7)
    ui.text(draw,(cx,cy-25),"BEST GRAPH",24,MUTED,anchor="mm",bold=True)
    ui.text(draw,(cx,cy+32),"SO FAR",42,TEXT,anchor="mm",bold=True)
    ui.text(draw,(960,110),"DEPENDENCY-AWARE AUTORESEARCH",30,TEAL,anchor="mm",bold=True)
    ui.text(draw,(960,905),"从问题节点出发，让 Agent 曝光持续进化",42,TEXT,anchor="mm",bold=True)
    ui.text(draw,(960,970),"可解释 · 可测量 · 可回滚 · 可复现",24,PINK,anchor="mm",bold=True)


SCENES=[(0,3.5,hook),(3.5,10,build_graph),(10,16.5,connect_graph),(16.5,23,diagnose),
        (23,29.5,mutate),(29.5,36,iterate),(36,42,close)]


def render_frame(sec: float) -> Image.Image:
    im=Image.new("RGBA",(W,H),BG); draw=ImageDraw.Draw(im)
    for start,end,fn in SCENES:
        if start<=sec<end:
            fn(sec-start,draw)
            local=sec-start; fade=min(1,local/.16,(end-sec)/.16)
            if fade<1: im.alpha_composite(Image.new("RGBA",(W,H),(11,13,18,round(255*(1-fade)))))
            break
    draw.rectangle((0,H-7,W,H),fill="#252b35")
    draw.rectangle((0,H-7,int(W*sec/DURATION),H),fill=PINK)
    return im.convert("RGB")


def audio(path: Path) -> None:
    rate=48000; n=rate*DURATION; tt=np.arange(n)/rate; out=np.zeros(n)
    # Faster original pulse bed at 120 BPM.
    for f,phase in ((110,0),(164.81,.7),(220,1.4)):
        out += .025*np.sin(2*np.pi*f*tt+phase)*(0.55+.2*np.sin(2*np.pi*.08*tt+phase))
    beat=np.mod(tt,.5); out += .045*np.exp(-beat*15)*np.sin(2*np.pi*62*tt)
    for when in [3.5,10,16.5,23,29.5,36]:
        idx=np.arange(int(when*rate),min(n,int((when+.8)*rate))); rel=idx/rate-when
        out[idx]+=.075*np.exp(-rel*5)*np.sin(2*np.pi*880*rel)
    out*=np.minimum(1,tt/.8)*np.minimum(1,(DURATION-tt)/1.2)
    pcm=np.int16(out/max(np.max(np.abs(out)),1e-8)*11500)
    with wave.open(str(path),"wb") as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(rate); f.writeframes(np.column_stack((pcm,pcm)).tobytes())


def main() -> None:
    ROOT.mkdir(parents=True,exist_ok=True)
    silent=ROOT/"autoresearch-geo-demo-v2-silent.mp4"; wav=ROOT/"autoresearch-geo-demo-v2.wav"
    final=ROOT/"autoresearch-geo-demo-v2-42s.mp4"; cover=ROOT/"autoresearch-geo-demo-v2-cover.png"
    render_frame(2).save(cover)
    proc=subprocess.Popen(["ffmpeg","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),
        "-i","-","-an","-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",str(silent)],
        stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    assert proc.stdin
    for i in range(DURATION*FPS): proc.stdin.write(render_frame(i/FPS).tobytes())
    proc.stdin.close(); err=proc.stderr.read().decode(); code=proc.wait()
    if code: raise RuntimeError(err[-4000:])
    audio(wav)
    subprocess.run(["ffmpeg","-y","-i",str(silent),"-i",str(wav),"-c:v","copy","-c:a","aac","-b:a","160k",
                    "-shortest","-movflags","+faststart",str(final)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    silent.unlink(); wav.unlink(); print(final)


if __name__=="__main__": main()
