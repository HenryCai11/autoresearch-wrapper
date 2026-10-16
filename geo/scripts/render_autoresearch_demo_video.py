#!/usr/bin/env python3
"""Render a short competition demo of the dependency-aware GEO loop."""

from __future__ import annotations

import math
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


W, H, FPS, DURATION = 1920, 1080, 30, 50
ROOT = Path(__file__).resolve().parents[1] / "instances/eau/runs/live-5-round/visualization"
OUT = ROOT / "demo"
FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
BG = "#0b0d12"
PANEL = "#141821"
TEXT = "#f7f3eb"
MUTED = "#87909d"
PINK = "#ff477e"
TEAL = "#23c7b7"
YELLOW = "#ffc857"
BLUE = "#6c8cff"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    # WQY has one weight; a stroke is used for emphasis where needed.
    return ImageFont.truetype(FONT, size=size)


def ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def smooth(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def appear(t: float, start: float, span: float = .7) -> float:
    return ease((t - start) / span)


def text(draw: ImageDraw.ImageDraw, xy: tuple[float, float], value: str, size: int,
         color: str = TEXT, anchor: str = "la", alpha: float = 1.0, bold: bool = False) -> None:
    if alpha <= 0:
        return
    rgba = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer = ImageDraw.Draw(rgba)
    layer.text(xy, value, font=font(size, bold), fill=color + f"{round(255*alpha):02x}",
               anchor=anchor, stroke_width=1 if bold else 0, stroke_fill=color)
    draw._image.alpha_composite(rgba)


def rr(draw: ImageDraw.ImageDraw, box, radius=26, fill=PANEL, outline=None, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def line(draw: ImageDraw.ImageDraw, points, fill=TEXT, width=4):
    draw.line(points, fill=fill, width=width, joint="curve")


def header(draw: ImageDraw.ImageDraw, index: int, label: str):
    text(draw, (92, 68), "AUTORESEARCH / GEO", 25, MUTED, bold=True)
    text(draw, (1828, 68), f"0{index}  {label}", 23, MUTED, anchor="ra")
    draw.line((92, 106, 1828, 106), fill="#262c36", width=2)


def scene_hook(t: float, draw: ImageDraw.ImageDraw):
    a = appear(t, .2)
    text(draw, (960, 345), "网站上线，只是起点。", 76, TEXT, anchor="mm", alpha=a, bold=True)
    text(draw, (960, 445), "Agent 会不会找到你？", 76, PINK, anchor="mm", alpha=appear(t, 1.2), bold=True)
    text(draw, (960, 565), "把 GEO 变成一个可测量、可回滚、会学习的优化循环", 32, MUTED,
         anchor="mm", alpha=appear(t, 2.2))
    p = appear(t, 3.0)
    for i, label in enumerate(("SCAN", "EDIT", "MEASURE", "KEEP")):
        x = 570 + i * 260
        draw.ellipse((x-10, 718-10, x+10, 718+10), fill=TEAL if i < 3 else PINK)
        text(draw, (x, 760), label, 21, TEXT, anchor="ma", alpha=p, bold=True)
        if i < 3:
            draw.line((x+20, 718, x+240, 718), fill="#38414c", width=4)
    text(draw, (960, 930), "DEPENDENCY-AWARE  ×  LIVE SEARCH  ×  BEST-SO-FAR", 22, MUTED,
         anchor="mm", alpha=appear(t, 3.5), bold=True)


def scene_inputs(t: float, draw: ImageDraw.ImageDraw):
    header(draw, 1, "DEFINE")
    text(draw, (92, 185), "先把“优化”定义清楚", 54, TEXT, bold=True, alpha=appear(t, 0))
    text(draw, (92, 252), "三个输入，把模糊目标锁成一次可复现实验。", 28, MUTED, alpha=appear(t, .3))
    cards = [
        ("01", "REPOSITORY", "要改哪里", "代码、页面、数据与依赖", TEAL),
        ("02", "OBJECTIVE", "要提升什么", "目标查询与曝光口径", BLUE),
        ("03", "EVALUATOR", "怎样算更好", "Inner gate + Outer search", PINK),
    ]
    for i, (n, cap, title, sub, color) in enumerate(cards):
        a = appear(t, .7 + i*.35)
        y = 365
        x = 92 + i * 590
        h = 410 * a
        rr(draw, (x, y, x+535, y+h), 30, PANEL, color, 3)
        if a > .25:
            text(draw, (x+38, y+48), n, 24, color, bold=True, alpha=a)
            text(draw, (x+38, y+108), cap, 20, MUTED, bold=True, alpha=a)
            text(draw, (x+38, y+206), title, 42, TEXT, bold=True, alpha=a)
            text(draw, (x+38, y+275), sub, 24, MUTED, alpha=a)
            draw.line((x+38, y+335, x+497, y+335), fill="#2a303b", width=2)
            text(draw, (x+38, y+372), "LOCKED FOR THIS RUN", 18, color, bold=True, alpha=a)


def scene_graph(t: float, draw: ImageDraw.ImageDraw):
    header(draw, 2, "MAP")
    text(draw, (92, 175), "从文件列表，构建可操作的依赖图", 50, TEXT, bold=True)
    text(draw, (92, 237), "每个节点都有缺口、成本、可达结果；边表示改动如何传播。", 27, MUTED)
    nodes = [
        (210, 470, "首页", "identity", TEAL), (565, 365, "方法页", "capability", BLUE),
        (565, 610, "论文页", "evidence", YELLOW), (990, 365, "JSON-LD", "entity", PINK),
        (990, 610, "GitHub", "authority", TEAL), (1430, 490, "Agent 搜索", "outcome", PINK),
    ]
    edges = [(0,1),(0,2),(1,3),(2,3),(2,4),(3,5),(4,5)]
    ep = ease(t/2.8)
    for j, (a,b) in enumerate(edges):
        if ep < (j+1)/len(edges):
            continue
        x1,y1,*_ = nodes[a]; x2,y2,*_ = nodes[b]
        line(draw, (x1+115,y1+42,x2-115,y2+42), "#39414c", 4)
    for i, (x,y,title,sub,color) in enumerate(nodes):
        a = appear(t, .25+i*.18)
        rr(draw, (x-115, y, x+115, y+84), 22, PANEL, color, 3)
        text(draw, (x, y+30), title, 24, TEXT, anchor="mm", alpha=a, bold=True)
        text(draw, (x, y+62), sub, 16, color, anchor="mm", alpha=a)
    hp = 0.5 + .5*math.sin(t*3.2)
    x,y,*_ = nodes[2]
    draw.rounded_rectangle((x-129,y-14,x+129,y+98), 28, outline=YELLOW, width=round(2+4*hp))
    a = appear(t, 2.6)
    rr(draw, (230, 835, 1690, 945), 24, "#10141b", "#29313c", 2)
    text(draw, (280, 873), "NEXT NODE", 18, YELLOW, alpha=a, bold=True)
    text(draw, (460, 873), "论文页 / evidence", 26, TEXT, alpha=a, bold=True)
    text(draw, (910, 873), "缺口  HIGH", 22, PINK, alpha=a, bold=True)
    text(draw, (1160, 873), "成本  3h", 22, MUTED, alpha=a)
    text(draw, (1390, 873), "可达  citation", 22, TEAL, alpha=a, bold=True)


def scene_candidates(t: float, draw: ImageDraw.ImageDraw):
    header(draw, 3, "EXPLORE")
    text(draw, (92, 175), "每个想法，进入独立候选工作树", 50, TEXT, bold=True)
    text(draw, (92, 237), "候选从当前最佳版本分叉；失败可以丢弃，证据不会丢失。", 27, MUTED)
    root = (310, 535)
    draw.line((root[0], root[1], 650, root[1]), fill=TEAL, width=8)
    rr(draw, (115,470,310,600), 26, PANEL, TEAL, 3)
    text(draw, (212, 515), "KEEP", 21, TEAL, anchor="mm", bold=True)
    text(draw, (212, 557), "R2 · 28.25", 26, TEXT, anchor="mm", bold=True)
    branches = [
        ("A", "重写实体描述", 370, BLUE, "27.50", "DISCARD"),
        ("B", "补充引用入口", 535, PINK, "28.61", "KEEP"),
        ("C", "连接权威来源", 700, YELLOW, "25.50", "DISCARD"),
    ]
    for i,(tag,label,y,color,score,status) in enumerate(branches):
        p = appear(t, .4+i*.45)
        end = 1160 + i*100
        mid = 650 + (end-650)*p
        line(draw, (650,root[1],780,y,mid,y), color, 5)
        if p > .7:
            rr(draw, (end-205,y-60,end+205,y+60), 22, PANEL, color, 3)
            text(draw, (end-170,y), tag, 25, color, anchor="lm", bold=True)
            text(draw, (end-120,y-18), label, 24, TEXT, anchor="lm", bold=True)
            text(draw, (end-120,y+23), f"score {score}", 18, MUTED, anchor="lm")
            decision_color = TEAL if status == "KEEP" else MUTED
            text(draw, (end+165,y), status, 18, decision_color, anchor="rm", bold=True)
    text(draw, (960, 914), "git worktree  →  edit  →  measure  →  keep / discard", 25, MUTED,
         anchor="mm", alpha=appear(t, 2.4), bold=True)


def scene_evaluate(t: float, draw: ImageDraw.ImageDraw):
    header(draw, 4, "MEASURE")
    text(draw, (92, 175), "两层评测，解决“看起来更好”的错觉", 50, TEXT, bold=True)
    p = appear(t, .2)
    # Inner gate
    rr(draw, (90,330,650,810), 32, PANEL, TEAL, 3)
    text(draw, (135,382), "INNER LOOP", 20, TEAL, bold=True)
    text(draw, (135,445), "快速、确定、便宜", 31, TEXT, bold=True)
    checks = ["结构化数据", "抓取可达性", "实体一致性", "内容覆盖"]
    for i,label in enumerate(checks):
        y=525+i*62
        draw.ellipse((137,y-11,159,y+11), fill=TEAL)
        text(draw, (149,y), "✓", 16, BG, anchor="mm", bold=True)
        text(draw, (182,y), label, 23, TEXT, anchor="lm", alpha=p)
    text(draw, (600,765), "99.0", 53, TEAL, anchor="rm", bold=True)
    # bridge
    line(draw, (650,570,810,570), "#39414c", 5)
    text(draw, (730,535), "GATE", 18, MUTED, anchor="mm", bold=True)
    # Outer
    rr(draw, (810,300,1828,840), 32, PANEL, PINK, 3)
    text(draw, (855,352), "OUTER LOOP", 20, PINK, bold=True)
    text(draw, (855,415), "真实搜索，决定是否晋级", 31, TEXT, bold=True)
    engines = [("GPT SEARCH",BLUE),("CODEX",TEAL),("EXA",YELLOW),("TAVILY",PINK)]
    for i,(name,color) in enumerate(engines):
        x=855+(i%2)*440; y=510+(i//2)*115
        rr(draw,(x,y,x+385,y+76),18,"#0f131a",color,2)
        draw.ellipse((x+22,y+25,x+48,y+51),fill=color)
        text(draw,(x+68,y+39),name,21,TEXT,anchor="lm",bold=True)
        text(draw,(x+345,y+39),"QUERY",15,color,anchor="rm",bold=True)
    text(draw,(855,770),"mention  ·  attribution  ·  citation  ·  rank",21,MUTED,bold=True)
    text(draw,(1755,770),"28.25",50,PINK,anchor="rm",bold=True)
    text(draw,(960,925),"Inner 负责筛选候选；Outer 才是最终优化方向。",27,TEXT,anchor="mm",
         alpha=appear(t,2.3),bold=True)


def scene_frontier(t: float, draw: ImageDraw.ImageDraw):
    header(draw, 5, "DECIDE")
    text(draw, (92, 175), "Frontier 只记录历史最佳", 50, TEXT, bold=True)
    text(draw, (92, 237), "候选分数会上下波动；best-so-far 只会上升或保持水平。", 27, MUTED)
    x0,y0,x1,y1=150,840,1790,340
    draw.line((x0,y0,x1,y0),fill="#3b434e",width=3)
    draw.line((x0,y0,x0,y1),fill="#3b434e",width=3)
    vals=[27.97,28.08,28.25,27.50,25.42,25.50]
    best=np.maximum.accumulate(vals)
    lo,hi=25.0,29.0
    xs=[x0+i*(x1-x0)/5 for i in range(6)]
    ys=lambda v:y0-(v-lo)/(hi-lo)*(y0-y1)
    for tick in range(25,30):
        y=ys(tick); draw.line((x0,y,x1,y),fill="#202631",width=2)
        text(draw,(x0-25,y),str(tick),18,MUTED,anchor="rm")
    progress=ease(t/3.8)
    visible=max(1,min(6,int(progress*6)+1))
    pts=[(xs[i],ys(vals[i])) for i in range(visible)]
    if len(pts)>1: line(draw,pts,"#737e87",4)
    for i,(x,y) in enumerate(pts):
        keep=i==0 or vals[i]>best[i-1]
        draw.ellipse((x-12,y-12,x+12,y+12),fill=TEAL if keep else MUTED)
        text(draw,(x,y+41),f"R{i}",18,MUTED,anchor="mm",bold=True)
    # Step line drawn segment by segment, making the horizontal incumbent explicit.
    step=[]
    for i in range(visible):
        if i==0: step.append((xs[i],ys(best[i])))
        else: step.extend([(xs[i],ys(best[i-1])),(xs[i],ys(best[i]))])
    if len(step)>1: line(draw,step,PINK,9)
    if visible>=3:
        text(draw,(xs[2]+35,ys(best[2])-40),"BEST 28.25",24,PINK,bold=True)
    if visible==6:
        text(draw,(1400,450),"R3–R5 未超过 incumbent",23,MUTED,anchor="mm")
        text(draw,(1400,500),"FRONTIER 保持水平",27,PINK,anchor="mm",bold=True)
    text(draw,(960,970),"KEEP improvements.  DISCARD regressions.  RETAIN every trace.",21,MUTED,
         anchor="mm",bold=True)


def scene_close(t: float, draw: ImageDraw.ImageDraw):
    p=appear(t,.1)
    text(draw,(960,175),"ONE LOOP.  BETTER EVIDENCE.",25,TEAL,anchor="mm",alpha=p,bold=True)
    text(draw,(960,315),"扫描 → 推理 → 修改 → 搜索 → 决策",57,TEXT,anchor="mm",alpha=p,bold=True)
    cx,cy=960,610
    labels=[("DEPENDENCY",-90,TEAL),("CANDIDATE",-18,BLUE),("EVALUATE",54,PINK),("KEEP",126,YELLOW),("REPEAT",198,TEAL)]
    for i,(label,deg,color) in enumerate(labels):
        a=appear(t,.5+i*.18)
        rad=math.radians(deg+t*3)
        x=cx+350*math.cos(rad); y=cy+190*math.sin(rad)
        draw.line((cx,cy,x,y),fill="#2d3540",width=3)
        draw.ellipse((x-54,y-54,x+54,y+54),fill=PANEL,outline=color,width=4)
        text(draw,(x,y),str(i+1),24,color,anchor="mm",alpha=a,bold=True)
        text(draw,(x,y+82),label,17,color,anchor="mm",alpha=a,bold=True)
    draw.ellipse((cx-105,cy-105,cx+105,cy+105),fill="#10151c",outline=PINK,width=6)
    text(draw,(cx,cy-12),"BEST",23,MUTED,anchor="mm",bold=True)
    text(draw,(cx,cy+35),"SO FAR",34,TEXT,anchor="mm",bold=True)
    text(draw,(960,925),"AUTORESEARCH WRAPPER  ·  DEPENDENCY-AWARE OPTIMIZATION",23,MUTED,
         anchor="mm",alpha=appear(t,2.3),bold=True)
    text(draw,(960,980),"让每一次 vibe coding 都能被测量、比较和复现",29,PINK,
         anchor="mm",alpha=appear(t,2.8),bold=True)


SCENES = [
    (0, 6, scene_hook), (6, 13, scene_inputs), (13, 21, scene_graph),
    (21, 29, scene_candidates), (29, 37, scene_evaluate),
    (37, 45, scene_frontier), (45, 50, scene_close),
]


def render_frame(seconds: float) -> Image.Image:
    image=Image.new("RGBA",(W,H),BG)
    draw=ImageDraw.Draw(image)
    for start,end,fn in SCENES:
        if start <= seconds < end or (seconds >= DURATION and end == DURATION):
            fn(seconds-start,draw)
            # small scene transition without hiding the core motion
            local=seconds-start; length=end-start
            fade=min(1.0,local/.28,(length-local)/.28)
            if fade<1:
                veil=Image.new("RGBA",(W,H),(11,13,18,round(255*(1-fade))))
                image.alpha_composite(veil)
            break
    # timeline
    draw.rectangle((0,H-8,W,H),fill="#202631")
    draw.rectangle((0,H-8,int(W*seconds/DURATION),H),fill=PINK)
    return image.convert("RGB")


def synth_audio(path: Path) -> None:
    rate=48000; n=rate*DURATION; tt=np.arange(n)/rate
    audio=np.zeros(n,dtype=np.float64)
    # Quiet, original ambient bed: fifths, slow pulse, and scene-change chimes.
    freqs=[110.0,164.81,220.0,246.94]
    for i,f in enumerate(freqs):
        lfo=.45+.18*np.sin(2*np.pi*(.035+i*.006)*tt+i)
        audio += .035*lfo*np.sin(2*np.pi*f*tt+i*.8)
    beat=np.mod(tt,1.0)
    audio += .025*np.exp(-beat*9)*np.sin(2*np.pi*55*tt)
    for when in [6,13,21,29,37,45]:
        idx=np.arange(max(0,int((when-.05)*rate)),min(n,int((when+1.4)*rate)))
        rel=idx/rate-when
        env=np.where(rel>=0,np.exp(-rel*3.2),0)
        audio[idx] += .07*env*np.sin(2*np.pi*660*rel)
        audio[idx] += .035*env*np.sin(2*np.pi*990*rel)
    audio*=np.minimum(1,tt/1.5)*np.minimum(1,(DURATION-tt)/1.8)
    peak=max(1e-9,np.abs(audio).max()); pcm=np.int16(audio/peak*11000)
    with wave.open(str(path),"wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(np.column_stack([pcm,pcm]).tobytes())


def main() -> None:
    OUT.mkdir(parents=True,exist_ok=True)
    video=OUT/"autoresearch-geo-demo-silent.mp4"
    audio=OUT/"autoresearch-geo-demo-bed.wav"
    final=OUT/"autoresearch-geo-demo-50s.mp4"
    cover=OUT/"autoresearch-geo-demo-cover.png"
    render_frame(2.6).save(cover)
    proc=subprocess.Popen([
        "ffmpeg","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}",
        "-r",str(FPS),"-i","-","-an","-c:v","libx264","-preset","medium","-crf","18",
        "-pix_fmt","yuv420p","-movflags","+faststart",str(video)
    ],stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    assert proc.stdin is not None
    for frame in range(DURATION*FPS):
        proc.stdin.write(render_frame(frame/FPS).tobytes())
    proc.stdin.close(); stderr=proc.stderr.read().decode(); code=proc.wait()
    if code: raise RuntimeError(stderr[-4000:])
    synth_audio(audio)
    subprocess.run([
        "ffmpeg","-y","-i",str(video),"-i",str(audio),"-c:v","copy","-c:a","aac","-b:a","160k",
        "-shortest","-movflags","+faststart",str(final)
    ],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    video.unlink()
    audio.unlink()
    print(final)


if __name__ == "__main__":
    main()
