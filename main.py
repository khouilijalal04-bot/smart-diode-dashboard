from flask import Flask, request, jsonify
import math, io, datetime

app = Flask(__name__)

# ═══════════════════════════════════════════════
#  DATA STORAGE
# ═══════════════════════════════════════════════
data_store      = []
running         = False
identified_diode = None


# ═══════════════════════════════════════════════
#  DIODE DATABASE  —  étendue + précise
# ═══════════════════════════════════════════════
DIODE_DATABASE = [
    # ── Schottky ──────────────────────────────
    {
        "id": "schottky",
        "name": "Schottky",
        "model": "BAT46 / 1N5817 / SS14",
        "color": "#ff9800",
        "description": "Jonction métal-semiconducteur — chute de tension très faible, commutation ultra-rapide",
        "vf_typ": 0.22, "vf_min": 0.08, "vf_max": 0.38,
        "Is_nA": 120.0, "n_typ": 1.05, "n_min": 0.8, "n_max": 1.3,
        "slope_factor": 3.5,   # pente normalisée forte
        "applications": "Redressement HF, protection inverse, détecteurs RF, OR-ing d'alimentations",
        "tech": "metal-semiconductor"
    },
    # ── Germanium ─────────────────────────────
    {
        "id": "germanium",
        "name": "Germanium",
        "model": "1N60 / OA91 / AA112",
        "color": "#9c27b0",
        "description": "Semiconducteur Ge — Vf très bas, courant de fuite élevé, sensible à la température",
        "vf_typ": 0.27, "vf_min": 0.12, "vf_max": 0.45,
        "Is_nA": 600.0, "n_typ": 1.0, "n_min": 0.8, "n_max": 1.2,
        "slope_factor": 3.2,
        "applications": "Détection AM, démodulation, circuits vintage, radio à galène",
        "tech": "germanium"
    },
    # ── Silicium signal ───────────────────────
    {
        "id": "silicon_signal",
        "name": "Silicium signal",
        "model": "1N4148 / 1N914 / BAV99",
        "color": "#2196f3",
        "description": "Diode Si signal rapide — polyvalente, switching ns, très répandue",
        "vf_typ": 0.52, "vf_min": 0.38, "vf_max": 0.62,
        "Is_nA": 8.0, "n_typ": 1.5, "n_min": 1.2, "n_max": 1.8,
        "slope_factor": 2.8,
        "applications": "Switching logique, démodulation, protection ESD, redressement signal",
        "tech": "silicon"
    },
    # ── Silicium redresseur ───────────────────
    {
        "id": "silicon_rect",
        "name": "Silicium redresseur",
        "model": "1N4001–1N4007 / 1N5408",
        "color": "#03a9f4",
        "description": "Diode Si redresseur robuste — courant élevé, standard industriel 50/60 Hz",
        "vf_typ": 0.70, "vf_min": 0.55, "vf_max": 0.85,
        "Is_nA": 12.0, "n_typ": 1.8, "n_min": 1.5, "n_max": 2.1,
        "slope_factor": 2.2,
        "applications": "Redressement 50 Hz, pont de Graetz, alimentation secteur, protection",
        "tech": "silicon"
    },
    # ── Zener ─────────────────────────────────
    {
        "id": "zener",
        "name": "Zener",
        "model": "BZX55 / 1N47xx / BZV55",
        "color": "#ff5722",
        "description": "Diode à avalanche — région directe semblable au Si, mais usage en inverse",
        "vf_typ": 0.65, "vf_min": 0.50, "vf_max": 0.80,
        "Is_nA": 6.0, "n_typ": 1.9, "n_min": 1.6, "n_max": 2.2,
        "slope_factor": 2.0,
        "applications": "Régulation tension, référence de tension, écrêtage, protection surtension",
        "tech": "silicon"
    },
    # ── LED IR ────────────────────────────────
    {
        "id": "led_ir",
        "name": "LED Infrarouge",
        "model": "TSUS5202 / LD271 / SFH484  (λ≈850–950 nm)",
        "color": "#b71c1c",
        "description": "LED GaAs/GaAlAs — émission infrarouge invisible, Vf bas pour une LED",
        "vf_typ": 1.10, "vf_min": 0.80, "vf_max": 1.45,
        "Is_nA": 0.002, "n_typ": 1.9, "n_min": 1.7, "n_max": 2.1,
        "slope_factor": 1.5,
        "applications": "Télécommandes IR, capteurs de proximité, barrières optiques, IRDA",
        "tech": "led", "wavelength": 900
    },
    # ── LED Rouge ─────────────────────────────
    {
        "id": "led_red",
        "name": "LED Rouge",
        "model": "L-934ID / HLMP-4700  (λ≈620–680 nm)",
        "color": "#e53935",
        "description": "LED GaAsP/AlGaInP — rouge classique, Vf modéré",
        "vf_typ": 1.85, "vf_min": 1.55, "vf_max": 2.20,
        "Is_nA": 0.0008, "n_typ": 2.0, "n_min": 1.8, "n_max": 2.2,
        "slope_factor": 1.4,
        "applications": "Signalisation, afficheurs 7 segments, indicateurs de présence",
        "tech": "led", "wavelength": 650
    },
    # ── LED Orange ────────────────────────────
    {
        "id": "led_orange",
        "name": "LED Orange",
        "model": "HLMP-EL3C / L-53HD  (λ≈600–620 nm)",
        "color": "#fb8c00",
        "description": "LED GaAsP — orange vif, bonne visibilité diurne",
        "vf_typ": 2.05, "vf_min": 1.80, "vf_max": 2.35,
        "Is_nA": 0.0003, "n_typ": 2.0, "n_min": 1.8, "n_max": 2.2,
        "slope_factor": 1.4,
        "applications": "Signalisation routière, afficheurs, panneaux d'information",
        "tech": "led", "wavelength": 610
    },
    # ── LED Jaune ─────────────────────────────
    {
        "id": "led_yellow",
        "name": "LED Jaune",
        "model": "TLHY5100 / L-53YD  (λ≈570–600 nm)",
        "color": "#fdd835",
        "description": "LED GaAsP/GaP — jaune, bon rendement lumineux",
        "vf_typ": 2.10, "vf_min": 1.90, "vf_max": 2.45,
        "Is_nA": 0.0001, "n_typ": 2.0, "n_min": 1.8, "n_max": 2.2,
        "slope_factor": 1.4,
        "applications": "Indicateurs, signalisation, balises lumineuses",
        "tech": "led", "wavelength": 585
    },
    # ── LED Verte bas rendement ───────────────
    {
        "id": "led_green_std",
        "name": "LED Verte standard",
        "model": "TLHG5800 / L-53GD  (λ≈525–565 nm, GaP)",
        "color": "#43a047",
        "description": "LED GaP — verte classique, rendement modéré",
        "vf_typ": 2.10, "vf_min": 1.90, "vf_max": 2.45,
        "Is_nA": 0.00005, "n_typ": 2.0, "n_min": 1.8, "n_max": 2.2,
        "slope_factor": 1.4,
        "applications": "Indicateurs, afficheurs, signalisation",
        "tech": "led", "wavelength": 545
    },
    # ── LED Verte haut rendement ──────────────
    {
        "id": "led_green_hb",
        "name": "LED Verte haute luminosité",
        "model": "TLHG640 / OVLGG4C7  (λ≈520–530 nm, InGaN)",
        "color": "#00c853",
        "description": "LED InGaN — verte haute luminosité, Vf légèrement plus élevé",
        "vf_typ": 2.60, "vf_min": 2.35, "vf_max": 2.90,
        "Is_nA": 0.00001, "n_typ": 2.1, "n_min": 1.9, "n_max": 2.3,
        "slope_factor": 1.3,
        "applications": "Éclairage, rétroéclairage, signalisation haute visibilité",
        "tech": "led", "wavelength": 525
    },
    # ── LED Bleue ─────────────────────────────
    {
        "id": "led_blue",
        "name": "LED Bleue",
        "model": "OVLBB4C7 / NSPB500S  (λ≈450–480 nm)",
        "color": "#1e88e5",
        "description": "LED InGaN — bleue, technologie moderne, Vf élevé",
        "vf_typ": 3.00, "vf_min": 2.70, "vf_max": 3.50,
        "Is_nA": 0.000002, "n_typ": 2.2, "n_min": 2.0, "n_max": 2.5,
        "slope_factor": 1.2,
        "applications": "Éclairage, écrans LCD, phares automobiles, indicateurs",
        "tech": "led", "wavelength": 465
    },
    # ── LED Blanche ───────────────────────────
    {
        "id": "led_white",
        "name": "LED Blanche",
        "model": "NSPW500GS / VLHW4100  (phosphore + InGaN bleu)",
        "color": "#90caf9",
        "description": "LED InGaN bleue + phosphore jaune — lumière blanche, Vf similaire à la LED bleue",
        "vf_typ": 3.10, "vf_min": 2.80, "vf_max": 3.60,
        "Is_nA": 0.000001, "n_typ": 2.3, "n_min": 2.0, "n_max": 2.6,
        "slope_factor": 1.2,
        "applications": "Éclairage général, lampes LED, torches, rétroéclairage",
        "tech": "led", "wavelength": 0
    },
    # ── LED UV ────────────────────────────────
    {
        "id": "led_uv",
        "name": "LED Ultraviolette",
        "model": "VLMU3100 / TLD1500  (λ≈365–405 nm)",
        "color": "#7b1fa2",
        "description": "LED GaN — ultraviolet, Vf très élevé, usage spécialisé",
        "vf_typ": 3.60, "vf_min": 3.30, "vf_max": 4.20,
        "Is_nA": 0.0000005, "n_typ": 2.4, "n_min": 2.1, "n_max": 2.7,
        "slope_factor": 1.1,
        "applications": "Stérilisation UV, détection de fluorescence, durcissement résine, détection billets",
        "tech": "led", "wavelength": 385
    },
]


# ═══════════════════════════════════════════════
#  IDENTIFICATION AVANCÉE — Multi-critères
# ═══════════════════════════════════════════════
def identify_diode_from_curve(data):
    """
    Algorithme d'identification multi-étapes :
      1. Calcul Vf précis par interpolation linéaire à plusieurs niveaux
      2. Estimation n et Is par régression sur région exponentielle
      3. Analyse de la forme de la courbe (slope_ratio, onset sharpness)
      4. Scoring pondéré avec pénalité de distance
      5. Séparation LED vs diode par plage Vf + tech
    """
    if len(data) < 6:
        return None

    data_s = sorted(data, key=lambda d: d['U'])
    u_vals = [d['U'] for d in data_s]
    i_vals = [d['I'] for d in data_s]
    Vt     = 0.02585          # V à 300 K
    I_mA_to_A = 1e-3

    i_max = max(i_vals)
    if i_max <= 0:
        return None

    # ── 1. Vf à plusieurs seuils (5%, 10%, 30%) ──────────────────────────
    def interp_vf(threshold_pct):
        target = i_max * threshold_pct
        for k in range(len(u_vals)):
            if i_vals[k] >= target:
                if k > 0:
                    dv = u_vals[k] - u_vals[k-1]
                    di = i_vals[k] - i_vals[k-1]
                    return u_vals[k-1] + (target - i_vals[k-1]) * dv / di if di > 0 else u_vals[k]
                return u_vals[k]
        return u_vals[-1]

    vf_5   = max(0.0, interp_vf(0.05))
    vf_10  = max(0.0, interp_vf(0.10))
    vf_30  = max(0.0, interp_vf(0.30))
    vf     = round(vf_10, 4)          # Vf de référence = 10 % Imax

    # ── 2. Pente normalisée (onset_sharpness) ────────────────────────────
    # Ratio entre U au 5 % et U au 30 % : courbe raide → ratio élevé
    onset_sharpness = (vf_30 - vf_5) / max(vf_5, 0.01)

    # ── 3. Régression exponentielle pour n et Is ─────────────────────────
    pts_exp = [
        (u, i * I_mA_to_A)
        for u, i in zip(u_vals, i_vals)
        if i > i_max * 0.03 and i < i_max * 0.75 and u > 0.02
    ]

    estimated_n  = 1.8
    estimated_Is = 10e-9

    if len(pts_exp) >= 4:
        # Régression linéaire sur ln(I) vs V  →  ln(I) = ln(Is) + V/(n·Vt)
        try:
            ln_i  = [math.log(p[1]) for p in pts_exp]
            v_arr = [p[0] for p in pts_exp]
            N = len(pts_exp)
            sum_v   = sum(v_arr)
            sum_li  = sum(ln_i)
            sum_vli = sum(v * l for v, l in zip(v_arr, ln_i))
            sum_v2  = sum(v * v for v in v_arr)
            denom   = N * sum_v2 - sum_v ** 2
            if abs(denom) > 1e-12:
                slope     = (N * sum_vli - sum_v * sum_li) / denom   # = 1/(n·Vt)
                intercept = (sum_li - slope * sum_v) / N              # = ln(Is)
                n_calc    = 1.0 / (slope * Vt) if slope > 0 else 1.8
                if 0.4 < n_calc < 3.5:
                    estimated_n  = round(n_calc, 3)
                Is_calc = math.exp(intercept)
                if 1e-18 < Is_calc < 1e-2:
                    estimated_Is = Is_calc
        except Exception:
            pass

    # ── 4. Courbure / non-linéarité ──────────────────────────────────────
    # Comparer la pente au début et à la fin de la région exponentielle
    slope_ratio = 1.0
    if len(pts_exp) >= 6:
        try:
            s1_dv = pts_exp[1][0]  - pts_exp[0][0]
            s1_di = pts_exp[1][1]  - pts_exp[0][1]
            s2_dv = pts_exp[-1][0] - pts_exp[-2][0]
            s2_di = pts_exp[-1][1] - pts_exp[-2][1]
            if s1_dv > 0 and s2_dv > 0 and s1_di > 0 and s2_di > 0:
                slope_ratio = (s2_di / s2_dv) / (s1_di / s1_dv)
        except Exception:
            pass

    # ── 5. Scoring multi-critères ─────────────────────────────────────────
    scores = []
    for diode in DIODE_DATABASE:
        score = 0.0

        # — Critère Vf (50 pts) —
        vf_center = diode["vf_typ"]
        vf_half   = (diode["vf_max"] - diode["vf_min"]) / 2
        if diode["vf_min"] <= vf <= diode["vf_max"]:
            dist_center = abs(vf - vf_center)
            vf_score    = max(0, 1 - dist_center / max(vf_half, 0.01))
            score += 50 * vf_score
        else:
            dist_out = min(abs(vf - diode["vf_min"]), abs(vf - diode["vf_max"]))
            score   -= dist_out * 55   # forte pénalité hors plage

        # — Critère n (25 pts) —
        n_center = diode["n_typ"]
        n_half   = (diode["n_max"] - diode["n_min"]) / 2
        if diode["n_min"] <= estimated_n <= diode["n_max"]:
            n_score = max(0, 1 - abs(estimated_n - n_center) / max(n_half, 0.01))
            score  += 25 * n_score
        else:
            score  -= abs(estimated_n - n_center) * 12

        # — Critère Is (15 pts) —
        try:
            log_is_meas  = math.log10(max(estimated_Is, 1e-22))
            log_is_ref   = math.log10(diode["Is_nA"] * 1e-9)
            is_diff      = abs(log_is_meas - log_is_ref)
            score       += max(0, 15 - is_diff * 4.5)
        except Exception:
            pass

        # — Critère onset_sharpness (10 pts) —
        ref_sharp = diode.get("slope_factor", 2.0)
        sharp_diff = abs(onset_sharpness - ref_sharp)
        score += max(0, 10 - sharp_diff * 3)

        scores.append({"diode": diode, "score": round(score, 2)})

    scores.sort(key=lambda x: x["score"], reverse=True)

    best       = scores[0]["diode"]
    best_score = scores[0]["score"]

    # ── 6. Confidence — normalisée sur l'écart avec le 2e candidat ──────
    gap = best_score - (scores[1]["score"] if len(scores) > 1 else 0)
    raw_conf = min(99, max(20, int(best_score * 0.85 + gap * 0.6)))

    # Boost si Vf bien dans la plage typique (± 5 mV)
    if abs(vf - best["vf_typ"]) < 0.05:
        raw_conf = min(99, raw_conf + 6)

    return {
        "type":         best["name"],
        "model":        best["model"],
        "id":           best["id"],
        "color":        best["color"],
        "description":  best["description"],
        "applications": best["applications"],
        "tech":         best.get("tech", "silicon"),
        "wavelength":   best.get("wavelength", 0),
        "vf":           round(vf, 3),
        "vf_5pct":      round(vf_5, 3),
        "vf_30pct":     round(vf_30, 3),
        "n":            round(estimated_n, 3),
        "Is_nA":        round(estimated_Is * 1e9, 6),
        "Is_display":   (f"{estimated_Is*1e9:.4f} nA"
                         if estimated_Is * 1e9 >= 0.001
                         else f"{estimated_Is*1e12:.4f} pA"),
        "onset_sharpness": round(onset_sharpness, 3),
        "confidence":   raw_conf,
        "scores":       scores[:6],
    }


# ═══════════════════════════════════════════════
#  ROUTES FLASK
# ═══════════════════════════════════════════════
@app.route("/")
def home():
    return DASHBOARD_HTML

@app.route("/status")
def status():
    return jsonify({"running": running})

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
    global data_store, identified_diode
    data_store = []
    identified_diode = None
    return jsonify({"status": "reset"})

@app.route("/data", methods=["POST"])
def receive_data():
    global data_store
    if not running:
        return jsonify({"status": "stopped"})
    d = request.json
    U = float(d.get("voltage", 0))
    I = float(d.get("current", 0))
    if U >= 0 and I >= 0:
        data_store.append({"U": round(U, 4), "I": round(I, 4)})
    return jsonify({"status": "ok"})

@app.route("/data_batch", methods=["POST"])
def receive_batch():
    global data_store
    if not running:
        return jsonify({"status": "stopped"})
    points = request.json
    if not isinstance(points, list):
        return jsonify({"error": "expected array"}), 400
    new_data = []
    for d in points:
        U = float(d.get("voltage", 0))
        I = float(d.get("current", 0))
        if U >= 0 and I >= 0:
            new_data.append({"U": round(U, 4), "I": round(I, 4)})
    data_store = new_data
    return jsonify({"status": "ok", "points": len(new_data)})

@app.route("/get_data")
def get_data():
    return jsonify(data_store)

@app.route("/identify")
def identify():
    global identified_diode
    if len(data_store) < 6:
        return jsonify({"error": "not enough data"})
    result = identify_diode_from_curve(data_store)
    if result is None:
        return jsonify({"error": "identification failed"})
    identified_diode = result
    return jsonify(result)

@app.route("/export_csv")
def export_csv():
    csv_data = "U(V),I(mA)\n" + "".join(
        f"{d['U']},{d['I']}\n" for d in data_store
    )
    return csv_data, 200, {
        "Content-Type": "text/csv",
        "Content-Disposition": "attachment; filename=mesures_diode.csv"
    }

@app.route("/export_pdf")
def export_pdf():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                        Paragraph, Spacer, Image, HRFlowable)
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib.enums import TA_CENTER
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        return "reportlab / matplotlib non installé", 500

    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                rightMargin=2*cm, leftMargin=2*cm,
                topMargin=2*cm,   bottomMargin=2*cm)
    elements = []

    T  = lambda txt, sty: Paragraph(txt, sty)
    HR = lambda: HRFlowable(width="100%", thickness=0.8,
                             color=colors.HexColor('#1e6ab0'), spaceAfter=10)

    s_title   = ParagraphStyle('t',  fontSize=20, textColor=colors.HexColor('#0a2342'),
                                fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=4)
    s_sub     = ParagraphStyle('s',  fontSize=10, textColor=colors.HexColor('#1e6ab0'),
                                fontName='Helvetica',      alignment=TA_CENTER, spaceAfter=2)
    s_date    = ParagraphStyle('d',  fontSize=9,  textColor=colors.grey,
                                fontName='Helvetica',      alignment=TA_CENTER, spaceAfter=12)
    s_section = ParagraphStyle('sc', fontSize=12, textColor=colors.HexColor('#0a2342'),
                                fontName='Helvetica-Bold', spaceAfter=6, spaceBefore=10)
    s_foot    = ParagraphStyle('f',  fontSize=8,  textColor=colors.grey,
                                fontName='Helvetica',      alignment=TA_CENTER)

    now = datetime.datetime.now().strftime("%d/%m/%Y à %H:%M:%S")
    elements += [T("SMART DIODE DASHBOARD", s_title),
                 T("Rapport de Mesures Expérimentales — ESP32 + MCP4725", s_sub),
                 T(f"Généré le : {now}", s_date), HR()]

    def styled_table(data, col_w):
        t = Table(data, colWidths=col_w)
        t.setStyle(TableStyle([
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
        return t

    if identified_diode:
        elements.append(T("Identification du Composant", s_section))
        id_rows = [
            ["Type identifié",         f"{identified_diode['type']} ({identified_diode['model']})"],
            ["Description",            identified_diode["description"]],
            ["Applications",           identified_diode.get("applications", "—")],
            ["Tension de seuil Vf",    f"{identified_diode['vf']} V"],
            ["Facteur d'idéalité n",   str(identified_diode["n"])],
            ["Courant de saturation Is",identified_diode.get("Is_display", "—")],
            ["Onset sharpness",        str(identified_diode.get("onset_sharpness", "—"))],
            ["Niveau de confiance",    f"{identified_diode['confidence']} %"],
        ]
        elements += [styled_table(id_rows, [5.5*cm, 10.5*cm]), Spacer(1, 0.4*cm)]

    nb    = len(data_store)
    u_max = max((d['U'] for d in data_store), default=0)
    i_max = max((d['I'] for d in data_store), default=0)

    elements.append(T("Informations de Mesure", s_section))
    info_rows = [
        ["Composant",            identified_diode["type"] if identified_diode else "Diode"],
        ["Points acquis",        str(nb)],
        ["Tension max mesurée",  f"{u_max:.3f} V"],
        ["Courant max mesuré",   f"{i_max:.3f} mA"],
    ]
    elements += [styled_table(info_rows, [5.5*cm, 10.5*cm]), Spacer(1, 0.4*cm)]

    # Courbe matplotlib
    if nb > 0:
        elements.append(HR())
        elements.append(T("Courbe Caractéristique I = f(U)", s_section))
        u_vals = [d['U'] for d in data_store]
        i_vals = [d['I'] for d in data_store]
        fig, ax = plt.subplots(figsize=(7.5, 4))
        ax.plot(u_vals, i_vals, color='#1e6ab0', linewidth=2.5,
                marker='o', markersize=3, label='Mesure réelle', zorder=3)
        if identified_diode:
            Is  = identified_diode['Is_nA'] * 1e-9
            n   = identified_diode['n']
            v_t = [i * max(u_vals, default=3.3) / 300 for i in range(301)]
            i_t = [min(Is*(math.exp(v/(n*Vt_plt))-1)*1000, i_max*2)
                   for v in v_t for Vt_plt in [0.02585]]
            # flatten generator
            i_t2 = []
            for v in v_t:
                val = Is * (math.exp(v / (n * 0.02585)) - 1) * 1000
                i_t2.append(min(val, i_max * 2))
            ax.plot(v_t, i_t2, color=identified_diode.get('color', '#ff9800'),
                    linewidth=2, linestyle='--',
                    label=f"Shockley — {identified_diode['type']}", zorder=2)
            ax.legend(fontsize=9)
        ax.set_xlabel("Tension U (V)", fontsize=10)
        ax.set_ylabel("Courant I (mA)", fontsize=10)
        ax.set_title(f"Courbe I = f(U) — {identified_diode['type'] if identified_diode else 'Diode'}",
                     fontsize=11, color='#0a2342', fontweight='bold')
        ax.grid(True, color='#e0e8f0', linewidth=0.5)
        ax.set_facecolor('#f8fbff'); fig.patch.set_facecolor('white')
        plt.tight_layout()
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=150, bbox_inches='tight')
        plt.close(); img_buf.seek(0)
        elements += [Image(img_buf, width=15*cm, height=8*cm), Spacer(1, 0.4*cm)]

    # Tableau données
    elements.append(HR())
    elements.append(T("Tableau des Données Acquises", s_section))
    tdata = [["#", "Tension U (V)", "Courant I (mA)"]] + \
            [[str(i+1), f"{float(d['U']):.3f}", f"{float(d['I']):.3f}"]
             for i, d in enumerate(data_store)]
    t = Table(tdata, colWidths=[2*cm, 7*cm, 7*cm], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  colors.HexColor('#0a2342')),
        ('TEXTCOLOR',     (0,0), (-1,0),  colors.white),
        ('FONTNAME',      (0,0), (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,0),  11),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING',    (0,0), (-1,0),  8), ('BOTTOMPADDING', (0,0), (-1,0),  8),
        ('FONTNAME',      (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE',      (0,1), (-1,-1), 10),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [colors.HexColor('#eef4fb'), colors.white]),
        ('TEXTCOLOR',     (0,1), (-1,-1), colors.HexColor('#0a2342')),
        ('TOPPADDING',    (0,1), (-1,-1), 5), ('BOTTOMPADDING', (0,1), (-1,-1), 5),
        ('GRID',          (0,0), (-1,-1), 0.5, colors.HexColor('#b0c8e0')),
        ('BOX',           (0,0), (-1,-1), 1.5, colors.HexColor('#0a2342')),
    ]))
    elements += [t, Spacer(1, 0.5*cm), HR(),
                 T("Smart Diode Dashboard — ESP32 + MCP4725 — Rapport automatique", s_foot)]

    doc.build(elements)
    buffer.seek(0)
    return buffer.read(), 200, {
        "Content-Type": "application/pdf",
        "Content-Disposition": "attachment; filename=rapport_diode.pdf"
    }


# ═══════════════════════════════════════════════
#  HTML DASHBOARD  (identique visuellement +
#  améliorations : panel debug scores, Vf multi)
# ═══════════════════════════════════════════════
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
:root{
  --bg:#060a10;--bg2:#0b1220;--bg3:#111827;
  --border:#1e2d45;--border2:#243450;
  --text:#e2eaf6;--muted:#5a7090;
  --accent:#00d4ff;--green:#00e5a0;--orange:#ff9500;--red:#ff4560;
  --mono:'Space Mono',monospace;--sans:'DM Sans',sans-serif;--radius:10px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);font-family:var(--sans);color:var(--text);min-height:100vh;overflow-x:hidden}
body::before{content:'';position:fixed;inset:0;
  background-image:linear-gradient(rgba(0,212,255,.03)1px,transparent 1px),
    linear-gradient(90deg,rgba(0,212,255,.03)1px,transparent 1px);
  background-size:40px 40px;pointer-events:none;z-index:0}
.header{position:relative;z-index:10;display:flex;align-items:center;
  justify-content:space-between;padding:0 28px;height:58px;
  background:rgba(11,18,32,.95);border-bottom:1px solid var(--border);backdrop-filter:blur(10px)}
.logo-icon{width:34px;height:34px;border-radius:8px;background:linear-gradient(135deg,#00d4ff22,#00d4ff44);
  border:1px solid var(--accent);display:flex;align-items:center;justify-content:center;font-size:16px}
.logo-text{font-family:var(--mono);font-size:13px;font-weight:700;letter-spacing:2px;color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1px;margin-top:1px}
.header-right{display:flex;align-items:center;gap:20px}
.header-stat-val{font-family:var(--mono);font-size:15px;font-weight:700}
.header-stat-lbl{font-size:9px;color:var(--muted);letter-spacing:1px;text-transform:uppercase}
.status-pill{display:flex;align-items:center;gap:7px;padding:5px 12px;border-radius:20px;
  background:var(--bg3);border:1px solid var(--border2);font-size:11px;color:var(--muted);font-family:var(--mono)}
.status-dot{width:7px;height:7px;border-radius:50%;background:var(--muted);transition:all .3s}
.status-dot.live{background:var(--green);box-shadow:0 0 8px var(--green);animation:pulse 1.5s infinite}
.status-dot.stopped{background:var(--red);box-shadow:0 0 6px var(--red)}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.layout{position:relative;z-index:1;display:grid;
  grid-template-columns:200px 1fr 290px;gap:12px;padding:12px;
  min-height:calc(100vh - 58px)}
.card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius);padding:16px;overflow:hidden}
.card-header{display:flex;align-items:center;gap:8px;margin-bottom:14px;
  padding-bottom:10px;border-bottom:1px solid var(--border)}
.card-icon{width:26px;height:26px;border-radius:6px;display:flex;align-items:center;
  justify-content:center;font-size:13px;flex-shrink:0}
.card-title{font-size:11px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted)}
.left-panel,.center-panel,.right-panel{grid-row:1/3;display:flex;flex-direction:column;gap:12px}
.right-panel{overflow-y:auto;scrollbar-width:thin;scrollbar-color:var(--border2) transparent}
.field{margin-bottom:10px}
.field label{display:block;font-size:10px;font-weight:500;color:var(--muted);
  letter-spacing:.8px;text-transform:uppercase;margin-bottom:4px}
input[type="number"],select{width:100%;padding:7px 10px;background:var(--bg);
  border:1px solid var(--border2);border-radius:6px;color:var(--text);
  font-family:var(--mono);font-size:12px;transition:border .2s;-moz-appearance:textfield}
input[type="number"]::-webkit-inner-spin-button{-webkit-appearance:none}
input[type="number"]:focus,select:focus{outline:none;border-color:var(--accent);
  box-shadow:0 0 0 3px rgba(0,212,255,.08)}
.btn{width:100%;padding:9px 12px;border:none;border-radius:7px;font-family:var(--mono);
  font-size:11px;font-weight:700;letter-spacing:1px;cursor:pointer;transition:all .2s;
  display:flex;align-items:center;justify-content:center;gap:6px}
.btn:hover{transform:translateY(-1px)}.btn:active{transform:translateY(0)}
.btn+.btn{margin-top:6px}
.btn-primary{background:linear-gradient(135deg,#00d4ff22,#00d4ff44);color:var(--accent);border:1px solid var(--accent)}
.btn-primary:hover{background:linear-gradient(135deg,#00d4ff33,#00d4ff55);box-shadow:0 0 16px rgba(0,212,255,.2)}
.btn-danger{background:linear-gradient(135deg,#ff456022,#ff456033);color:var(--red);border:1px solid #ff456066}
.btn-ghost{background:var(--bg3);color:var(--muted);border:1px solid var(--border)}
.btn-ghost:hover{color:var(--text);border-color:var(--border2)}
.btn-identify{background:linear-gradient(135deg,#ff950022,#ff950044);color:var(--orange);
  border:1px solid #ff950066;padding:11px 12px;font-size:12px}
.btn-identify:hover{background:linear-gradient(135deg,#ff950033,#ff950055);box-shadow:0 0 16px rgba(255,149,0,.2)}
.btn-export{background:linear-gradient(135deg,#00e5a022,#00e5a033);color:var(--green);border:1px solid #00e5a066}
.btn-pdf{background:linear-gradient(135deg,#9c27b022,#9c27b033);color:#ce93d8;border:1px solid #9c27b066}
.live-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.live-item{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px;text-align:center}
.live-label{font-size:9px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;margin-bottom:4px}
.live-val{font-family:var(--mono);font-size:18px;font-weight:700;line-height:1}
.live-unit{font-size:10px;color:var(--muted);margin-top:2px}
.chart-wrap{position:relative;flex:1}
canvas{width:100%!important}
.table-wrap{flex:1;overflow-y:auto;max-height:200px;scrollbar-width:thin}
table{width:100%;border-collapse:collapse;font-size:11px}
thead th{background:var(--bg);padding:6px 8px;color:var(--muted);font-size:9px;font-weight:600;
  text-transform:uppercase;letter-spacing:1px;position:sticky;top:0;text-align:center;
  border-bottom:1px solid var(--border)}
tbody td{padding:5px 8px;text-align:center;border-bottom:1px solid var(--border);
  font-family:var(--mono);font-size:11px;color:#8aafc8;transition:background .1s}
tbody tr:hover td{background:var(--bg3);color:var(--text)}
.axes-panel{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 12px;margin-top:8px}
.axes-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.axes-grid .field{margin-bottom:0}
.axes-grid label{font-size:9px}
.axes-grid input{padding:5px 8px;font-size:11px}
#id-result{display:none;animation:fadeUp .4s ease}
@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.id-card{background:var(--bg);border-radius:8px;padding:12px;border:1px solid var(--border2);transition:border-color .3s}
.id-type{font-family:var(--mono);font-size:14px;font-weight:700;line-height:1.2}
.id-model{font-size:10px;color:var(--muted);margin-top:2px}
.id-desc{font-size:10px;color:#6a8aaa;margin-top:6px;line-height:1.5;padding-top:8px;border-top:1px solid var(--border)}
.id-params{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:8px}
.id-param{background:var(--bg2);border:1px solid var(--border);border-radius:6px;padding:7px 5px;text-align:center}
.id-param-name{font-size:8px;color:var(--muted);letter-spacing:.5px;text-transform:uppercase}
.id-param-val{font-family:var(--mono);font-size:12px;font-weight:700;margin-top:3px;color:var(--green)}
.confidence-row{display:flex;align-items:center;justify-content:space-between;margin-top:8px;gap:8px}
.conf-label{font-size:9px;color:var(--muted)}
.conf-bar-wrap{flex:1;height:4px;background:var(--border);border-radius:2px;overflow:hidden}
.conf-bar-fill{height:100%;border-radius:2px;transition:width .8s ease,background .5s}
.conf-pct{font-family:var(--mono);font-size:11px;font-weight:700}
.id-apps{margin-top:8px;padding:7px 10px;background:var(--bg2);border-radius:6px;border-left:2px solid var(--orange)}
.id-apps-label{font-size:9px;color:var(--orange);text-transform:uppercase;letter-spacing:1px;font-weight:600}
.id-apps-text{font-size:10px;color:#8aafc8;margin-top:3px;line-height:1.4}
.candidates{margin-top:8px}
.cand-title{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}
.cand-item{display:flex;align-items:center;gap:8px;padding:4px 0;
  border-bottom:1px solid var(--border);font-size:10px}
.cand-item:last-child{border-bottom:none}
.cand-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.cand-name{flex:1;color:#6a8aaa}
.cand-score{font-family:var(--mono);font-size:10px;color:var(--muted)}
.shockley-row{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.shockley-row .field{margin-bottom:0}
/* Vf multi-level badges */
.vf-row{display:flex;gap:5px;margin-top:6px;flex-wrap:wrap}
.vf-badge{padding:3px 7px;border-radius:4px;font-family:var(--mono);font-size:9px;font-weight:700}
/* Score debug table */
.score-tbl{width:100%;border-collapse:collapse;font-size:9px;margin-top:6px}
.score-tbl th{color:var(--muted);font-size:8px;text-transform:uppercase;letter-spacing:.5px;
  padding:3px 5px;border-bottom:1px solid var(--border);text-align:left}
.score-tbl td{padding:3px 5px;border-bottom:1px solid var(--border);font-family:var(--mono);font-size:9px}
.score-bar{height:3px;border-radius:2px;margin-top:2px}

@media(max-width:1200px){
  .layout{grid-template-columns:1fr;height:auto}
  .left-panel,.center-panel,.right-panel{grid-row:auto}
  .chart-wrap{height:400px}
}
@media(max-width:768px){
  .layout{padding:8px;gap:8px}
  .card{padding:12px}
  .live-grid,.axes-grid,.shockley-row,.id-params{grid-template-columns:1fr}
  .chart-wrap{height:300px}
  .btn{font-size:10px;padding:10px}
  table{font-size:10px}
}
</style>
</head>
<body>

<header class="header">
  <div style="display:flex;align-items:center;gap:12px">
    <div class="logo-icon">⚡</div>
    <div>
      <div class="logo-text">SMART DIODE</div>
      <div class="logo-sub">ESP32 · MCP4725 · AI IDENTIFY</div>
    </div>
  </div>
  <div class="header-right">
    <div style="text-align:right">
      <div class="header-stat-val" id="hdr-v" style="color:var(--accent)">0.000<span style="font-size:10px;color:var(--muted)"> V</span></div>
      <div class="header-stat-lbl">Tension</div>
    </div>
    <div style="text-align:right">
      <div class="header-stat-val" id="hdr-i" style="color:var(--green)">0.000<span style="font-size:10px;color:var(--muted)"> mA</span></div>
      <div class="header-stat-lbl">Courant</div>
    </div>
    <div style="text-align:right">
      <div class="header-stat-val" id="hdr-pts" style="color:var(--muted)">0<span style="font-size:10px;color:var(--muted)"> pts</span></div>
      <div class="header-stat-lbl">Points</div>
    </div>
    <div class="status-pill">
      <div class="status-dot" id="status-dot"></div>
      <span id="status-text">IDLE</span>
    </div>
  </div>
</header>

<div class="layout">

  <!-- ══ LEFT ══ -->
  <div class="left-panel">
    <div class="card">
      <div class="card-header">
        <div class="card-icon" style="background:#00d4ff11;border:1px solid #00d4ff44">🎛</div>
        <div class="card-title">Contrôle</div>
      </div>
      <div class="field">
        <label>Composant</label>
        <select><option>Diode / LED</option></select>
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

    <div class="card">
      <div class="card-header">
        <div class="card-icon" style="background:#00e5a011;border:1px solid #00e5a044">⚡</div>
        <div class="card-title">Mesure live</div>
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

    <div class="card" style="flex:1;display:flex;flex-direction:column;min-height:0">
      <div class="card-header">
        <div class="card-icon" style="background:#9c27b011;border:1px solid #9c27b044">📊</div>
        <div class="card-title">Données</div>
      </div>
      <div class="table-wrap" style="flex:1">
        <table>
          <thead><tr><th>#</th><th>U (V)</th><th>I (mA)</th></tr></thead>
          <tbody id="table-body"></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ══ CENTER ══ -->
  <div class="center-panel">
    <div class="card" style="flex:1;display:flex;flex-direction:column">
      <div class="card-header">
        <div class="card-icon" style="background:#00d4ff11;border:1px solid #00d4ff44">📈</div>
        <div class="card-title">Courbe I = f(U)</div>
        <div style="margin-left:auto;font-family:var(--mono);font-size:9px;color:var(--muted)">
          Scroll = zoom &nbsp;·&nbsp; Drag = pan
        </div>
      </div>
      <div class="chart-wrap" style="flex:1;position:relative">
        <canvas id="chart"></canvas>
      </div>
      <div class="axes-panel">
        <div class="axes-grid">
          <div class="field"><label>X min</label><input type="number" id="xmin" value="0"   step="0.1" oninput="updateAxes()"></div>
          <div class="field"><label>X max</label><input type="number" id="xmax" value="3.3" step="0.1" oninput="updateAxes()"></div>
          <div class="field"><label>Y min</label><input type="number" id="ymin" value="0"   step="0.05" oninput="updateAxes()"></div>
          <div class="field"><label>Y max</label><input type="number" id="ymax" value="2"   step="0.1"  oninput="updateAxes()"></div>
        </div>
        <div style="display:flex;gap:6px;margin-top:8px">
          <button class="btn btn-ghost" style="font-size:10px;padding:5px" onclick="chart.resetZoom()">🔍 Reset Zoom</button>
          <button class="btn btn-ghost" style="font-size:10px;padding:5px" onclick="autoScale()">⊡ Auto Scale</button>
        </div>
      </div>
    </div>
  </div>

  <!-- ══ RIGHT ══ -->
  <div class="right-panel">

    <!-- Identification -->
    <div class="card">
      <div class="card-header">
        <div class="card-icon" style="background:#ff950011;border:1px solid #ff950044">🔬</div>
        <div class="card-title">Identification IA</div>
      </div>
      <button class="btn btn-identify" id="btn-identify" onclick="identifyDiode()">
        🔍 &nbsp;IDENTIFIER LA DIODE / LED
      </button>

      <div id="id-result" style="margin-top:10px">
        <div class="id-card" id="id-card">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px">
            <div>
              <div class="id-type" id="id-type">—</div>
              <div class="id-model" id="id-model">—</div>
            </div>
            <div style="width:10px;height:10px;border-radius:50%;flex-shrink:0;margin-top:4px" id="id-dot"></div>
          </div>
          <div class="id-desc" id="id-desc">—</div>

          <!-- Vf multi-niveaux -->
          <div class="vf-row" id="vf-badges"></div>

          <div class="id-params">
            <div class="id-param">
              <div class="id-param-name">Vf @10%</div>
              <div class="id-param-val" id="id-vf">—</div>
            </div>
            <div class="id-param">
              <div class="id-param-name">n</div>
              <div class="id-param-val" id="id-n">—</div>
            </div>
            <div class="id-param">
              <div class="id-param-name">Is</div>
              <div class="id-param-val" id="id-is" style="font-size:10px">—</div>
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

          <!-- Candidats avec barre de score -->
          <div class="candidates" id="candidates"></div>

          <!-- Debug scores -->
          <details style="margin-top:8px">
            <summary style="font-size:9px;color:var(--muted);cursor:pointer;letter-spacing:.5px;
              text-transform:uppercase">▸ Détail scoring</summary>
            <div id="score-debug" style="margin-top:6px"></div>
          </details>
        </div>
      </div>
    </div>

    <!-- Export -->
    <div class="card">
      <div class="card-header">
        <div class="card-icon" style="background:#00e5a011;border:1px solid #00e5a044">💾</div>
        <div class="card-title">Export</div>
      </div>
      <button class="btn btn-export" onclick="exportCSV()">📥 &nbsp;EXPORT CSV</button>
      <button class="btn btn-pdf"    onclick="window.location.href='/export_pdf'">📄 &nbsp;EXPORT PDF</button>
    </div>

    <!-- Shockley manuel -->
    <div class="card">
      <div class="card-header">
        <div class="card-icon" style="background:#ff456011;border:1px solid #ff456044">📉</div>
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
      <div class="field" style="margin-top:6px"><label>Vt (mV)</label>
        <input type="number" id="Vt_val" value="25.85" step="0.1" oninput="updateShockley()">
      </div>
      <div style="margin-top:6px;padding:6px 8px;background:var(--bg);border-radius:6px;
        border:1px solid var(--border);font-family:var(--mono);font-size:10px;
        color:var(--muted);text-align:center" id="shockley-info">
        I = Is·(e^(V/n·Vt) − 1)
      </div>
    </div>

  </div>
</div>

<script>
// ─── CHART ────────────────────────────────────────
let chart;
function initChart(){
  const ctx=document.getElementById('chart').getContext('2d');
  chart=new Chart(ctx,{
    type:'line',
    data:{datasets:[
      {label:'Mesure réelle',data:[],borderColor:'#00d4ff',
       backgroundColor:'rgba(0,212,255,.06)',pointRadius:2.5,
       pointHoverRadius:6,pointBackgroundColor:'#00d4ff',
       borderWidth:2,tension:.3,fill:true,order:1},
      {label:'Shockley manuel',data:[],borderColor:'#ff4560',
       backgroundColor:'transparent',pointRadius:0,borderWidth:1.5,
       showLine:true,segment:{borderDash:[5,3]},tension:.4,order:3},
      {label:'Shockley identifiée',data:[],borderColor:'#ff9500',
       backgroundColor:'transparent',pointRadius:0,borderWidth:2,
       showLine:true,segment:{borderDash:[3,3]},tension:.4,hidden:true,order:2}
    ]},
    options:{
      responsive:true,maintainAspectRatio:false,animation:false,parsing:false,
      interaction:{mode:'nearest',intersect:false,axis:'x'},
      plugins:{
        legend:{labels:{color:'#5a7090',font:{size:10,family:"'Space Mono',monospace"},
          boxWidth:20,padding:12}},
        tooltip:{backgroundColor:'#0b1220',borderColor:'#1e2d45',borderWidth:1,
          titleColor:'#00d4ff',bodyColor:'#e2eaf6',padding:10,
          titleFont:{family:"'Space Mono',monospace",size:11},
          bodyFont:{family:"'Space Mono',monospace",size:11},
          callbacks:{
            title:i=>'U = '+Number(i[0].parsed.x).toFixed(3)+' V',
            label:i=>i.dataset.label+': '+Number(i[0].parsed.y).toFixed(4)+' mA'
          }},
        zoom:{zoom:{wheel:{enabled:true,speed:.08},pinch:{enabled:true},mode:'xy'},
              pan:{enabled:true,mode:'xy'}}
      },
      scales:{
        x:{type:'linear',min:0,max:3.3,
           title:{display:true,text:'Tension U (V)',color:'#5a7090',font:{size:10}},
           ticks:{color:'#3a5070',font:{size:9,family:"'Space Mono',monospace"},maxTicksLimit:10},
           grid:{color:'#0f1e30'}},
        y:{min:0,max:2,
           title:{display:true,text:'Courant I (mA)',color:'#5a7090',font:{size:10}},
           ticks:{color:'#3a5070',font:{size:9,family:"'Space Mono',monospace"}},
           grid:{color:'#0f1e30'}}
      }
    }
  });
}

function updateAxes(){
  const xmin=+document.getElementById('xmin').value||0;
  const xmax=+document.getElementById('xmax').value||3.3;
  const ymin=+document.getElementById('ymin').value||0;
  const ymax=+document.getElementById('ymax').value||2;
  if(xmin>=xmax||ymin>=ymax)return;
  chart.options.scales.x.min=xmin; chart.options.scales.x.max=xmax;
  chart.options.scales.y.min=ymin; chart.options.scales.y.max=ymax;
  chart.update(); updateShockley();
}

function autoScale(){
  const d=chart.data.datasets[0].data;
  if(!d.length)return;
  const xs=d.map(p=>p.x),ys=d.map(p=>p.y);
  const xm=Math.max(...xs)*1.05,ym=Math.max(...ys)*1.15;
  document.getElementById('xmin').value=0;
  document.getElementById('xmax').value=xm.toFixed(2);
  document.getElementById('ymin').value=0;
  document.getElementById('ymax').value=ym.toFixed(2);
  updateAxes();
}

function shockleyPoints(Is_nA,n,Vt_mV,xmax){
  const Is=Is_nA*1e-9,Vt=Vt_mV*1e-3,pts=[];
  for(let i=0;i<=400;i++){
    const V=(xmax/400)*i;
    const I=Is*(Math.exp(V/(n*Vt))-1)*1000;
    if(I>=0&&I<50000)pts.push({x:V,y:I});
  }
  return pts;
}

function updateShockley(){
  const Is=+document.getElementById('Is_val').value||10;
  const n =+document.getElementById('n_val').value||1.8;
  const Vt=+document.getElementById('Vt_val').value||25.85;
  const xmax=+document.getElementById('xmax').value||3.3;
  chart.data.datasets[1].data=shockleyPoints(Is,n,Vt,xmax);
  chart.update();
  document.getElementById('shockley-info').textContent=
    `Is=${Is.toFixed(3)} nA  ·  n=${n}  ·  Vt=${Vt} mV`;
}

// ─── IDENTIFICATION ───────────────────────────────
function identifyDiode(){
  const btn=document.getElementById('btn-identify');
  btn.textContent='⏳  Analyse en cours...';
  btn.disabled=true;

  fetch('/identify').then(r=>r.json()).then(res=>{
    btn.innerHTML='🔍 &nbsp;IDENTIFIER LA DIODE / LED';
    btn.disabled=false;
    if(res.error){
      alert(res.error==='not enough data'?'⚠️ Minimum 6 points requis.':'⚠️ '+res.error);
      return;
    }

    const panel=document.getElementById('id-result');
    panel.style.display='block';
    const card=document.getElementById('id-card');
    card.style.borderColor=res.color;
    document.getElementById('id-dot').style.cssText=
      `background:${res.color};box-shadow:0 0 8px ${res.color}`;
    document.getElementById('id-type').textContent=res.type;
    document.getElementById('id-type').style.color=res.color;
    document.getElementById('id-model').textContent=res.model;
    document.getElementById('id-desc').textContent=res.description;
    document.getElementById('id-vf').textContent=res.vf+' V';
    document.getElementById('id-n').textContent=res.n;
    document.getElementById('id-is').textContent=res.Is_display;
    document.getElementById('id-apps').textContent=res.applications;
    document.getElementById('conf-pct').textContent=res.confidence+'%';
    const col=res.confidence>75?'var(--green)':res.confidence>45?'var(--orange)':'var(--red)';
    document.getElementById('conf-pct').style.color=col;
    const fill=document.getElementById('conf-fill');
    fill.style.width=res.confidence+'%';
    fill.style.background=col;

    // Vf multi-badges
    document.getElementById('vf-badges').innerHTML=
      `<span class="vf-badge" style="background:#00e5a022;color:var(--green)">Vf @5% = ${res.vf_5pct} V</span>
       <span class="vf-badge" style="background:#00d4ff22;color:var(--accent)">Vf @10% = ${res.vf} V</span>
       <span class="vf-badge" style="background:#ff950022;color:var(--orange)">Vf @30% = ${res.vf_30pct} V</span>`;

    // Candidats
    if(res.scores&&res.scores.length>1){
      const maxSc=res.scores[0].score||1;
      let html='<div class="cand-title">Autres candidats</div>';
      res.scores.slice(1).forEach(s=>{
        const pct=Math.max(0,s.score/maxSc*100).toFixed(0);
        html+=`<div class="cand-item">
          <div class="cand-dot" style="background:${s.diode.color}"></div>
          <div class="cand-name">${s.diode.name}</div>
          <div style="flex:1;height:3px;background:var(--border);border-radius:2px;overflow:hidden">
            <div style="width:${pct}%;height:100%;background:${s.diode.color};opacity:.6;border-radius:2px"></div>
          </div>
          <div class="cand-score">${Math.max(0,s.score).toFixed(1)}</div>
        </div>`;
      });
      document.getElementById('candidates').innerHTML=html;
    }

    // Score debug table
    let dbg='<table class="score-tbl"><tr><th>Type</th><th>Score</th><th>Vf min</th><th>Vf max</th><th>n typ</th></tr>';
    res.scores.forEach(s=>{
      dbg+=`<tr>
        <td><span style="display:inline-block;width:6px;height:6px;border-radius:50%;
          background:${s.diode.color};margin-right:4px"></span>${s.diode.name}</td>
        <td style="color:${s.diode.id===res.id?'var(--green)':'var(--muted)'};font-weight:700">
          ${Math.max(0,s.score).toFixed(1)}</td>
        <td>${s.diode.vf_min}</td><td>${s.diode.vf_max}</td><td>${s.diode.n_typ}</td>
      </tr>`;
    });
    dbg+='</table>';
    dbg+=`<div style="margin-top:4px;font-size:9px;color:var(--muted)">
      onset_sharpness = ${res.onset_sharpness}</div>`;
    document.getElementById('score-debug').innerHTML=dbg;

    // Shockley identifiée
    document.getElementById('Is_val').value=res.Is_nA.toFixed(4);
    document.getElementById('n_val').value=res.n;
    updateShockley();
    const xmax=+document.getElementById('xmax').value||3.3;
    chart.data.datasets[2].data=shockleyPoints(res.Is_nA,res.n,25.85,xmax);
    chart.data.datasets[2].borderColor=res.color;
    chart.data.datasets[2].label='Shockley — '+res.type;
    chart.data.datasets[2].hidden=false;
    chart.update();
  }).catch(()=>{
    btn.innerHTML='🔍 &nbsp;IDENTIFIER LA DIODE / LED';
    btn.disabled=false;
    alert('Erreur de connexion.');
  });
}

// ─── LIVE UPDATE ──────────────────────────────────
function updateDashboard(){
  fetch('/get_data').then(r=>r.json()).then(data=>{
    chart.data.datasets[0].data=data.map(d=>({x:+d.U,y:+d.I}));
    chart.update('none');
    const tbody=document.getElementById('table-body');
    const sl=data.slice(-100);
    tbody.innerHTML=sl.map((d,i)=>
      `<tr><td>${data.length-sl.length+i+1}</td><td>${(+d.U).toFixed(3)}</td><td>${(+d.I).toFixed(3)}</td></tr>`
    ).join('');
    if(data.length>0){
      const last=data[data.length-1];
      const U=(+last.U).toFixed(3),I=(+last.I).toFixed(3);
      document.getElementById('voltage').textContent=U;
      document.getElementById('current').textContent=I;
      document.getElementById('hdr-v').innerHTML=U+'<span style="font-size:10px;color:var(--muted)"> V</span>';
      document.getElementById('hdr-i').innerHTML=I+'<span style="font-size:10px;color:var(--muted)"> mA</span>';
      document.getElementById('hdr-pts').innerHTML=data.length+'<span style="font-size:10px;color:var(--muted)"> pts</span>';
    }
  });
}

function setStatus(m){
  const dot=document.getElementById('status-dot'),txt=document.getElementById('status-text');
  const map={live:['live','LIVE'],stopped:['stopped','STOP'],idle:['','IDLE'],reset:['stopped','RESET']};
  const [cls,lbl]=map[m]||['','IDLE'];
  dot.className='status-dot '+cls; txt.textContent=lbl;
}

function startSweep(){fetch('/start');setStatus('live')}
function stopSweep(){fetch('/stop');setStatus('stopped')}

function resetData(){
  fetch('/stop');fetch('/reset');
  chart.data.datasets[0].data=[];
  chart.data.datasets[2].data=[];
  chart.data.datasets[2].hidden=true;
  document.getElementById('table-body').innerHTML='';
  document.getElementById('voltage').textContent='0.000';
  document.getElementById('current').textContent='0.000';
  document.getElementById('hdr-v').innerHTML='0.000<span style="font-size:10px;color:var(--muted)"> V</span>';
  document.getElementById('hdr-i').innerHTML='0.000<span style="font-size:10px;color:var(--muted)"> mA</span>';
  document.getElementById('hdr-pts').innerHTML='0<span style="font-size:10px;color:var(--muted)"> pts</span>';
  document.getElementById('id-result').style.display='none';
  setStatus('reset'); chart.update();
}

function exportCSV(){window.location.href='/export_csv'}

window.onload=function(){initChart();updateShockley();setInterval(updateDashboard,1000)};
</script>
</body>
</html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)