from flask import Flask, request, jsonify
import math
from collections import deque

app = Flask(__name__)

# ======================
# CONFIG
# ======================
MAX_POINTS = 500
data_store = deque(maxlen=MAX_POINTS)

running = False
sampling_interval = 0.5  # default 0.5s

identified_diode = None

# ======================
# DIODE DB (clean)
# ======================
DIODE_DATABASE = [
    {"id":"schottky","name":"Schottky","vf_min":0.1,"vf_max":0.35,"n":1.1,"Is_nA":100},
    {"id":"germanium","name":"Germanium","vf_min":0.15,"vf_max":0.40,"n":1.0,"Is_nA":500},
    {"id":"silicon","name":"Silicon","vf_min":0.55,"vf_max":0.80,"n":1.8,"Is_nA":10},
    {"id":"led","name":"LED","vf_min":1.6,"vf_max":3.3,"n":2.0,"Is_nA":0.001},
]

# ======================
# SAFE EXP (important)
# ======================
def safe_exp(x):
    if x > 40:
        return math.exp(40)
    return math.exp(x)

# ======================
# SIMPLE SMOOTHING
# ======================
def smooth(data, window=3):
    if len(data) < window:
        return data
    out = []
    for i in range(len(data)):
        chunk = data[max(0,i-window):i+1]
        u = sum(p["U"] for p in chunk)/len(chunk)
        i_ = sum(p["I"] for p in chunk)/len(chunk)
        out.append({"U":u,"I":i_})
    return out

# ======================
# IDENTIFICATION v2
# ======================
def identify(data):
    if len(data) < 10:
        return None

    data = smooth(list(data))

    u = [p["U"] for p in data]
    i = [p["I"] for p in data]

    imax = max(i)
    if imax <= 0:
        return None

    vf = next((u[k] for k in range(len(i)) if i[k] > 0.1*imax), u[-1])

    best = None
    best_score = -999

    for d in DIODE_DATABASE:
        score = 0

        # Vf match
        if d["vf_min"] <= vf <= d["vf_max"]:
            score += 60
        else:
            score -= abs(vf - d["vf_min"]) * 30

        # realism bonus
        score += 20 if d["n"] > 1 else 10

        if score > best_score:
            best_score = score
            best = d

    return {
        "type": best["name"],
        "vf": round(vf,3),
        "confidence": min(95, max(40, int(best_score))),
        "n": best["n"],
        "Is_nA": best["Is_nA"]
    }

# ======================
# ROUTES
# ======================
@app.route("/start")
def start():
    global running
    running = True
    return {"status":"running","interval":sampling_interval}

@app.route("/stop")
def stop():
    global running
    running = False
    return {"status":"stopped"}

@app.route("/set_interval/<float:t>")
def set_interval(t):
    global sampling_interval
    sampling_interval = max(0.1, min(5, t))
    return {"interval":sampling_interval}

@app.route("/reset")
def reset():
    data_store.clear()
    return {"status":"reset"}

@app.route("/data", methods=["POST"])
def data():
    if not running:
        return {"status":"stopped"}

    d = request.json
    U = float(d.get("voltage",0))
    I = float(d.get("current",0))

    if U >= 0 and I >= 0:
        data_store.append({"U":U,"I":I})

    return {"ok":True,"size":len(data_store)}

@app.route("/get_data")
def get_data():
    return list(data_store)

@app.route("/identify")
def do_identify():
    global identified_diode
    res = identify(data_store)
    identified_diode = res
    return res or {"error":"not enough data"}


@app.route("/export_csv")
def export_csv():
    csv_data = "U(V),I(mA)\n"
    for d in data_store:
        csv_data += f"{d['U']},{d['I']}\n"
    return csv_data, 200, {
        "Content-Type": "text/csv",
        "Content-Disposition": "attachment; filename=mesures_diode.csv"
    }


@app.route("/export_pdf")
def export_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                     Paragraph, Spacer, Image, HRFlowable)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    import io, datetime, matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    elements = []

    title_style   = ParagraphStyle('t',   fontSize=20, textColor=colors.HexColor('#0a2342'),
                                   fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=4)
    sub_style     = ParagraphStyle('s',   fontSize=10, textColor=colors.HexColor('#1e6ab0'),
                                   fontName='Helvetica', alignment=TA_CENTER, spaceAfter=2)
    date_style    = ParagraphStyle('d',   fontSize=9,  textColor=colors.grey,
                                   fontName='Helvetica', alignment=TA_CENTER, spaceAfter=12)
    section_style = ParagraphStyle('sec', fontSize=12, textColor=colors.HexColor('#0a2342'),
                                   fontName='Helvetica-Bold', spaceAfter=6, spaceBefore=10)

    now = datetime.datetime.now().strftime("%d/%m/%Y à %H:%M:%S")

    elements.append(Paragraph("SMART DIODE DASHBOARD", title_style))
    elements.append(Paragraph("Rapport de Mesures Expérimentales — ESP32 + MCP4725", sub_style))
    elements.append(Paragraph(f"Généré le : {now}", date_style))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1e6ab0'), spaceAfter=12))

    if identified_diode:
        elements.append(Paragraph("Identification de la Diode", section_style))
        id_data = [
            ["Type identifié", f"{identified_diode['type']} ({identified_diode['model']})"],
            ["Description", identified_diode["description"]],
            ["Applications", identified_diode.get("applications", "—")],
            ["Tension de seuil Vf", f"{identified_diode['vf']} V"],
            ["Facteur d'idéalité n", str(identified_diode["n"])],
            ["Courant de saturation Is", identified_diode.get("Is_display", "—")],
            ["Niveau de confiance", f"{identified_diode['confidence']} %"],
        ]
        id_table = Table(id_data, colWidths=[5.5*cm, 10.5*cm])
        id_table.setStyle(TableStyle([
            ('FONTNAME',      (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME',      (1,0), (1,-1), 'Helvetica'),
            ('FONTSIZE',      (0,0), (-1,-1), 10),
            ('TEXTCOLOR',     (0,0), (0,-1), colors.HexColor('#0a2342')),
            ('ROWBACKGROUNDS',(0,0), (-1,-1), [colors.HexColor('#eef4fb'), colors.white]),
            ('GRID',          (0,0), (-1,-1), 0.5, colors.HexColor('#b0c8e0')),
            ('TOPPADDING',    (0,0), (-1,-1), 7),
            ('BOTTOMPADDING', (0,0), (-1,-1), 7),
            ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ]))
        elements.append(id_table)
        elements.append(Spacer(1, 0.4*cm))

    nb = len(data_store)
    u_max = max((d['U'] for d in data_store), default=0)
    i_max = max((d['I'] for d in data_store), default=0)

    elements.append(Paragraph("Informations de Mesure", section_style))
    info_data = [
        ["Composant", identified_diode["type"] if identified_diode else "Diode"],
        ["Points acquis", str(nb)],
        ["Tension max mesurée", f"{u_max:.3f} V"],
        ["Courant max mesuré", f"{i_max:.3f} mA"],
    ]
    info_table = Table(info_data, colWidths=[5.5*cm, 10.5*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME',      (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 10),
        ('TEXTCOLOR',     (0,0), (0,-1), colors.HexColor('#0a2342')),
        ('ROWBACKGROUNDS',(0,0), (-1,-1), [colors.HexColor('#eef4fb'), colors.white]),
        ('GRID',          (0,0), (-1,-1), 0.5, colors.HexColor('#b0c8e0')),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.4*cm))

    if nb > 0:
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#ccc'), spaceAfter=8))
        elements.append(Paragraph("Courbe Caractéristique I = f(U)", section_style))

        u_vals = [d['U'] for d in data_store]
        i_vals = [d['I'] for d in data_store]

        fig, ax = plt.subplots(figsize=(7.5, 4))
        ax.plot(u_vals, i_vals, color='#1e6ab0', linewidth=2.5, marker='o',
                markersize=3, label='Mesure réelle', zorder=3)

        if identified_diode:
            Is = identified_diode['Is_nA'] * 1e-9
            n  = identified_diode['n']
            Vt = 0.02585
            v_th = [i * max(u_vals, default=3.3) / 300 for i in range(301)]
            i_th = [min(Is * (math.exp(v / (n * Vt)) - 1) * 1000, i_max * 2) for v in v_th]
            color_hex = identified_diode.get('color', '#ff9800')
            ax.plot(v_th, i_th, color=color_hex, linewidth=2, linestyle='--',
                    label=f"Shockley — {identified_diode['type']}", zorder=2)
            ax.legend(fontsize=9, facecolor='#f8fbff')

        ax.set_xlabel("Tension U (V)", fontsize=10)
        ax.set_ylabel("Courant I (mA)", fontsize=10)
        title_txt = identified_diode["type"] if identified_diode else "Diode"
        ax.set_title(f"Courbe I = f(U) — {title_txt}", fontsize=11,
                     color='#0a2342', fontweight='bold')
        ax.grid(True, color='#e0e8f0', linewidth=0.5)
        ax.set_facecolor('#f8fbff')
        fig.patch.set_facecolor('white')
        plt.tight_layout()

        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        img_buf.seek(0)
        elements.append(Image(img_buf, width=15*cm, height=8*cm))
        elements.append(Spacer(1, 0.4*cm))

    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#ccc'), spaceAfter=8))
    elements.append(Paragraph("Tableau des Données Acquises", section_style))

    table_data = [["#", "Tension U (V)", "Courant I (mA)"]]
    for i, d in enumerate(data_store):
        table_data.append([str(i+1), f"{float(d['U']):.3f}", f"{float(d['I']):.3f}"])

    t = Table(table_data, colWidths=[2*cm, 7*cm, 7*cm], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  colors.HexColor('#0a2342')),
        ('TEXTCOLOR',     (0,0), (-1,0),  colors.white),
        ('FONTNAME',      (0,0), (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,0),  11),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING',    (0,0), (-1,0),  8),
        ('BOTTOMPADDING', (0,0), (-1,0),  8),
        ('FONTNAME',      (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE',      (0,1), (-1,-1), 10),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [colors.HexColor('#eef4fb'), colors.white]),
        ('TEXTCOLOR',     (0,1), (-1,-1), colors.HexColor('#0a2342')),
        ('TOPPADDING',    (0,1), (-1,-1), 5),
        ('BOTTOMPADDING', (0,1), (-1,-1), 5),
        ('GRID',          (0,0), (-1,-1), 0.5, colors.HexColor('#b0c8e0')),
        ('BOX',           (0,0), (-1,-1), 1.5, colors.HexColor('#0a2342')),
    ]))
    elements.append(t)

    elements.append(Spacer(1, 0.5*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#ccc'), spaceAfter=4))
    elements.append(Paragraph("Smart Diode Dashboard — ESP32 + MCP4725 — Rapport automatique",
        ParagraphStyle('foot', fontSize=8, textColor=colors.grey, alignment=TA_CENTER)))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read(), 200, {
        "Content-Type": "application/pdf",
        "Content-Disposition": "attachment; filename=rapport_diode.pdf"
    }


# ===============================
# HTML DASHBOARD
# ===============================
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Smart Diode Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/hammerjs@2.0.8/hammer.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>
<style>
:root {
  --bg:        #060a10;
  --bg2:       #0b1220;
  --bg3:       #111827;
  --border:    #1e2d45;
  --border2:   #243450;
  --text:      #e2eaf6;
  --muted:     #5a7090;
  --accent:    #00d4ff;
  --accent2:   #0099cc;
  --green:     #00e5a0;
  --orange:    #ff9500;
  --red:       #ff4560;
  --mono:      'Space Mono', monospace;
  --sans:      'DM Sans', sans-serif;
  --radius:    10px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--bg);
  font-family: var(--sans);
  color: var(--text);
  min-height: 100vh;
  overflow-x: hidden;
}

/* ── GRID BACKGROUND ── */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 0;
}

/* ── HEADER ── */
.header {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
  height: 58px;
  background: rgba(11,18,32,0.95);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(10px);
}
.header-logo {
  display: flex;
  align-items: center;
  gap: 12px;
}
.logo-icon {
  width: 34px; height: 34px;
  border-radius: 8px;
  background: linear-gradient(135deg, #00d4ff22, #00d4ff44);
  border: 1px solid var(--accent);
  display: flex; align-items: center; justify-content: center;
  font-size: 16px;
}
.logo-text {
  font-family: var(--mono);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 2px;
  color: var(--accent);
}
.logo-sub {
  font-size: 10px;
  color: var(--muted);
  letter-spacing: 1px;
  margin-top: 1px;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}
.header-stat {
  text-align: right;
}
.header-stat-val {
  font-family: var(--mono);
  font-size: 15px;
  font-weight: 700;
}
.header-stat-lbl {
  font-size: 9px;
  color: var(--muted);
  letter-spacing: 1px;
  text-transform: uppercase;
}
.status-pill {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 5px 12px;
  border-radius: 20px;
  background: var(--bg3);
  border: 1px solid var(--border2);
  font-size: 11px;
  color: var(--muted);
  font-family: var(--mono);
}
.status-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--muted);
  transition: all 0.3s;
}
.status-dot.live {
  background: var(--green);
  box-shadow: 0 0 8px var(--green);
  animation: pulse 1.5s infinite;
}
.status-dot.stopped { background: var(--red); box-shadow: 0 0 6px var(--red); }
@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }

/* ── MAIN LAYOUT ── */
.layout {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 200px 1fr 280px;
  grid-template-rows: auto 1fr;
  gap: 12px;
  padding: 12px;
  min-height: calc(100vh - 58px);
  width: 100%;
  overflow-x: hidden;
}
/* =========================
   RESPONSIVE MOBILE FIX
========================= */

@media (max-width: 1200px) {

  .layout {
    grid-template-columns: 1fr;
    height: auto;
  }

  .left-panel,
  .center-panel,
  .right-panel {
    grid-row: auto;
  }

  .header {
    flex-direction: column;
    height: auto;
    gap: 10px;
    padding: 12px;
  }

  .header-right {
    width: 100%;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
  }

  .chart-wrap {
    height: 400px;
  }

  .table-wrap {
    max-height: 300px;
  }

}

@media (max-width: 768px) {

  body {
    overflow-x: hidden;
  }

  .layout {
    padding: 8px;
    gap: 8px;
  }

  .card {
    padding: 12px;
  }

  .header {
    padding: 10px;
  }

  .logo-text {
    font-size: 11px;
  }

  .logo-sub {
    font-size: 8px;
  }

  .header-stat-val {
    font-size: 12px;
  }

  .live-grid,
  .axes-grid,
  .shockley-row,
  .id-params {
    grid-template-columns: 1fr;
  }

  .chart-wrap {
    height: 300px;
  }

  canvas {
    max-width: 100% !important;
  }

  .btn {
    font-size: 10px;
    padding: 10px;
  }

  table {
    font-size: 10px;
  }

  tbody td,
  thead th {
    padding: 4px;
  }

}

/* ── CARDS ── */
.card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  overflow: hidden;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}
.card-icon {
  width: 26px; height: 26px;
  border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px;
  flex-shrink: 0;
}
.card-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--muted);
}

/* ── LEFT PANEL ── */
.left-panel {
  grid-row: 1 / 3;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* ── CENTER PANEL ── */
.center-panel {
  grid-row: 1 / 3;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* ── RIGHT PANEL ── */
.right-panel {
  grid-row: 1 / 3;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}
.right-panel::-webkit-scrollbar { width: 3px; }
.right-panel::-webkit-scrollbar-track { background: transparent; }
.right-panel::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }

/* ── FORM ELEMENTS ── */
.field { margin-bottom: 10px; }
.field label {
  display: block;
  font-size: 10px;
  font-weight: 500;
  color: var(--muted);
  letter-spacing: 0.8px;
  text-transform: uppercase;
  margin-bottom: 4px;
}
input[type="number"], select {
  width: 100%;
  padding: 7px 10px;
  background: var(--bg);
  border: 1px solid var(--border2);
  border-radius: 6px;
  color: var(--text);
  font-family: var(--mono);
  font-size: 12px;
  transition: border 0.2s;
  -moz-appearance: textfield;
}
input[type="number"]::-webkit-inner-spin-button { -webkit-appearance: none; }
input[type="number"]:focus, select:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(0,212,255,0.08);
}
select option { background: var(--bg2); }

/* ── BUTTONS ── */
.btn {
  width: 100%;
  padding: 9px 12px;
  border: none;
  border-radius: 7px;
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.btn:hover { transform: translateY(-1px); }
.btn:active { transform: translateY(0); }
.btn + .btn { margin-top: 6px; }

.btn-primary {
  background: linear-gradient(135deg, #00d4ff22, #00d4ff44);
  color: var(--accent);
  border: 1px solid var(--accent);
}
.btn-primary:hover { background: linear-gradient(135deg, #00d4ff33, #00d4ff55); box-shadow: 0 0 16px rgba(0,212,255,0.2); }

.btn-danger {
  background: linear-gradient(135deg, #ff456022, #ff456033);
  color: var(--red);
  border: 1px solid #ff456066;
}
.btn-ghost {
  background: var(--bg3);
  color: var(--muted);
  border: 1px solid var(--border);
}
.btn-ghost:hover { color: var(--text); border-color: var(--border2); }

.btn-identify {
  background: linear-gradient(135deg, #ff950022, #ff950044);
  color: var(--orange);
  border: 1px solid #ff950066;
  padding: 11px 12px;
  font-size: 12px;
}
.btn-identify:hover { background: linear-gradient(135deg, #ff950033, #ff950055); box-shadow: 0 0 16px rgba(255,149,0,0.2); }

.btn-export {
  background: linear-gradient(135deg, #00e5a022, #00e5a033);
  color: var(--green);
  border: 1px solid #00e5a066;
}
.btn-export:hover { box-shadow: 0 0 12px rgba(0,229,160,0.15); }

.btn-pdf {
  background: linear-gradient(135deg, #9c27b022, #9c27b033);
  color: #ce93d8;
  border: 1px solid #9c27b066;
}

/* ── LIVE VALUES ── */
.live-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.live-item {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px;
  text-align: center;
}
.live-label {
  font-size: 9px;
  color: var(--muted);
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-bottom: 4px;
}
.live-val {
  font-family: var(--mono);
  font-size: 18px;
  font-weight: 700;
  line-height: 1;
}
.live-unit {
  font-size: 10px;
  color: var(--muted);
  margin-top: 2px;
}

/* ── CHART ── */
.chart-wrap {
  position: relative;
  flex: 1;
}
canvas { width: 100% !important; }

/* ── TABLE ── */
.table-wrap {
  flex: 1;
  overflow-y: auto;
  max-height: 200px;
}
.table-wrap::-webkit-scrollbar { width: 3px; }
.table-wrap::-webkit-scrollbar-track { background: transparent; }
.table-wrap::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }

table { width: 100%; border-collapse: collapse; font-size: 11px; }
thead th {
  background: var(--bg);
  padding: 6px 8px;
  color: var(--muted);
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  position: sticky;
  top: 0;
  text-align: center;
  border-bottom: 1px solid var(--border);
}
tbody td {
  padding: 5px 8px;
  text-align: center;
  border-bottom: 1px solid var(--border);
  font-family: var(--mono);
  font-size: 11px;
  color: #8aafc8;
  transition: background 0.1s;
}
tbody tr:hover td { background: var(--bg3); color: var(--text); }
tbody tr:last-child td { border-bottom: none; }

/* ── AXES PANEL ── */
.axes-panel {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  margin-top: 8px;
}
.axes-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.axes-grid .field { margin-bottom: 0; }
.axes-grid label { font-size: 9px; }
.axes-grid input { padding: 5px 8px; font-size: 11px; }
.axes-hint { margin-top: 6px; text-align: center; font-size: 9px; color: var(--muted); }

/* ── IDENTIFICATION RESULT ── */
#id-result {
  display: none;
  animation: fadeUp 0.4s ease;
}
@keyframes fadeUp { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }

.id-card {
  background: var(--bg);
  border-radius: 8px;
  padding: 12px;
  border: 1px solid var(--border2);
  transition: border-color 0.3s;
}
.id-type {
  font-family: var(--mono);
  font-size: 14px;
  font-weight: 700;
  line-height: 1.2;
}
.id-model {
  font-size: 11px;
  color: var(--muted);
  margin-top: 2px;
}
.id-desc {
  font-size: 10px;
  color: #6a8aaa;
  margin-top: 6px;
  line-height: 1.5;
  padding-top: 8px;
  border-top: 1px solid var(--border);
}
.id-params {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  margin-top: 8px;
}
.id-param {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 7px 5px;
  text-align: center;
}
.id-param-name {
  font-size: 8px;
  color: var(--muted);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.id-param-val {
  font-family: var(--mono);
  font-size: 13px;
  font-weight: 700;
  margin-top: 3px;
  color: var(--green);
}

/* CONFIDENCE */
.confidence-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
  gap: 8px;
}
.conf-label { font-size: 9px; color: var(--muted); }
.conf-bar-wrap { flex: 1; height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; }
.conf-bar-fill { height: 100%; border-radius: 2px; transition: width 0.8s ease, background 0.5s; }
.conf-pct { font-family: var(--mono); font-size: 11px; font-weight: 700; }

/* APPS */
.id-apps {
  margin-top: 8px;
  padding: 7px 10px;
  background: var(--bg2);
  border-radius: 6px;
  border-left: 2px solid var(--orange);
}
.id-apps-label { font-size: 9px; color: var(--orange); text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
.id-apps-text { font-size: 10px; color: #8aafc8; margin-top: 3px; line-height: 1.4; }

/* CANDIDATES */
.candidates { margin-top: 8px; }
.cand-title { font-size: 9px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px; }
.cand-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  border-bottom: 1px solid var(--border);
  font-size: 10px;
}
.cand-item:last-child { border-bottom: none; }
.cand-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.cand-name { flex: 1; color: #6a8aaa; }
.cand-score { font-family: var(--mono); font-size: 10px; color: var(--muted); }

/* ── SHOCKLEY ── */
.shockley-row { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.shockley-row .field { margin-bottom: 0; }

/* ── SEPARATOR ── */
.sep {
  height: 1px;
  background: var(--border);
  margin: 10px 0;
}

/* ── SCROLLBAR RESET ── */
.right-panel { scrollbar-width: thin; scrollbar-color: var(--border2) transparent; }
</style>
</head>
<body>

<!-- HEADER -->
<header class="header">
  <div class="header-logo">
    <div class="logo-icon">⚡</div>
    <div>
      <div class="logo-text">SMART DIODE</div>
      <div class="logo-sub">ESP32 · MCP4725 · DASHBOARD</div>
    </div>
  </div>
  <div class="header-right">
    <div class="header-stat">
      <div class="header-stat-val" id="hdr-v" style="color:var(--accent)">0.000<span style="font-size:10px;color:var(--muted)"> V</span></div>
      <div class="header-stat-lbl">Tension</div>
    </div>
    <div class="header-stat">
      <div class="header-stat-val" id="hdr-i" style="color:var(--green)">0.000<span style="font-size:10px;color:var(--muted)"> mA</span></div>
      <div class="header-stat-lbl">Courant</div>
    </div>
    <div class="header-stat">
      <div class="header-stat-val" id="hdr-pts" style="color:var(--muted)">0<span style="font-size:10px;color:var(--muted)"> pts</span></div>
      <div class="header-stat-lbl">Points</div>
    </div>
    <div class="status-pill">
      <div class="status-dot" id="status-dot"></div>
      <span id="status-text">IDLE</span>
    </div>
  </div>
</header>

<!-- MAIN LAYOUT -->
<div class="layout">

  <!-- ── LEFT ── -->
  <div class="left-panel">

    <!-- CONTROL -->
    <div class="card">
      <div class="card-header">
        <div class="card-icon" style="background:#00d4ff11;border:1px solid #00d4ff44;">🎛</div>
        <div class="card-title">Contrôle</div>
      </div>
      <div class="field">
        <label>Composant</label>
        <select><option>Diode</option></select>
      </div>
      <div class="field">
        <label>V max (V)</label>
        <input type="number" value="3.3" id="vmax_ctrl" step="0.1">
      </div>
      <div class="field">
        <label>Pas (V)</label>
        <input type="number" value="0.02" step="0.01">
      </div>
      <button class="btn btn-primary" onclick="startSweep()">▶ START SWEEP</button>
      <button class="btn btn-danger"  onclick="stopSweep()">■ STOP</button>
      <button class="btn btn-ghost"   onclick="resetData()">↺ RESET</button>
    </div>

    <!-- LIVE VALUES -->
    <div class="card">
      <div class="card-header">
        <div class="card-icon" style="background:#00e5a011;border:1px solid #00e5a044;">⚡</div>
        <div class="card-title">Mesure</div>
      </div>
      <div class="live-grid">
        <div class="live-item">
          <div class="live-label">Tension</div>
          <div class="live-val" id="voltage" style="color:var(--accent)">0.000</div>
          <div class="live-unit">Volts</div>
        </div>
        <div class="live-item">
          <div class="live-label">Courant</div>
          <div class="live-val" id="current" style="color:var(--green)">0.000</div>
          <div class="live-unit">mA</div>
        </div>
      </div>
    </div>

    <!-- DATA TABLE -->
    <div class="card" style="flex:1;display:flex;flex-direction:column;min-height:0;">
      <div class="card-header">
        <div class="card-icon" style="background:#9c27b011;border:1px solid #9c27b044;">📊</div>
        <div class="card-title">Données</div>
      </div>
      <div class="table-wrap" style="flex:1;">
        <table>
          <thead><tr><th>#</th><th>U (V)</th><th>I (mA)</th></tr></thead>
          <tbody id="table-body"></tbody>
        </table>
      </div>
    </div>

  </div>

  <!-- ── CENTER ── -->
  <div class="center-panel">

    <!-- CHART -->
    <div class="card" style="flex:1;display:flex;flex-direction:column;">
      <div class="card-header">
        <div class="card-icon" style="background:#00d4ff11;border:1px solid #00d4ff44;">📈</div>
        <div class="card-title">Courbe I = f(U)</div>
        <div style="margin-left:auto;font-family:var(--mono);font-size:9px;color:var(--muted);">
          Scroll = zoom &nbsp;·&nbsp; Drag = pan
        </div>
      </div>
      <div class="chart-wrap" style="flex:1;position:relative;">
        <canvas id="chart"></canvas>
      </div>
      <div class="axes-panel">
        <div class="axes-grid">
          <div class="field"><label>X min (V)</label><input type="number" id="xmin" value="0" step="0.1" oninput="updateAxes()"></div>
          <div class="field"><label>X max (V)</label><input type="number" id="xmax" value="3.3" step="0.1" oninput="updateAxes()"></div>
          <div class="field"><label>Y min (mA)</label><input type="number" id="ymin" value="0" step="0.05" oninput="updateAxes()"></div>
          <div class="field"><label>Y max (mA)</label><input type="number" id="ymax" value="2" step="0.1" oninput="updateAxes()"></div>
        </div>
        <div style="display:flex;gap:6px;margin-top:8px;">
          <button class="btn btn-ghost" style="font-size:10px;padding:5px;" onclick="chart.resetZoom()">🔍 Reset Zoom</button>
          <button class="btn btn-ghost" style="font-size:10px;padding:5px;" onclick="autoScale()">⊡ Auto Scale</button>
        </div>
      </div>
    </div>

  </div>

  <!-- ── RIGHT ── -->
  <div class="right-panel">

    <!-- IDENTIFY -->
    <div class="card">
      <div class="card-header">
        <div class="card-icon" style="background:#ff950011;border:1px solid #ff950044;">🔬</div>
        <div class="card-title">Identification</div>
      </div>
      <button class="btn btn-identify" id="btn-identify" onclick="identifyDiode()">
        🔍 &nbsp;IDENTIFIER LA DIODE
      </button>

      <div id="id-result" style="margin-top:10px;">
        <div class="id-card" id="id-card">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;">
            <div>
              <div class="id-type" id="id-type">—</div>
              <div class="id-model" id="id-model">—</div>
            </div>
            <div style="width:10px;height:10px;border-radius:50%;flex-shrink:0;margin-top:4px;" id="id-dot"></div>
          </div>
          <div class="id-desc" id="id-desc">—</div>
          <div class="id-params">
            <div class="id-param">
              <div class="id-param-name">Vf</div>
              <div class="id-param-val" id="id-vf">—</div>
            </div>
            <div class="id-param">
              <div class="id-param-name">n</div>
              <div class="id-param-val" id="id-n">—</div>
            </div>
            <div class="id-param">
              <div class="id-param-name">Is</div>
              <div class="id-param-val" id="id-is" style="font-size:10px;">—</div>
            </div>
          </div>
          <div class="confidence-row">
            <div class="conf-label">Confiance</div>
            <div class="conf-bar-wrap"><div class="conf-bar-fill" id="conf-fill" style="width:0%"></div></div>
            <div class="conf-pct" id="conf-pct">—</div>
          </div>
          <div class="id-apps">
            <div class="id-apps-label">Applications</div>
            <div class="id-apps-text" id="id-apps">—</div>
          </div>
          <div class="candidates" id="candidates"></div>
        </div>
      </div>
    </div>

    <!-- EXPORT -->
    <div class="card">
      <div class="card-header">
        <div class="card-icon" style="background:#00e5a011;border:1px solid #00e5a044;">💾</div>
        <div class="card-title">Export</div>
      </div>
      <button class="btn btn-export" onclick="exportCSV()">📥 &nbsp;EXPORT CSV</button>
      <button class="btn btn-pdf" onclick="window.location.href='/export_pdf'">📄 &nbsp;EXPORT PDF</button>
    </div>

    <!-- SHOCKLEY MANUAL -->
    <div class="card">
      <div class="card-header">
        <div class="card-icon" style="background:#ff456011;border:1px solid #ff456044;">📉</div>
        <div class="card-title">Shockley Manuel</div>
      </div>
      <div class="shockley-row">
        <div class="field"><label>Is (nA)</label>
          <input type="number" id="Is_val" value="10" step="1" oninput="updateShockley()">
        </div>
        <div class="field"><label>n</label>
          <input type="number" id="n_val" value="1.8" step="0.05" oninput="updateShockley()">
        </div>
      </div>
      <div class="field" style="margin-top:6px;"><label>Vt (mV)</label>
        <input type="number" id="Vt_val" value="25.85" step="0.1" oninput="updateShockley()">
      </div>
      <div style="margin-top:6px;padding:6px 8px;background:var(--bg);border-radius:6px;border:1px solid var(--border);font-family:var(--mono);font-size:10px;color:var(--muted);text-align:center;" id="shockley-info">
        I = Is·(e^(V/n·Vt) − 1)
      </div>
    </div>

  </div>

</div>

<script>
// ========================
// CHART INIT
// ========================
let chart;

function initChart() {
  const ctx = document.getElementById('chart').getContext('2d');
  chart = new Chart(ctx, {
    type: 'line',
    data: {
      datasets: [
        {
          label: 'Mesure réelle',
          data: [],
          borderColor: '#00d4ff',
          backgroundColor: 'rgba(0,212,255,0.06)',
          pointRadius: 2.5,
          pointHoverRadius: 6,
          pointBackgroundColor: '#00d4ff',
          borderWidth: 2,
          tension: 0.3,
          fill: true,
          order: 1
        },
        {
          label: 'Shockley manuel',
          data: [],
          borderColor: '#ff4560',
          backgroundColor: 'transparent',
          pointRadius: 0,
          borderWidth: 1.5,
          showLine: true,
          segment: { borderDash: [5,3] },
          tension: 0.4,
          order: 3
        },
        {
          label: 'Shockley identifiée',
          data: [],
          borderColor: '#ff9500',
          backgroundColor: 'transparent',
          pointRadius: 0,
          borderWidth: 2,
          showLine: true,
          segment: { borderDash: [3,3] },
          tension: 0.4,
          hidden: true,
          order: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      parsing: false,
      interaction: { mode: 'nearest', intersect: false, axis: 'x' },
      plugins: {
        legend: {
          labels: {
            color: '#5a7090',
            font: { size: 10, family: "'Space Mono', monospace" },
            boxWidth: 20,
            padding: 12
          }
        },
        tooltip: {
          backgroundColor: '#0b1220',
          borderColor: '#1e2d45',
          borderWidth: 1,
          titleColor: '#00d4ff',
          bodyColor: '#e2eaf6',
          padding: 10,
          titleFont: { family: "'Space Mono', monospace", size: 11 },
          bodyFont: { family: "'Space Mono', monospace", size: 11 },
          callbacks: {
            title: items => 'U = ' + Number(items[0].parsed.x).toFixed(3) + ' V',
            label: item => item.dataset.label + ': ' + Number(item.parsed.y).toFixed(4) + ' mA'
          }
        },
        zoom: {
          zoom: { wheel: { enabled: true, speed: 0.08 }, pinch: { enabled: true }, mode: 'xy' },
          pan:  { enabled: true, mode: 'xy' }
        }
      },
      scales: {
        x: {
          type: 'linear', min: 0, max: 3.3,
          title: { display: true, text: 'Tension U (V)', color: '#5a7090', font: { size: 10 } },
          ticks: { color: '#3a5070', font: { size: 9, family: "'Space Mono', monospace" }, maxTicksLimit: 10 },
          grid: { color: '#0f1e30' }
        },
        y: {
          min: 0, max: 2,
          title: { display: true, text: 'Courant I (mA)', color: '#5a7090', font: { size: 10 } },
          ticks: { color: '#3a5070', font: { size: 9, family: "'Space Mono', monospace" } },
          grid: { color: '#0f1e30' }
        }
      }
    }
  });
}

// ========================
// AXES
// ========================
function updateAxes() {
  const xmin = parseFloat(document.getElementById('xmin').value) || 0;
  const xmax = parseFloat(document.getElementById('xmax').value) || 3.3;
  const ymin = parseFloat(document.getElementById('ymin').value) || 0;
  const ymax = parseFloat(document.getElementById('ymax').value) || 2;
  if (xmin >= xmax || ymin >= ymax) return;
  chart.options.scales.x.min = xmin;
  chart.options.scales.x.max = xmax;
  chart.options.scales.y.min = ymin;
  chart.options.scales.y.max = ymax;
  chart.update();
  updateShockley();
}

function autoScale() {
  const data = chart.data.datasets[0].data;
  if (!data.length) return;
  const xs = data.map(p => p.x);
  const ys = data.map(p => p.y);
  const xmax = Math.max(...xs) * 1.05;
  const ymax = Math.max(...ys) * 1.15;
  document.getElementById('xmin').value = 0;
  document.getElementById('xmax').value = xmax.toFixed(2);
  document.getElementById('ymin').value = 0;
  document.getElementById('ymax').value = ymax.toFixed(2);
  updateAxes();
}

// ========================
// SHOCKLEY CURVE
// ========================
function shockleyPoints(Is_nA, n, Vt_mV, xmax) {
  const Is = Is_nA * 1e-9;
  const Vt = Vt_mV * 1e-3;
  const pts = [];
  for (let i = 0; i <= 400; i++) {
    const V = (xmax / 400) * i;
    const I = Is * (Math.exp(V / (n * Vt)) - 1) * 1000;
    if (I >= 0 && I < 5000) pts.push({ x: V, y: I });
  }
  return pts;
}

function updateShockley() {
  const Is = parseFloat(document.getElementById('Is_val').value) || 10;
  const n  = parseFloat(document.getElementById('n_val').value)  || 1.8;
  const Vt = parseFloat(document.getElementById('Vt_val').value) || 25.85;
  const xmax = parseFloat(document.getElementById('xmax').value) || 3.3;
  chart.data.datasets[1].data = shockleyPoints(Is, n, Vt, xmax);
  chart.update();
  document.getElementById('shockley-info').textContent =
    `Is=${Is.toFixed(2)} nA  ·  n=${n}  ·  Vt=${Vt} mV`;
}

// ========================
// IDENTIFY
// ========================
function identifyDiode() {
  const btn = document.getElementById('btn-identify');
  btn.textContent = '⏳  Analyse...';
  btn.disabled = true;

  fetch('/identify')
    .then(r => r.json())
    .then(res => {
      btn.innerHTML = '🔍 &nbsp;IDENTIFIER LA DIODE';
      btn.disabled = false;

      if (res.error) {
        alert(res.error === 'not enough data'
          ? '⚠️ Pas assez de données — lance un sweep complet d\'abord.'
          : '⚠️ ' + res.error);
        return;
      }

      // Show result panel
      const panel = document.getElementById('id-result');
      panel.style.display = 'block';

      const card = document.getElementById('id-card');
      card.style.borderColor = res.color;

      document.getElementById('id-dot').style.background = res.color;
      document.getElementById('id-dot').style.boxShadow = `0 0 8px ${res.color}`;
      document.getElementById('id-type').textContent  = res.type;
      document.getElementById('id-type').style.color  = res.color;
      document.getElementById('id-model').textContent = res.model || '—';
      document.getElementById('id-desc').textContent  = res.description;
      document.getElementById('id-vf').textContent    = res.vf + ' V';
      document.getElementById('id-n').textContent     = res.n;
      document.getElementById('id-is').textContent    = res.Is_display;
      document.getElementById('id-apps').textContent  = res.applications;
      document.getElementById('conf-pct').textContent = res.confidence + '%';
      document.getElementById('conf-pct').style.color = res.confidence > 70 ? 'var(--green)' : res.confidence > 40 ? 'var(--orange)' : 'var(--red)';

      const fill = document.getElementById('conf-fill');
      fill.style.width = res.confidence + '%';
      fill.style.background = res.confidence > 70 ? 'var(--green)' : res.confidence > 40 ? 'var(--orange)' : 'var(--red)';

      // Candidates
      if (res.scores && res.scores.length > 1) {
        let html = '<div class="cand-title">Autres candidats</div>';
        res.scores.slice(1).forEach(s => {
          html += `<div class="cand-item">
            <div class="cand-dot" style="background:${s.diode.color}"></div>
            <div class="cand-name">${s.diode.name}</div>
            <div class="cand-score">${Math.max(0, s.score)} pts</div>
          </div>`;
        });
        document.getElementById('candidates').innerHTML = html;
      }

      // Update Shockley inputs + redraw
      document.getElementById('Is_val').value = res.Is_nA.toFixed(3);
      document.getElementById('n_val').value  = res.n;
      updateShockley();

      // Draw identified Shockley
      const xmax = parseFloat(document.getElementById('xmax').value) || 3.3;
      chart.data.datasets[2].data         = shockleyPoints(res.Is_nA, res.n, 25.85, xmax);
      chart.data.datasets[2].borderColor  = res.color;
      chart.data.datasets[2].label        = 'Shockley — ' + res.type;
      chart.data.datasets[2].hidden       = false;
      chart.update();
    })
    .catch(() => {
      btn.innerHTML = '🔍 &nbsp;IDENTIFIER LA DIODE';
      btn.disabled = false;
      alert('Erreur de connexion.');
    });
}

// ========================
// LIVE DASHBOARD UPDATE
// ========================
function updateDashboard() {
  fetch('/get_data')
    .then(r => r.json())
    .then(data => {
      // Chart
      const pts = data.map(d => ({ x: Number(d.U), y: Number(d.I) }));
      chart.data.datasets[0].data = pts;
      chart.update('none');

      // Table (last 100 rows)
      const tbody = document.getElementById('table-body');
      const slice = data.slice(-100);
      tbody.innerHTML = slice.map((d, i) =>
        `<tr><td>${data.length - slice.length + i + 1}</td><td>${Number(d.U).toFixed(3)}</td><td>${Number(d.I).toFixed(3)}</td></tr>`
      ).join('');

      // Header live values
      if (data.length > 0) {
        const last = data[data.length - 1];
        const U = Number(last.U).toFixed(3);
        const I = Number(last.I).toFixed(3);
        document.getElementById('voltage').textContent = U;
        document.getElementById('current').textContent = I;
        document.getElementById('hdr-v').innerHTML = U + '<span style="font-size:10px;color:var(--muted)"> V</span>';
        document.getElementById('hdr-i').innerHTML = I + '<span style="font-size:10px;color:var(--muted)"> mA</span>';
        document.getElementById('hdr-pts').innerHTML = data.length + '<span style="font-size:10px;color:var(--muted)"> pts</span>';
      }
    });
}

// ========================
// CONTROLS
// ========================
function setStatus(mode) {
  const dot  = document.getElementById('status-dot');
  const text = document.getElementById('status-text');
  const modes = {
    live:    ['live',    'LIVE'],
    stopped: ['stopped', 'STOP'],
    idle:    ['',        'IDLE'],
    reset:   ['stopped', 'RESET']
  };
  const [cls, label] = modes[mode] || ['', 'IDLE'];
  dot.className  = 'status-dot ' + cls;
  text.textContent = label;
}

function startSweep() { fetch('/start'); setStatus('live'); }
function stopSweep()  { fetch('/stop');  setStatus('stopped'); }

function resetData() {
  fetch('/stop');
  fetch('/reset');
  chart.data.datasets[0].data = [];
  chart.data.datasets[2].data = [];
  chart.data.datasets[2].hidden = true;
  document.getElementById('table-body').innerHTML = '';
  document.getElementById('voltage').textContent = '0.000';
  document.getElementById('current').textContent = '0.000';
  document.getElementById('hdr-v').innerHTML = '0.000<span style="font-size:10px;color:var(--muted)"> V</span>';
  document.getElementById('hdr-i').innerHTML = '0.000<span style="font-size:10px;color:var(--muted)"> mA</span>';
  document.getElementById('hdr-pts').innerHTML = '0<span style="font-size:10px;color:var(--muted)"> pts</span>';
  document.getElementById('id-result').style.display = 'none';
  setStatus('reset');
  chart.update();
}

function exportCSV() { window.location.href = '/export_csv'; }

// ========================
// BOOT
// ========================
window.onload = function() {
  initChart();
  updateShockley();
  setInterval(updateDashboard, 1000);
};
</script>
</body>
</html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)