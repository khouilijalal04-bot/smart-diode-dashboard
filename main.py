from flask import Flask, request, jsonify
import math, io, datetime

app = Flask(__name__)

# ═══════════════════════════════════════════════
#  DATA STORAGE
# ═══════════════════════════════════════════════
data_store       = []
running          = False
identified_diode = None

# ═══════════════════════════════════════════════
#  DIODE DATABASE — étendue + précise
# ═══════════════════════════════════════════════
DIODE_DATABASE = [
    {
        "id": "schottky",
        "name": "Schottky",
        "model": "BAT46 / 1N5817 / SS14",
        "color": "#ff9800",
        "description": "Jonction métal-semiconducteur — chute de tension très faible, commutation ultra-rapide",
        "vf_typ": 0.22, "vf_min": 0.08, "vf_max": 0.38,
        "Is_nA": 120.0, "n_typ": 1.05, "n_min": 0.8, "n_max": 1.3,
        "slope_factor": 3.5,
        "curvature": 0.85,
        "applications": "Redressement HF, protection inverse, détecteurs RF, OR-ing d'alimentations",
        "tech": "metal-semiconductor"
    },
    {
        "id": "germanium",
        "name": "Germanium",
        "model": "1N60 / OA91 / AA112",
        "color": "#9c27b0",
        "description": "Semiconducteur Ge — Vf très bas, courant de fuite élevé, sensible à la température",
        "vf_typ": 0.27, "vf_min": 0.12, "vf_max": 0.45,
        "Is_nA": 600.0, "n_typ": 1.0, "n_min": 0.8, "n_max": 1.2,
        "slope_factor": 3.2,
        "curvature": 0.80,
        "applications": "Détection AM, démodulation, circuits vintage, radio à galène",
        "tech": "germanium"
    },
    {
        "id": "silicon_signal",
        "name": "Silicium signal",
        "model": "1N4148 / 1N914 / BAV99",
        "color": "#2196f3",
        "description": "Diode Si signal rapide — polyvalente, switching ns, très répandue",
        "vf_typ": 0.52, "vf_min": 0.38, "vf_max": 0.62,
        "Is_nA": 8.0, "n_typ": 1.5, "n_min": 1.2, "n_max": 1.8,
        "slope_factor": 2.8,
        "curvature": 0.72,
        "applications": "Switching logique, démodulation, protection ESD, redressement signal",
        "tech": "silicon"
    },
    {
        "id": "silicon_rect",
        "name": "Silicium redresseur",
        "model": "1N4001–1N4007 / 1N5408",
        "color": "#03a9f4",
        "description": "Diode Si redresseur robuste — courant élevé, standard industriel 50/60 Hz",
        "vf_typ": 0.70, "vf_min": 0.55, "vf_max": 0.85,
        "Is_nA": 12.0, "n_typ": 1.8, "n_min": 1.5, "n_max": 2.1,
        "slope_factor": 2.2,
        "curvature": 0.62,
        "applications": "Redressement 50 Hz, pont de Graetz, alimentation secteur, protection",
        "tech": "silicon"
    },
    {
        "id": "zener",
        "name": "Zener",
        "model": "BZX55 / 1N47xx / BZV55",
        "color": "#ff5722",
        "description": "Diode à avalanche — région directe semblable au Si, mais usage en inverse",
        "vf_typ": 0.65, "vf_min": 0.50, "vf_max": 0.80,
        "Is_nA": 6.0, "n_typ": 1.9, "n_min": 1.6, "n_max": 2.2,
        "slope_factor": 2.0,
        "curvature": 0.58,
        "applications": "Régulation tension, référence de tension, écrêtage, protection surtension",
        "tech": "silicon"
    },
    {
        "id": "led_ir",
        "name": "LED Infrarouge",
        "model": "TSUS5202 / LD271 / SFH484  (λ≈850–950 nm)",
        "color": "#b71c1c",
        "description": "LED GaAs/GaAlAs — émission infrarouge invisible, Vf bas pour une LED",
        "vf_typ": 1.10, "vf_min": 0.80, "vf_max": 1.45,
        "Is_nA": 0.002, "n_typ": 1.9, "n_min": 1.7, "n_max": 2.1,
        "slope_factor": 1.5,
        "curvature": 0.45,
        "applications": "Télécommandes IR, capteurs de proximité, barrières optiques, IRDA",
        "tech": "led", "wavelength": 900
    },
    {
        "id": "led_red",
        "name": "LED Rouge",
        "model": "L-934ID / HLMP-4700  (λ≈620–680 nm)",
        "color": "#e53935",
        "description": "LED GaAsP/AlGaInP — rouge classique, Vf modéré",
        "vf_typ": 1.85, "vf_min": 1.55, "vf_max": 2.20,
        "Is_nA": 0.0008, "n_typ": 2.0, "n_min": 1.8, "n_max": 2.2,
        "slope_factor": 1.4,
        "curvature": 0.40,
        "applications": "Signalisation, afficheurs 7 segments, indicateurs de présence",
        "tech": "led", "wavelength": 650
    },
    {
        "id": "led_orange",
        "name": "LED Orange",
        "model": "HLMP-EL3C / L-53HD  (λ≈600–620 nm)",
        "color": "#fb8c00",
        "description": "LED GaAsP — orange vif, bonne visibilité diurne",
        "vf_typ": 2.05, "vf_min": 1.80, "vf_max": 2.35,
        "Is_nA": 0.0003, "n_typ": 2.0, "n_min": 1.8, "n_max": 2.2,
        "slope_factor": 1.4,
        "curvature": 0.40,
        "applications": "Signalisation routière, afficheurs, panneaux d'information",
        "tech": "led", "wavelength": 610
    },
    {
        "id": "led_yellow",
        "name": "LED Jaune",
        "model": "TLHY5100 / L-53YD  (λ≈570–600 nm)",
        "color": "#fdd835",
        "description": "LED GaAsP/GaP — jaune, bon rendement lumineux",
        "vf_typ": 2.10, "vf_min": 1.90, "vf_max": 2.45,
        "Is_nA": 0.0001, "n_typ": 2.0, "n_min": 1.8, "n_max": 2.2,
        "slope_factor": 1.4,
        "curvature": 0.40,
        "applications": "Indicateurs, signalisation, balises lumineuses",
        "tech": "led", "wavelength": 585
    },
    {
        "id": "led_green_std",
        "name": "LED Verte standard",
        "model": "TLHG5800 / L-53GD  (λ≈525–565 nm, GaP)",
        "color": "#43a047",
        "description": "LED GaP — verte classique, rendement modéré",
        "vf_typ": 2.10, "vf_min": 1.90, "vf_max": 2.45,
        "Is_nA": 0.00005, "n_typ": 2.0, "n_min": 1.8, "n_max": 2.2,
        "slope_factor": 1.4,
        "curvature": 0.40,
        "applications": "Indicateurs, afficheurs, signalisation",
        "tech": "led", "wavelength": 545
    },
    {
        "id": "led_green_hb",
        "name": "LED Verte haute luminosité",
        "model": "TLHG640 / OVLGG4C7  (λ≈520–530 nm, InGaN)",
        "color": "#00c853",
        "description": "LED InGaN — verte haute luminosité, Vf légèrement plus élevé",
        "vf_typ": 2.60, "vf_min": 2.35, "vf_max": 2.90,
        "Is_nA": 0.00001, "n_typ": 2.1, "n_min": 1.9, "n_max": 2.3,
        "slope_factor": 1.3,
        "curvature": 0.38,
        "applications": "Éclairage, rétroéclairage, signalisation haute visibilité",
        "tech": "led", "wavelength": 525
    },
    {
        "id": "led_blue",
        "name": "LED Bleue",
        "model": "OVLBB4C7 / NSPB500S  (λ≈450–480 nm)",
        "color": "#1e88e5",
        "description": "LED InGaN — bleue, technologie moderne, Vf élevé",
        "vf_typ": 3.00, "vf_min": 2.70, "vf_max": 3.50,
        "Is_nA": 0.000002, "n_typ": 2.2, "n_min": 2.0, "n_max": 2.5,
        "slope_factor": 1.2,
        "curvature": 0.35,
        "applications": "Éclairage, écrans LCD, phares automobiles, indicateurs",
        "tech": "led", "wavelength": 465
    },
    {
        "id": "led_white",
        "name": "LED Blanche",
        "model": "NSPW500GS / VLHW4100  (phosphore + InGaN bleu)",
        "color": "#90caf9",
        "description": "LED InGaN bleue + phosphore jaune — lumière blanche, Vf similaire à la LED bleue",
        "vf_typ": 3.10, "vf_min": 2.80, "vf_max": 3.60,
        "Is_nA": 0.000001, "n_typ": 2.3, "n_min": 2.0, "n_max": 2.6,
        "slope_factor": 1.2,
        "curvature": 0.35,
        "applications": "Éclairage général, lampes LED, torches, rétroéclairage",
        "tech": "led", "wavelength": 0
    },
    {
        "id": "led_uv",
        "name": "LED Ultraviolette",
        "model": "VLMU3100 / TLD1500  (λ≈365–405 nm)",
        "color": "#7b1fa2",
        "description": "LED GaN — ultraviolet, Vf très élevé, usage spécialisé",
        "vf_typ": 3.60, "vf_min": 3.30, "vf_max": 4.20,
        "Is_nA": 0.0000005, "n_typ": 2.4, "n_min": 2.1, "n_max": 2.7,
        "slope_factor": 1.1,
        "curvature": 0.32,
        "applications": "Stérilisation UV, détection de fluorescence, durcissement résine, détection billets",
        "tech": "led", "wavelength": 385
    },
]


# ═══════════════════════════════════════════════
#  IDENTIFICATION AVANCÉE — Algorithme Précis
# ═══════════════════════════════════════════════
def identify_diode_from_curve(data):
    """
    Algorithme d'identification physique rigoureux:
      1. Extraction Vf multi-seuils par interpolation linéaire
      2. Régression LSQ robuste sur ln(I) = ln(Is) + V/(n·Vt)
      3. Analyse de courbure normalisée (R² de la région exponentielle)
      4. Calcul de la pente dynamique (dI/dV) normalisée
      5. Analyse onset: sharpness = (Vf30-Vf5)/Vf5
      6. Scoring bayésien pondéré avec intervalles de confiance
      7. Boost si n et Is concordent simultanément
    """
    if len(data) < 6:
        return None

    data_s = sorted(data, key=lambda d: d['U'])
    u_vals = [d['U'] for d in data_s]
    i_vals = [d['I'] for d in data_s]
    Vt     = 0.02585   # V à T=300 K

    i_max = max(i_vals)
    if i_max <= 0:
        return None

    # ══ 1. Vf multi-seuils ════════════════════════════════════════════════
    def interp_vf(threshold_pct):
        target = i_max * threshold_pct
        for k in range(len(u_vals)):
            if i_vals[k] >= target:
                if k > 0 and (i_vals[k] - i_vals[k-1]) > 0:
                    dv = u_vals[k] - u_vals[k-1]
                    di = i_vals[k] - i_vals[k-1]
                    return u_vals[k-1] + (target - i_vals[k-1]) * dv / di
                return u_vals[k]
        return u_vals[-1]

    vf_2   = max(0.0, interp_vf(0.02))
    vf_5   = max(0.0, interp_vf(0.05))
    vf_10  = max(0.0, interp_vf(0.10))
    vf_20  = max(0.0, interp_vf(0.20))
    vf_30  = max(0.0, interp_vf(0.30))
    vf_50  = max(0.0, interp_vf(0.50))

    vf = round(vf_10, 4)  # référence principale

    # ══ 2. Onset sharpness (robuste) ══════════════════════════════════════
    onset_sharpness = (vf_30 - vf_5) / max(vf_5, 0.01)

    # ══ 3. Régression exponentielle robuste ═══════════════════════════════
    # Région: 3% à 70% de I_max (évite bruit faible + saturation résistance série)
    pts_exp = [
        (u, i * 1e-3)   # mA → A
        for u, i in zip(u_vals, i_vals)
        if i > i_max * 0.03 and i < i_max * 0.70 and u > 0.02
    ]

    estimated_n  = 1.8
    estimated_Is = 10e-9
    r2_exp       = 0.0

    if len(pts_exp) >= 5:
        try:
            ln_i  = [math.log(max(p[1], 1e-20)) for p in pts_exp]
            v_arr = [p[0] for p in pts_exp]
            N     = len(pts_exp)
            sum_v   = sum(v_arr)
            sum_li  = sum(ln_i)
            sum_vli = sum(v * l for v, l in zip(v_arr, ln_i))
            sum_v2  = sum(v * v for v in v_arr)
            denom   = N * sum_v2 - sum_v ** 2
            if abs(denom) > 1e-12:
                slope     = (N * sum_vli - sum_v * sum_li) / denom
                intercept = (sum_li - slope * sum_v) / N
                n_calc    = 1.0 / (slope * Vt) if slope > 0 else 1.8
                if 0.5 < n_calc < 3.5:
                    estimated_n = round(n_calc, 4)
                Is_calc = math.exp(intercept)
                if 1e-20 < Is_calc < 1e-2:
                    estimated_Is = Is_calc
                # R² de la régression
                mean_li = sum_li / N
                ss_tot  = sum((l - mean_li)**2 for l in ln_i)
                ss_res  = sum((l - (slope * v + intercept))**2
                              for v, l in zip(v_arr, ln_i))
                r2_exp  = max(0.0, 1 - ss_res / max(ss_tot, 1e-12))
        except Exception:
            pass

    # ══ 4. Pente dynamique normalisée (dI/dV au pic) ══════════════════════
    # Pente maximale de la courbe I=f(V), normalisée par I_max
    max_slope_norm = 0.0
    for k in range(1, len(u_vals)):
        dv = u_vals[k] - u_vals[k-1]
        di = i_vals[k] - i_vals[k-1]
        if dv > 1e-4:
            sl = (di / dv) / max(i_max, 0.001)
            max_slope_norm = max(max_slope_norm, sl)

    # ══ 5. Courbure de la région exponentielle ════════════════════════════
    # Mesure la non-linéarité: ratio pente_fin / pente_debut
    slope_ratio = 1.0
    if len(pts_exp) >= 6:
        try:
            n_seg = max(2, len(pts_exp) // 4)
            seg1  = pts_exp[:n_seg]
            seg2  = pts_exp[-n_seg:]
            dv1   = seg1[-1][0] - seg1[0][0]
            di1   = seg1[-1][1] - seg1[0][1]
            dv2   = seg2[-1][0] - seg2[0][0]
            di2   = seg2[-1][1] - seg2[0][1]
            if dv1 > 1e-4 and dv2 > 1e-4 and di1 > 0 and di2 > 0:
                slope_ratio = (di2 / dv2) / (di1 / dv1)
        except Exception:
            pass

    # ══ 6. Scoring bayésien multi-critères ════════════════════════════════
    scores = []
    for diode in DIODE_DATABASE:
        score = 0.0

        # ── Critère Vf (45 pts) — poids principal ──
        vf_center = diode["vf_typ"]
        vf_half   = (diode["vf_max"] - diode["vf_min"]) / 2.0
        if diode["vf_min"] <= vf <= diode["vf_max"]:
            dist_c  = abs(vf - vf_center)
            vf_score = max(0.0, 1.0 - (dist_c / max(vf_half, 0.01))**1.5)
            score += 45.0 * vf_score
        else:
            dist_out = min(abs(vf - diode["vf_min"]),
                           abs(vf - diode["vf_max"]))
            score   -= dist_out * 70.0   # forte pénalité hors plage

        # ── Critère n (25 pts) ──
        n_center = diode["n_typ"]
        n_half   = (diode["n_max"] - diode["n_min"]) / 2.0
        if diode["n_min"] <= estimated_n <= diode["n_max"]:
            n_score = max(0.0, 1.0 - abs(estimated_n - n_center) / max(n_half, 0.01))
            score  += 25.0 * n_score
        else:
            score  -= abs(estimated_n - n_center) * 15.0

        # ── Critère Is (15 pts) ──
        try:
            log_is_meas = math.log10(max(estimated_Is, 1e-22))
            log_is_ref  = math.log10(diode["Is_nA"] * 1e-9)
            is_diff     = abs(log_is_meas - log_is_ref)
            score      += max(0.0, 15.0 - is_diff * 4.0)
        except Exception:
            pass

        # ── Critère onset_sharpness (10 pts) ──
        ref_sharp  = diode.get("slope_factor", 2.0)
        sharp_diff = abs(onset_sharpness - ref_sharp)
        score     += max(0.0, 10.0 - sharp_diff * 3.5)

        # ── Bonus cohérence physique ──
        # Si R² élevé ET n dans plage → la courbe ressemble vraiment au modèle
        if r2_exp > 0.92 and diode["n_min"] <= estimated_n <= diode["n_max"]:
            score += 5.0 * r2_exp

        # ── Bonus Vf concordant à plusieurs seuils ──
        # Si vf_50 aussi dans la plage du diode (cohérence globale)
        if diode["vf_min"] * 1.2 <= vf_50 <= diode["vf_max"] * 1.5:
            score += 3.0

        scores.append({"diode": diode, "score": round(score, 2)})

    scores.sort(key=lambda x: x["score"], reverse=True)

    best       = scores[0]["diode"]
    best_score = scores[0]["score"]
    sec_score  = scores[1]["score"] if len(scores) > 1 else 0.0
    gap        = best_score - sec_score

    # ══ 7. Confidence calibrée ════════════════════════════════════════════
    conf_base = min(95, max(20, int(best_score * 0.80 + gap * 0.55)))
    # Boost R² (courbe bien exponentielle)
    conf_base = min(97, conf_base + int(r2_exp * 8))
    # Boost si Vf très proche du typique (< 20 mV)
    if abs(vf - best["vf_typ"]) < 0.02:
        conf_base = min(99, conf_base + 5)
    elif abs(vf - best["vf_typ"]) < 0.05:
        conf_base = min(99, conf_base + 2)

    return {
        "type":            best["name"],
        "model":           best["model"],
        "id":              best["id"],
        "color":           best["color"],
        "description":     best["description"],
        "applications":    best["applications"],
        "tech":            best.get("tech", "silicon"),
        "wavelength":      best.get("wavelength", 0),
        "vf":              round(vf, 3),
        "vf_2pct":         round(vf_2, 3),
        "vf_5pct":         round(vf_5, 3),
        "vf_20pct":        round(vf_20, 3),
        "vf_30pct":        round(vf_30, 3),
        "vf_50pct":        round(vf_50, 3),
        "n":               round(estimated_n, 3),
        "Is_nA":           round(estimated_Is * 1e9, 6),
        "Is_display":      (f"{estimated_Is*1e9:.4f} nA"
                            if estimated_Is * 1e9 >= 0.001
                            else f"{estimated_Is*1e12:.4f} pA"),
        "r2_exp":          round(r2_exp, 4),
        "onset_sharpness": round(onset_sharpness, 3),
        "slope_ratio":     round(slope_ratio, 3),
        "confidence":      conf_base,
        "scores":          scores[:8],
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
    global running, data_store, identified_diode
    data_store       = []          # reset data on new sweep
    identified_diode = None
    running          = True
    return jsonify({"status": "running"})

@app.route("/stop")
def stop():
    global running
    running = False
    return jsonify({"status": "stopped"})

@app.route("/reset")
def reset():
    global data_store, identified_diode
    data_store       = []
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
            ["Type identifié",          f"{identified_diode['type']} ({identified_diode['model']})"],
            ["Description",             identified_diode["description"]],
            ["Applications",            identified_diode.get("applications", "—")],
            ["Tension de seuil Vf",     f"{identified_diode['vf']} V"],
            ["Facteur d'idéalité n",    str(identified_diode["n"])],
            ["Courant de saturation Is",identified_diode.get("Is_display", "—")],
            ["R² régression exp.",      str(identified_diode.get("r2_exp", "—"))],
            ["Onset sharpness",         str(identified_diode.get("onset_sharpness", "—"))],
            ["Niveau de confiance",     f"{identified_diode['confidence']} %"],
        ]
        elements += [styled_table(id_rows, [5.5*cm, 10.5*cm]), Spacer(1, 0.4*cm)]

    nb    = len(data_store)
    u_max = max((d['U'] for d in data_store), default=0)
    i_max = max((d['I'] for d in data_store), default=0)

    elements.append(T("Informations de Mesure", s_section))
    info_rows = [
        ["Composant",           identified_diode["type"] if identified_diode else "Diode"],
        ["Points acquis",       str(nb)],
        ["Tension max mesurée", f"{u_max:.3f} V"],
        ["Courant max mesuré",  f"{i_max:.3f} mA"],
    ]
    elements += [styled_table(info_rows, [5.5*cm, 10.5*cm]), Spacer(1, 0.4*cm)]

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
            Vt  = 0.02585
            v_t = [i * max(u_vals, default=3.3) / 300 for i in range(301)]
            i_t = []
            for v in v_t:
                val = Is * (math.exp(v / (n * Vt)) - 1) * 1000
                i_t.append(min(val, i_max * 2))
            ax.plot(v_t, i_t, color=identified_diode.get('color', '#ff9800'),
                    linewidth=2, linestyle='--',
                    label=f"Shockley — {identified_diode['type']}", zorder=2)
            ax.legend(fontsize=9)
        ax.set_xlabel("Tension U (V)", fontsize=10)
        ax.set_ylabel("Courant I (mA)", fontsize=10)
        ax.set_title(
            f"Courbe I = f(U) — {identified_diode['type'] if identified_diode else 'Diode'}",
            fontsize=11, color='#0a2342', fontweight='bold')
        ax.grid(True, color='#e0e8f0', linewidth=0.5)
        ax.set_facecolor('#f8fbff'); fig.patch.set_facecolor('white')
        plt.tight_layout()
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=150, bbox_inches='tight')
        plt.close(); img_buf.seek(0)
        elements += [Image(img_buf, width=15*cm, height=8*cm), Spacer(1, 0.4*cm)]

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
#  HTML DASHBOARD — Version améliorée
#  • Courbe persistante (data APPEND, reset seulement sur START)
#  • Courbe théorique auto-tracée après identification
#  • Panel AI amélioré avec R², Vf multi-seuils, scores détaillés
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
  --accent:#00d4ff;--green:#00e5a0;--orange:#ff9500;--red:#ff4560;--purple:#ce93d8;
  --mono:'Space Mono',monospace;--sans:'DM Sans',sans-serif;--radius:10px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{background:var(--bg);font-family:var(--sans);color:var(--text);min-height:100vh;overflow-x:hidden}
body::before{content:'';position:fixed;inset:0;
  background-image:linear-gradient(rgba(0,212,255,.025)1px,transparent 1px),
    linear-gradient(90deg,rgba(0,212,255,.025)1px,transparent 1px);
  background-size:40px 40px;pointer-events:none;z-index:0}

/* ─── HEADER ─── */
.header{position:relative;z-index:10;display:flex;align-items:center;
  justify-content:space-between;padding:0 28px;height:58px;
  background:rgba(11,18,32,.97);border-bottom:1px solid var(--border);
  backdrop-filter:blur(10px)}
.logo-icon{width:34px;height:34px;border-radius:8px;
  background:linear-gradient(135deg,#00d4ff15,#00d4ff30);
  border:1px solid var(--accent);display:flex;align-items:center;
  justify-content:center;font-size:16px}
.logo-text{font-family:var(--mono);font-size:13px;font-weight:700;
  letter-spacing:2px;color:var(--accent)}
.logo-sub{font-size:10px;color:var(--muted);letter-spacing:1px;margin-top:1px}
.header-right{display:flex;align-items:center;gap:20px}
.header-stat-val{font-family:var(--mono);font-size:15px;font-weight:700}
.header-stat-lbl{font-size:9px;color:var(--muted);letter-spacing:1px;text-transform:uppercase}
.status-pill{display:flex;align-items:center;gap:7px;padding:5px 14px;
  border-radius:20px;background:var(--bg3);border:1px solid var(--border2);
  font-size:11px;color:var(--muted);font-family:var(--mono);min-width:80px;
  justify-content:center}
.status-dot{width:7px;height:7px;border-radius:50%;background:var(--muted);transition:all .3s}
.status-dot.live{background:var(--green);box-shadow:0 0 10px var(--green);animation:pulse 1.2s infinite}
.status-dot.stopped{background:var(--red);box-shadow:0 0 6px var(--red)}
.status-dot.done{background:var(--orange);box-shadow:0 0 6px var(--orange)}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.85)}}

/* ─── LAYOUT ─── */
.layout{position:relative;z-index:1;display:grid;
  grid-template-columns:200px 1fr 300px;gap:12px;padding:12px;
  height:calc(100vh - 58px);overflow:hidden}
.card{background:var(--bg2);border:1px solid var(--border);
  border-radius:var(--radius);padding:16px;overflow:hidden}
.card-header{display:flex;align-items:center;gap:8px;margin-bottom:14px;
  padding-bottom:10px;border-bottom:1px solid var(--border)}
.card-icon{width:26px;height:26px;border-radius:6px;display:flex;align-items:center;
  justify-content:center;font-size:13px;flex-shrink:0}
.card-title{font-size:10px;font-weight:600;letter-spacing:1.5px;
  text-transform:uppercase;color:var(--muted)}

.left-panel{display:flex;flex-direction:column;gap:12px;overflow:hidden}
.center-panel{display:flex;flex-direction:column;gap:12px;overflow:hidden}
.right-panel{display:flex;flex-direction:column;gap:12px;overflow-y:auto;
  scrollbar-width:thin;scrollbar-color:var(--border2) transparent}

/* ─── FORM ELEMENTS ─── */
.field{margin-bottom:10px}
.field label{display:block;font-size:10px;font-weight:500;color:var(--muted);
  letter-spacing:.8px;text-transform:uppercase;margin-bottom:4px}
input[type="number"],select{width:100%;padding:7px 10px;background:var(--bg);
  border:1px solid var(--border2);border-radius:6px;color:var(--text);
  font-family:var(--mono);font-size:12px;transition:border .2s;-moz-appearance:textfield}
input[type="number"]::-webkit-inner-spin-button{-webkit-appearance:none}
input:focus,select:focus{outline:none;border-color:var(--accent);
  box-shadow:0 0 0 3px rgba(0,212,255,.08)}

/* ─── BUTTONS ─── */
.btn{width:100%;padding:9px 12px;border:none;border-radius:7px;
  font-family:var(--mono);font-size:11px;font-weight:700;letter-spacing:1px;
  cursor:pointer;transition:all .2s;display:flex;align-items:center;
  justify-content:center;gap:6px}
.btn:hover{transform:translateY(-1px)}.btn:active{transform:translateY(0)}
.btn+.btn{margin-top:6px}
.btn:disabled{opacity:.45;cursor:not-allowed;transform:none}
.btn-primary{background:linear-gradient(135deg,#00d4ff18,#00d4ff35);
  color:var(--accent);border:1px solid var(--accent)}
.btn-primary:hover:not(:disabled){background:linear-gradient(135deg,#00d4ff28,#00d4ff50);
  box-shadow:0 0 18px rgba(0,212,255,.22)}
.btn-danger{background:linear-gradient(135deg,#ff456018,#ff456030);
  color:var(--red);border:1px solid #ff456055}
.btn-ghost{background:var(--bg3);color:var(--muted);border:1px solid var(--border)}
.btn-ghost:hover{color:var(--text);border-color:var(--border2)}
.btn-identify{background:linear-gradient(135deg,#ff950018,#ff950035);
  color:var(--orange);border:1px solid #ff950055;padding:11px 12px;font-size:12px}
.btn-identify:hover:not(:disabled){background:linear-gradient(135deg,#ff950028,#ff950055);
  box-shadow:0 0 18px rgba(255,149,0,.22)}
.btn-export{background:linear-gradient(135deg,#00e5a018,#00e5a030);
  color:var(--green);border:1px solid #00e5a055}
.btn-pdf{background:linear-gradient(135deg,#ce93d818,#ce93d830);
  color:var(--purple);border:1px solid #ce93d855}

/* ─── LIVE VALUES ─── */
.live-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.live-item{background:var(--bg);border:1px solid var(--border);
  border-radius:8px;padding:10px;text-align:center;transition:border-color .3s}
.live-label{font-size:9px;color:var(--muted);letter-spacing:1px;
  text-transform:uppercase;margin-bottom:4px}
.live-val{font-family:var(--mono);font-size:18px;font-weight:700;line-height:1;
  transition:color .3s}
.live-unit{font-size:10px;color:var(--muted);margin-top:2px}

/* ─── CHART AREA ─── */
.chart-wrap{flex:1;position:relative;min-height:0}
canvas{width:100%!important;height:100%!important}
.axes-panel{background:var(--bg);border:1px solid var(--border);
  border-radius:8px;padding:10px 12px;flex-shrink:0}
.axes-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.axes-grid .field{margin-bottom:0}
.axes-grid label{font-size:9px}
.axes-grid input{padding:5px 8px;font-size:11px}
.axes-btns{display:flex;gap:6px;margin-top:8px}
.axes-btns .btn{flex:1;font-size:10px;padding:5px}

/* ─── TABLE ─── */
.table-wrap{flex:1;overflow-y:auto;min-height:0;
  scrollbar-width:thin;scrollbar-color:var(--border2) transparent}
table{width:100%;border-collapse:collapse;font-size:11px}
thead th{background:var(--bg);padding:6px 8px;color:var(--muted);font-size:9px;
  font-weight:600;text-transform:uppercase;letter-spacing:1px;
  position:sticky;top:0;text-align:center;border-bottom:1px solid var(--border);z-index:1}
tbody td{padding:5px 8px;text-align:center;border-bottom:1px solid var(--border);
  font-family:var(--mono);font-size:11px;color:#8aafc8;transition:background .1s}
tbody tr:hover td{background:var(--bg3);color:var(--text)}

/* ─── IDENTIFICATION PANEL ─── */
.id-result-wrap{display:none;animation:fadeUp .35s ease}
@keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.id-card{background:var(--bg);border-radius:8px;padding:12px;
  border:1px solid var(--border2);transition:border-color .4s,box-shadow .4s}
.id-type{font-family:var(--mono);font-size:14px;font-weight:700;line-height:1.2;
  transition:color .3s}
.id-model{font-size:10px;color:var(--muted);margin-top:2px}
.id-desc{font-size:10px;color:#6a8aaa;margin-top:6px;line-height:1.5;
  padding-top:8px;border-top:1px solid var(--border)}
.id-params{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:8px}
.id-param{background:var(--bg2);border:1px solid var(--border);
  border-radius:6px;padding:7px 5px;text-align:center}
.id-param-name{font-size:8px;color:var(--muted);letter-spacing:.5px;text-transform:uppercase}
.id-param-val{font-family:var(--mono);font-size:11px;font-weight:700;
  margin-top:3px;color:var(--green)}
.conf-row{display:flex;align-items:center;justify-content:space-between;
  margin-top:8px;gap:8px}
.conf-label{font-size:9px;color:var(--muted);white-space:nowrap}
.conf-bar-wrap{flex:1;height:5px;background:var(--border);border-radius:3px;overflow:hidden}
.conf-bar-fill{height:100%;border-radius:3px;transition:width .9s ease,background .5s}
.conf-pct{font-family:var(--mono);font-size:12px;font-weight:700}
.id-apps{margin-top:8px;padding:7px 10px;background:var(--bg2);
  border-radius:6px;border-left:2px solid var(--orange)}
.id-apps-label{font-size:9px;color:var(--orange);text-transform:uppercase;
  letter-spacing:1px;font-weight:600}
.id-apps-text{font-size:10px;color:#8aafc8;margin-top:3px;line-height:1.4}
.vf-badges{display:flex;gap:4px;margin-top:8px;flex-wrap:wrap}
.vf-badge{padding:3px 7px;border-radius:4px;font-family:var(--mono);
  font-size:9px;font-weight:700}
.r2-row{display:flex;align-items:center;gap:8px;margin-top:6px;
  padding:5px 8px;background:var(--bg2);border-radius:5px;
  border:1px solid var(--border)}
.r2-label{font-size:9px;color:var(--muted);flex:1}
.r2-val{font-family:var(--mono);font-size:11px;font-weight:700}
.candidates-wrap{margin-top:8px}
.cand-title{font-size:9px;color:var(--muted);text-transform:uppercase;
  letter-spacing:.5px;margin-bottom:5px}
.cand-item{display:flex;align-items:center;gap:8px;padding:4px 0;
  border-bottom:1px solid var(--border);font-size:10px}
.cand-item:last-child{border-bottom:none}
.cand-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.cand-name{flex:1;color:#6a8aaa}
.cand-bar-wrap{width:50px;height:3px;background:var(--border);border-radius:2px;overflow:hidden}
.cand-bar-fill{height:100%;border-radius:2px;opacity:.65}
.cand-score{font-family:var(--mono);font-size:10px;color:var(--muted);
  width:30px;text-align:right}
/* Score debug */
.score-tbl{width:100%;border-collapse:collapse;font-size:9px}
.score-tbl th{color:var(--muted);font-size:8px;text-transform:uppercase;
  letter-spacing:.5px;padding:3px 5px;border-bottom:1px solid var(--border);
  text-align:left}
.score-tbl td{padding:3px 5px;border-bottom:1px solid var(--border);
  font-family:var(--mono);font-size:9px}

/* ─── SHOCKLEY ─── */
.shockley-row{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.shockley-row .field{margin-bottom:0}
.shockley-info{margin-top:6px;padding:6px 8px;background:var(--bg);
  border-radius:6px;border:1px solid var(--border);
  font-family:var(--mono);font-size:10px;color:var(--muted);text-align:center}

/* ─── NOTIFICATIONS ─── */
.toast{position:fixed;bottom:20px;right:20px;z-index:1000;
  padding:10px 16px;border-radius:8px;font-family:var(--mono);font-size:11px;
  background:var(--bg2);border:1px solid var(--border2);color:var(--text);
  transform:translateY(60px);opacity:0;transition:all .3s;pointer-events:none}
.toast.show{transform:translateY(0);opacity:1}
.toast.success{border-color:var(--green);color:var(--green)}
.toast.error{border-color:var(--red);color:var(--red)}
.toast.info{border-color:var(--accent);color:var(--accent)}

@media(max-width:1200px){
  .layout{grid-template-columns:1fr;height:auto;overflow:visible}
  .chart-wrap{height:380px}
}
</style>
</head>
<body>

<!-- ══════════════════════════ HEADER ══════════════════════════ -->
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

<!-- ══════════════════════════ LAYOUT ══════════════════════════ -->
<div class="layout">

  <!-- ══ LEFT PANEL ══ -->
  <div class="left-panel">
    <!-- Contrôle -->
    <div class="card" style="flex-shrink:0">
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
        <input type="number" value="3.3" id="vmax_ctrl" step="0.1" min="0.5" max="5">
      </div>
      <div class="field">
        <label>Pas (V)</label>
        <input type="number" value="0.02" step="0.01" min="0.005">
      </div>
      <button class="btn btn-primary" id="btn-start" onclick="startSweep()">▶ START SWEEP</button>
      <button class="btn btn-danger"  id="btn-stop"  onclick="stopSweep()">■ STOP</button>
      <button class="btn btn-ghost"   id="btn-reset" onclick="resetData()">↺ RESET</button>
    </div>

    <!-- Live -->
    <div class="card" style="flex-shrink:0">
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

    <!-- Table -->
    <div class="card" style="flex:1;display:flex;flex-direction:column;min-height:0">
      <div class="card-header" style="flex-shrink:0">
        <div class="card-icon" style="background:#9c27b011;border:1px solid #9c27b044">📊</div>
        <div class="card-title">Données</div>
        <div style="margin-left:auto;font-family:var(--mono);font-size:10px;color:var(--muted)" id="pts-count">0 pts</div>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>#</th><th>U (V)</th><th>I (mA)</th></tr></thead>
          <tbody id="table-body"></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ══ CENTER PANEL ══ -->
  <div class="center-panel">
    <div class="card" style="flex:1;display:flex;flex-direction:column;min-height:0">
      <div class="card-header" style="flex-shrink:0">
        <div class="card-icon" style="background:#00d4ff11;border:1px solid #00d4ff44">📈</div>
        <div class="card-title">Courbe I = f(U)</div>
        <!-- Legend théorique -->
        <div id="theory-legend" style="display:none;margin-left:8px;display:flex;
          align-items:center;gap:5px;font-size:9px;color:var(--muted)">
          <span style="display:inline-block;width:18px;height:2px;
            border-top:2px dashed var(--orange);vertical-align:middle"></span>
          <span id="theory-legend-label">Théorique</span>
        </div>
        <div style="margin-left:auto;font-family:var(--mono);font-size:9px;color:var(--muted)">
          Scroll=zoom · Drag=pan
        </div>
      </div>
      <div class="chart-wrap">
        <canvas id="chart"></canvas>
      </div>
      <div class="axes-panel">
        <div class="axes-grid">
          <div class="field"><label>X min</label>
            <input type="number" id="xmin" value="0"   step="0.1" oninput="updateAxes()"></div>
          <div class="field"><label>X max</label>
            <input type="number" id="xmax" value="3.3" step="0.1" oninput="updateAxes()"></div>
          <div class="field"><label>Y min</label>
            <input type="number" id="ymin" value="0"   step="0.05" oninput="updateAxes()"></div>
          <div class="field"><label>Y max</label>
            <input type="number" id="ymax" value="2"   step="0.1"  oninput="updateAxes()"></div>
        </div>
        <div class="axes-btns">
          <button class="btn btn-ghost" onclick="chart.resetZoom()">🔍 Reset Zoom</button>
          <button class="btn btn-ghost" onclick="autoScale()">⊡ Auto Scale</button>
        </div>
      </div>
    </div>
  </div>

  <!-- ══ RIGHT PANEL ══ -->
  <div class="right-panel">

    <!-- Identification IA -->
    <div class="card">
      <div class="card-header">
        <div class="card-icon" style="background:#ff950011;border:1px solid #ff950044">🔬</div>
        <div class="card-title">Identification IA</div>
      </div>
      <button class="btn btn-identify" id="btn-identify" onclick="identifyDiode()">
        🔍 &nbsp;IDENTIFIER LA DIODE / LED
      </button>

      <div class="id-result-wrap" id="id-result">
        <div class="id-card" id="id-card">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px">
            <div>
              <div class="id-type" id="id-type">—</div>
              <div class="id-model" id="id-model">—</div>
            </div>
            <div style="width:11px;height:11px;border-radius:50%;flex-shrink:0;
              margin-top:3px;transition:all .3s" id="id-dot"></div>
          </div>
          <div class="id-desc" id="id-desc">—</div>

          <!-- Vf multi-seuils -->
          <div class="vf-badges" id="vf-badges"></div>

          <div class="id-params">
            <div class="id-param">
              <div class="id-param-name">Vf @10%</div>
              <div class="id-param-val" id="id-vf">—</div>
            </div>
            <div class="id-param">
              <div class="id-param-name">n (idéalité)</div>
              <div class="id-param-val" id="id-n">—</div>
            </div>
            <div class="id-param">
              <div class="id-param-name">Is</div>
              <div class="id-param-val" id="id-is" style="font-size:9px">—</div>
            </div>
          </div>

          <!-- R² -->
          <div class="r2-row">
            <div class="r2-label">R² régression exponentielle</div>
            <div class="r2-val" id="id-r2" style="color:var(--green)">—</div>
          </div>

          <!-- Confidence -->
          <div class="conf-row">
            <div class="conf-label">Confiance</div>
            <div class="conf-bar-wrap">
              <div class="conf-bar-fill" id="conf-fill" style="width:0%"></div>
            </div>
            <div class="conf-pct" id="conf-pct">—</div>
          </div>

          <!-- Applications -->
          <div class="id-apps">
            <div class="id-apps-label">Applications</div>
            <div class="id-apps-text" id="id-apps">—</div>
          </div>

          <!-- Candidats -->
          <div class="candidates-wrap" id="candidates"></div>

          <!-- Debug -->
          <details style="margin-top:8px">
            <summary style="font-size:9px;color:var(--muted);cursor:pointer;
              letter-spacing:.5px;text-transform:uppercase;user-select:none">
              ▸ Détail scoring complet</summary>
            <div id="score-debug" style="margin-top:6px;overflow-x:auto"></div>
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

    <!-- Shockley Manuel -->
    <div class="card">
      <div class="card-header">
        <div class="card-icon" style="background:#ff456011;border:1px solid #ff456044">📉</div>
        <div class="card-title">Shockley Manuel</div>
      </div>
      <div class="shockley-row">
        <div class="field"><label>Is (nA)</label>
          <input type="number" id="Is_val" value="10" step="0.1" oninput="updateShockley()">
        </div>
        <div class="field"><label>n</label>
          <input type="number" id="n_val" value="1.8" step="0.05" oninput="updateShockley()">
        </div>
      </div>
      <div class="field" style="margin-top:6px"><label>Vt (mV)</label>
        <input type="number" id="Vt_val" value="25.85" step="0.1" oninput="updateShockley()">
      </div>
      <div class="shockley-info" id="shockley-info">I = Is·(e^(V/n·Vt) − 1)</div>
    </div>

  </div><!-- /right-panel -->
</div><!-- /layout -->

<!-- Toast notification -->
<div class="toast" id="toast"></div>

<script>
// ══════════════════════════════════════════════
//  GLOBALS
// ══════════════════════════════════════════════
let chart;
let currentIdentified = null;   // résultat dernier identify
let isRunning = false;

// ══════════════════════════════════════════════
//  TOAST
// ══════════════════════════════════════════════
function toast(msg, type='info', duration=2500){
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className   = `toast ${type} show`;
  setTimeout(()=>{ el.className='toast'; }, duration);
}

// ══════════════════════════════════════════════
//  CHART INIT
// ══════════════════════════════════════════════
function initChart(){
  const ctx = document.getElementById('chart').getContext('2d');
  chart = new Chart(ctx, {
    type: 'line',
    data: {
      datasets: [
        {
          label: 'Mesure réelle',
          data: [],
          borderColor: '#00d4ff',
          backgroundColor: 'rgba(0,212,255,.07)',
          pointRadius: 2.5,
          pointHoverRadius: 7,
          pointBackgroundColor: '#00d4ff',
          borderWidth: 2,
          tension: .25,
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
          segment: { borderDash:[6,3] },
          tension: .4,
          order: 3
        },
        {
          label: 'Théorique identifiée',
          data: [],
          borderColor: '#ff9500',
          backgroundColor: 'transparent',
          pointRadius: 0,
          borderWidth: 2.5,
          showLine: true,
          segment: { borderDash:[4,3] },
          tension: .4,
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
      interaction: { mode:'nearest', intersect:false, axis:'x' },
      plugins: {
        legend: {
          labels: {
            color:'#5a7090',
            font:{size:10,family:"'Space Mono',monospace"},
            boxWidth:22,
            padding:14,
            filter: item => !item.hidden
          }
        },
        tooltip: {
          backgroundColor:'#0b1220',
          borderColor:'#1e2d45',
          borderWidth:1,
          titleColor:'#00d4ff',
          bodyColor:'#e2eaf6',
          padding:10,
          titleFont:{family:"'Space Mono',monospace",size:11},
          bodyFont:{family:"'Space Mono',monospace",size:11},
          callbacks: {
            title: i => 'U = '+Number(i[0].parsed.x).toFixed(3)+' V',
            label: i => i.dataset.label+': '+Number(i[0].parsed.y).toFixed(4)+' mA'
          }
        },
        zoom: {
          zoom:{wheel:{enabled:true,speed:.08},pinch:{enabled:true},mode:'xy'},
          pan:{enabled:true,mode:'xy'}
        }
      },
      scales: {
        x:{
          type:'linear', min:0, max:3.3,
          title:{display:true,text:'Tension U (V)',color:'#5a7090',font:{size:10}},
          ticks:{color:'#3a5070',font:{size:9,family:"'Space Mono',monospace"},maxTicksLimit:10},
          grid:{color:'#0f1e30'}
        },
        y:{
          min:0, max:2,
          title:{display:true,text:'Courant I (mA)',color:'#5a7090',font:{size:10}},
          ticks:{color:'#3a5070',font:{size:9,family:"'Space Mono',monospace"}},
          grid:{color:'#0f1e30'}
        }
      }
    }
  });
}

// ══════════════════════════════════════════════
//  AXES / SCALE
// ══════════════════════════════════════════════
function updateAxes(){
  const xmin = +document.getElementById('xmin').value || 0;
  const xmax = +document.getElementById('xmax').value || 3.3;
  const ymin = +document.getElementById('ymin').value || 0;
  const ymax = +document.getElementById('ymax').value || 2;
  if(xmin >= xmax || ymin >= ymax) return;
  chart.options.scales.x.min = xmin;
  chart.options.scales.x.max = xmax;
  chart.options.scales.y.min = ymin;
  chart.options.scales.y.max = ymax;
  chart.update('none');
  updateShockley();
  // Recalc theoretical with new xmax if we have identification
  if(currentIdentified) drawTheoretical(currentIdentified);
}

function autoScale(){
  const d = chart.data.datasets[0].data;
  if(!d.length){ toast('Aucune donnée à mettre à l\'échelle','error'); return; }
  const xs = d.map(p=>p.x), ys = d.map(p=>p.y);
  const xm = Math.max(...xs)*1.06;
  const ym = Math.max(...ys)*1.18;
  document.getElementById('xmin').value = 0;
  document.getElementById('xmax').value = xm.toFixed(2);
  document.getElementById('ymin').value = 0;
  document.getElementById('ymax').value = ym.toFixed(2);
  updateAxes();
}

// ══════════════════════════════════════════════
//  SHOCKLEY CURVE
// ══════════════════════════════════════════════
function shockleyPoints(Is_nA, n, Vt_mV, xmax, steps=500){
  const Is = Is_nA*1e-9, Vt = Vt_mV*1e-3, pts = [];
  for(let i=0; i<=steps; i++){
    const V = (xmax/steps)*i;
    const I = Is*(Math.exp(V/(n*Vt))-1)*1000;
    if(I >= 0 && I < 100000) pts.push({x:V, y:I});
  }
  return pts;
}

function updateShockley(){
  const Is = +document.getElementById('Is_val').value || 10;
  const n  = +document.getElementById('n_val').value  || 1.8;
  const Vt = +document.getElementById('Vt_val').value || 25.85;
  const xmax = +document.getElementById('xmax').value || 3.3;
  chart.data.datasets[1].data = shockleyPoints(Is, n, Vt, xmax);
  chart.update('none');
  document.getElementById('shockley-info').textContent =
    `Is = ${Is} nA  ·  n = ${n}  ·  Vt = ${Vt} mV`;
}

// ══════════════════════════════════════════════
//  THEORETICAL CURVE (après identification)
// ══════════════════════════════════════════════
function drawTheoretical(res){
  const xmax = +document.getElementById('xmax').value || 3.3;
  const pts  = shockleyPoints(res.Is_nA, res.n, 25.85, xmax, 600);
  chart.data.datasets[2].data        = pts;
  chart.data.datasets[2].borderColor = res.color;
  chart.data.datasets[2].label       = `Théorique — ${res.type}`;
  chart.data.datasets[2].hidden      = false;
  chart.update('none');

  // Légende dans l'en-tête
  const leg = document.getElementById('theory-legend');
  const lbl = document.getElementById('theory-legend-label');
  if(leg){
    leg.style.display = 'flex';
    leg.querySelector('span:first-child').style.borderTopColor = res.color;
    lbl.textContent = res.type;
  }
}

// ══════════════════════════════════════════════
//  IDENTIFICATION
// ══════════════════════════════════════════════
function identifyDiode(){
  const btn = document.getElementById('btn-identify');
  btn.innerHTML = '⏳ &nbsp;Analyse en cours...';
  btn.disabled  = true;

  fetch('/identify')
    .then(r => r.json())
    .then(res => {
      btn.innerHTML = '🔍 &nbsp;IDENTIFIER LA DIODE / LED';
      btn.disabled  = false;

      if(res.error){
        toast(res.error === 'not enough data'
          ? '⚠️ Minimum 6 points requis'
          : '⚠️ '+res.error, 'error', 3000);
        return;
      }

      currentIdentified = res;

      // ── Affichage résultat ──
      const panel = document.getElementById('id-result');
      panel.style.display = 'block';
      const card = document.getElementById('id-card');
      card.style.borderColor  = res.color;
      card.style.boxShadow    = `0 0 20px ${res.color}18`;

      document.getElementById('id-dot').style.cssText =
        `background:${res.color};box-shadow:0 0 10px ${res.color};
         width:11px;height:11px;border-radius:50%;flex-shrink:0;margin-top:3px`;

      document.getElementById('id-type').textContent  = res.type;
      document.getElementById('id-type').style.color  = res.color;
      document.getElementById('id-model').textContent = res.model;
      document.getElementById('id-desc').textContent  = res.description;
      document.getElementById('id-vf').textContent    = res.vf + ' V';
      document.getElementById('id-n').textContent     = res.n;
      document.getElementById('id-is').textContent    = res.Is_display;
      document.getElementById('id-apps').textContent  = res.applications;
      document.getElementById('conf-pct').textContent = res.confidence + '%';

      const r2Val = res.r2_exp;
      const r2El  = document.getElementById('id-r2');
      r2El.textContent = r2Val.toFixed(4);
      r2El.style.color = r2Val > 0.95 ? 'var(--green)'
                       : r2Val > 0.85 ? 'var(--orange)' : 'var(--red)';

      const confColor = res.confidence > 75 ? 'var(--green)'
                      : res.confidence > 45 ? 'var(--orange)' : 'var(--red)';
      document.getElementById('conf-pct').style.color = confColor;
      const fill = document.getElementById('conf-fill');
      fill.style.width      = res.confidence + '%';
      fill.style.background = confColor;

      // Vf multi-seuils badges
      document.getElementById('vf-badges').innerHTML =
        `<span class="vf-badge" style="background:#00e5a018;color:var(--green)">@5% ${res.vf_5pct}V</span>
         <span class="vf-badge" style="background:#00d4ff18;color:var(--accent)">@10% ${res.vf}V</span>
         <span class="vf-badge" style="background:#ff970018;color:var(--orange)">@20% ${res.vf_20pct}V</span>
         <span class="vf-badge" style="background:#ff456018;color:var(--red)">@30% ${res.vf_30pct}V</span>`;

      // Candidats
      if(res.scores && res.scores.length > 1){
        const maxSc = Math.max(1, res.scores[0].score);
        let html = '<div class="cand-title">Autres candidats</div>';
        res.scores.slice(1,6).forEach(s => {
          const pct = Math.max(0, s.score / maxSc * 100).toFixed(0);
          html += `<div class="cand-item">
            <div class="cand-dot" style="background:${s.diode.color}"></div>
            <div class="cand-name">${s.diode.name}</div>
            <div class="cand-bar-wrap">
              <div class="cand-bar-fill" style="width:${pct}%;background:${s.diode.color}"></div>
            </div>
            <div class="cand-score">${Math.max(0,s.score).toFixed(1)}</div>
          </div>`;
        });
        document.getElementById('candidates').innerHTML = html;
      }

      // Debug scoring complet
      let dbg = `<table class="score-tbl">
        <tr><th>Type</th><th>Score</th><th>Vf min</th><th>Vf max</th><th>n typ</th><th>Is (nA)</th></tr>`;
      res.scores.forEach(s => {
        const isWinner = s.diode.id === res.id;
        dbg += `<tr>
          <td><span style="display:inline-block;width:6px;height:6px;border-radius:50%;
            background:${s.diode.color};margin-right:4px;vertical-align:middle"></span>
            ${s.diode.name}</td>
          <td style="color:${isWinner?'var(--green)':'var(--muted)'};
            font-weight:${isWinner?'700':'400'}">
            ${Math.max(0,s.score).toFixed(1)}</td>
          <td>${s.diode.vf_min}</td>
          <td>${s.diode.vf_max}</td>
          <td>${s.diode.n_typ}</td>
          <td>${s.diode.Is_nA}</td>
        </tr>`;
      });
      dbg += `</table>
        <div style="margin-top:5px;font-size:9px;color:var(--muted);line-height:1.6">
          onset = ${res.onset_sharpness} &nbsp;·&nbsp;
          slope_ratio = ${res.slope_ratio} &nbsp;·&nbsp;
          R² = ${res.r2_exp}
        </div>`;
      document.getElementById('score-debug').innerHTML = dbg;

      // Sync Shockley manuel
      document.getElementById('Is_val').value = res.Is_nA.toFixed(4);
      document.getElementById('n_val').value  = res.n;
      updateShockley();

      // ━━ COURBE THÉORIQUE AUTO ━━
      drawTheoretical(res);

      toast(`✅ ${res.type} identifiée — confiance ${res.confidence}%`, 'success', 3000);
    })
    .catch(() => {
      btn.innerHTML = '🔍 &nbsp;IDENTIFIER LA DIODE / LED';
      btn.disabled  = false;
      toast('Erreur de connexion au serveur', 'error');
    });
}

// ══════════════════════════════════════════════
//  LIVE DATA FETCH (polling)
// ══════════════════════════════════════════════
function updateDashboard(){
  fetch('/get_data')
    .then(r => r.json())
    .then(data => {
      // Mise à jour courbe
      chart.data.datasets[0].data = data.map(d => ({x:+d.U, y:+d.I}));
      chart.update('none');

      // Mise à jour table (50 derniers points)
      const tbody = document.getElementById('table-body');
      const sl    = data.slice(-80);
      tbody.innerHTML = sl.map((d,i) =>
        `<tr>
          <td>${data.length - sl.length + i + 1}</td>
          <td>${(+d.U).toFixed(3)}</td>
          <td>${(+d.I).toFixed(3)}</td>
        </tr>`
      ).join('');

      // Header + live vals
      const n = data.length;
      document.getElementById('pts-count').textContent = n + ' pts';
      document.getElementById('hdr-pts').innerHTML =
        n + '<span style="font-size:10px;color:var(--muted)"> pts</span>';

      if(n > 0){
        const last = data[n-1];
        const U = (+last.U).toFixed(3), I = (+last.I).toFixed(3);
        document.getElementById('voltage').textContent = U;
        document.getElementById('current').textContent = I;
        document.getElementById('hdr-v').innerHTML =
          U + '<span style="font-size:10px;color:var(--muted)"> V</span>';
        document.getElementById('hdr-i').innerHTML =
          I + '<span style="font-size:10px;color:var(--muted)"> mA</span>';
      }
    })
    .catch(() => {});   // silently ignore network errors
}

// ══════════════════════════════════════════════
//  STATUS
// ══════════════════════════════════════════════
function setStatus(m){
  const dot = document.getElementById('status-dot');
  const txt = document.getElementById('status-text');
  const map = {
    live:    ['live',    'LIVE'],
    stopped: ['stopped', 'STOP'],
    idle:    ['',        'IDLE'],
    reset:   ['',        'IDLE'],
    done:    ['done',    'DONE'],
  };
  const [cls, lbl] = map[m] || ['','IDLE'];
  dot.className = 'status-dot ' + cls;
  txt.textContent = lbl;
}

// ══════════════════════════════════════════════
//  SWEEP CONTROLS
// ══════════════════════════════════════════════
function startSweep(){
  // START efface les données (côté serveur aussi) et relance
  fetch('/start').then(() => {
    isRunning = true;
    setStatus('live');
    // Vider courbe + table localement (le serveur a déjà reset data)
    chart.data.datasets[0].data = [];
    chart.data.datasets[2].data = [];
    chart.data.datasets[2].hidden = true;
    currentIdentified = null;
    document.getElementById('table-body').innerHTML = '';
    document.getElementById('id-result').style.display = 'none';
    document.getElementById('pts-count').textContent = '0 pts';
    document.getElementById('hdr-pts').innerHTML =
      '0<span style="font-size:10px;color:var(--muted)"> pts</span>';
    const leg = document.getElementById('theory-legend');
    if(leg) leg.style.display = 'none';
    chart.update('none');
    toast('▶ Sweep démarré — données réinitialisées', 'info');
  });
}

function stopSweep(){
  fetch('/stop').then(() => {
    isRunning = false;
    setStatus('stopped');
    toast('■ Sweep arrêté', 'info');
  });
}

function resetData(){
  fetch('/stop');
  fetch('/reset').then(() => {
    isRunning = false;
    chart.data.datasets[0].data = [];
    chart.data.datasets[2].data = [];
    chart.data.datasets[2].hidden = true;
    currentIdentified = null;
    document.getElementById('table-body').innerHTML = '';
    document.getElementById('voltage').textContent = '0.000';
    document.getElementById('current').textContent = '0.000';
    document.getElementById('hdr-v').innerHTML =
      '0.000<span style="font-size:10px;color:var(--muted)"> V</span>';
    document.getElementById('hdr-i').innerHTML =
      '0.000<span style="font-size:10px;color:var(--muted)"> mA</span>';
    document.getElementById('hdr-pts').innerHTML =
      '0<span style="font-size:10px;color:var(--muted)"> pts</span>';
    document.getElementById('pts-count').textContent = '0 pts';
    document.getElementById('id-result').style.display = 'none';
    const leg = document.getElementById('theory-legend');
    if(leg) leg.style.display = 'none';
    setStatus('idle');
    chart.update('none');
    toast('↺ Données réinitialisées', 'info');
  });
}

function exportCSV(){ window.location.href='/export_csv'; }

// ══════════════════════════════════════════════
//  BOOT
// ══════════════════════════════════════════════
window.onload = function(){
  initChart();
  updateShockley();
  setInterval(updateDashboard, 800);   // poll toutes les 800 ms
};
</script>
</body>
</html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)