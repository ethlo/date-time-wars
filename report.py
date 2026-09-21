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

REPO_URL = "https://github.com/ethlo/date-time-wars"

# --- candidates ---------------------------------------------------------------
# Benchmarks live in candidates.<id>.<Class>.<method>; <id> is the candidate key.
# key -> (label, library key in LIBS, what the candidate actually calls). The
# library's version comes from run.properties (`lib.<artifact>=`, written by
# bench.sh from the shaded jar) so the report names what was measured, not what
# the pom says today.
CANDIDATES = OrderedDict([
    ("itu", ("ITU", "itu",
             "ITU.parseDateTime, parseLenient, isValid, formatUtc*, parseDuration and Duration.normalized()")),
    ("itu_configurable", ("ITU (configurable)", "itu",
                          "ConfigurableDateTimeParser with a token layout of yyyy-MM-ddTHH:mm:ss[.fff]+offset, "
                          "the same inputs as the fixed parser")),
    ("itu_buffer", ("ITU (char[] buffer)", "itu",
                    "ITU.parseLenient over a char[] window into a reusable MutableDateTimeBuffer - the zero-allocation path")),
    ("itu_clamped", ("ITU (hours)", "itu",
                     "Duration.normalized(HOURS), so it decomposes a duration the way java.time.Duration.toString() does")),
    ("itu_duration", ("ITU", "itu", "ITU.parseDuration and Duration.normalized()")),  # legacy package name
    ("jdk", ("JDK java.time", "jdk",
             "OffsetDateTime.parse, a DateTimeFormatterBuilder layout with optional parts for lenient parsing, "
             "parse-and-catch for isValid, Duration.parse / toString")),
    ("jdk_instant", ("JDK Instant", "jdk", "Instant.parse - the fastest built-in path for RFC-3339 input")),
    ("google", ("Google HTTP client", "google-http-client", "DateTime.parseRfc3339ToSecondsAndNanos")),
    ("epoch", ("Epoch millis", "jdk",
               "Long.parseLong / Long.toString on the epoch count - the number an API would carry instead of "
               "a date-time string. Not a parser; a reference for the “epoch is faster” argument")),
    ("itu_epoch", ("ITU (epoch millis)", "itu",
                   "ITU.parseEpochMilli on the same epoch-millis text, into the same DateTime the string parsers "
                   "produce - the epoch argument measured to a temporal value, not to a long")),
    ("itu_epoch_buffer", ("ITU (epoch millis, char[] buffer)", "itu",
                          "ITU.parseEpochMilli over a char[] window into a reusable MutableDateTimeBuffer - the "
                          "zero-allocation path for epoch text, the like-for-like of the char[] buffer row")),
])
# Reference rows are shown but never declared the winner of anything. The epoch rows parse a
# different text than the date-time rows, so none of them can be "the fastest date-time parser".
REFERENCE = {"epoch", "itu_epoch", "itu_epoch_buffer"}
# library key -> (name, url, run.properties key for its version; None = the JDK)
LIBS = OrderedDict([
    ("itu", ("ITU - Internet Time Utility", "https://github.com/ethlo/itu", "lib.itu")),
    ("jdk", ("JDK java.time", "https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/time/package-summary.html", None)),
    ("google-http-client", ("Google HTTP client", "https://github.com/googleapis/google-http-java-client", "lib.google-http-client")),
])
LABELS = {k: v[0] for k, v in CANDIDATES.items()}
# The harness floor lives outside candidates.* (see floor.HarnessFloorBenchmark);
# it is reported as an environment fact, not as a section.
FLOOR_METHOD = "floor"

# Report sections: heading -> benchmark methods in display order. Methods not
# listed here end up under "Other".
SECTIONS = OrderedDict([
    ("Date-time parsing", ["parse", "parseLenient", "isValid"]),
    ("Date-time formatting", ["formatSeconds", "formatMillis", "formatNanos"]),
    ("Duration", ["parseDuration", "formatDuration"]),
])
METHOD_DESC = {
    "parse": "strict RFC-3339 / ISO-8601 date-time",
    "parseLenient": "lenient date-time (optional fields)",
    "isValid": "strict RFC-3339 validity check, valid and invalid inputs",
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


def input_label(params):
    """The @Param values alone, for rows under a heading that already names the method."""
    return ", ".join(v for _, v in params) if params else "–"


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


def environment(results, props, floor=None):
    e = results[0].entry
    env = OrderedDict()
    env["Date"] = props.get("date", datetime.now().isoformat(timespec="seconds"))
    if props.get("label"):
        env["Run"] = props["label"]
    env["JDK"] = "%s (%s %s)" % (e.get("jdkVersion", "?"), e.get("vmName", ""), e.get("vmVersion", ""))
    env["JVM args"] = " ".join(e.get("jvmArgs", [])) or "-"
    mode = (" (--%s)" % props["mode"]) if props.get("mode") else ""
    env["Iterations"] = "%s fork(s), %s × %s warmup, %s × %s measurement%s" % (
        e.get("forks"), e.get("warmupIterations"), e.get("warmupTime"),
        e.get("measurementIterations"), e.get("measurementTime"), mode)
    for k, name in (("cpu", "CPU"), ("os", "OS"), ("git", "Git")):
        if props.get(k):
            env[name] = props[k]
    if floor:
        env["Harness floor"] = "%s %s - the JMH loop, state loads and Blackhole with no parsing at all; " \
                               "subtract it from a parse score for the parser's own cost" % (
                                   _fmt_span([r.score for r in floor], 2), floor[0].unit)
    return env


def lib_versions(results, props):
    """-> OrderedDict library key -> version string, or None when the run did not record it."""
    out = OrderedDict()
    for key, (_, _, prop) in LIBS.items():
        if prop is None:
            out[key] = results[0].entry.get("jdkVersion")
        else:
            out[key] = props.get(prop)
    return out


def split_floor(results):
    """Separate the harness floor rows from the candidates."""
    floor = [r for r in results if r.method == FLOOR_METHOD]
    return [r for r in results if r.method != FLOOR_METHOD], floor


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


def svg_chart(method, scenarios, slots, unit, cid, row_label=None):
    """One grouped horizontal bar chart per method: a row per scenario, a bar per candidate.

    row_label maps a scenario key to its row text; by default the input alone, since the
    method is the chart's heading."""
    row_label = row_label or (lambda m, p: input_label(p))
    candidates = OrderedDict()
    for rs in scenarios.values():
        for r in rs:
            candidates.setdefault(r.label, r.label)
    cand_order = sorted(candidates, key=slots.get)

    max_score = max(r.score + r.error for rs in scenarios.values() for r in rs)
    bar_h, gap, group_pad = 18, 2, 18
    # the method is the chart's heading, so rows are labelled by input alone
    label_w = 24 + 7 * max(len(row_label(m, p)) for (m, p) in scenarios)
    label_w = min(label_w, 300)
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
                   % (label_w - 10, y + (len(cand_order) * (bar_h + gap)) / 2 + 4, html.escape(row_label(m, params))))
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
  --link:#1d5fb4; --best:rgba(42,120,214,.08);
  {light_slots}
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  color-scheme: dark;
  --page:#0d0d0d; --surface:#1a1a19; --ink:#fff; --ink2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --axis:#383835; --border:rgba(255,255,255,.10); --good:#0ca30c; --bad:#e66767;
  --link:#6ea6f0; --best:rgba(57,135,229,.14);
  {dark_slots}
}} }}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --page:#0d0d0d; --surface:#1a1a19; --ink:#fff; --ink2:#c3c2b7; --muted:#898781;
  --grid:#2c2c2a; --axis:#383835; --border:rgba(255,255,255,.10); --good:#0ca30c; --bad:#e66767;
  --link:#6ea6f0; --best:rgba(57,135,229,.14);
  {dark_slots}
}}
* {{ box-sizing:border-box }}
html {{ scroll-behavior:smooth }}
body {{ margin:0; padding:24px 16px 48px; background:var(--page); color:var(--ink);
  font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif }}
main {{ max-width:1040px; margin:0 auto }}
a {{ color:var(--link); text-decoration:none }} a:hover {{ text-decoration:underline }}
h1 {{ font-size:26px; margin:0 0 4px }}
h2 {{ font-size:18px; margin:44px 0 8px; padding-bottom:6px; border-bottom:1px solid var(--grid) }}
h3.method {{ font-size:16px; margin:26px 0 8px }}
h3.method > span:last-child {{ font-size:13px; font-weight:400; color:var(--ink2); margin-left:8px }}
code, .mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.93em }}
.sub {{ color:var(--ink2); margin:0 0 10px }}
.sub b {{ color:var(--ink); font-weight:600 }}
nav {{ display:flex; flex-wrap:wrap; gap:4px 18px; font-size:13px; margin:0 0 8px; padding:8px 0; border-top:1px solid var(--grid); border-bottom:1px solid var(--grid) }}
.lead {{ color:var(--ink2); margin:0 0 14px; max-width:72ch }}
.env {{ display:grid; grid-template-columns:max-content 1fr; gap:3px 14px; font-size:13px; color:var(--ink2);
  background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:12px 16px; margin:0 0 8px }}
.env b {{ color:var(--ink); font-weight:600 }}
.card {{ background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:12px 16px 8px; overflow-x:auto }}
.legend {{ display:flex; flex-wrap:wrap; gap:6px 18px; margin:0 0 6px; font-size:13px; color:var(--ink2) }}
.legend i, i.sw {{ display:inline-block; width:12px; height:12px; border-radius:3px; margin-right:6px; vertical-align:-1px }}
svg.chart {{ display:block; min-width:640px }}
svg .grid {{ stroke:var(--grid); stroke-width:1 }}
svg .axis {{ stroke:var(--axis); stroke-width:1 }}
svg .parity {{ stroke:var(--ink2); stroke-width:1; stroke-dasharray:3 3 }}
svg .tick {{ fill:var(--muted); font-size:11px; font-variant-numeric:tabular-nums }}
svg .rowlabel {{ fill:var(--ink2); font-size:12px; font-family:ui-monospace,SFMono-Regular,Menlo,monospace }}
svg .val {{ fill:var(--ink2); font-size:11px; font-variant-numeric:tabular-nums }}
svg .err line {{ stroke:var(--ink2); stroke-width:1; opacity:.7 }}
svg .range {{ stroke-width:3; stroke-linecap:round; opacity:.45 }}
svg .dot {{ stroke:var(--surface); stroke-width:2 }}
svg .hit {{ fill:transparent }}
svg .bar:hover path, svg .bar:hover circle {{ filter:brightness(1.12) }}
svg .bar:hover .val {{ fill:var(--ink); font-weight:600 }}
#tip {{ position:fixed; pointer-events:none; display:none; background:var(--ink); color:var(--page);
  padding:6px 10px; border-radius:6px; font-size:12px; max-width:420px; z-index:9 }}
.tw {{ overflow-x:auto; margin:4px 0 12px }}
table {{ border-collapse:collapse; width:100%; font-size:13px }}
table.pivot {{ width:auto; min-width:60% }}
table.pivot td:not(.l) {{ min-width:8em }}
th, td {{ padding:6px 10px; text-align:right; border-bottom:1px solid var(--grid); font-variant-numeric:tabular-nums; vertical-align:top }}
th {{ color:var(--ink2); font-weight:600; white-space:nowrap }}
th.l, td.l {{ text-align:left }}
td.l {{ white-space:nowrap }}
td.wrap {{ white-space:normal; text-align:left; color:var(--ink2); min-width:26ch }}
tr.sec td {{ text-align:left; font-weight:600; color:var(--ink2); background:var(--surface); padding-top:10px; font-size:12px; text-transform:uppercase; letter-spacing:.04em }}
td.best {{ background:var(--best); font-weight:600 }}
td small {{ color:var(--muted); font-weight:400; font-size:11px }}
td .rel {{ display:block; color:var(--muted); font-weight:400; font-size:11px }}
td.na {{ color:var(--muted) }}
.pill {{ display:inline-block; font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:.04em; color:var(--ink2);
  border:1px solid var(--border); border-radius:10px; padding:0 7px; margin-left:6px; vertical-align:1px }}
.good {{ color:var(--good) }} .bad {{ color:var(--bad) }}
.speedup {{ font-weight:600; white-space:nowrap }}
.note {{ font-size:12px; color:var(--muted); margin:6px 0 0 }}
footer {{ margin-top:40px; color:var(--muted); font-size:12px; display:flex; flex-wrap:wrap; gap:4px 18px }}
</style></head><body><main>
"""


def _slug(text):
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


def _swatch(slots, label):
    return '<i class="sw" style="background:var(--s%d)"></i>' % (slots[label] % len(PALETTE_LIGHT))


def _fastest(scenarios):
    """The candidate that wins most inputs, references excluded -> label or None."""
    wins = defaultdict(int)
    for rs in scenarios.values():
        for r in rs:
            if r.candidate not in REFERENCE:
                wins[r.label] += 1
                break
    return max(wins, key=wins.get) if wins else None


def svg_speedup(rows, slots):
    """Summary chart: per method, the ITU-vs-JDK speed-up span across inputs on a log axis.

    A range with a dot at the geometric mean rather than a bar, because a bar's length means
    nothing on a log scale and the spread across inputs is the honest part of the number."""
    row_h, top, bottom = 26, 28, 30
    label_w, width = 130, 960
    plot_w = width - label_w - 110
    height = top + row_h * len(rows) + bottom
    lo = min(min(sp) for *_, sp in rows)
    hi = max(max(sp) for *_, sp in rows)
    xmin, xmax = min(0.5, lo / 1.3), hi * 1.6
    ticks = [t for t in (0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000) if xmin <= t <= xmax]

    def sx(v):
        return label_w + (math.log10(v) - math.log10(xmin)) / (math.log10(xmax) - math.log10(xmin)) * plot_w

    out = ['<svg class="chart" viewBox="0 0 %d %d" width="100%%" role="img" aria-labelledby="sp-t">' % (width, height),
           '<title id="sp-t">%s speed-up over %s per operation, log scale</title>' % (SUMMARY_SUBJECT, SUMMARY_BASELINE)]
    for t in ticks:
        x = sx(t)
        cls = "parity" if t == 1 else "grid"
        out.append('<line class="%s" x1="%.1f" y1="%d" x2="%.1f" y2="%d"/>' % (cls, x, top - 8, x, height - bottom + 6))
        out.append('<text class="tick" x="%.1f" y="%d" text-anchor="middle">%s</text>'
                   % (x, height - bottom + 20, "parity" if t == 1 else fmt_num(t, 1 if t < 1 else 0) + "×"))
    out.append('<text class="tick" x="%d" y="%d" text-anchor="end">× faster than %s, log scale</text>'
               % (width - 4, 14, html.escape(SUMMARY_BASELINE)))
    color = "var(--s%d)" % (slots.get(SUMMARY_SUBJECT, 0) % len(PALETTE_LIGHT))
    for i, (method, unit, subj, base, sp) in enumerate(rows):
        y = top + i * row_h + row_h / 2
        gm = _geomean(sp)
        tip = "%s: %s %s vs %s %s %s - %s× (geometric mean %s× over %d input%s)" % (
            method, SUMMARY_SUBJECT, _fmt_span(subj), SUMMARY_BASELINE, _fmt_span(base), unit,
            _fmt_speedup(sp), fmt_num(gm, 0 if gm >= 10 else 1), len(sp), "" if len(sp) == 1 else "s")
        out.append('<g class="bar" data-tip="%s">' % html.escape(tip, quote=True))
        out.append('<rect class="hit" x="0" y="%.1f" width="%d" height="%d"/>' % (y - row_h / 2, width, row_h))
        out.append('<text class="rowlabel" x="%d" y="%.1f" text-anchor="end">%s</text>' % (label_w - 12, y + 4, html.escape(method)))
        out.append('<line class="range" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s"/>'
                   % (sx(min(sp)), y, sx(max(sp)), y, color))
        out.append('<circle class="dot" cx="%.1f" cy="%.1f" r="5" fill="%s"/>' % (sx(gm), y, color))
        out.append('<text class="val" x="%.1f" y="%.1f">%s×</text>' % (sx(max(sp)) + 10, y + 4, _fmt_speedup(sp)))
        out.append('</g>')
    out.append('<line class="axis" x1="%d" y1="%d" x2="%d" y2="%d"/>' % (label_w, top - 8, label_w, height - bottom + 6))
    out.append('</svg>')
    return "\n".join(out)


def _cell(r, best, baseline, has_alloc):
    if r is None:
        return '<td class="na">–</td>'
    cls = ' class="best"' if r is best else ""
    body = '%s <small>±%s</small>' % (fmt_num(r.score), fmt_num(r.error, 1))
    body += '<span class="rel">%s</span>' % ("fastest" if r is best else "%.2f×" % rel(r, best))
    if has_alloc:
        body += '<span class="rel">%s B/op</span>' % fmt_num(r.alloc, 0)
    if baseline:
        d = delta(r, baseline)
        if d is None:
            body += '<span class="rel">new</span>'
        else:
            c = "good" if d < -1 else ("bad" if d > 1 else "")
            body += '<span class="rel %s">%s vs baseline</span>' % (c, fmt_delta(d))
    return "<td%s>%s</td>" % (cls, body)


def pivot_table(scenarios, slots, baseline, has_alloc, row_label=None, row_head="Input"):
    """One table per method: a row per input, a column per candidate, so it mirrors the chart."""
    show_input = any(p for (_, p) in scenarios) or row_label is not None
    row_label = row_label or (lambda m, p: input_label(p))
    cand_order = sorted({r.label for rs in scenarios.values() for r in rs}, key=slots.get)
    p = ['<div class="tw"><table class="pivot"><tr>']
    if show_input:
        p.append('<th class="l">%s</th>' % html.escape(row_head))
    for c in cand_order:
        p.append('<th>%s%s</th>' % (_swatch(slots, c), html.escape(c)))
    p.append('</tr>')
    for (m, params), rs in scenarios.items():
        by_cand = {r.label: r for r in rs}
        p.append('<tr>')
        if show_input:
            p.append('<td class="l mono">%s</td>' % html.escape(row_label(m, params)))
        for c in cand_order:
            p.append(_cell(by_cand.get(c), rs[0], baseline, has_alloc))
        p.append('</tr>')
    p.append('</table></div>')
    return "".join(p)


def write_html(path, by_method, env, slots, baseline, title, all_results, versions, pages_url=None):
    light = " ".join("--s%d:%s;" % (i, c) for i, c in enumerate(PALETTE_LIGHT))
    dark = " ".join("--s%d:%s;" % (i, c) for i, c in enumerate(PALETTE_DARK))
    has_alloc = any(r.alloc is not None for r in all_results)
    e = all_results[0].entry
    sections = by_section(by_method)
    p = [HTML_HEAD.format(title=html.escape(title), light_slots=light, dark_slots=dark)]

    # --- header
    p.append("<h1>%s</h1>" % html.escape(title))
    facts = ["%d benchmarks" % len(all_results), "%d candidates" % len(slots),
             "<b>%s</b>, lower is better" % html.escape(all_results[0].unit)]
    for k in ("JDK", "CPU"):
        if k in env:
            facts.append(html.escape(env[k].split(" (")[0]))
    facts.append(html.escape(env["Date"][:10]))
    p.append('<p class="sub">%s</p>' % " · ".join(facts))
    nav = [("summary", "Summary"), ("candidates", "Candidates")] + \
          [(_slug(s), s) for s in sections] + [("environment", "Environment")]
    p.append("<nav>%s</nav>" % "".join('<a href="#%s">%s</a>' % (i, html.escape(n)) for i, n in nav))

    # --- summary: one row per method, ITU against the JDK
    rows = summary_rows(by_method)
    p.append('<h2 id="summary">Summary</h2>')
    if rows:
        p.append('<p class="lead">%s against %s, one row per operation. Spans cover the inputs of that '
                 'operation; the speed-up is %s time divided by %s time, per input. The other candidates '
                 'are in the sections below.</p>'
                 % tuple(html.escape(x) for x in (SUMMARY_SUBJECT, SUMMARY_BASELINE, SUMMARY_BASELINE, SUMMARY_SUBJECT)))
        p.append('<div class="card">%s</div>' % svg_speedup(rows, slots))
        by_m = {m: (u, s, b, sp) for m, u, s, b, sp in rows}
        p.append('<div class="tw"><table><tr><th class="l">Operation</th><th class="l">What</th><th>Inputs</th>'
                 '<th>%s</th><th>%s</th><th>Speed-up</th><th class="l">Fastest overall</th></tr>'
                 % (html.escape(SUMMARY_SUBJECT), html.escape(SUMMARY_BASELINE)))
        for section, methods in sections.items():
            in_section = [m for m in methods if m in by_m]
            if not in_section:
                continue
            p.append('<tr class="sec"><td colspan="7">%s</td></tr>' % html.escape(section))
            for m in in_section:
                unit, subj, base, sp = by_m[m]
                fastest = _fastest(methods[m])
                p.append('<tr><td class="l"><a href="#m-%s" class="mono">%s</a></td><td class="wrap">%s</td>'
                         '<td>%d</td><td>%s</td><td>%s</td><td class="speedup">%s×</td><td class="l">%s</td></tr>'
                         % (_slug(m), html.escape(m), html.escape(METHOD_DESC.get(m, "")), len(sp),
                            _fmt_span(subj), _fmt_span(base), _fmt_speedup(sp),
                            (_swatch(slots, fastest) + html.escape(fastest)) if fastest else "–"))
        p.append('</table></div>')
        p.append('<p class="note">Times in %s. “Fastest overall” counts every candidate except the '
                 'reference rows, which are not date-time parsers.</p>' % html.escape(all_results[0].unit))
    else:
        p.append('<p class="lead">No %s vs %s pairs in this run.</p>' % (SUMMARY_SUBJECT, SUMMARY_BASELINE))

    # --- candidates: what each row of the charts actually is, with library and version
    p.append('<h2 id="candidates">Candidates</h2>')
    p.append('<div class="tw"><table><tr><th class="l">Candidate</th><th class="l">Library</th>'
             '<th class="l">Version</th><th class="l">Under test</th></tr>')
    present = {r.candidate for r in all_results}
    seen = set()
    for key, (label, lib, what) in CANDIDATES.items():
        if key not in present or label in seen:
            continue
        seen.add(label)
        name, url, _ = LIBS.get(lib, (lib, None, None))
        version = versions.get(lib)
        pill = '<span class="pill">reference</span>' if key in REFERENCE else ""
        p.append('<tr><td class="l">%s%s%s</td><td class="l">%s</td><td class="l mono">%s</td><td class="wrap">%s</td></tr>'
                 % (_swatch(slots, label), html.escape(label), pill,
                    ('<a href="%s">%s</a>' % (html.escape(url, quote=True), html.escape(name))) if url else html.escape(name),
                    html.escape(version) if version else '<span class="pill">not recorded</span>',
                    html.escape(what)))
    for label in sorted({r.label for r in all_results if r.candidate not in CANDIDATES}):
        p.append('<tr><td class="l">%s%s</td><td class="l">–</td><td class="l">–</td><td class="wrap">–</td></tr>'
                 % (_swatch(slots, label), html.escape(label)))
    p.append('</table></div>')

    # --- detail sections: a chart and a pivot table per method
    i = 0
    for section, methods in sections.items():
        p.append('<h2 id="%s">%s</h2>' % (_slug(section), html.escape(section)))
        # Methods with a single, parameterless input (the formatters) share one chart and
        # one table with a row per method, instead of a chart each for one number.
        if len(methods) > 1 and all(len(sc) == 1 and not next(iter(sc))[1] for sc in methods.values()):
            i += 1
            merged = OrderedDict((k, rs) for sc in methods.values() for k, rs in sc.items())
            unit = next(iter(merged.values()))[0].unit
            p.append('<h3 class="method">%s <span>one operation per row</span></h3>'
                     % " \u00b7 ".join('<span id="m-%s">%s</span>' % (_slug(m), html.escape(m)) for m in methods))
            by_method_label = lambda m, _p: m
            p.append('<div class="card">%s</div>' % svg_chart(section, merged, slots, unit, "c%d" % i, by_method_label))
            p.append(pivot_table(merged, slots, baseline, has_alloc, by_method_label, "Operation"))
            continue
        for method, scenarios in methods.items():
            i += 1
            unit = next(iter(scenarios.values()))[0].unit
            p.append('<h3 class="method" id="m-%s">%s <span>%s</span></h3>'
                     % (_slug(method), html.escape(method), html.escape(METHOD_DESC.get(method, ""))))
            p.append('<div class="card">%s</div>' % svg_chart(method, scenarios, slots, unit, "c%d" % i))
            p.append(pivot_table(scenarios, slots, baseline, has_alloc))
    p.append('<p class="note">%s per operation; ± is JMH’s 99.9%% confidence interval over all measurement '
             'iterations. The small figure under each value is the ratio to the fastest candidate on that input.</p>'
             % html.escape(all_results[0].unit))

    # --- environment
    p.append('<h2 id="environment">Environment</h2>')
    p.append('<div class="env">')
    for k, v in env.items():
        if k == "Git":
            sha, dirty = (v[:-6], True) if v.endswith("-dirty") else (v, False)
            v = '<a href="%s/commit/%s">%s</a>%s' % (REPO_URL, html.escape(sha), html.escape(sha),
                                                   " (with uncommitted changes)" if dirty else "")
        else:
            v = html.escape(v)
        p.append("<b>%s</b><span>%s</span>" % (html.escape(k), v))
    p.append("</div>")
    p.append('<p class="note">JMH %s. Each run records this in <code>run.properties</code> next to its results; '
             'library versions are read from the jar that ran, not from the pom.</p>' % html.escape(e.get("jmhVersion", "")))

    links = ['Generated %s by <a href="%s">report.py</a>' % (datetime.now().strftime("%Y-%m-%d %H:%M"), REPO_URL),
             '<a href="jmh-result-grouped.json">raw JMH results</a>']
    if pages_url:
        links.append('<a href="https://jmh.morethan.io/?source=%sjmh-result-grouped.json">open in JMH Visualizer</a>'
                     % html.escape(pages_url.rstrip("/") + "/", quote=True))
    p.append('<footer>%s</footer>' % " · ".join(links))
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
    ap.add_argument("--pages-url", help="where report.html will be published; adds a JMH Visualizer link")
    ap.add_argument("-q", "--quiet", action="store_true", help="don't print the summary")
    args = ap.parse_args(argv)

    results, floor = split_floor(load(args.input))
    if not results:
        sys.exit("No candidate results in %s" % args.input)
    out_dir = args.out or os.path.dirname(os.path.abspath(args.input))
    os.makedirs(out_dir, exist_ok=True)
    props = read_properties(os.path.join(out_dir, "run.properties"))
    env = environment(results, props, floor)
    versions = lib_versions(results, props)
    by_method = group(results)
    slots = candidate_slots(results)
    baseline = {r.key: r for r in load(args.baseline)} if args.baseline else None
    title = args.title or ("date-time-wars" + (" · " + props["label"] if props.get("label") else ""))

    write_markdown(os.path.join(out_dir, "report.md"), by_method, env, baseline, title)
    write_html(os.path.join(out_dir, "report.html"), by_method, env, slots, baseline, title, results,
               versions, args.pages_url)
    write_grouped(os.path.join(out_dir, "jmh-result-grouped.json"), results + floor)
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
