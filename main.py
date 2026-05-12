from flask import Flask, request, jsonify

app = Flask(__name__)

# ===============================
# DATA STORAGE
# ===============================
data_store = []
running = True
last_voltage = 0
last_current = 0


# ===============================
# MAIN PAGE
# ===============================
@app.route("/")
def home():
    return """
<!DOCTYPE html>
<html lang="fr">

<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Smart Diode Dashboard</title>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/hammerjs@2.0.8/hammer.min.js"></script>

<style>

* { box-sizing: border-box; }

body {
    margin: 0;
    padding: 0;
    background: #111318;
    font-family: Arial;
    color: white;
}

.header {
    width: 100%;
    background: #181c24;
    padding: 18px;
    text-align: center;
    font-size: 28px;
    font-weight: bold;
    color: #3fa9ff;
    border-bottom: 2px solid #2d3442;
}

.container {
    display: grid;
    grid-template-columns: 240px 1fr 320px 220px;
    gap: 15px;
    padding: 15px;
}

.card {
    background: #1b1f27;
    border: 1px solid #2e3545;
    border-radius: 12px;
    padding: 15px;
    box-shadow: 0 0 10px rgba(0,0,0,0.3);
}

.title {
    text-align: center;
    color: #3fa9ff;
    font-size: 20px;
    margin-bottom: 15px;
    font-weight: bold;
}

label {
    display: block;
    margin-top: 12px;
    margin-bottom: 6px;
    font-size: 14px;
}

input[type="number"], select {
    width: 100%;
    padding: 10px;
    border: none;
    border-radius: 8px;
    background: #2b3140;
    color: white;
    font-size: 15px;
}

button {
    width: 100%;
    padding: 14px;
    margin-top: 14px;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: bold;
    cursor: pointer;
    transition: 0.2s;
}

button:hover { transform: scale(1.03); }

.start  { background: #22c55e; color: white; }
.stop   { background: #ef4444; color: white; }
.reset  { background: #444;    color: white; }
.csv    { background: #16a34a; color: white; }
.pdf    { background: #7c3aed; color: white; }
.orange { background: #ea580c; color: white; }

.live-value { text-align: center; margin-top: 25px; }
.live-value h2 { margin: 0; font-size: 18px; color: #ddd; }
.live-value p  { margin-top: 10px; font-size: 34px; font-weight: bold; }

.blue  { color: #3fa9ff; }
.green { color: #22c55e; }

.table-container { max-height: 380px; overflow-y: auto; }

table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { background: #242b38; padding: 10px; position: sticky; top: 0; }
td { text-align: center; padding: 8px; border-bottom: 1px solid #2f3748; }
tr:nth-child(even) { background: #202632; }

canvas { width: 100% !important; height: 460px !important; }

/* ---- AXIS CONTROLS ---- */
.axis-controls {
    margin-top: 12px;
    background: #151921;
    border-radius: 10px;
    padding: 12px 14px;
    border: 1px solid #2a3040;
}

.axis-controls .ax-title {
    color: #3fa9ff;
    font-size: 13px;
    font-weight: bold;
    margin-bottom: 12px;
    text-align: center;
    letter-spacing: 1px;
}

.ax-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px 14px;
}

.ax-field label {
    font-size: 12px;
    color: #aaa;
    margin-bottom: 4px;
    margin-top: 0;
}

.ax-field input[type="number"] {
    width: 100%;
    padding: 7px 10px;
    border-radius: 6px;
    background: #2b3140;
    color: #3fa9ff;
    border: 1px solid #3fa9ff44;
    font-size: 14px;
    font-weight: bold;
}

.ax-field input[type="number"]:focus {
    outline: none;
    border-color: #3fa9ff;
}

.zoom-hint {
    margin-top: 10px;
    text-align: center;
    font-size: 12px;
    color: #666;
}

.zoom-reset-btn {
    margin-top: 8px;
    padding: 7px;
    font-size: 12px;
    background: #1e3a5f;
    color: #3fa9ff;
    border: 1px solid #3fa9ff44;
    border-radius: 6px;
    cursor: pointer;
    width: 100%;
}

.zoom-reset-btn:hover { background: #254a75; }

@media(max-width:1400px) {
    .container { grid-template-columns: 1fr; }
}

</style>
</head>

<body>

<div class="header">⚡ SMART DIODE DASHBOARD</div>

<div class="container">

    <!-- CONTROL -->
    <div class="card">
        <div class="title">CONTRÔLE</div>

        <label>Choix du circuit</label>
        <select>
            <option>Diode</option>
        </select>

        <label>Tension max (V)</label>
        <input type="number" value="3.3">

        <label>Pas (V)</label>
        <input type="number" value="0.02">

        <button class="start" onclick="startSweep()">START SWEEP</button>
        <button class="stop"  onclick="stopSweep()">STOP</button>
        <button class="reset" onclick="resetData()">RESET</button>
    </div>

    <!-- GRAPH -->
    <div class="card">
        <div class="title">COURBE I = f(U)</div>

        <canvas id="chart"></canvas>

        <!-- AXIS CONTROLS -->
        <div class="axis-controls">
            <div class="ax-title">⚙ AXES</div>
            <div class="ax-grid">
                <div class="ax-field">
                    <label>X min (V)</label>
                    <input type="number" id="xmin" value="0" step="0.1" oninput="updateAxes()">
                </div>
                <div class="ax-field">
                    <label>X max (V)</label>
                    <input type="number" id="xmax" value="3.3" step="0.1" oninput="updateAxes()">
                </div>
                <div class="ax-field">
                    <label>Y min (mA)</label>
                    <input type="number" id="ymin" value="0" step="0.05" oninput="updateAxes()">
                </div>
                <div class="ax-field">
                    <label>Y max (mA)</label>
                    <input type="number" id="ymax" value="2" step="0.1" oninput="updateAxes()">
                </div>
            </div>
            <button class="zoom-reset-btn" onclick="resetZoom()">🔍 Reset Zoom</button>
            <div class="zoom-hint">🖱 Scroll sur le graphe pour zoomer</div>
        </div>
    </div>

    <!-- VALUES + TABLE -->
    <div>
        <div class="card">
            <div class="title">VALEURS INSTANTANÉES</div>
            <div class="live-value">
                <h2>Tension U (V)</h2>
                <p class="blue" id="voltage">0.00 V</p>
                <h2>Courant I (mA)</h2>
                <p class="green" id="current">0.00 mA</p>
            </div>
        </div>

        <div class="card" style="margin-top:15px;">
            <div class="title">DONNÉES ACQUISES</div>
            <div class="table-container">
                <table id="table">
                    <tr><th>#</th><th>U (V)</th><th>I (mA)</th></tr>
                </table>
            </div>
        </div>
    </div>

    <!-- ACTIONS -->
    <div class="card">
        <div class="title">ACTIONS</div>
        <button class="csv"    onclick="exportCSV()">EXPORT CSV</button>
        <button class="pdf"    onclick="window.location.href='/export_pdf'">EXPORT PDF</button>
        <button class="orange" onclick="resetData()">RESET DONNÉES</button>

        <!-- SHOCKLEY PANEL -->
        <div style="margin-top:20px; border-top:1px solid #2e3545; padding-top:14px;">
            <div class="title" style="font-size:14px; margin-bottom:10px;">🔴 SHOCKLEY THÉORIQUE</div>

            <div class="ax-field" style="margin-bottom:8px;">
                <label style="font-size:12px; color:#aaa;">Is (nA)</label>
                <input type="number" id="Is_val" value="10" step="1" min="0.1"
                    style="background:#2b3140;color:#ff6b6b;border:1px solid #ff6b6b44;
                           border-radius:6px;padding:6px 10px;font-size:13px;font-weight:bold;width:100%;"
                    oninput="updateShockley()">
            </div>

            <div class="ax-field" style="margin-bottom:8px;">
                <label style="font-size:12px; color:#aaa;">n (facteur d'idéalité)</label>
                <input type="number" id="n_val" value="1.8" step="0.05" min="1" max="2"
                    style="background:#2b3140;color:#ff6b6b;border:1px solid #ff6b6b44;
                           border-radius:6px;padding:6px 10px;font-size:13px;font-weight:bold;width:100%;"
                    oninput="updateShockley()">
            </div>

            <div class="ax-field">
                <label style="font-size:12px; color:#aaa;">Vt (mV) — temp. ambiante</label>
                <input type="number" id="Vt_val" value="25.85" step="0.1"
                    style="background:#2b3140;color:#ff6b6b;border:1px solid #ff6b6b44;
                           border-radius:6px;padding:6px 10px;font-size:13px;font-weight:bold;width:100%;"
                    oninput="updateShockley()">
            </div>

            <div id="shockley-info" style="margin-top:10px; font-size:11px; color:#888; text-align:center;"></div>
        </div>
    </div>

</div>

<script>

let chart;

function initChart() {
    const ctx = document.getElementById('chart').getContext('2d');

    chart = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [
            {
                label: 'Courant I mesuré (mA)',
                data: [],
                borderColor: '#3fa9ff',
                backgroundColor: '#3fa9ff',
                pointRadius: 4,
                pointHoverRadius: 8,
                borderWidth: 3,
                tension: 0.35
            },
            {
                label: 'Shockley théorique (mA)',
                data: [],
                borderColor: '#ff6b6b',
                backgroundColor: 'transparent',
                pointRadius: 0,
                pointHoverRadius: 0,
                borderWidth: 2.5,
                showLine: true,
                segment: { borderDash: [6, 3] },
                tension: 0.4
            }
            ]
        },
        options: {
            responsive: true,
            animation: false,
            parsing: false,
            interaction: {
                mode: 'nearest',
                intersect: false
            },
            plugins: {
                legend: {
                    labels: { color: 'white' }
                },
                tooltip: {
                    backgroundColor: '#1b1f27',
                    borderColor: '#3fa9ff',
                    borderWidth: 1,
                    titleColor: '#3fa9ff',
                    bodyColor: '#ffffff',
                    padding: 10,
                    callbacks: {
                        title: function(items) {
                            return 'U = ' + Number(items[0].parsed.x).toFixed(3) + ' V';
                        },
                        label: function(item) {
                            return 'I = ' + Number(item.parsed.y).toFixed(3) + ' mA';
                        }
                    }
                },
                zoom: {
                    zoom: {
                        wheel: { enabled: true, speed: 0.1 },
                        pinch: { enabled: true },
                        mode: 'xy'
                    },
                    pan: {
                        enabled: true,
                        mode: 'xy'
                    }
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    min: 0,
                    max: 3.3,
                    title: { display: true, text: 'Tension U (V)', color: 'white' },
                    ticks: { color: 'white' },
                    grid:  { color: '#333' }
                },
                y: {
                    min: 0,
                    max: 2,
                    title: { display: true, text: 'Courant I (mA)', color: 'white' },
                    ticks: { color: 'white' },
                    grid:  { color: '#333' }
                }
            }
        }
    });
}

// =========================
// AXIS NUMBER INPUTS
// =========================
function updateAxes() {
    let xmin = parseFloat(document.getElementById('xmin').value) || 0;
    let xmax = parseFloat(document.getElementById('xmax').value) || 3.3;
    let ymin = parseFloat(document.getElementById('ymin').value) || 0;
    let ymax = parseFloat(document.getElementById('ymax').value) || 2;

    if (xmin >= xmax) return;
    if (ymin >= ymax) return;

    chart.options.scales.x.min = xmin;
    chart.options.scales.x.max = xmax;
    chart.options.scales.y.min = ymin;
    chart.options.scales.y.max = ymax;
    chart.update();
}

function resetZoom() {
    chart.resetZoom();
}

// =========================
// SHOCKLEY THÉORIQUE
// =========================
function updateShockley() {
    const Is = parseFloat(document.getElementById('Is_val').value) * 1e-9; // nA → A
    const n  = parseFloat(document.getElementById('n_val').value);
    const Vt = parseFloat(document.getElementById('Vt_val').value) * 1e-3; // mV → V

    const xmax = parseFloat(document.getElementById('xmax').value) || 3.3;
    const pts  = 200;
    const shockleyData = [];

    for (let i = 0; i <= pts; i++) {
        const V = (xmax / pts) * i;
        const I = Is * (Math.exp(V / (n * Vt)) - 1) * 1000; // A → mA
        if (I < 500) shockleyData.push({ x: V, y: I }); // limite à 500mA
    }

    chart.data.datasets[1].data = shockleyData;
    chart.update();

    // info
    const Vf_approx = n * Vt * Math.log(1 / (Is * 1e9) + 1) * 0 + 0.6; // approx
    document.getElementById('shockley-info').innerHTML =
        `Is=${(Is*1e9).toFixed(1)}nA &nbsp;|&nbsp; n=${n} &nbsp;|&nbsp; Vt=${(Vt*1000).toFixed(2)}mV`;
}

// =========================
// UPDATE DATA
// =========================
function updateDashboard() {
    fetch('/get_data')
    .then(r => r.json())
    .then(data => {

        let table = document.getElementById("table");
        table.innerHTML = '<tr><th>#</th><th>U (V)</th><th>I (mA)</th></tr>';
        chart.data.datasets[0].data = [];

        data.forEach((d, index) => {
            table.innerHTML += `<tr>
                <td>${index + 1}</td>
                <td>${Number(d.U).toFixed(2)}</td>
                <td>${Number(d.I).toFixed(2)}</td>
            </tr>`;
            chart.data.datasets[0].data.push({
                x: Number(d.U),
                y: Number(d.I)
            });
        });

        if (data.length > 0) {
            let last = data[data.length - 1];
            document.getElementById("voltage").innerHTML = Number(last.U).toFixed(2) + " V";
            document.getElementById("current").innerHTML = Number(last.I).toFixed(2) + " mA";
        }

        chart.update();
    });
}

// =========================
// BUTTONS
// =========================
function startSweep() { fetch('/start'); }
function stopSweep()  { fetch('/stop'); }
function resetData()  {
    fetch('/stop');
    fetch('/reset');
    chart.data.datasets[0].data = [];
    chart.update();
}
function exportCSV() { window.location.href = '/export_csv'; }

// =========================
// START
// =========================
window.onload = function() {
    initChart();
    updateShockley();
    setInterval(updateDashboard, 1000);
};

</script>

</body>
</html>
"""


# ===============================
# RECEIVE DATA
# ===============================
@app.route("/data", methods=["POST"])
def receive_data():
    global data_store, running, last_voltage, last_current

    if not running:
        return jsonify({"status": "stopped"})

    d = request.json
    U = float(d.get("voltage", 0))
    I = float(d.get("current", 0))

    if U < last_voltage - 0.3:
        data_store = []

    last_voltage = U
    last_current = I
    data_store.append({"U": U, "I": I})

    return jsonify({"status": "ok"})


# ===============================
# GET DATA
# ===============================
@app.route("/get_data")
def get_data():
    return jsonify(data_store)


# ===============================
# START / STOP / RESET
# ===============================
@app.route("/start")
def start():
    global running
    running = True
    return jsonify({"status": "running"})

@app.route("/stop")
def stop():
    global running
    running = False
    return jsonify({"status": "stopped"})

@app.route("/reset")
def reset():
    global data_store
    data_store = []
    return jsonify({"status": "reset"})


# ===============================
# PDF EXPORT
# ===============================
@app.route("/export_pdf")
def export_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    import io, datetime, matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    elements = []

    # ---- STYLES ----
    title_style = ParagraphStyle('t', fontSize=20, textColor=colors.HexColor('#1a3a6b'),
                                  fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=4)
    sub_style   = ParagraphStyle('s', fontSize=10, textColor=colors.HexColor('#3fa9ff'),
                                  fontName='Helvetica', alignment=TA_CENTER, spaceAfter=2)
    date_style  = ParagraphStyle('d', fontSize=9, textColor=colors.grey,
                                  fontName='Helvetica', alignment=TA_CENTER, spaceAfter=12)
    section_style = ParagraphStyle('sec', fontSize=12, textColor=colors.HexColor('#1a3a6b'),
                                    fontName='Helvetica-Bold', spaceAfter=6, spaceBefore=10)
    info_style  = ParagraphStyle('inf', fontSize=10, textColor=colors.HexColor('#222'),
                                  fontName='Helvetica', spaceAfter=4, leftIndent=10)

    now = datetime.datetime.now().strftime("%d/%m/%Y à %H:%M:%S")

    # ---- HEADER ----
    elements.append(Paragraph("⚡ SMART DIODE DASHBOARD", title_style))
    elements.append(Paragraph("Rapport de Mesures Expérimentales", sub_style))
    elements.append(Paragraph(f"Généré le : {now}", date_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#3fa9ff'), spaceAfter=10))

    # ---- INFOS MESURE ----
    elements.append(Paragraph("📋 Informations de mesure", section_style))

    nb_points = len(data_store)
    u_max = max((d['U'] for d in data_store), default=0)
    i_max = max((d['I'] for d in data_store), default=0)
    i_min = min((d['I'] for d in data_store), default=0)

    info_data = [
        ["Composant", "Diode"],
        ["Nombre de points", str(nb_points)],
        ["Tension max mesurée (V)", f"{u_max:.3f} V"],
        ["Courant max mesuré (mA)", f"{i_max:.3f} mA"],
        ["Courant min mesuré (mA)", f"{i_min:.3f} mA"],
    ]

    info_table = Table(info_data, colWidths=[7*cm, 9*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME',  (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME',  (1,0), (1,-1), 'Helvetica'),
        ('FONTSIZE',  (0,0), (-1,-1), 10),
        ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#1a3a6b')),
        ('TEXTCOLOR', (1,0), (1,-1), colors.HexColor('#222')),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.HexColor('#f0f6ff'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#c0cfe0')),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.4*cm))

    # ---- GRAPH ----
    if nb_points > 0:
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#ddd'), spaceAfter=8))
        elements.append(Paragraph("📈 Courbe caractéristique I = f(U)", section_style))

        u_vals = [d['U'] for d in data_store]
        i_vals = [d['I'] for d in data_store]

        fig, ax = plt.subplots(figsize=(7, 3.5))
        ax.plot(u_vals, i_vals, color='#3fa9ff', linewidth=2, marker='o', markersize=3)
        ax.set_xlabel("Tension U (V)", fontsize=10)
        ax.set_ylabel("Courant I (mA)", fontsize=10)
        ax.set_title("Courbe I = f(U) — Diode", fontsize=11, color='#1a3a6b')
        ax.grid(True, color='#e0e0e0', linewidth=0.5)
        ax.set_facecolor('#f8fbff')
        fig.patch.set_facecolor('white')
        plt.tight_layout()

        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        img_buf.seek(0)

        img = Image(img_buf, width=14*cm, height=7*cm)
        elements.append(img)
        elements.append(Spacer(1, 0.4*cm))

    # ---- TABLE ----
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#ddd'), spaceAfter=8))
    elements.append(Paragraph("📊 Tableau des données acquises", section_style))

    table_data = [["#", "Tension U (V)", "Courant I (mA)"]]
    for i, d in enumerate(data_store):
        table_data.append([str(i+1), f"{float(d['U']):.3f}", f"{float(d['I']):.3f}"])

    t = Table(table_data, colWidths=[2*cm, 7*cm, 7*cm], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  colors.HexColor('#1a3a6b')),
        ('TEXTCOLOR',     (0,0), (-1,0),  colors.white),
        ('FONTNAME',      (0,0), (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,0),  11),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING',    (0,0), (-1,0),  8),
        ('BOTTOMPADDING', (0,0), (-1,0),  8),
        ('FONTNAME',      (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE',      (0,1), (-1,-1), 10),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [colors.HexColor('#f0f6ff'), colors.white]),
        ('TEXTCOLOR',     (0,1), (-1,-1), colors.HexColor('#1a1a2e')),
        ('TOPPADDING',    (0,1), (-1,-1), 5),
        ('BOTTOMPADDING', (0,1), (-1,-1), 5),
        ('GRID',          (0,0), (-1,-1), 0.5, colors.HexColor('#c0cfe0')),
        ('BOX',           (0,0), (-1,-1), 1.5, colors.HexColor('#1a3a6b')),
    ]))
    elements.append(t)

    # ---- FOOTER ----
    elements.append(Spacer(1, 0.5*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#ddd'), spaceAfter=4))
    elements.append(Paragraph("Smart Diode Dashboard — ESP32 + MCP4725 — Rapport automatique", 
                               ParagraphStyle('foot', fontSize=8, textColor=colors.grey, alignment=TA_CENTER)))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read(), 200, {
        "Content-Type": "application/pdf",
        "Content-Disposition": "attachment; filename=rapport_diode.pdf"
    }


# ===============================
# CSV EXPORT
# ===============================
@app.route("/export_csv")
def export_csv():
    csv_data = "U(V),I(mA)\n"
    for d in data_store:
        csv_data += f"{d['U']},{d['I']}\n"
    return csv_data, 200, {
        "Content-Type": "text/csv",
        "Content-Disposition": "attachment; filename=mesures.csv"
    }


# ===============================
# RUN
# ===============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)