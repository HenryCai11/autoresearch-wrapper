#!/usr/bin/env python3
"""Render the EAU inner/outer optimization history as a static chart and MP4."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter
from matplotlib.patches import Circle
import numpy as np


ROOT = Path(__file__).resolve().parents[1] / "instances/eau/runs/live-5-round"
OUT = ROOT / "visualization"
ROUND_DIRS = [
    "round-0-pre-geo-baseline",
    "round-1-exact-identity",
    "round-2-fuzzy-capability",
    "round-3-broad-domain",
    "round-4-authority-relations",
    "round-5-cross-engine-residuals",
]
SHORT = ["Baseline", "Identity", "Capability", "Research context", "Entity graph", "GitHub bridge"]
DETAIL = [
    "Pre-GEO site",
    "Machine-readable identity",
    "Focused method page",
    "Broad-topic context page",
    "Bibliographic entity graph",
    "Repository authority links",
]
INNER = [43.43, 74.43, 86.83, 92.33, 99.00, 99.00]
OUTER = [27.97, 28.08, 28.25, 27.50, 25.42, 18.50]
SUCCESS = [0.9167, 0.9000, 0.9000, 0.8667, 0.8333, 0.7167]
STATUS = ["baseline", "kept", "best", "no lift", "inconclusive", "no immediate lift"]
W = {"site_cited": 0.45, "attributed": 0.25, "reciprocal_rank": 0.20, "mention": 0.10}


def yes(value: str) -> bool:
    return value.lower() == "true"


def load_cells() -> tuple[list[list[float]], list[float]]:
    cells, valid_scores = [], []
    for directory in ROUND_DIRS:
        rows = list(csv.DictReader((ROOT / directory / "search-matrix.csv").open()))
        contribution = []
        valid = []
        for row in rows:
            value = 100 * (
                W["site_cited"] * yes(row["site_cited"])
                + W["attributed"] * yes(row["attributed"])
                + W["reciprocal_rank"] * float(row["reciprocal_rank"])
                + W["mention"] * yes(row["mention"])
            )
            contribution.append(value)
            if not yes(row["answer_empty"]):
                valid.append(value)
        cells.append(contribution)
        valid_scores.append(round(sum(valid) / len(valid), 2))
    return cells, valid_scores


CELLS, VALID = load_cells()
BEST = np.maximum.accumulate(OUTER)
X = np.arange(6)


def draw(limit: float, output: Path | None = None) -> None:
    visible = int(np.floor(limit))
    progress = limit - visible
    upto = min(visible + 1, 6)
    fig = plt.figure(figsize=(16, 10), facecolor="#fbfaf7")
    graph = fig.add_axes([0.055, 0.43, 0.89, 0.51])
    chart = fig.add_axes([0.075, 0.09, 0.85, 0.28])
    graph.set_xlim(-0.5, 5.5); graph.set_ylim(-0.15, 1.2); graph.axis("off")

    fig.text(0.06, 0.965, f"STEP  {min(visible + 1, 6)} / 6", fontsize=11, color="#697176", weight="bold")
    score = VALID[min(visible, 5)]
    fig.text(0.06, 0.925, "VALID-RESPONSE OUTER", fontsize=10, color="#697176", weight="bold")
    fig.text(0.06, 0.875, f"{score:.2f}", fontsize=28, color="#15191c", weight="bold")
    fig.text(0.25, 0.925, "EAU GEO optimization", fontsize=23, weight="bold", color="#15191c")
    fig.text(0.25, 0.89, "Each intervention is admitted by readiness and judged by live search.", fontsize=12, color="#697176")

    positions = [(0, .55), (1, .86), (2, .60), (3, .92), (4, .56), (5, .83)]
    for i in range(1, upto):
        a, b = positions[i-1], positions[i]
        graph.plot([a[0], b[0]], [a[1], b[1]], color="#cbd2d1", lw=1.5, zorder=1)
    for i in range(upto):
        px, py = positions[i]
        color = "#07867f" if i <= 2 else ("#ff4f83" if i == visible else "#bac2c2")
        edge = "#ff4f83" if i >= 3 else "#07867f"
        radius = .12 if i == visible else .085
        graph.add_patch(Circle((px, py), radius, facecolor=color if i <= 2 else "#fbfaf7", edgecolor=edge, lw=2.2, zorder=3))
        graph.text(px, py, f"R{i}", ha="center", va="center", fontsize=9, weight="bold", color="white" if i <= 2 else "#32383b")
        graph.text(px, py-.17, SHORT[i], ha="center", va="top", fontsize=10, weight="bold", color="#202528")
        graph.text(px, py-.235, STATUS[i], ha="center", va="top", fontsize=8.5, color=edge)
        if i > 0:
            for j, label in enumerate(("exact", "fuzzy", "broad")):
                oy = py + .13 + j*.055
                graph.plot([px, px+.25], [py, oy], color="#e4e7e5", lw=.8, zorder=0)
                graph.scatter([px+.25], [oy], s=16, color="#d8ddda", zorder=2)
    graph.text(visible, positions[visible][1]+.19, DETAIL[visible], ha="center", fontsize=10.5, color="#ff4f83", weight="bold")

    chart.set_facecolor("#fbfaf7")
    chart.set_xlim(-.25, 5.25); chart.set_ylim(0, 105)
    chart.spines[["top", "right"]].set_visible(False)
    chart.spines[["left", "bottom"]].set_color("#c7cecc")
    chart.grid(axis="y", color="#e7eae7", linewidth=.8)
    chart.set_ylabel("score", color="#697176")
    chart.set_xticks(X, [f"R{i}\n{SHORT[i]}" for i in range(6)], fontsize=9)
    chart.tick_params(colors="#697176")

    rng = np.random.default_rng(7)
    for i in range(upto):
        jitter = rng.uniform(-.09, .09, len(CELLS[i]))
        chart.scatter(np.full(len(CELLS[i]), i)+jitter, CELLS[i], s=9, color="#c7cdca", alpha=.28, edgecolors="none", zorder=1)
    chart.plot(X[:upto], INNER[:upto], color="#07867f", lw=2.2, marker="o", label="inner readiness proxy", zorder=4)
    chart.plot(X[:upto], OUTER[:upto], color="#bca6ad", lw=1.3, ls=":", marker="o", label="outer: all scheduled cells", zorder=3)
    chart.plot(X[:upto], VALID[:upto], color="#ff4f83", lw=2.2, marker="o", mfc="#fbfaf7", label="outer: valid responses", zorder=5)
    chart.step(X[:upto], BEST[:upto], where="post", color="#c8255d", lw=3.0, label="best observed outer", zorder=3)
    chart.legend(loc="upper left", ncol=2, frameon=False, fontsize=9)
    for i in range(upto):
        chart.text(i, OUTER[i]-6.5, f"{OUTER[i]:.2f} all\n{SUCCESS[i]*100:.0f}% returned", ha="center", fontsize=8, color="#8b4a61")
    if visible == 5:
        chart.annotate("Codex probe failed: 0/15", xy=(5, OUTER[5]), xytext=(4.15, 8),
                       arrowprops={"arrowstyle": "->", "color": "#8b4a61"},
                       fontsize=9, color="#8b4a61", weight="bold")
    chart.text(5.2, 101, "60 observations per round", ha="right", va="top", fontsize=8.5, color="#8a9293")
    fig.text(.93, .035, "inner qualifies candidates · outer decides promotion", ha="right", fontsize=9.5, color="#697176")
    if output:
        fig.savefig(output, dpi=180, facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    draw(5, OUT / "eau-geo-score-curve.png")
    frames = OUT / "frames"
    frames.mkdir(exist_ok=True)
    for i in range(6):
        draw(i, frames / f"step-{i:02d}.png")
    data = []
    for i in range(6):
        data.append({"round": i, "change": SHORT[i], "inner": INNER[i], "outer_all": OUTER[i], "outer_valid": VALID[i], "answer_success": SUCCESS[i], "best_outer": float(BEST[i]), "status": STATUS[i]})
    with (OUT / "score-curve-data.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=data[0].keys()); writer.writeheader(); writer.writerows(data)
    (OUT / "score-curve-data.json").write_text(json.dumps(data, indent=2) + "\n")

    fig = plt.figure(figsize=(16, 10))
    def animate(frame: int):
        plt.close(fig)
        step = min(frame // 18, 5)
        draw(step, frames / f"anim-{frame:03d}.png")
        return []
    # Rendered step frames are assembled by ffmpeg outside matplotlib to keep output deterministic.
    print(json.dumps({"png": str(OUT / 'eau-geo-score-curve.png'), "frames": str(frames), "csv": str(OUT / 'score-curve-data.csv')}))


if __name__ == "__main__":
    main()
