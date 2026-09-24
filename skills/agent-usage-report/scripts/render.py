"""Self-contained HTML report: inline CSS, inline SVG, no network, no JS.

Every chart is generated as SVG in Python, so the output file renders on a
plane and can be emailed as a single file. Hover text uses SVG ``<title>``
elements, which every browser shows natively.
"""

from __future__ import annotations

import datetime
import html
import json

BG = "#0e1116"
PANEL = "#161b22"
PANEL2 = "#1c232d"
GRID = "#2a2f3a"
TEXT = "#e6edf3"
MUTED = "#8b949e"
BLUE = "#6ea8fe"
GREEN = "#5fd38d"
AMBER = "#f2c14e"
RED = "#ef6f6c"
PURPLE = "#b388ff"
TEAL = "#4dd0c7"

PALETTE = [BLUE, GREEN, AMBER, PURPLE, TEAL, RED, "#f78fb3", "#9ecbff"]

HARNESS_LABELS = {
    "pi": "pi",
    "claude_code": "Claude Code",
    "codex": "Codex",
    "opencode": "opencode",
    "generic": "Other",
}


def esc(value):
    return html.escape(str(value), quote=True)


def fmt_tokens(value):
    value = float(value or 0)
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "k")):
        if abs(value) >= limit:
            return "%.2f%s" % (value / limit, suffix)
    return "%d" % round(value)


def fmt_int(value):
    return "{:,}".format(int(round(float(value or 0))))


def fmt_money(value, places=None):
    value = float(value or 0)
    if places is None:
        places = 4 if abs(value) < 1 else 2
    return "$%s" % ("{:,.%df}" % places).format(value)


def fmt_people(value):
    return "%.2f" % float(value or 0)


# --------------------------------------------------------------------------
# SVG primitives
# --------------------------------------------------------------------------

def hbar(rows, width=760, row_height=28, label_width=210, value_width=90,
         color=BLUE, value_format=fmt_tokens, aria="chart"):
    """Horizontal bars. rows = [(label, value, note)]."""
    rows = [r for r in rows if r]
    if not rows:
        return _empty(aria)
    peak = max(abs(float(r[1] or 0)) for r in rows) or 1.0
    height = row_height * len(rows) + 10
    track = width - label_width - value_width
    parts = [_svg_open(width, height, aria)]
    for index, row in enumerate(rows):
        label, value = row[0], float(row[1] or 0)
        note = row[2] if len(row) > 2 and row[2] else ""
        bar_color = row[3] if len(row) > 3 and row[3] else color
        y = 5 + index * row_height
        bar_w = max(1.0, abs(value) / peak * track)
        parts.append('<title>%s: %s%s</title>' % (
            esc(label), esc(value_format(value)), (" - " + esc(note)) if note else ""))
        parts.append('<text x="0" y="%d" fill="%s" font-size="12">%s</text>'
                     % (y + 15, TEXT, esc(_clip(label, 30))))
        parts.append('<rect x="%d" y="%d" width="%d" height="14" rx="3" fill="%s" opacity="0.25"/>'
                     % (label_width, y + 4, track, bar_color))
        parts.append('<rect x="%d" y="%d" width="%d" height="14" rx="3" fill="%s"/>'
                     % (label_width, y + 4, bar_w, bar_color))
        parts.append('<text x="%d" y="%d" fill="%s" font-size="12">%s</text>'
                     % (label_width + track + 8, y + 15, MUTED, esc(value_format(value))))
        if note:
            parts.append('<text x="%d" y="%d" fill="%s" font-size="10">%s</text>'
                         % (label_width + 6, y + 26, MUTED, esc(_clip(note, 60))))
    parts.append("</svg>")
    return "".join(parts)


def vbar(rows, width=760, height=240, color=BLUE, value_format=fmt_tokens,
         aria="chart"):
    """Vertical bars. rows = [(label, value, note)]."""
    rows = [r for r in rows if r]
    if not rows:
        return _empty(aria)
    pad_bottom, pad_top, pad_left = 46, 14, 0
    plot_h = height - pad_bottom - pad_top
    peak = max(float(r[1] or 0) for r in rows) or 1.0
    slot = width / float(len(rows))
    bar_w = max(2.0, min(46.0, slot * 0.6))
    parts = [_svg_open(width, height, aria)]
    for index, row in enumerate(rows):
        label, value = row[0], float(row[1] or 0)
        note = row[2] if len(row) > 2 and row[2] else ""
        bar_h = value / peak * plot_h
        x = index * slot + (slot - bar_w) / 2.0
        y = pad_top + plot_h - bar_h
        parts.append('<title>%s: %s%s</title>' % (
            esc(label), esc(value_format(value)), (" - " + esc(note)) if note else ""))
        parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="3" fill="%s"/>'
                     % (x, y, bar_w, max(1.0, bar_h), color))
        parts.append('<text x="%.1f" y="%d" fill="%s" font-size="10" text-anchor="middle">%s</text>'
                     % (x + bar_w / 2.0, pad_top + plot_h + 14, MUTED,
                        esc(_clip(label, 10))))
    parts.append('<line x1="0" y1="%d" x2="%d" y2="%d" stroke="%s"/>'
                 % (pad_top + plot_h, width, pad_top + plot_h, GRID))
    parts.append("</svg>")
    return "".join(parts)


def line_chart(points, width=760, height=240, color=BLUE, value_format=fmt_money,
               aria="chart"):
    """Cumulative or per-day line. points = [(label, value)]."""
    points = [(p[0], float(p[1] or 0)) for p in points if p]
    if len(points) < 2:
        return _empty(aria) if not points else vbar(
            [(p[0], p[1]) for p in points], width, height, color, value_format, aria)
    pad_bottom, pad_top, pad_right = 44, 14, 16
    plot_h = height - pad_bottom - pad_top
    plot_w = width - pad_right
    peak = max(p[1] for p in points) or 1.0
    step = plot_w / float(len(points) - 1)
    coords = []
    for index, (label, value) in enumerate(points):
        x = index * step
        y = pad_top + plot_h - (value / peak * plot_h)
        coords.append((x, y, label, value))
    area = "M %.1f %.1f " % (coords[0][0], pad_top + plot_h)
    area += " ".join("L %.1f %.1f" % (c[0], c[1]) for c in coords)
    area += " L %.1f %.1f Z" % (coords[-1][0], pad_top + plot_h)
    parts = [_svg_open(width, height, aria)]
    parts.append('<path d="%s" fill="%s" opacity="0.16"/>' % (area, color))
    parts.append('<polyline fill="none" stroke="%s" stroke-width="2" points="%s"/>'
                 % (color, " ".join("%.1f,%.1f" % (c[0], c[1]) for c in coords)))
    for x, y, label, value in coords:
        parts.append('<circle cx="%.1f" cy="%.1f" r="3" fill="%s">'
                     '<title>%s: %s</title></circle>'
                     % (x, y, color, esc(label), esc(value_format(value))))
    for index in (0, len(coords) // 2, len(coords) - 1):
        x, _, label, _ = coords[index]
        parts.append('<text x="%.1f" y="%d" fill="%s" font-size="10" text-anchor="middle">%s</text>'
                     % (x, pad_top + plot_h + 16, MUTED, esc(label)))
    parts.append('<line x1="0" y1="%d" x2="%d" y2="%d" stroke="%s"/>'
                 % (pad_top + plot_h, width, pad_top + plot_h, GRID))
    parts.append("</svg>")
    return "".join(parts)


def heatmap(matrix, row_labels, col_labels, width=760, height=250, aria="heatmap"):
    rows = len(matrix) or 1
    cols = len(matrix[0]) if matrix else 24
    cell_w = (width - 60) / float(cols)
    cell_h = (height - 30) / float(rows)
    peak = max((max(r) for r in matrix), default=1) or 1
    parts = [_svg_open(width, height, aria)]
    for ri in range(rows):
        for ci in range(cols):
            value = matrix[ri][ci]
            intensity = (value / float(peak)) ** 0.6 if value else 0
            parts.append(
                '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2" '
                'fill="%s" opacity="%.2f"><title>%s %02d:00 - %d turns</title></rect>'
                % (60 + ci * cell_w, 8 + ri * cell_h, cell_w - 2, cell_h - 2,
                   BLUE, 0.08 + intensity * 0.92, esc(row_labels[ri]), ci, value))
        parts.append('<text x="0" y="%.1f" fill="%s" font-size="11">%s</text>'
                     % (15 + ri * cell_h, MUTED, esc(row_labels[ri])))
    for ci in range(0, cols, 3):
        parts.append('<text x="%.1f" y="%d" fill="%s" font-size="9" text-anchor="middle">%02d</text>'
                     % (60 + ci * cell_w + cell_w / 2.0, height - 6, MUTED, ci))
    parts.append("</svg>")
    return "".join(parts)


def donut(parts_in, width=260, height=260, aria="donut"):
    """parts = [(label, value, color)]."""
    parts_in = [(p[0], float(p[1] or 0), p[2]) for p in parts_in if p and float(p[1] or 0) > 0]
    total = sum(p[1] for p in parts_in)
    if not parts_in or not total:
        return _empty(aria)
    import math
    cx, cy, outer, inner = width / 2.0, height / 2.0, 92.0, 58.0
    angle = -math.pi / 2
    parts = [_svg_open(width, height, aria)]
    for label, value, color in parts_in:
        sweep = value / total * 2 * math.pi
        end = angle + sweep
        large = 1 if sweep > math.pi else 0
        x1, y1 = cx + outer * math.cos(angle), cy + outer * math.sin(angle)
        x2, y2 = cx + outer * math.cos(end), cy + outer * math.sin(end)
        x3, y3 = cx + inner * math.cos(end), cy + inner * math.sin(end)
        x4, y4 = cx + inner * math.cos(angle), cy + inner * math.sin(angle)
        parts.append(
            '<path d="M %.1f %.1f A %.1f %.1f 0 %d 1 %.1f %.1f L %.1f %.1f '
            'A %.1f %.1f 0 %d 0 %.1f %.1f Z" fill="%s">'
            '<title>%s: %s (%.1f%%)</title></path>'
            % (x1, y1, outer, outer, large, x2, y2, x3, y3, inner, inner, large,
               x4, y4, color, esc(label), esc(fmt_tokens(value)), value / total * 100.0))
        angle = end
    parts.append('<text x="%.1f" y="%.1f" fill="%s" font-size="16" text-anchor="middle">%s</text>'
                 % (cx, cy - 2, TEXT, esc(fmt_tokens(total))))
    parts.append('<text x="%.1f" y="%.1f" fill="%s" font-size="10" text-anchor="middle">tokens</text>'
                 % (cx, cy + 16, MUTED))
    parts.append("</svg>")
    return "".join(parts)


def scatter(points, width=760, height=340, x_label="cost per 1M ($)",
            y_label="intelligence", aria="scatter"):
    """points = [(label, x, y, color)]."""
    points = [p for p in points if p]
    if not points:
        return _empty(aria)
    pad_left, pad_bottom, pad_top, pad_right = 52, 46, 18, 100
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_bottom - pad_top
    xs = [float(p[1]) for p in points]
    ys = [float(p[2]) for p in points]
    x_lo, x_hi = min(xs), max(xs)
    y_lo, y_hi = 0.0, max(ys) * 1.15 or 1.0
    if x_hi <= x_lo:
        x_hi = x_lo + 1
    parts = [_svg_open(width, height, aria)]
    for frac in (0.25, 0.5, 0.75, 1.0):
        y = pad_top + plot_h - frac * plot_h
        parts.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" opacity="0.5"/>'
                     % (pad_left, y, pad_left + plot_w, y, GRID))
        parts.append('<text x="%d" y="%.1f" fill="%s" font-size="10" text-anchor="end">%.0f</text>'
                     % (pad_left - 8, y + 4, MUTED, y_hi * frac))
    for index, (label, x, y, color) in enumerate(points):
        px = pad_left + (float(x) - x_lo) / (x_hi - x_lo) * plot_w
        py = pad_top + plot_h - (float(y) - y_lo) / (y_hi - y_lo) * plot_h
        parts.append('<circle cx="%.1f" cy="%.1f" r="6" fill="%s" opacity="0.85">'
                     '<title>%s - %s=%s, %s=%s</title></circle>'
                     % (px, py, color, esc(label), esc(x_label), esc(fmt_money(x)),
                        esc(y_label), esc(fmt_people(y))))
        parts.append('<text x="%.1f" y="%.1f" fill="%s" font-size="10">%s</text>'
                     % (px + 9, py + 4, TEXT, esc(_clip(label, 22))))
    parts.append('<text x="%.1f" y="%d" fill="%s" font-size="11" text-anchor="middle">%s</text>'
                 % (pad_left + plot_w / 2.0, height - 8, MUTED, esc(x_label)))
    parts.append("</svg>")
    return "".join(parts)


def _svg_open(width, height, aria):
    return ('<svg viewBox="0 0 %d %d" width="100%%" role="img" aria-label="%s" '
            'preserveAspectRatio="xMidYMid meet">' % (width, height, esc(aria)))


def _empty(aria):
    return ('<svg viewBox="0 0 760 80" width="100%%" role="img" aria-label="%s">'
            '<text x="10" y="44" fill="%s" font-size="12">no data</text></svg>'
            % (esc(aria), MUTED))


def _clip(text, limit):
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1] + "\u2026"


# --------------------------------------------------------------------------
# Client-side table: sorting and filtering (no dependencies, offline-safe)
# --------------------------------------------------------------------------

_SCRIPT = """
(function () {
  var table = document.getElementById('lb');
  if (!table) { return; }
  document.getElementById('lb-hint').style.display = 'none';
  var tbody = table.tBodies[0];
  var headers = Array.prototype.slice.call(table.tHead.rows[0].cells);
  var search = document.getElementById('lb-search');
  var harness = document.getElementById('lb-harness');
  var rankedBox = document.getElementById('lb-ranked');
  var count = document.getElementById('lb-count');
  var sortKey = 'total';
  var sortDir = -1;

  function cell(row, key) {
    for (var i = 0; i < row.cells.length; i++) {
      if (row.cells[i].getAttribute('data-key') === key) { return row.cells[i]; }
    }
    return null;
  }

  function numeric(row, key) {
    var node = cell(row, key);
    if (!node) { return -Infinity; }
    var raw = node.getAttribute('data-sort');
    if (raw === null) { return -Infinity; }
    var value = parseFloat(raw);
    return isNaN(value) ? -Infinity : value;
  }

  function text(row, key) {
    var node = cell(row, key);
    return node ? node.textContent.trim().toLowerCase() : '';
  }

  function ranked(row) { return row.getAttribute('data-ranked') === '1'; }

  function passes(row) {
    if (rankedBox.checked && !ranked(row)) { return false; }
    if (harness.value && row.getAttribute('data-harness') !== harness.value) { return false; }
    var query = search.value.trim().toLowerCase();
    if (query) {
      var haystack = row.getAttribute('data-model') + ' ' + row.getAttribute('data-harness');
      if (haystack.toLowerCase().indexOf(query) < 0) { return false; }
    }
    return true;
  }

  function sortRows(rows) {
    var isText = ['model', 'harness', 'provenance'].indexOf(sortKey) >= 0;
    rows.sort(function (a, b) {
      var result;
      if (isText) {
        result = text(a, sortKey) < text(b, sortKey) ? -1 : text(a, sortKey) > text(b, sortKey) ? 1 : 0;
      } else {
        result = numeric(a, sortKey) - numeric(b, sortKey);
      }
      return result * sortDir;
    });
    return rows;
  }

  function render() {
    var rows = Array.prototype.slice.call(tbody.rows);
    var shown = sortRows(rows.filter(passes));
    tbody.innerHTML = '';
    for (var i = 0; i < shown.length; i++) { tbody.appendChild(shown[i]); }
    for (var j = 0; j < rows.length; j++) {
      rows[j].style.display = shown.indexOf(rows[j]) >= 0 ? '' : 'none';
    }
    count.textContent = shown.length + ' of ' + rows.length + ' models shown';
  }

  headers.forEach(function (node) {
    var key = node.getAttribute('data-key');
    if (!key) { return; }
    var arrow = document.createElement('span');
    arrow.className = 'arrow';
    node.appendChild(arrow);
    node.addEventListener('click', function () {
      if (sortKey === key) { sortDir = -sortDir; } else { sortKey = key; sortDir = -1; }
      headers.forEach(function (other) {
        var mark = other.querySelector('.arrow');
        if (mark) { mark.textContent = other.getAttribute('data-key') === sortKey ? (sortDir < 0 ? '\u25bc' : '\u25b2') : ''; }
      });
      render();
    });
  });

  search.addEventListener('input', render);
  harness.addEventListener('change', render);
  rankedBox.addEventListener('change', render);
  render();
})();
"""


# --------------------------------------------------------------------------
# Report assembly
# --------------------------------------------------------------------------

def build(dataset, meta, config=None):
    models = dataset["models"]
    totals = dataset["totals"]
    ranked = sorted(dataset["ranking"], key=lambda e: e["intelligence_score"], reverse=True)
    all_models = sorted(models.values(), key=lambda e: e["total"], reverse=True)

    sections = [
        _hero(dataset, meta, totals),
        _leaders(dataset, totals),
        _leaderboard(all_models, dataset["min_turns"]),
        _cost_section(all_models, totals),
        _intelligence_section(ranked, dataset),
        _efficiency_section(dataset),
        _projects_section(dataset),
        _time_section(dataset),
        _tools_section(all_models),
        _context_section(all_models),
        _activity_section(dataset),
        _switching_section(dataset),
        _waste_section(all_models, totals),
        _methodology(dataset, meta),
    ]
    return _page(meta, sections)


def _page(meta, sections):
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent usage report - %(title)s</title>
<style>
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; background: %(bg)s; color: %(text)s;
  font: 14px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Ubuntu, sans-serif; }
.wrap { max-width: 1020px; margin: 0 auto; padding: 32px 20px 80px; }
h1 { font-size: 26px; margin: 0 0 4px; letter-spacing: -0.02em; }
h2 { font-size: 18px; margin: 0 0 14px; letter-spacing: -0.01em; }
h3 { font-size: 14px; margin: 0 0 10px; color: %(muted)s; text-transform: uppercase; letter-spacing: 0.08em; }
p { margin: 0 0 12px; }
.sub { color: %(muted)s; margin-bottom: 26px; }
section { background: %(panel)s; border: 1px solid %(grid)s; border-radius: 12px;
  padding: 22px; margin-bottom: 18px; }
.grid { display: grid; gap: 12px; }
.cards { grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }
.two { grid-template-columns: 1fr 1fr; }
@media (max-width: 720px) { .two { grid-template-columns: 1fr; } }
.card { background: %(panel2)s; border: 1px solid %(grid)s; border-radius: 10px; padding: 14px; }
.card .k { color: %(muted)s; font-size: 11px; text-transform: uppercase; letter-spacing: 0.07em; }
.card .v { font-size: 22px; font-weight: 600; margin-top: 4px; letter-spacing: -0.02em; }
.card .n { color: %(muted)s; font-size: 11px; margin-top: 2px; }
table { width: 100%%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: right; padding: 8px 6px; border-bottom: 1px solid %(grid)s; white-space: nowrap; }
th:first-child, td:first-child { text-align: left; }
th { color: %(muted)s; font-weight: 500; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }
td.num, th.num { font-variant-numeric: tabular-nums; }
tr.dim td { opacity: 0.5; }
.badge { display: inline-block; padding: 1px 7px; border-radius: 20px; font-size: 11px;
  border: 1px solid %(grid)s; color: %(muted)s; }
.badge.good { color: %(green)s; border-color: rgba(95,211,141,0.4); }
.badge.warn { color: %(amber)s; border-color: rgba(242,193,78,0.4); }
.badge.bad { color: %(red)s; border-color: rgba(239,111,108,0.4); }
.winner { border-color: rgba(110,168,254,0.5);
  background: linear-gradient(180deg, rgba(110,168,254,0.09), rgba(110,168,254,0.02)); }
.winner .v { color: %(blue)s; }
.scroll { overflow-x: auto; }
.reasons { margin: 0; padding-left: 18px; color: %(muted)s; font-size: 13px; }
.reasons li { margin-bottom: 3px; }
.reasons b { color: %(text)s; font-weight: 600; }
.legend { display: flex; gap: 14px; flex-wrap: wrap; color: %(muted)s; font-size: 12px; margin-top: 8px; }
.legend span i { display: inline-block; width: 9px; height: 9px; border-radius: 3px; margin-right: 5px; }
svg { display: block; }
footer { color: %(muted)s; font-size: 12px; margin-top: 26px; }
code { background: %(panel2)s; padding: 1px 5px; border-radius: 4px; font-size: 12px; }
.controls { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-bottom: 14px; }
.controls input[type=text], .controls select { background: %(panel2)s; border: 1px solid %(grid)s;
  color: %(text)s; padding: 6px 10px; border-radius: 8px; font-size: 13px; min-width: 150px; }
.controls input[type=text]:focus, .controls select:focus { outline: 1px solid %(blue)s; }
.controls label { color: %(muted)s; font-size: 12px; display: flex; align-items: center; gap: 5px; }
.controls .count { color: %(muted)s; font-size: 12px; margin-left: auto; }
th[data-key] { cursor: pointer; user-select: none; }
th[data-key]:hover { color: %(text)s; }
th .arrow { opacity: 0.55; margin-left: 4px; font-size: 9px; }
.nojs { color: %(amber)s; font-size: 12px; }
</style>
</head>
<body><div class="wrap">
%(body)s
<footer>Generated %(generated)s by <code>agent-usage-report</code>.</footer>
</div>
<script>
%(script)s
</script>
</body></html>""" % {
        "bg": BG, "panel": PANEL, "panel2": PANEL2, "grid": GRID, "text": TEXT,
        "muted": MUTED, "blue": BLUE, "green": GREEN, "amber": AMBER, "red": RED,
        "title": esc(meta["window"]),
        "generated": esc(meta["generated"]),
        "body": "\n".join(sections),
        "script": _SCRIPT,
    }


def _card(key, value, note="", klass=""):
    return ('<div class="card %s"><div class="k">%s</div><div class="v">%s</div>'
            '<div class="n">%s</div></div>' % (klass, esc(key), esc(value), esc(note)))


def _hero(dataset, meta, totals):
    cards = [
        _card("Total spend", fmt_money(totals["cost"]),
              "%s recorded, %s estimated" % (
                  fmt_money(totals["cost_recorded"]), fmt_money(totals["cost_computed"]))),
        _card("Total tokens", fmt_tokens(totals["tokens"]),
              "%s in, %s out" % (fmt_tokens(totals["input"] + totals["cache_read"]),
                                 fmt_tokens(totals["output"]))),
        _card("Models", fmt_int(totals["models"]),
              "%d ranked, %d low-sample" % (len(dataset["ranking"]), len(dataset["unranked"]))),
        _card("Sessions", fmt_int(totals["sessions"]),
              "%s requests, %s turns" % (fmt_int(totals["requests"]), fmt_int(totals["turns"]))),
        _card("Blended rate", "%s / 1M" % fmt_money(totals["blended_per_million"]),
              "across all models and harnesses"),
        _card("Cache hit rate", "%.1f%%" % totals["cache_hit_rate"],
              "%s avoided at full input rates" % fmt_money(totals["cache_saving"])),
    ]
    harness_bits = ", ".join("%s (%s)" % (esc(h["label"]), fmt_int(h["records"]))
                             for h in meta["detected"]) or "none"
    window = ("%s to %s" % (esc(meta["window_start"]), esc(meta["window_end"])))
    return section(
        "<h1>Agent usage and spend</h1>"
        '<p class="sub">%s &middot; harnesses found: %s</p>'
        '<div class="grid cards">%s</div>' % (window, harness_bits, "".join(cards)),
        title=None)


def section(body, title=None):
    heading = "<h2>%s</h2>" % esc(title) if title else ""
    return '<section>%s%s</section>' % (heading, body)


def _leaders(dataset, totals):
    intel = dataset["leaders"]["most_intelligent"]
    eff = dataset["leaders"]["most_efficient"]
    cards = []
    if intel:
        cards.append(_winner_card("Most intelligent", intel, _intel_reasons(intel, dataset)))
    else:
        cards.append('<div class="card"><div class="k">Most intelligent</div>'
                     '<div class="v">&ndash;</div><div class="n">no model reached the '
                     'minimum of %d turns</div></div>' % dataset["min_turns"])
    if eff:
        cards.append(_winner_card("Most efficient", eff, _eff_reasons(eff, dataset)))
    else:
        cards.append('<div class="card"><div class="k">Most efficient</div>'
                     '<div class="v">&ndash;</div><div class="n">not enough data</div></div>')
    return section('<div class="grid two">%s</div>' % "".join(cards),
                   "The verdicts")


def _winner_card(title, entry, reasons):
    badge = "high" if entry.get("confidence") == "high" else entry.get("confidence", "")
    return ('<div class="card winner"><div class="k">%s</div>'
            '<div class="v">%s</div>'
            '<div class="n">%s turns &middot; %s / 1M &middot; %s intelligence '
            '&middot; <span class="badge good">%s confidence</span></div>'
            '<ul class="reasons">%s</ul></div>'
            % (esc(title), esc(entry["model"]), fmt_int(entry["turns"]),
               fmt_money(entry["cost_per_million"]), fmt_people(entry["intelligence_score"]),
               esc(badge),
               "".join("<li>%s</li>" % r for r in reasons)))


def _intel_reasons(entry, dataset):
    signals = entry.get("signals") or {}
    weights = dataset["weights"]
    ranked_by = sorted(signals.items(), key=lambda kv: -kv[1] * weights.get(kv[0], 0))
    labels = {
        "turns_per_request": "%s turns/request",
        "failure_rate": "%s%% failed turns or tool calls",
        "reasoning_share": "%s%% reasoning share",
        "tokens_per_request": "%s tokens/request",
        "correction_rate": "%s%% correction rate",
    }
    reasons = []
    for name, _ in ranked_by[:3]:
        reasons.append("<b>%s</b>: %s" % (
            esc(name.replace("_", " ")), esc(labels[name] % fmt_people(entry.get(name)))))
    reasons.append("scored against %d other models with 30+ turns" % max(0, len(dataset["ranking"]) - 1))
    return reasons


def _eff_reasons(entry, dataset):
    return [
        "<b>value per dollar</b>: %s intelligence per $1/1M" % fmt_people(entry.get("value_per_dollar")),
        "<b>blended rate</b>: %s per 1M tokens" % fmt_money(entry["cost_per_million"]),
        "<b>total spend</b>: %s over %s turns" % (fmt_money(entry["cost_total"]), fmt_int(entry["turns"])),
    ]


def _leaderboard(all_models, min_turns):
    if not all_models:
        return section("<p>No model turns found.</p>", "Model leaderboard")

    columns = [
        ("model", "Model", "text"),
        ("harness", "Harness", "text"),
        ("turns", "Turns", "num"),
        ("input", "Input", "num"),
        ("output", "Output", "num"),
        ("total", "Total", "num"),
        ("cost_per_million", "$/1M", "num"),
        ("cost_total", "Cost", "num"),
        ("intelligence_score", "Intel", "num"),
        ("efficiency_score", "Eff", "num"),
        ("provenance", "Cost source", "text"),
    ]
    head = "<tr>" + "".join(
        "<th data-key='%s' class='%s'>%s</th>" % (key, "num" if kind == "num" else "", label)
        for key, label, kind in columns) + "</tr>"

    rows = []
    for entry in all_models:
        harness = _dominant(entry.get("harnesses"))
        is_ranked = entry.get("intelligence_score") is not None
        dim = "" if is_ranked else ' class="dim"'
        provenance = entry.get("cost_provenance") or "?"
        prov_class = {"recorded": "good", "computed": "warn", "mixed": ""}.get(provenance, "")
        cells = [
            ("model", entry["model"], None, "text"),
            ("harness", HARNESS_LABELS.get(harness, harness), None, "text"),
            ("turns", fmt_int(entry["turns"]), entry["turns"], "num"),
            ("input", fmt_tokens(entry["input"]), entry["input"], "num"),
            ("output", fmt_tokens(entry["output"]), entry["output"], "num"),
            ("total", fmt_tokens(entry["total"]), entry["total"], "num"),
            ("cost_per_million", fmt_money(entry["cost_per_million"]),
             entry["cost_per_million"], "num"),
            ("cost_total", fmt_money(entry["cost_total"]), entry["cost_total"], "num"),
            ("intelligence_score",
             "%.1f" % entry["intelligence_score"] if is_ranked else "&ndash;",
             entry["intelligence_score"] if is_ranked else None, "num"),
            ("efficiency_score",
             "%.0f" % entry["efficiency_score"] if is_ranked else "&ndash;",
             entry["efficiency_score"] if is_ranked else None, "num"),
            ("provenance", "<span class='badge %s'>%s</span>" % (prov_class, esc(provenance)),
             None, "text"),
        ]
        rendered = []
        for key, display, sort_value, kind in cells:
            sort_attr = "" if sort_value is None else " data-sort='%s'" % sort_value
            klass = " class='num'" if kind == "num" else ""
            rendered.append("<td data-key='%s'%s%s>%s</td>" % (key, klass, sort_attr, display))
        rows.append("<tr%s data-model=\"%s\" data-harness=\"%s\" data-ranked=\"%d\">%s</tr>"
                    % (dim, esc(entry["model"]), esc(harness), 1 if is_ranked else 0,
                       "".join(rendered)))

    harnesses = sorted({_dominant(e.get("harnesses")) for e in all_models})
    options = "".join("<option value='%s'>%s</option>" % (esc(name), esc(HARNESS_LABELS.get(name, name)))
                      for name in harnesses)
    controls = (
        '<div class="controls">'
        '<input type="text" id="lb-search" placeholder="Filter models...">'
        '<select id="lb-harness"><option value="">All harnesses</option>%s</select>'
        '<label><input type="checkbox" id="lb-ranked"> Ranked only</label>'
        '<span class="count" id="lb-count"></span>'
        '</div>' % options)
    hint = ('<p class="nojs" id="lb-hint">Sort by clicking a column header, or filter '
            'with the controls above. (Enable JavaScript to use them.)</p>')
    note = ("Models under %d turns are dimmed and not ranked: too little data to "
            "compare fairly. Click a column to sort; every sort is stable and "
            "low-sample models stay dimmed." % min_turns)
    return section(controls + hint
                   + '<div class="scroll"><table id="lb"><thead>%s</thead><tbody>%s</tbody></table></div>'
                   % (head, "".join(rows))
                   + '<p class="sub" style="margin-top:12px">%s</p>' % esc(note),
                   "Model leaderboard")


def _dominant(mapping):
    if not mapping:
        return ""
    return sorted(mapping.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def _cost_section(all_models, totals):
    with_cost = [e for e in all_models if e.get("cost_per_million")]
    rows = [(e["model"], e["cost_per_million"],
             "%s total, %s turns" % (fmt_money(e["cost_total"]), fmt_int(e["turns"])),
             PALETTE[index % len(PALETTE)]) for index, e in enumerate(with_cost)]
    split = totals.get("cost_split") or {}
    donut_parts = [
        ("Cache read", split.get("cache_read", 0), TEAL),
        ("Cache write", split.get("cache_write", 0), PURPLE),
        ("Output", split.get("output", 0), GREEN),
        ("Input (uncached)", split.get("input", 0), BLUE),
    ]
    top = sorted(with_cost, key=lambda e: -e["cost_total"])[:5]
    legend = "".join('<span><i style="background:%s"></i>%s %s</span>'
                     % (color, esc(label), fmt_money(value))
                     for label, value, color in donut_parts)
    body = ('<div class="grid two"><div><h3>Cost per 1 million tokens</h3>%s</div>'
            '<div><h3>Where the money went (estimated from rates)</h3>%s'
            '<div class="legend">%s</div></div></div>'
            '<p class="sub" style="margin-top:14px">Blended rate across everything: '
            '<b>%s per 1M</b>. Cache reads served <b>%.1f%%</b> of all input tokens; '
            'paying full input rates for that volume would have added about <b>%s</b>.</p>'
            '<h3 style="margin-top:18px">Top spenders</h3>%s'
            % (hbar(rows, value_format=lambda v: fmt_money(v), color=AMBER),
               donut(donut_parts), legend,
               fmt_money(totals["blended_per_million"]), totals["cache_hit_rate"],
               fmt_money(totals["cache_saving"]),
               hbar([(e["model"], e["cost_total"],
                      "%s%% of spend" % fmt_people(
                          e["cost_total"] * 100.0 / (totals["cost"] or 1)))
                     for e in top], value_format=fmt_money, color=RED)))
    return section(body, "Cost")


def _intelligence_section(ranked, dataset):
    if not ranked:
        return section("<p>No model has enough turns to rank.</p>", "Intelligence signals")
    weights = dataset["weights"]
    rows = [(e["model"], e["intelligence_score"], e.get("confidence", "")) for e in ranked]
    signal_rows = []
    for name, weight in sorted(weights.items(), key=lambda kv: -kv[1]):
        value = ranked[0].get("signals", {}).get(name, 0)
        signal_rows.append("%s (weight %.0f%%)" % (esc(name.replace("_", " ")), weight * 100))
    signal_svg = vbar([(name.replace("_", " "), ranked[0]["signals"].get(name, 0))
                       for name in weights], color=BLUE,
                      value_format=lambda v: "%.0f" % v)
    body = ('<div class="grid two"><div>%s</div><div><h3>%s - signal breakdown</h3>%s</div></div>'
            '<div class="legend">%s</div>'
            % (hbar(rows, value_format=lambda v: "%.1f" % v, color=BLUE),
               esc(ranked[0]["model"]), signal_svg,
               "".join("<span>%s</span>" % s for s in signal_rows)))
    return section(body, "Intelligence")


def _efficiency_section(dataset):
    ranked = dataset["ranking"]
    if not ranked:
        return section("<p>No model has enough turns to rank.</p>", "Efficiency")
    points = [(e["model"], e["cost_per_million"], e["intelligence_score"],
               PALETTE[index % len(PALETTE)]) for index, e in enumerate(ranked)]
    rows = [(e["model"], e["efficiency_score"],
             "%s intel per $1/1M" % fmt_people(e.get("value_per_dollar"))) for e in
            sorted(ranked, key=lambda x: -x["efficiency_score"])]
    return section(
        '<h3>Quality per dollar - upper-left is best</h3>%s'
        '<div class="grid two" style="margin-top:14px"><div><h3>Efficiency score</h3>%s</div></div>'
        % (scatter(points), hbar(rows, value_format=lambda v: "%.0f" % v, color=GREEN)),
        "Efficiency")


def _projects_section(dataset):
    projects = sorted(dataset["projects"].values(), key=lambda p: -p["total"])[:12]
    if not projects:
        return section("<p>No project data.</p>", "Projects")
    rows = [(p["project"], p["total"],
             "%s, %s turns" % (fmt_money(p.get("cost_recorded", 0)), fmt_int(p["turns"])),
             PALETTE[index % len(PALETTE)]) for index, p in enumerate(projects)]
    return section(hbar(rows, label_width=280), "Projects by tokens")


def _time_section(dataset):
    daily = sorted(dataset["daily"].values(), key=lambda d: d["day"])
    if not daily:
        return section("<p>No time data.</p>", "Spend over time")
    cost_points = [(d["day"][5:], d["cost_recorded"]) for d in daily]
    token_points = [(d["day"][5:], d["total"]) for d in daily]
    total_cost = sum(d["cost_recorded"] for d in daily)
    days = max(1, len(daily))
    burn = total_cost / days
    body = ('<div class="grid two"><div><h3>Recorded cost per day</h3>%s</div>'
            '<div><h3>Tokens per day</h3>%s</div></div>'
            '<p class="sub" style="margin-top:12px">Average burn %s/day across %d active days '
            '(recorded cost only; estimated cost from Claude Code and Codex is not dated per day).</p>'
            % (line_chart(cost_points, value_format=fmt_money, color=AMBER),
               line_chart(token_points, value_format=fmt_tokens, color=BLUE),
               fmt_money(burn), days))
    return section(body, "Spend over time")


def _tools_section(all_models):
    totals = {}
    for entry in all_models:
        for name, count in (entry.get("tools") or {}).items():
            totals[name] = totals.get(name, 0) + count
    if not totals:
        return section("<p>No tool call data in these harnesses.</p>", "Tool usage")
    rows = sorted(totals.items(), key=lambda kv: -kv[1])[:14]
    per_model = [(e["model"], e["tool_calls"], "%s%% tool error rate" % fmt_people(e["tool_error_rate"]))
                 for e in sorted(all_models, key=lambda x: -x["tool_calls"])[:10] if e["tool_calls"]]
    body = ('<div class="grid two"><div><h3>Most-called tools (all harnesses)</h3>%s</div>'
            '<div><h3>Tool calls per model</h3>%s</div></div>'
            % (hbar([(k, v) for k, v in rows], color=TEAL), hbar(per_model, color=PURPLE)))
    return section(body, "Tool usage")


def _context_section(all_models):
    rows = [(e["model"], e.get("avg_input_per_turn", 0),
             "%s%% of a %s window" % (fmt_people(e.get("context_pressure", 0)),
                                      fmt_tokens(e.get("context_window", 0))))
            for e in all_models if e.get("context_window")]
    if not rows:
        return section("<p>No context window data (pricing catalog unavailable).</p>",
                       "Context pressure")
    rows.sort(key=lambda r: -r[1])
    body = ('<h3>Average input tokens per turn</h3>%s'
            '<p class="sub" style="margin-top:12px">How much of the model context window an '
            'average turn consumes. Higher means you rely on long context and pay more per call.</p>'
            % hbar(rows[:14], color=BLUE))
    return section(body, "Context pressure")


def _activity_section(dataset):
    matrix = dataset["hourly"]
    if not any(any(row) for row in matrix):
        return section("<p>No activity data.</p>", "When you work")
    body = ('<h3>Turns by weekday and hour (local time)</h3>%s'
            % heatmap(matrix, dataset["weekdays"], [str(h) for h in range(24)]))
    return section(body, "When you work")


def _switching_section(dataset):
    switches = dataset.get("switches") or {}
    if not switches:
        return section("<p>No model switching detected.</p>", "Model switching")
    rows = sorted(switches.items(), key=lambda kv: -kv[1])[:10]
    items = [("%s → %s" % (a, b), count) for (a, b), count in rows]
    return section(hbar(items, label_width=300, color=PURPLE), "Model switching")


def _waste_section(all_models, totals):
    wasteful = [e for e in all_models if e.get("error_stops")]
    if not wasteful:
        return section('<p class="sub">No failed or aborted turns recorded. Clean run.</p>',
                       "Waste")
    rows = [(e["model"], e["waste_cost"],
             "%s failed/aborted of %s turns (%s%%)"
             % (fmt_int(e["error_stops"]), fmt_int(e["turns"]), fmt_people(e["error_rate"])))
            for e in sorted(wasteful, key=lambda x: -x.get("waste_cost", 0))]
    body = ('<div class="grid cards">%s%s</div><div style="margin-top:16px">%s</div>'
            % (_card("Failed turns", fmt_int(totals["wasted_turns"])),
               _card("Estimated waste", fmt_money(totals["waste"]),
                     "cost of turns that errored or aborted"),
               hbar(rows, value_format=fmt_money, color=RED)))
    return section(body, "Waste")


def _methodology(dataset, meta):
    weights = dataset["weights"]
    weight_bits = ", ".join("%s %.0f%%" % (esc(k.replace("_", " ")), v * 100)
                            for k, v in sorted(weights.items(), key=lambda kv: -kv[1]))
    detected = ", ".join("%s (%s records)" % (esc(h["label"]), fmt_int(h["records"]))
                         for h in meta["detected"]) or "none"
    missing = ", ".join(esc(m) for m in meta["missing"]) or "none"
    body = """
<h3>Signals</h3>
<p class="sub">Intelligence is a weighted percentile composite: %s. Each signal is
scaled 0-100 across the models you actually used, best to worst, so a score is
relative to your own usage, not a public benchmark.</p>
<h3>Ranking rules</h3>
<ul class="reasons">
<li>Models with fewer than <b>%d turns</b> are listed but not ranked.</li>
<li>Scores are shrunk toward the group mean by sample size (k = <b>%s turns</b>), so a
model with barely enough turns cannot win on a lucky percentile.</li>
<li><b>Efficiency</b> = intelligence divided by blended cost per 1M tokens; a free
model that also scores well wins outright.</li>
<li><b>Corrections</b> are short user messages after the first that push back
(keywords such as "no", "wrong", "actually", "try again"). This is a heuristic.</li>
<li>Requests and their tokens depend on how hard a task was, so a model used for
short questions can look thriftier than one driving long agentic sessions.
Read the score alongside the turns column, not on its own.</li>
</ul>
<h3>Cost</h3>
<p class="sub">Harnesses that record real spend (pi, opencode) keep it. Claude Code
and Codex log tokens but no dollars, so their cost is estimated from per-million
rates. Rates come from: <b>%s</b>. Records marked <span class="badge good">recorded</span>
are billed truth; <span class="badge warn">computed</span> are estimates.</p>
<h3>Sources</h3>
<ul class="reasons">
<li>Harnesses found: %s</li>
<li>Harnesses not present: %s</li>
<li>Pricing catalog: %s</li>
</ul>
""" % (weight_bits, dataset["min_turns"], fmt_people(dataset.get("shrink_turns", 0)),
       esc(meta["pricing_source"]),
       detected, missing, fmt_int(meta["pricing_models"]) + " models")
    return section(body, "Methodology")


def dump_json(dataset, meta):
    """A compact machine-readable sidecar (no raw turns)."""
    models = []
    for entry in sorted(dataset["models"].values(), key=lambda e: -e["total"]):
        clean = {k: v for k, v in entry.items() if not k.startswith("_")}
        clean["harnesses"] = dict(entry.get("harnesses") or {})
        clean["providers"] = dict(entry.get("providers") or {})
        models.append(clean)
    payload = {
        "generated": meta["generated"],
        "window": meta["window"],
        "pricing_source": meta["pricing_source"],
        "min_turns": dataset["min_turns"],
        "weights": dataset["weights"],
        "totals": dataset["totals"],
        "leaders": {
            "most_intelligent": (dataset["leaders"]["most_intelligent"] or {}).get("model"),
            "most_efficient": (dataset["leaders"]["most_efficient"] or {}).get("model"),
        },
        "models": models,
    }
    return json.dumps(payload, indent=2, sort_keys=True, default=str)
