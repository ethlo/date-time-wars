#!/usr/bin/env python3
"""
report.py - turn a JMH json result into something humans want to look at.

    python3 report.py results/latest/jmh-result.json
    python3 report.py run.json -o out/ --baseline previous.json

Produces, in the output directory (default: next to the input file):

    report.md                 markdown tables, ready to paste into the README
    report.html               self-contained page with SVG bar charts + tables
    report.png                matplotlib chart (only if matplotlib is installed)
    summary.md                one headline ITU-vs-JDK row per method, for the ITU README
    summary.png               compact speed-up chart, transparent for light/dark READMEs
    jmh-result-grouped.json   the input, relabelled and sorted, for jmh.morethan.io

and prints a ranked summary to the terminal. No dependencies beyond the stdlib.
"""

import argparse
import html
import io
import json
import math
import os
import sys
from collections import OrderedDict, defaultdict
from datetime import datetime

# --- candidate naming ---------------------------------------------------------
# Benchmarks live in candidates.<id>.<Class>.<method>; <id> is the candidate key.
# Add a pretty name here when the package name isn't good enough.
LABELS = {
    "itu": "ITU",
    "itu_configurable": "ITU (configurable)",
    "itu_clamped": "ITU (hours)",
    "itu_duration": "ITU",  # legacy package name
    "jdk": "JDK java.time",
    "jdk_instant": "JDK Instant",
    "google": "Google HTTP client",
}

# Report sections: heading -> benchmark methods in display order. Methods not
# listed here end up under "Other".
SECTIONS = OrderedDict([
    ("Date-time parsing", ["parse", "parseLenient"]),
    ("Date-time formatting", ["formatSeconds", "formatMillis", "formatNanos"]),
    ("Duration", ["parseDuration", "formatDuration"]),
])
METHOD_DESC = {
    "parse": "strict RFC-3339 / ISO-8601 date-time",
    "parseLenient": "lenient date-time (optional fields)",
    "formatSeconds": "format UTC, second resolution",
    "formatMillis": "format UTC, millisecond resolution",
    "formatNanos": "format UTC, nanosecond resolution",
    "parseDuration": "ISO-8601 duration",
    "formatDuration": "ISO-8601 duration",
}
_METHOD_ORDER = {m: i for i, m in enumerate(m for ms in SECTIONS.values() for m in ms)}

# The headline summary (summary.md / summary.png) reduces the whole run to one
# "how much faster is ITU than the JDK" row per benchmark method.
SUMMARY_SUBJECT = "ITU"
SUMMARY_BASELINE = "JDK java.time"


def section_of(method):
    return next((h for h, ms in SECTIONS.items() if method in ms), "Other")


def method_sort_key(method):
    return (_METHOD_ORDER.get(method, len(_METHOD_ORDER)), method)


# Categorical palette (light / dark) - fixed slot order, assigned per candidate.
PALETTE_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
PALETTE_DARK = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"]


# --- data model ---------------------------------------------------------------
class Result:
    __slots__ = ("candidate", "label", "clazz", "method", "params", "score", "error",
                 "unit", "alloc", "raw", "entry")

    def __init__(self, entry):
        parts = entry["benchmark"].split(".")
        self.entry = entry
        if len(parts) == 2:
            # already-grouped format written by this script: <method>.<candidate>
            self.method, self.candidate = parts
            self.clazz = self.candidate
        else:
            self.method = parts[-1]
            self.clazz = parts[-2]
            # candidates.<id>.<Class>.<method> -> <id>; fall back to the class name
            self.candidate = parts[1] if len(parts) >= 4 and parts[0] == "candidates" else self.clazz
        self.label = LABELS.get(self.candidate, self.candidate)
        self.params = OrderedDict(sorted((entry.get("params") or {}).items()))
        pm = entry["primaryMetric"]
        self.score = float(pm["score"])
        self.error = _num(pm.get("scoreError"))
        self.unit = pm.get("scoreUnit", "")
        self.raw = [x for fork in pm.get("rawData", []) for x in fork]
        alloc = (entry.get("secondaryMetrics") or {}).get("gc.alloc.rate.norm")
        self.alloc = float(alloc["score"]) if alloc else None

    @property
    def scenario_key(self):
        return (self.method, tuple(self.params.items()))

    @property
    def key(self):
        return (self.candidate,) + self.scenario_key


def _num(v):
    try:
        f = float(v)
        return 0.0 if math.isnan(f) else f
    except (TypeError, ValueError):
        return 0.0


def load(path):
    with open(path) as f:
        return [Result(e) for e in json.load(f)]


def scenario_title(method, params):
    if not params:
        return method + "()"
    return "%s(%s)" % (method, ", ".join('"%s"' % v for _, v in params))


def group(results):
    """-> OrderedDict method -> OrderedDict scenario_key -> [Result sorted fastest first]"""
    by_method = OrderedDict()
    for r in sorted(results, key=lambda r: (method_sort_key(r.method), tuple(r.params.items()), r.score)):
        by_method.setdefault(r.method, OrderedDict()).setdefault(r.scenario_key, []).append(r)
    return by_method


def by_section(by_method):
    """-> OrderedDict section heading -> OrderedDict method -> scenarios"""
    out = OrderedDict()
    for method, scenarios in by_method.items():
        out.setdefault(section_of(method), OrderedDict())[method] = scenarios
    return out


def candidate_slots(results):
    """Stable color slot per candidate label: LABELS order first, unknown labels alphabetically after."""
    known = list(OrderedDict.fromkeys(LABELS.values()))
    labels = {r.label for r in results}
    ordered = [l for l in known if l in labels] + sorted(labels - set(known))
    return {l: i for i, l in enumerate(ordered)}


# --- formatting helpers -------------------------------------------------------
def fmt_num(v, digits=None):
    if v is None:
        return "-"
    if digits is None:
        digits = 2 if v < 10 else (1 if v < 100 else 0)
    return "{:,.{d}f}".format(v, d=digits)


def fmt_delta(pct):
    if pct is None:
        return ""
    return "%+.1f%%" % pct


def rel(r, best):
    return r.score / best.score if best.score else float("nan")


def read_properties(path):
    props = OrderedDict()
    if os.path.isfile(path):
        with open(path) as f:
            for line in f:
                if "=" in line:
                    k, v = line.rstrip("\n").split("=", 1)
                    props[k] = v
    return props


def environment(results, props):
    e = results[0].entry
    env = OrderedDict()
    env["Date"] = props.get("date", datetime.now().isoformat(timespec="seconds"))
    if props.get("label"):
        env["Run"] = props["label"]
    env["JDK"] = "%s (%s %s)" % (e.get("jdkVersion", "?"), e.get("vmName", ""), e.get("vmVersion", ""))
    env["JVM args"] = " ".join(e.get("jvmArgs", [])) or "-"
    env["Iterations"] = "%s fork(s), %s × %s warmup, %s × %s measurement" % (
        e.get("forks"), e.get("warmupIterations"), e.get("warmupTime"),
        e.get("measurementIterations"), e.get("measurementTime"))
    for k, name in (("cpu", "CPU"), ("os", "OS"), ("git", "Git")):
        if props.get(k):
            env[name] = props[k]
    return env


# --- terminal -----------------------------------------------------------------
def print_summary(by_method, baseline, out):
    color = out.isatty()
    B, D, G, R, Y, X = (("\033[1m", "\033[2m", "\033[32m", "\033[31m", "\033[33m", "\033[0m")
                        if color else ("",) * 6)
    has_alloc = any(r.alloc is not None for scen in by_method.values() for rs in scen.values() for r in rs)
    for section, methods in by_section(by_method).items():
        print("\n%s%s%s %s%s%s" % (B, "═" * 3, X, B, section, X), file=out)
        for method, scenarios in methods.items():
            for (m, params), rs in scenarios.items():
                best = rs[0]
                print("\n%s%s%s  %s%s%s" % (B, scenario_title(m, params), X, D, METHOD_DESC.get(m, ""), X), file=out)
                width = max(len(r.label) for r in rs)
                hdr = "  %-3s %-*s %17s %8s" % ("#", width, "candidate", best.unit, "rel")
                if has_alloc:
                    hdr += " %10s" % "B/op"
                if baseline:
                    hdr += " %10s" % "vs base"
                print(D + hdr + X, file=out)
                for i, r in enumerate(rs, 1):
                    line = "  %-3d %-*s %8s ±%-7s %7.2f×" % (
                        i, width, r.label, fmt_num(r.score), fmt_num(r.error, 1), rel(r, best))
                    if has_alloc:
                        line += " %10s" % fmt_num(r.alloc, 0)
                    if baseline:
                        d = delta(r, baseline)
                        if d is None:
                            line += " %10s" % "new"
                        else:
                            c = G if d < -1 else (R if d > 1 else "")
                            line += " %s%10s%s" % (c, fmt_delta(d), X)
                    print(line, file=out)
    print(file=out)


def delta(r, baseline):
    b = baseline.get(r.key)
    if b is None or not b.score:
        return None
    return (r.score - b.score) / b.score * 100.0


# --- markdown -----------------------------------------------------------------
def write_markdown(path, by_method, env, baseline, title):
    has_alloc = any(r.alloc is not None for scen in by_method.values() for rs in scen.values() for r in rs)
    lines = ["# %s" % title, ""]
    for k, v in env.items():
        lines.append("* **%s:** %s" % (k, v))
    lines.append("")
    lines.append("Lower is better. *rel* is the score relative to the fastest candidate in the same row.")
    lines.append("")
    for section, methods in by_section(by_method).items():
        lines.append("## %s" % section)
        lines.append("")
        for method, scenarios in methods.items():
            lines.append("### %s" % method)
            if METHOD_DESC.get(method):
                lines.append("")
                lines.append("*%s*" % METHOD_DESC[method])
            lines.append("")
            for (m, params), rs in scenarios.items():
                best = rs[0]
                lines.append("#### `%s`" % scenario_title(m, params))
                lines.append("")
                hdr = ["#", "Candidate", best.unit, "± error", "rel"]
                if has_alloc:
                    hdr.append("B/op")
                if baseline:
                    hdr.append("vs baseline")
                lines.append("| " + " | ".join(hdr) + " |")
                lines.append("|" + "|".join("---:" if i not in (1,) else ":---" for i in range(len(hdr))) + "|")
                for i, r in enumerate(rs, 1):
                    row = [str(i), ("**%s**" % r.label) if i == 1 else r.label,
                           fmt_num(r.score), fmt_num(r.error, 1), "%.2f×" % rel(r, best)]
                    if has_alloc:
                        row.append(fmt_num(r.alloc, 0))
                    if baseline:
                        d = delta(r, baseline)
                        row.append("new" if d is None else fmt_delta(d))
                    lines.append("| " + " | ".join(row) + " |")
                lines.append("")
    with open(path, "w") as f:
        f.write("\n".join(lines))


# --- html ---------------------------------------------------------------------
def bar_path(x, y, w, h, r=4):
    """Horizontal bar: square at the baseline (left), rounded data-end (right)."""
    w = max(w, 0.0)
    r = min(r, w, h / 2)
    return ("M{x},{y} h{w1} a{r},{r} 0 0 1 {r},{r} v{h1} a{r},{r} 0 0 1 -{r},{r} h-{w1} z"
            .format(x=x, y=y, w1=w - r, r=r, h1=h - 2 * r))


def svg_chart(method, scenarios, slots, unit, cid):
    """One grouped horizontal bar chart per method: a row per scenario, a bar per candidate."""
    candidates = OrderedDict()
    for rs in scenarios.values():
        for r in rs:
            candidates.setdefault(r.label, r.label)
    cand_order = sorted(candidates, key=slots.get)

    max_score = max(r.score + r.error for rs in scenarios.values() for r in rs)
    bar_h, gap, group_pad = 18, 2, 18
    label_w = 40 + 7 * max(len(scenario_title(m, p)) for (m, p) in scenarios)
    label_w = min(label_w, 360)
    width = 960
    plot_w = width - label_w - 90
    row_h = len(cand_order) * (bar_h + gap) + group_pad
    height = len(scenarios) * row_h + 40

    # nice tick step
    raw_step = max_score / 5.0 if max_score else 1
    mag = 10 ** math.floor(math.log10(raw_step)) if raw_step > 0 else 1
    step = next(s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw_step)
    ticks = [i * step for i in range(int(max_score / step) + 2)]
    xmax = ticks[-1]

    def sx(v):
        return label_w + v / xmax * plot_w

    out = ['<svg class="chart" viewBox="0 0 %d %d" width="100%%" role="img" aria-labelledby="%s-t">'
           % (width, height, cid),
           '<title id="%s-t">%s - %s, lower is better</title>' % (cid, html.escape(method), unit)]
    # grid + axis ticks
    for t in ticks:
        x = sx(t)
        out.append('<line class="grid" x1="%.1f" y1="20" x2="%.1f" y2="%d"/>' % (x, x, height - 20))
        out.append('<text class="tick" x="%.1f" y="%d" text-anchor="middle">%s</text>'
                   % (x, height - 6, fmt_num(t, 0)))
    out.append('<text class="tick" x="%d" y="%d" text-anchor="end">%s</text>' % (width - 4, 14, unit))

    y = 24
    for (m, params), rs in scenarios.items():
        by_cand = {r.label: r for r in rs}
        best = rs[0]
        title = scenario_title(m, params)
        out.append('<text class="rowlabel" x="%d" y="%.1f" text-anchor="end">%s</text>'
                   % (label_w - 10, y + (len(cand_order) * (bar_h + gap)) / 2 + 4, html.escape(title)))
        for c in cand_order:
            r = by_cand.get(c)
            if r is None:
                y += bar_h + gap
                continue
            w = sx(r.score) - label_w
            tip = "%s · %s: %s ± %s %s (%.2f× of fastest)" % (
                title, r.label, fmt_num(r.score), fmt_num(r.error, 1), r.unit, rel(r, best))
            out.append('<g class="bar" data-tip="%s">' % html.escape(tip, quote=True))
            out.append('<rect class="hit" x="%d" y="%.1f" width="%d" height="%d"/>'
                       % (label_w, y - gap / 2, plot_w + 80, bar_h + gap))
            out.append('<path fill="var(--s%d)" d="%s"/>' % (slots[c] % len(PALETTE_LIGHT), bar_path(label_w, y, w, bar_h)))
            if r.error:
                x1, x2 = sx(max(r.score - r.error, 0)), sx(r.score + r.error)
                cy = y + bar_h / 2
                out.append('<g class="err"><line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                           '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                           '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/></g>'
                           % (x1, cy, x2, cy, x1, cy - 4, x1, cy + 4, x2, cy - 4, x2, cy + 4))
            lx = sx(r.score + r.error) + 6
            out.append('<text class="val" x="%.1f" y="%.1f">%s</text>'
                       % (lx, y + bar_h / 2 + 4, fmt_num(r.score)))
            out.append('</g>')
            y += bar_h + gap
        y += group_pad
    out.append('<line class="axis" x1="%d" y1="20" x2="%d" y2="%d"/>' % (label_w, label_w, height - 20))
    out.append('</svg>')

    legend = "".join('<span class="key"><i style="background:var(--s%d)"></i>%s</span>'
                     % (slots[c] % len(PALETTE_LIGHT), html.escape(candidates[c])) for c in cand_order)
    return '<div class="legend">%s</div>%s' % (legend, "\n".join(out))


HTML_HEAD = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{
  color-scheme: light;
  --page:#f9f9f7; --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781;
  --grid:#e1e0d9; --axis:#c3c2b7; --border:rgba(11,11,11,.10); --good:#006300; --bad:#b32d2d;
  {light_slots}
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  color-scheme: dark;
  --page:#0d0d0d; --surface:#1a1a19; --ink:#fff; --ink2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --axis:#383835; --border:rgba(255,255,255,.10); --good:#0ca30c; --bad:#e66767;
  {dark_slots}
}} }}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --page:#0d0d0d; --surface:#1a1a19; --ink:#fff; --ink2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --axis:#383835; --border:rgba(255,255,255,.10); --good:#0ca30c; --bad:#e66767;
  {dark_slots}
}}
* {{ box-sizing:border-box }}
body {{ margin:0; padding:24px 16px 48px; background:var(--page); color:var(--ink);
  font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif }}
main {{ max-width:1040px; margin:0 auto }}
h1 {{ font-size:26px; margin:0 0 4px }}
h2 {{ font-size:18px; margin:40px 0 8px; padding-bottom:6px; border-bottom:1px solid var(--grid) }}
h3.method {{ font-size:16px; margin:22px 0 8px }}
h3.method span {{ font-size:13px; font-weight:400; color:var(--ink2); margin-left:8px }}
h4 {{ font-size:13px; margin:18px 0 4px; color:var(--ink2); font-weight:600 }}
.sub {{ color:var(--ink2); margin:0 0 18px }}
.env {{ display:grid; grid-template-columns:max-content 1fr; gap:2px 14px; font-size:13px; color:var(--ink2);
  background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:12px 16px; margin:0 0 8px }}
.env b {{ color:var(--ink); font-weight:600 }}
.tiles {{ display:flex; flex-wrap:wrap; gap:12px; margin:18px 0 8px }}
.tile {{ flex:1 1 200px; background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:12px 16px }}
.tile .label {{ font-size:12px; color:var(--ink2) }}
.tile .value {{ font-size:28px; font-weight:600; line-height:1.2 }}
.tile .value small {{ font-size:13px; font-weight:400; color:var(--ink2) }}
.tile .who {{ font-size:13px; color:var(--ink2) }}
.tile .who i {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:6px; vertical-align:-1px }}
.card {{ background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:12px 16px 8px; overflow-x:auto }}
.legend {{ display:flex; flex-wrap:wrap; gap:6px 18px; margin:0 0 6px; font-size:13px; color:var(--ink2) }}
.legend i {{ display:inline-block; width:12px; height:12px; border-radius:3px; margin-right:6px; vertical-align:-1px }}
svg.chart {{ display:block; min-width:640px }}
svg .grid {{ stroke:var(--grid); stroke-width:1 }}
svg .axis {{ stroke:var(--axis); stroke-width:1 }}
svg .tick {{ fill:var(--muted); font-size:11px; font-variant-numeric:tabular-nums }}
svg .rowlabel {{ fill:var(--ink2); font-size:12px; font-family:ui-monospace,SFMono-Regular,Menlo,monospace }}
svg .val {{ fill:var(--ink2); font-size:11px; font-variant-numeric:tabular-nums }}
svg .err line {{ stroke:var(--ink2); stroke-width:1; opacity:.7 }}
svg .hit {{ fill:transparent }}
svg .bar:hover path {{ filter:brightness(1.12) }}
svg .bar:hover .val {{ fill:var(--ink); font-weight:600 }}
#tip {{ position:fixed; pointer-events:none; display:none; background:var(--ink); color:var(--page);
  padding:6px 10px; border-radius:6px; font-size:12px; max-width:420px; z-index:9 }}
table {{ border-collapse:collapse; width:100%; font-size:13px; margin:4px 0 12px }}
th, td {{ padding:5px 10px; text-align:right; border-bottom:1px solid var(--grid); font-variant-numeric:tabular-nums }}
th {{ color:var(--ink2); font-weight:600 }}
th:nth-child(2), td:nth-child(2) {{ text-align:left }}
td i.sw {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:8px; vertical-align:-1px }}
tr.best td {{ font-weight:600 }}
.good {{ color:var(--good) }} .bad {{ color:var(--bad) }}
details {{ margin:8px 0 }} summary {{ cursor:pointer; color:var(--ink2); font-size:13px }}
footer {{ margin-top:40px; color:var(--muted); font-size:12px }}
</style></head><body><main>
"""


def write_html(path, by_method, env, slots, baseline, title, all_results):
    light = " ".join("--s%d:%s;" % (i, c) for i, c in enumerate(PALETTE_LIGHT))
    dark = " ".join("--s%d:%s;" % (i, c) for i, c in enumerate(PALETTE_DARK))
    has_alloc = any(r.alloc is not None for r in all_results)
    p = [HTML_HEAD.format(title=html.escape(title), light_slots=light, dark_slots=dark)]
    p.append("<h1>%s</h1>" % html.escape(title))
    p.append('<p class="sub">%d benchmarks · %d candidates · average time per operation, lower is better</p>'
             % (len(all_results), len(slots)))
    p.append('<div class="env">' + "".join("<b>%s</b><span>%s</span>" % (html.escape(k), html.escape(v))
                                           for k, v in env.items()) + "</div>")

    # headline tiles: fastest candidate per method and how far ahead it is
    p.append('<div class="tiles">')
    for method, scenarios in by_method.items():
        wins = defaultdict(int)
        ratios = []
        for rs in scenarios.values():
            wins[rs[0].label] += 1
            if len(rs) > 1:
                ratios.append(rs[-1].score / rs[0].score)
        winner = max(wins, key=wins.get)
        label = winner
        speed = ("%.1f×" % (sum(ratios) / len(ratios))) if ratios else "-"
        p.append('<div class="tile"><div class="label">%s · fastest</div>'
                 '<div class="who"><i style="background:var(--s%d)"></i>%s</div>'
                 '<div class="value">%s <small>faster than slowest, avg</small></div></div>'
                 % (html.escape(method), slots[winner] % len(PALETTE_LIGHT), html.escape(label), speed))
    p.append('</div>')

    i = 0
    for section, methods in by_section(by_method).items():
        p.append("<h2>%s</h2>" % html.escape(section))
        for method, scenarios in methods.items():
            i += 1
            unit = next(iter(scenarios.values()))[0].unit
            p.append('<h3 class="method">%s <span>%s</span></h3>'
                     % (html.escape(method), html.escape(METHOD_DESC.get(method, ""))))
            p.append('<div class="card">%s</div>' % svg_chart(method, scenarios, slots, unit, "c%d" % i))
            for (m, params), rs in scenarios.items():
                best = rs[0]
                p.append("<h4><code>%s</code></h4>" % html.escape(scenario_title(m, params)))
                hdr = "<tr><th>#</th><th>Candidate</th><th>%s</th><th>± error</th><th>rel</th>" % unit
                if has_alloc:
                    hdr += "<th>B/op</th>"
                if baseline:
                    hdr += "<th>vs baseline</th>"
                p.append("<table>" + hdr + "</tr>")
                for j, r in enumerate(rs, 1):
                    row = ('<tr%s><td>%d</td><td><i class="sw" style="background:var(--s%d)"></i>%s</td>'
                           '<td>%s</td><td>%s</td><td>%.2f×</td>'
                           % (' class="best"' if j == 1 else "", j, slots[r.label] % len(PALETTE_LIGHT),
                              html.escape(r.label), fmt_num(r.score), fmt_num(r.error, 1), rel(r, best)))
                    if has_alloc:
                        row += "<td>%s</td>" % fmt_num(r.alloc, 0)
                    if baseline:
                        d = delta(r, baseline)
                        cls = "" if d is None else ("good" if d < -1 else ("bad" if d > 1 else ""))
                        row += '<td class="%s">%s</td>' % (cls, "new" if d is None else fmt_delta(d))
                    p.append(row + "</tr>")
                p.append("</table>")

    p.append('<footer>Generated %s by report.py · JMH %s</footer>' % (
        datetime.now().strftime("%Y-%m-%d %H:%M"), html.escape(all_results[0].entry.get("jmhVersion", ""))))
    p.append('<div id="tip"></div>')
    p.append("""<script>
(function(){var t=document.getElementById('tip');
document.querySelectorAll('svg .bar').forEach(function(b){
 b.addEventListener('mousemove',function(e){t.textContent=b.dataset.tip;t.style.display='block';
  t.style.left=Math.min(e.clientX+14,window.innerWidth-t.offsetWidth-8)+'px';t.style.top=(e.clientY+14)+'px';});
 b.addEventListener('mouseleave',function(){t.style.display='none';});});})();
</script></main></body></html>""")
    with open(path, "w") as f:
        f.write("\n".join(p))


# --- png (optional) -----------------------------------------------------------
def write_png(path, by_method, slots, title):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    style = os.path.join(os.path.dirname(os.path.abspath(__file__)), "theme.mplstyle")
    if os.path.isfile(style):
        plt.style.use(style)
    n = len(by_method)
    rows = sum(len(s) for s in by_method.values())
    fig, axes = plt.subplots(n, 1, figsize=(11, 1.2 * rows + 1.5 * n), squeeze=False)
    for ax, (method, scenarios) in zip(axes[:, 0], by_method.items()):
        cands = OrderedDict()
        for rs in scenarios.values():
            for r in rs:
                cands.setdefault(r.label, r.label)
        order = sorted(cands, key=slots.get)
        bar_h = 0.8 / len(order)
        for idx, ((m, params), rs) in enumerate(scenarios.items()):
            by_c = {r.label: r for r in rs}
            for k, c in enumerate(order):
                r = by_c.get(c)
                if r is None:
                    continue
                ax.barh(idx + k * bar_h, r.score, height=bar_h * 0.9, xerr=r.error,
                        color=PALETTE_LIGHT[slots[c] % len(PALETTE_LIGHT)],
                        label=cands[c] if idx == 0 else None, error_kw={"lw": 1, "capsize": 2})
                ax.text(r.score + r.error + ax.get_xlim()[1] * 0.005, idx + k * bar_h,
                        fmt_num(r.score), va="center", fontsize=8, color="#52514e")
        ax.set_yticks([i + (len(order) - 1) * bar_h / 2 for i in range(len(scenarios))])
        ax.set_yticklabels([scenario_title(m, p) for (m, p) in scenarios], fontsize=8, family="monospace")
        ax.invert_yaxis()
        ax.set_xlabel(rs[0].unit + " (lower is better)")
        ax.set_title(method, loc="left", fontsize=11, fontweight="bold")
        ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(0, -0.18 * (2.0 / max(len(scenarios), 1))),
                  ncol=min(len(order), 4), frameon=False)
        ax.set_xlim(0, ax.get_xlim()[1] * 1.12)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    fig.suptitle(title, fontsize=13, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return True


# --- headline summary ---------------------------------------------------------
def summary_rows(by_method):
    """-> [(method, unit, [subject scores], [baseline scores], [speedups])] per method.

    Only scenarios where both SUMMARY_SUBJECT and SUMMARY_BASELINE ran are counted,
    so a candidate that skips an input can't skew the comparison.
    """
    rows = []
    for method, scenarios in by_method.items():
        subj, base, unit = [], [], ""
        for rs in scenarios.values():
            by_label = {r.label: r for r in rs}
            s_, b_ = by_label.get(SUMMARY_SUBJECT), by_label.get(SUMMARY_BASELINE)
            if s_ and b_ and s_.score > 0:
                subj.append(s_.score)
                base.append(b_.score)
                unit = s_.unit
        if subj:
            rows.append((method, unit, subj, base, [b / s_ for s_, b in zip(subj, base)]))
    return rows


def _geomean(vals):
    return math.exp(sum(math.log(v) for v in vals) / len(vals))


def _fmt_span(vals, digits=0):
    """One number, or a lo-hi span. Collapses only when both ends round alike,
    so a real spread is never flattened into a bogus "5-5"."""
    lo, hi = fmt_num(min(vals), digits), fmt_num(max(vals), digits)
    return lo if lo == hi else "%s\u2013%s" % (lo, hi)


def _fmt_speedup(vals):
    """Speed-ups need a decimal below 10x, or 5.0x-5.4x collapses to "5-5"."""
    return _fmt_span(vals, 0 if min(vals) >= 10 else 1)


def summary_table(rows):
    lines = ["| Operation | %s | %s | Speed-up |" % (SUMMARY_SUBJECT, "JDK `java.time`"),
             "|:---|---:|---:|---:|"]
    for method, unit, subj, base, speedups in rows:
        lines.append("| `%s` | %s %s | %s %s | **%s\u00d7** |" % (
            method, _fmt_span(subj), unit, _fmt_span(base), unit, _fmt_speedup(speedups)))
    return "\n".join(lines) + "\n"


def write_summary_markdown(path, rows, url=None):
    table = summary_table(rows)
    if url:
        table += "\n[Full report with error bars, inputs and environment \u00bb](%s)\n" % url
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(table)


README_START = "<!-- BENCH:START"
README_END = "<!-- BENCH:END -->"


def update_readme(path, table):
    """Replace whatever sits between the BENCH markers in an external README."""
    with io.open(path, encoding="utf-8") as f:
        text = f.read()
    i, j = text.find(README_START), text.find(README_END)
    if i < 0 or j < 0:
        return False
    head_end = text.find("-->", i)
    if head_end < 0 or head_end > j:
        return False
    new = text[:head_end + 3] + "\n" + table.rstrip("\n") + "\n" + text[j:]
    if new == text:
        return True
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(new)
    return True


def write_summary_png(path, rows):
    """Compact speed-up chart for a README. Transparent, so it works on light and dark."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    rows = list(reversed(rows))  # matplotlib draws bottom-up
    ink, accent = "#8b8b8b", PALETTE_LIGHT[0]
    fig, ax = plt.subplots(figsize=(8, 0.42 * len(rows) + 0.9))
    factors = [_geomean(sp) for _, _, _, _, sp in rows]
    ax.barh(range(len(rows)), factors, height=0.62, color=accent, zorder=2)
    for i, (f, (method, unit, subj, base, sp)) in enumerate(zip(factors, rows)):
        ax.text(f + max(factors) * 0.012, i, " %s\u00d7" % fmt_num(f, 0 if f >= 10 else 1),
                va="center", fontsize=9, color=ink, fontweight="bold")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([m for m, _, _, _, _ in rows], fontsize=9, family="monospace", color=ink)
    ax.set_xlim(0, max(factors) * 1.22)  # headroom for the value labels
    ax.set_xlabel("times faster than JDK java.time (higher is better)", fontsize=9, color=ink)
    ax.tick_params(axis="x", colors=ink, labelsize=8)
    ax.grid(axis="x", color=ink, alpha=0.18, zorder=0)
    ax.set_facecolor("none")
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    fig.patch.set_alpha(0)
    fig.tight_layout()
    fig.savefig(path, dpi=160, transparent=True)
    plt.close(fig)
    return True


# --- grouped json (jmh.morethan.io compatible) --------------------------------
def write_grouped(path, results):
    arr = []
    for r in sorted(results, key=lambda r: r.score):
        e = dict(r.entry)
        e["benchmark"] = "%s.%s" % (r.method, r.candidate)
        arr.append(e)
    with open(path, "w") as f:
        json.dump(arr, f, indent=2)


# --- main ---------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate reports from a JMH json result file.")
    ap.add_argument("input", nargs="?", default="jmh-result.json", help="JMH json result (default: jmh-result.json)")
    ap.add_argument("-o", "--out", help="output directory (default: directory of the input file)")
    ap.add_argument("--baseline", help="previous jmh-result.json to compare against")
    ap.add_argument("--title", help="report title")
    ap.add_argument("--no-png", action="store_true", help="skip the matplotlib charts")
    ap.add_argument("--summary-url", default="https://ethlo.github.io/date-time-wars/",
                    help="link target appended to summary.md")
    ap.add_argument("--readme", help="splice the summary table into this README's BENCH:START/END block")
    ap.add_argument("-q", "--quiet", action="store_true", help="don't print the summary")
    args = ap.parse_args(argv)

    results = load(args.input)
    if not results:
        sys.exit("No results in %s" % args.input)
    out_dir = args.out or os.path.dirname(os.path.abspath(args.input))
    os.makedirs(out_dir, exist_ok=True)
    props = read_properties(os.path.join(out_dir, "run.properties"))
    env = environment(results, props)
    by_method = group(results)
    slots = candidate_slots(results)
    baseline = {r.key: r for r in load(args.baseline)} if args.baseline else None
    title = args.title or ("date-time-wars" + (" · " + props["label"] if props.get("label") else ""))

    write_markdown(os.path.join(out_dir, "report.md"), by_method, env, baseline, title)
    write_html(os.path.join(out_dir, "report.html"), by_method, env, slots, baseline, title, results)
    write_grouped(os.path.join(out_dir, "jmh-result-grouped.json"), results)
    png = False if args.no_png else write_png(os.path.join(out_dir, "report.png"), by_method, slots, title)

    rows = summary_rows(by_method)
    if rows:
        write_summary_markdown(os.path.join(out_dir, "summary.md"), rows, args.summary_url)
        if not args.no_png:
            write_summary_png(os.path.join(out_dir, "summary.png"), rows)
        if args.readme:
            if update_readme(args.readme, summary_table(rows)):
                print("Updated %s" % args.readme)
            else:
                print("No %s ... %s block in %s" % (README_START, README_END, args.readme), file=sys.stderr)
    else:
        print("No %s vs %s pairs; skipping summary" % (SUMMARY_SUBJECT, SUMMARY_BASELINE), file=sys.stderr)

    if not args.quiet:
        print_summary(by_method, baseline, sys.stdout)
        print("Reports written to %s/: report.md, report.html%s, jmh-result-grouped.json%s"
              % (out_dir, ", report.png" if png else "", ", summary.md" if rows else ""))
        if not png and not args.no_png:
            print("(install matplotlib for report.png)")


if __name__ == "__main__":
    main()
