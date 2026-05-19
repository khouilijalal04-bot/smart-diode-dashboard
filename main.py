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
#  BASE DE DONNÉES DES DIODES
# ═══════════════════════════════════════════════
DIODE_DATABASE = [
    {
        "id": "schottky",
        "name": "Schottky",
        "model": "BAT46 / 1N5817 / SS14",
        "color": "#ff9800",
        "description": "Jonction métal-semiconducteur — chute de tension très faible, commutation ultra-rapide.",
        "vf_1mA": 0.18,  "vf_1mA_min": 0.08, "vf_1mA_max": 0.32,
        "vf_5mA": 0.25,  "vf_5mA_min": 0.12, "vf_5mA_max": 0.40,
        "vf_10mA":0.30,  "vf_10mA_min":0.16, "vf_10mA_max":0.45,
        "vf_typ": 0.22, "vf_min": 0.08, "vf_max": 0.38,
        "Is_nA": 120.0, "n_typ": 1.05, "n_min": 0.8, "n_max": 1.3,
        "slope_factor": 3.5, "curvature": 0.85,
        "tech": "diode",
        "applications": "Redressement HF, protection inverse, détecteurs RF, OR-ing d'alimentations.",
    },
    {
        "id": "germanium",
        "name": "Germanium",
        # ✅ FIX 1 : 1N34A ajouté en premier
        "model": "1N34A / 1N60 / OA91 / AA112",
        "color": "#9c27b0",
        "description": "Semiconducteur Ge — Vf très bas, courant de fuite élevé, sensible à la température.",
        # ✅ FIX 2 : plages élargies pour mieux couvrir la 1N34A
        "vf_1mA": 0.20,  "vf_1mA_min": 0.08, "vf_1mA_max": 0.35,
        "vf_5mA": 0.28,  "vf_5mA_min": 0.14, "vf_5mA_max": 0.44,
        "vf_10mA":0.34,  "vf_10mA_min":0.18, "vf_10mA_max":0.52,
        "vf_typ": 0.25, "vf_min": 0.10, "vf_max": 0.45,
        # ✅ FIX 3 : Is plus élevé — Ge fuit beaucoup plus
        "Is_nA": 800.0, "n_typ": 1.0, "n_min": 0.7, "n_max": 1.2,
        "slope_factor": 3.2, "curvature": 0.80,
        "tech": "diode",
        "applications": "Détection AM, démodulation, circuits vintage, radio à galène.",
    },
    {
        "id": "silicon_signal",
        "name": "Silicium signal",
        "model": "1N4148 / 1N914 / BAV99",
        "color": "#2196f3",
        "description": "Diode Si signal rapide — polyvalente, switching ns, très répandue.",
        "vf_1mA": 0.48,  "vf_1mA_min": 0.35, "vf_1mA_max": 0.62,
        "vf_5mA": 0.58,  "vf_5mA_min": 0.44, "vf_5mA_max": 0.72,
        "vf_10mA":0.65,  "vf_10mA_min":0.50, "vf_10mA_max":0.80,
        "vf_typ": 0.52, "vf_min": 0.38, "vf_max": 0.62,
        "Is_nA": 8.0, "n_typ": 1.5, "n_min": 1.2, "n_max": 1.8,
        "slope_factor": 2.8, "curvature": 0.72,
        "tech": "diode",
        "applications": "Switching logique, démodulation, protection ESD, redressement signal.",
    },
    {
        "id": "silicon_rect",
        "name": "Silicium redresseur",
        # ✅ FIX 4 : 1N4007 explicite dans le nom
        "model": "1N4001 / 1N4004 / 1N4007 / 1N5408",
        "color": "#03a9f4",
        "description": "Diode Si redresseur robuste — courant élevé, standard industriel 50/60 Hz.",
        # ✅ FIX 5 : plages ajustées — 1N4007 a Vf légèrement plus élevé
        "vf_1mA": 0.58,  "vf_1mA_min": 0.44, "vf_1mA_max": 0.72,
        "vf_5mA": 0.72,  "vf_5mA_min": 0.58, "vf_5mA_max": 0.86,
        "vf_10mA":0.80,  "vf_10mA_min":0.64, "vf_10mA_max":0.95,
        "vf_typ": 0.72, "vf_min": 0.58, "vf_max": 0.90,
        "Is_nA": 10.0, "n_typ": 1.8, "n_min": 1.5, "n_max": 2.1,
        "slope_factor": 2.2, "curvature": 0.62,
        "tech": "diode",
        "applications": "Redressement 50 Hz, pont de Graetz, alimentation secteur, protection.",
    },
    {
        "id": "zener",
        "name": "Zener",
        "model": "BZX55 / 1N47xx / BZV55",
        "color": "#ff5722",
        "description": "Diode à avalanche — région directe semblable au Si, mais usage en inverse.",
        "vf_1mA": 0.55,  "vf_1mA_min": 0.42, "vf_1mA_max": 0.72,
        "vf_5mA": 0.68,  "vf_5mA_min": 0.52, "vf_5mA_max": 0.84,
        "vf_10mA":0.76,  "vf_10mA_min":0.58, "vf_10mA_max":0.92,
        "vf_typ": 0.65, "vf_min": 0.50, "vf_max": 0.80,
        "Is_nA": 6.0, "n_typ": 1.9, "n_min": 1.6, "n_max": 2.2,
        "slope_factor": 2.0, "curvature": 0.58,
        "tech": "diode",
        "applications": "Régulation tension, référence de tension, écrêtage, protection surtension.",
    },
    {
        "id": "led_ir",
        "name": "LED Infrarouge",
        "model": "TSUS5202 / LD271 / SFH484  (λ≈850–950 nm)",
        "color": "#b71c1c",
        "description": "LED GaAs/GaAlAs — émission infrarouge invisible, Vf bas pour une LED.",
        "vf_1mA": 0.95,  "vf_1mA_min": 0.75, "vf_1mA_max": 1.25,
        "vf_5mA": 1.10,  "vf_5mA_min": 0.88, "vf_5mA_max": 1.40,
        "vf_10mA":1.20,  "vf_10mA_min":0.95, "vf_10mA_max":1.55,
        "vf_typ": 1.10, "vf_min": 0.80, "vf_max": 1.45,
        "Is_nA": 0.002, "n_typ": 1.9, "n_min": 1.7, "n_max": 2.1,
        "slope_factor": 1.5, "curvature": 0.45,
        "tech": "led", "wavelength": 900,
        "applications": "Télécommandes IR, capteurs de proximité, barrières optiques, IRDA.",
    },
    {
        "id": "led_red",
        "name": "LED Rouge",
        "model": "L-934ID / HLMP-4700  (λ≈620–680 nm)",
        "color": "#e53935",
        "description": "LED GaAsP/AlGaInP — rouge classique, Vf modéré.",
        # ✅ FIX 6 : plages élargies LED rouge — variations fabricant importantes
        "vf_1mA": 1.65,  "vf_1mA_min": 1.30, "vf_1mA_max": 2.10,
        "vf_5mA": 1.90,  "vf_5mA_min": 1.55, "vf_5mA_max": 2.30,
        "vf_10mA":2.00,  "vf_10mA_min":1.65, "vf_10mA_max":2.45,
        "vf_typ": 1.85, "vf_min": 1.45, "vf_max": 2.30,
        "Is_nA": 0.0008, "n_typ": 2.0, "n_min": 1.7, "n_max": 2.3,
        "slope_factor": 1.4, "curvature": 0.40,
        "tech": "led", "wavelength": 650,
        "applications": "Signalisation, afficheurs 7 segments, indicateurs de présence.",
    },
    {
        "id": "led_orange",
        "name": "LED Orange",
        "model": "HLMP-EL3C / L-53HD  (λ≈600–620 nm)",
        "color": "#fb8c00",
        "description": "LED GaAsP — orange vif, bonne visibilité diurne.",
        "vf_1mA": 1.85,  "vf_1mA_min": 1.60, "vf_1mA_max": 2.15,
        "vf_5mA": 2.05,  "vf_5mA_min": 1.78, "vf_5mA_max": 2.35,
        "vf_10mA":2.15,  "vf_10mA_min":1.85, "vf_10mA_max":2.48,
        "vf_typ": 2.05, "vf_min": 1.80, "vf_max": 2.35,
        "Is_nA": 0.0003, "n_typ": 2.0, "n_min": 1.8, "n_max": 2.2,
        "slope_factor": 1.4, "curvature": 0.40,
        "tech": "led", "wavelength": 610,
        "applications": "Signalisation routière, afficheurs, panneaux d'information.",
    },
    {
        "id": "led_yellow",
        "name": "LED Jaune",
        "model": "TLHY5100 / L-53YD  (λ≈570–600 nm)",
        "color": "#fdd835",
        "description": "LED GaAsP/GaP — jaune, bon rendement lumineux.",
        "vf_1mA": 1.90,  "vf_1mA_min": 1.68, "vf_1mA_max": 2.20,
        "vf_5mA": 2.10,  "vf_5mA_min": 1.88, "vf_5mA_max": 2.42,
        "vf_10mA":2.20,  "vf_10mA_min":1.96, "vf_10mA_max":2.55,
        "vf_typ": 2.10, "vf_min": 1.90, "vf_max": 2.45,
        "Is_nA": 0.0001, "n_typ": 2.0, "n_min": 1.8, "n_max": 2.2,
        "slope_factor": 1.4, "curvature": 0.40,
        "tech": "led", "wavelength": 585,
        "applications": "Indicateurs, signalisation, balises lumineuses.",
    },
    {
        "id": "led_green_std",
        "name": "LED Verte standard",
        "model": "TLHG5800 / L-53GD  (λ≈525–565 nm, GaP)",
        "color": "#43a047",
        "description": "LED GaP — verte classique, rendement modéré.",
        "vf_1mA": 1.90,  "vf_1mA_min": 1.68, "vf_1mA_max": 2.20,
        "vf_5mA": 2.10,  "vf_5mA_min": 1.88, "vf_5mA_max": 2.42,
        "vf_10mA":2.20,  "vf_10mA_min":1.96, "vf_10mA_max":2.55,
        "vf_typ": 2.10, "vf_min": 1.90, "vf_max": 2.45,
        "Is_nA": 0.00005, "n_typ": 2.0, "n_min": 1.8, "n_max": 2.2,
        "slope_factor": 1.4, "curvature": 0.40,
        "tech": "led", "wavelength": 545,
        "applications": "Indicateurs, afficheurs, signalisation.",
    },
    {
        "id": "led_green_hb",
        "name": "LED Verte haute luminosité",
        "model": "TLHG640 / OVLGG4C7  (λ≈520–530 nm, InGaN)",
        "color": "#00c853",
        "description": "LED InGaN — verte haute luminosité, Vf légèrement plus élevé.",
        "vf_1mA": 2.40,  "vf_1mA_min": 2.15, "vf_1mA_max": 2.70,
        "vf_5mA": 2.60,  "vf_5mA_min": 2.35, "vf_5mA_max": 2.88,
        "vf_10mA":2.70,  "vf_10mA_min":2.44, "vf_10mA_max":3.00,
        "vf_typ": 2.60, "vf_min": 2.35, "vf_max": 2.90,
        "Is_nA": 0.00001, "n_typ": 2.1, "n_min": 1.9, "n_max": 2.3,
        "slope_factor": 1.3, "curvature": 0.38,
        "tech": "led", "wavelength": 525,
        "applications": "Éclairage, rétroéclairage, signalisation haute visibilité.",
    },
    {
        "id": "led_blue",
        "name": "LED Bleue",
        "model": "OVLBB4C7 / NSPB500S  (λ≈450–480 nm)",
        "color": "#1e88e5",
        "description": "LED InGaN — bleue, technologie moderne, Vf élevé.",
        # ✅ FIX 7 : Vf réalistes LED bleue InGaN — corrigés datasheet
        "vf_1mA": 2.85,  "vf_1mA_min": 2.50, "vf_1mA_max": 3.30,
        "vf_5mA": 3.10,  "vf_5mA_min": 2.75, "vf_5mA_max": 3.55,
        "vf_10mA":3.25,  "vf_10mA_min":2.90, "vf_10mA_max":3.70,
        "vf_typ": 3.10, "vf_min": 2.70, "vf_max": 3.60,
        # ✅ FIX 8 : Is beaucoup plus faible pour LED bleue
        "Is_nA": 0.0000005, "n_typ": 2.3, "n_min": 2.0, "n_max": 2.6,
        "slope_factor": 1.2, "curvature": 0.35,
        "tech": "led", "wavelength": 465,
        "applications": "Éclairage, écrans LCD, phares automobiles, indicateurs.",
    },
    {
        "id": "led_white",
        "name": "LED Blanche",
        "model": "NSPW500GS / VLHW4100  (phosphore + InGaN bleu)",
        "color": "#90caf9",
        "description": "LED InGaN bleue + phosphore jaune — lumière blanche, Vf similaire à la LED bleue.",
        "vf_1mA": 2.75,  "vf_1mA_min": 2.50, "vf_1mA_max": 3.25,
        "vf_5mA": 3.00,  "vf_5mA_min": 2.70, "vf_5mA_max": 3.50,
        "vf_10mA":3.15,  "vf_10mA_min":2.82, "vf_10mA_max":3.65,
        "vf_typ": 3.10, "vf_min": 2.80, "vf_max": 3.60,
        "Is_nA": 0.000001, "n_typ": 2.3, "n_min": 2.0, "n_max": 2.6,
        "slope_factor": 1.2, "curvature": 0.35,
        "tech": "led", "wavelength": 0,
        "applications": "Éclairage général, lampes LED, torches, rétroéclairage.",
    },
    {
        "id": "led_uv",
        "name": "LED Ultraviolette",
        "model": "VLMU3100 / TLD1500  (λ≈365–405 nm)",
        "color": "#7b1fa2",
        "description": "LED GaN — ultraviolet, Vf très élevé, usage spécialisé.",
        "vf_1mA": 3.30,  "vf_1mA_min": 3.00, "vf_1mA_max": 3.85,
        "vf_5mA": 3.55,  "vf_5mA_min": 3.22, "vf_5mA_max": 4.10,
        "vf_10mA":3.70,  "vf_10mA_min":3.35, "vf_10mA_max":4.28,
        "vf_typ": 3.60, "vf_min": 3.30, "vf_max": 4.20,
        "Is_nA": 0.0000005, "n_typ": 2.4, "n_min": 2.1, "n_max": 2.7,
        "slope_factor": 1.1, "curvature": 0.32,
        "tech": "led", "wavelength": 385,
        "applications": "Stérilisation UV, détection de fluorescence, durcissement résine, détection billets.",
    },
]


# ═══════════════════════════════════════════════
#  ALGORITHME D'IDENTIFICATION ROBUSTE
# ═══════════════════════════════════════════════
def identify_diode_from_curve(data):
    if len(data) < 6:
        return None

    data_s  = sorted(data, key=lambda d: d['U'])
    u_vals  = [d['U'] for d in data_s]
    i_vals  = [d['I'] for d in data_s]   # en mA
    Vt      = 0.02585                     # V à T = 300 K

    # ══ CORRECTION BASELINE (0 → 0.2 V) ════════════════════════════════
    # Tous les composants ont un offset de courant au démarrage
    # (bruit ADC, courant de fuite, offset MCP4725).
    # On calcule la moyenne des points entre 0 et 0.2V
    # et on la soustrait à toute la courbe.
    baseline_pts = [i for u, i in zip(u_vals, i_vals) if 0.0 <= u <= 0.2]
    if len(baseline_pts) >= 2:
        baseline = sum(baseline_pts) / len(baseline_pts)
    elif len(baseline_pts) == 1:
        baseline = baseline_pts[0]
    else:
        baseline = 0.0
    # Soustraction et clamp à 0 (le courant ne peut pas être négatif)
    i_vals = [max(0.0, i - baseline) for i in i_vals]
    # ════════════════════════════════════════════════════════════════════

    i_max = max(i_vals)
    if i_max <= 0:
        return None

    # ══ 1. Vf à seuils absolus (mA) ════════════════════════════════════
    def interp_vf_abs(threshold_mA):
        for k in range(len(u_vals)):
            if i_vals[k] >= threshold_mA:
                if k > 0 and (i_vals[k] - i_vals[k - 1]) > 1e-9:
                    dv = u_vals[k] - u_vals[k - 1]
                    di = i_vals[k] - i_vals[k - 1]
                    return u_vals[k - 1] + (threshold_mA - i_vals[k - 1]) * dv / di
                return u_vals[k]
        return None

    vf_1mA  = interp_vf_abs(1.0)
    vf_5mA  = interp_vf_abs(5.0)
    vf_10mA = interp_vf_abs(10.0)

    def interp_vf_pct(pct):
        target = i_max * pct
        for k in range(len(u_vals)):
            if i_vals[k] >= target:
                if k > 0 and (i_vals[k] - i_vals[k - 1]) > 1e-9:
                    dv = u_vals[k] - u_vals[k - 1]
                    di = i_vals[k] - i_vals[k - 1]
                    return u_vals[k - 1] + (target - i_vals[k - 1]) * dv / di
                return u_vals[k]
        return u_vals[-1]

    vf_5pct  = max(0.0, interp_vf_pct(0.05))
    vf_10pct = max(0.0, interp_vf_pct(0.10))
    vf_20pct = max(0.0, interp_vf_pct(0.20))
    vf_30pct = max(0.0, interp_vf_pct(0.30))

    # ══ 2. Régression exponentielle (3 % à 70 % de I_max) ══════════════
    pts_exp = [
        (u, i * 1e-3)
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
            sv    = sum(v_arr)
            sl    = sum(ln_i)
            svl   = sum(v * l for v, l in zip(v_arr, ln_i))
            sv2   = sum(v * v for v in v_arr)
            denom = N * sv2 - sv ** 2
            if abs(denom) > 1e-12:
                slope     = (N * svl - sv * sl) / denom
                intercept = (sl - slope * sv) / N
                n_calc    = 1.0 / (slope * Vt) if slope > 0 else 1.8
                if 0.5 < n_calc < 3.5:
                    estimated_n = round(n_calc, 4)
                Is_calc = math.exp(intercept)
                if 1e-20 < Is_calc < 1e-2:
                    estimated_Is = Is_calc
                mean_li = sl / N
                ss_tot  = sum((l - mean_li) ** 2 for l in ln_i)
                ss_res  = sum((l - (slope * v + intercept)) ** 2
                              for v, l in zip(v_arr, ln_i))
                r2_exp  = max(0.0, 1.0 - ss_res / max(ss_tot, 1e-12))
        except Exception:
            pass

    # ══ 3. Onset sharpness ══════════════════════════════════════════════
    onset_sharpness = (vf_30pct - vf_5pct) / max(vf_5pct, 0.01)

    # ══ 4. Pente normalisée max ══════════════════════════════════════════
    max_slope_norm = 0.0
    for k in range(1, len(u_vals)):
        dv = u_vals[k] - u_vals[k - 1]
        di = i_vals[k] - i_vals[k - 1]
        if dv > 1e-4:
            sl_loc = (di / dv) / max(i_max, 0.001)
            if sl_loc > max_slope_norm:
                max_slope_norm = sl_loc

    # ══ 5. SCORING multi-critères ═══════════════════════════════════════
    scores = []
    for diode in DIODE_DATABASE:
        score = 0.0
        veto  = False

        # ── Critère Vf à 1 mA (40 pts) ──
        if vf_1mA is not None:
            lo, hi, typ = diode["vf_1mA_min"], diode["vf_1mA_max"], diode["vf_1mA"]
            if lo <= vf_1mA <= hi:
                dist = abs(vf_1mA - typ) / max((hi - lo) / 2.0, 0.01)
                score += 40.0 * max(0.0, 1.0 - dist ** 1.5)
            else:
                gap = min(abs(vf_1mA - lo), abs(vf_1mA - hi))
                score -= gap * 80.0
                if gap > 0.30:
                    veto = True

        # ── Critère Vf à 5 mA (20 pts) ──
        if vf_5mA is not None:
            lo, hi, typ = diode["vf_5mA_min"], diode["vf_5mA_max"], diode["vf_5mA"]
            if lo <= vf_5mA <= hi:
                dist = abs(vf_5mA - typ) / max((hi - lo) / 2.0, 0.01)
                score += 20.0 * max(0.0, 1.0 - dist ** 1.5)
            else:
                gap = min(abs(vf_5mA - lo), abs(vf_5mA - hi))
                score -= gap * 40.0

        # ── Critère Vf à 10 mA (15 pts) ──
        if vf_10mA is not None:
            lo, hi, typ = diode["vf_10mA_min"], diode["vf_10mA_max"], diode["vf_10mA"]
            if lo <= vf_10mA <= hi:
                dist = abs(vf_10mA - typ) / max((hi - lo) / 2.0, 0.01)
                score += 15.0 * max(0.0, 1.0 - dist ** 1.5)
            else:
                gap = min(abs(vf_10mA - lo), abs(vf_10mA - hi))
                score -= gap * 30.0

        # ── Critère n idéalité (15 pts) ──
        n_typ = diode["n_typ"]
        n_min = diode["n_min"]
        n_max = diode["n_max"]
        if n_min <= estimated_n <= n_max:
            n_dist = abs(estimated_n - n_typ) / max((n_max - n_min) / 2.0, 0.01)
            score += 15.0 * max(0.0, 1.0 - n_dist)
        else:
            score -= abs(estimated_n - n_typ) * 12.0

        # ── Critère Is (8 pts) ──
        try:
            log_is_meas = math.log10(max(estimated_Is, 1e-22))
            log_is_ref  = math.log10(diode["Is_nA"] * 1e-9)
            is_diff     = abs(log_is_meas - log_is_ref)
            score      += max(0.0, 8.0 - is_diff * 3.0)
        except Exception:
            pass

        # ── Onset sharpness (5 pts) ──
        ref_sharp  = diode.get("slope_factor", 2.0)
        sharp_diff = abs(onset_sharpness - ref_sharp)
        score     += max(0.0, 5.0 - sharp_diff * 2.5)

        # ── Bonus cohérence physique ──
        if r2_exp > 0.92 and n_min <= estimated_n <= n_max:
            score += 5.0 * r2_exp

        # ── Bonus Vf 5 mA dans la plage ──
        if vf_5mA is not None and diode["vf_5mA_min"] <= vf_5mA <= diode["vf_5mA_max"]:
            score += 2.0

        # ── Veto absolu ──
        if veto:
            score = min(score, -10.0)

        scores.append({"diode": diode, "score": round(score, 2)})

    scores.sort(key=lambda x: x["score"], reverse=True)

    best       = scores[0]["diode"]
    best_score = scores[0]["score"]
    sec_score  = scores[1]["score"] if len(scores) > 1 else 0.0
    gap        = best_score - sec_score

    # ══ 6. Calibration de la confiance ══════════════════════════════════
    conf = min(95, max(15, int(best_score * 0.75 + gap * 0.50)))
    conf = min(97, conf + int(r2_exp * 8))
    if vf_1mA is not None:
        if abs(vf_1mA - best["vf_1mA"]) < 0.02:
            conf = min(99, conf + 6)
        elif abs(vf_1mA - best["vf_1mA"]) < 0.06:
            conf = min(99, conf + 3)

    # ══ 7. Votes méthodes ═══════════════════════════════════════════════
    method_votes = []
    if vf_1mA is not None:
        ok = best["vf_1mA_min"] <= vf_1mA <= best["vf_1mA_max"]
        method_votes.append({"label": "Vf@1mA", "result": f"{vf_1mA:.3f}V", "ok": ok})
    if vf_5mA is not None:
        ok = best["vf_5mA_min"] <= vf_5mA <= best["vf_5mA_max"]
        method_votes.append({"label": "Vf@5mA", "result": f"{vf_5mA:.3f}V", "ok": ok})
    if vf_10mA is not None:
        ok = best["vf_10mA_min"] <= vf_10mA <= best["vf_10mA_max"]
        method_votes.append({"label": "Vf@10mA", "result": f"{vf_10mA:.3f}V", "ok": ok})
    n_ok = best["n_min"] <= estimated_n <= best["n_max"]
    method_votes.append({"label": f"n={estimated_n:.3f}", "result": best["name"], "ok": n_ok})
    # Badge baseline pour debug
    method_votes.append({"label": "baseline", "result": f"{baseline:.4f}mA", "ok": True})

    if estimated_Is * 1e9 >= 0.001:
        is_display = f"{estimated_Is * 1e9:.4f} nA"
    else:
        is_display = f"{estimated_Is * 1e12:.4f} pA"

    return {
        "type":            best["name"],
        "model":           best["model"],
        "id":              best["id"],
        "color":           best["color"],
        "description":     best["description"],
        "applications":    best.get("applications", "—"),
        "tech":            best.get("tech", "diode"),
        "wavelength":      best.get("wavelength", 0),
        "vf_1mA":          round(vf_1mA, 3)  if vf_1mA  is not None else None,
        "vf_5mA":          round(vf_5mA, 3)  if vf_5mA  is not None else None,
        "vf_10mA":         round(vf_10mA, 3) if vf_10mA is not None else None,
        "vf":              round(vf_10pct, 3),
        "vf_5pct":         round(vf_5pct,  3),
        "vf_10pct":        round(vf_10pct, 3),
        "vf_20pct":        round(vf_20pct, 3),
        "vf_30pct":        round(vf_30pct, 3),
        "n":               round(estimated_n,  3),
        "Is_nA":           round(estimated_Is * 1e9, 6),
        "Is_display":      is_display,
        "r2_exp":          round(r2_exp, 4),
        "onset_sharpness": round(onset_sharpness, 3),
        "confidence":      conf,
        "baseline_mA":     round(baseline, 4),   # ← nouveau
        "scores":          scores[:8],
        "method_votes":    method_votes,
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
    data_store       = []
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
            ('FONTNAME',       (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME',       (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE',       (0, 0), (-1, -1), 10),
            ('TEXTCOLOR',      (0, 0), (0, -1), colors.HexColor('#0a2342')),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.HexColor('#eef4fb'), colors.white]),
            ('GRID',           (0, 0), (-1, -1), 0.5, colors.HexColor('#b0c8e0')),
            ('TOPPADDING',     (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING',  (0, 0), (-1, -1), 7),
            ('LEFTPADDING',    (0, 0), (-1, -1), 10),
        ]))
        return t

    if identified_diode:
        elements.append(T("Identification du Composant", s_section))
        vf1  = identified_diode.get("vf_1mA")
        vf5  = identified_diode.get("vf_5mA")
        vf10 = identified_diode.get("vf_10mA")
        id_rows = [
            ["Type identifié",           f"{identified_diode['type']} ({identified_diode['model']})"],
            ["Description",              identified_diode["description"]],
            ["Applications",             identified_diode.get("applications", "—")],
            ["Vf à 1 mA",               f"{vf1} V"  if vf1  is not None else "—"],
            ["Vf à 5 mA",               f"{vf5} V"  if vf5  is not None else "—"],
            ["Vf à 10 mA",              f"{vf10} V" if vf10 is not None else "—"],
            ["Facteur d'idéalité n",     str(identified_diode["n"])],
            ["Courant de saturation Is", identified_diode.get("Is_display", "—")],
            ["R² régression exp.",       str(identified_diode.get("r2_exp", "—"))],
            ["Baseline soustraite",      f"{identified_diode.get('baseline_mA', 0):.4f} mA"],
            ["Niveau de confiance",      f"{identified_diode['confidence']} %"],
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
        i_vals_raw = [d['I'] for d in data_store]
        fig, ax = plt.subplots(figsize=(7.5, 4))
        ax.plot(u_vals, i_vals_raw, color='#1e6ab0', linewidth=2.5,
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
        ax.set_facecolor('#f8fbff')
        fig.patch.set_facecolor('white')
        plt.tight_layout()
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        img_buf.seek(0)
        elements += [Image(img_buf, width=15*cm, height=8*cm), Spacer(1, 0.4*cm)]

    elements.append(HR())
    elements.append(T("Tableau des Données Acquises", s_section))
    tdata = [["#", "Tension U (V)", "Courant I (mA)"]] + [
        [str(i + 1), f"{float(d['U']):.3f}", f"{float(d['I']):.3f}"]
        for i, d in enumerate(data_store)
    ]
    t = Table(tdata, colWidths=[2*cm, 7*cm, 7*cm], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',     (0, 0), (-1, 0),  colors.HexColor('#0a2342')),
        ('TEXTCOLOR',      (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',       (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',       (0, 0), (-1, 0),  11),
        ('ALIGN',          (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING',     (0, 0), (-1, 0),  8),
        ('BOTTOMPADDING',  (0, 0), (-1, 0),  8),
        ('FONTNAME',       (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',       (0, 1), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#eef4fb'), colors.white]),
        ('TEXTCOLOR',      (0, 1), (-1, -1), colors.HexColor('#0a2342')),
        ('TOPPADDING',     (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING',  (0, 1), (-1, -1), 5),
        ('GRID',           (0, 0), (-1, -1), 0.5, colors.HexColor('#b0c8e0')),
        ('BOX',            (0, 0), (-1, -1), 1.5, colors.HexColor('#0a2342')),
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
#  DASHBOARD HTML
# ═══════════════════════════════════════════════
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Smart Diode Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.19.0/dist/tabler-icons.min.css">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/hammerjs@2.0.8/hammer.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>
<style>
:root{
  --bg:#f4f6f9;--surface:#ffffff;--surface2:#f8f9fc;
  --border:#e2e8f0;--border2:#cbd5e1;
  --text:#1e293b;--muted:#64748b;--hint:#94a3b8;
  --blue:#185FA5;--blue-lt:#E6F1FB;--blue-dk:#0C447C;
  --green:#3B6D11;--green-lt:#EAF3DE;--green-dk:#27500A;
  --red:#A32D2D;--red-lt:#FCEBEB;--red-dk:#791F1F;
  --amber:#854F0B;--amber-lt:#FAEEDA;--amber-dk:#633806;
  --purple:#534AB7;--purple-lt:#EEEDFE;
  --mono:'JetBrains Mono',monospace;--sans:'Inter',sans-serif;
  --radius:10px;--radius-sm:6px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:var(--bg);font-family:var(--sans);color:var(--text);overflow-x:hidden}
.header{
  height:54px;display:flex;align-items:center;justify-content:space-between;
  padding:0 20px;background:var(--surface);border-bottom:1px solid var(--border);
  position:sticky;top:0;z-index:100;
}
.logo{display:flex;align-items:center;gap:10px}
.logo-icon{width:32px;height:32px;border-radius:8px;background:var(--blue-lt);
  border:1px solid var(--blue);display:flex;align-items:center;justify-content:center;
  color:var(--blue);font-size:16px}
.logo-name{font-size:14px;font-weight:600;color:var(--text);letter-spacing:0.3px}
.logo-sub{font-size:10px;color:var(--muted);margin-top:1px}
.hdr-stats{display:flex;align-items:center;gap:20px}
.hdr-stat{text-align:right}
.hdr-val{font-family:var(--mono);font-size:15px;font-weight:600}
.hdr-lbl{font-size:9px;color:var(--muted);letter-spacing:0.8px;text-transform:uppercase}
.status-pill{display:flex;align-items:center;gap:6px;padding:5px 12px;border-radius:20px;
  background:var(--surface2);border:1px solid var(--border2);font-size:11px;
  font-weight:500;color:var(--muted);min-width:78px;justify-content:center}
.sdot{width:7px;height:7px;border-radius:50%;background:var(--hint);transition:all .3s}
.sdot.live{background:var(--green);animation:pulse 1.2s infinite}
.sdot.stop{background:var(--red)}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.35;transform:scale(.8)}}
.layout{display:grid;grid-template-columns:210px 1fr 270px;gap:10px;
  padding:10px;min-height:calc(100vh - 54px)}
.col{display:flex;flex-direction:column;gap:10px}
.panel{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius);padding:14px}
.panel-hd{display:flex;align-items:center;gap:7px;margin-bottom:12px;
  padding-bottom:10px;border-bottom:1px solid var(--border)}
.panel-hd i{font-size:16px;color:var(--blue)}
.panel-title{font-size:10px;font-weight:600;letter-spacing:1.2px;
  text-transform:uppercase;color:var(--muted)}
label{display:block;font-size:10px;font-weight:500;color:var(--muted);
  letter-spacing:.5px;text-transform:uppercase;margin-bottom:3px;margin-top:8px}
label:first-of-type{margin-top:0}
input[type="number"],select{
  width:100%;padding:7px 10px;background:var(--surface2);
  border:1px solid var(--border2);border-radius:var(--radius-sm);
  color:var(--text);font-family:var(--mono);font-size:12px;
  transition:border .15s;-moz-appearance:textfield;outline:none}
input[type="number"]::-webkit-inner-spin-button{-webkit-appearance:none}
input:focus,select:focus{border-color:var(--blue);box-shadow:0 0 0 3px rgba(24,95,165,.10)}
.btn{
  width:100%;padding:8px 12px;border-radius:var(--radius-sm);font-family:var(--sans);
  font-size:12px;font-weight:500;cursor:pointer;transition:all .15s;
  display:flex;align-items:center;justify-content:center;gap:6px;
  border:1px solid var(--border2);background:var(--surface);color:var(--text)
}
.btn:hover{background:var(--surface2);border-color:var(--blue)}
.btn:active{transform:scale(.98)}
.btn:disabled{opacity:.45;cursor:not-allowed;transform:none}
.btn+.btn{margin-top:6px}
.btn i{font-size:15px}
.btn-start{background:var(--green-lt);color:var(--green-dk);border-color:#C0DD97}
.btn-start:hover{background:#C0DD97;border-color:var(--green)}
.btn-stop{background:var(--red-lt);color:var(--red-dk);border-color:#F7C1C1}
.btn-stop:hover{background:#F7C1C1;border-color:var(--red)}
.btn-id{background:var(--blue-lt);color:var(--blue-dk);border-color:#B5D4F4;padding:10px 12px;font-size:13px}
.btn-id:hover:not(:disabled){background:#B5D4F4;border-color:var(--blue)}
.live-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.live-box{background:var(--surface2);border:1px solid var(--border);
  border-radius:var(--radius-sm);padding:8px;text-align:center}
.live-val{font-family:var(--mono);font-size:19px;font-weight:600;line-height:1;transition:color .3s}
.live-lbl{font-size:9px;color:var(--muted);margin-top:2px;letter-spacing:.5px;text-transform:uppercase}
.chart-wrap{flex:1;position:relative;min-height:300px}
canvas{width:100%!important;height:100%!important}
.axes-grid{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:6px;margin-top:8px}
.axes-grid label{font-size:9px;margin-top:0}
.axes-grid input{font-size:11px;padding:5px 7px}
.axes-btns{display:flex;gap:6px;margin-top:6px}
.axes-btns .btn{flex:1;font-size:10px;padding:5px 6px}
.tbl-wrap{flex:1;overflow-y:auto;max-height:170px;border:1px solid var(--border);
  border-radius:var(--radius-sm);scrollbar-width:thin;scrollbar-color:var(--border2) transparent}
table{width:100%;border-collapse:collapse}
thead th{background:var(--surface2);padding:5px 8px;color:var(--muted);font-size:9px;
  font-weight:600;text-transform:uppercase;letter-spacing:.8px;
  position:sticky;top:0;text-align:center;border-bottom:1px solid var(--border);z-index:1}
tbody td{padding:4px 8px;text-align:center;border-bottom:1px solid var(--border);
  font-family:var(--mono);font-size:11px;color:var(--muted)}
tbody tr:hover td{background:var(--surface2);color:var(--text)}
.right-col{overflow-y:auto;max-height:calc(100vh - 74px);
  scrollbar-width:thin;scrollbar-color:var(--border2) transparent}
.id-card{border:1px solid var(--border);border-radius:var(--radius-sm);
  padding:12px;margin-top:12px;transition:border-color .35s,box-shadow .35s;
  animation:fadeUp .3s ease}
@keyframes fadeUp{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
.id-type{font-size:16px;font-weight:600;line-height:1.2}
.id-model{font-size:10px;color:var(--muted);margin-top:2px}
.id-desc{font-size:11px;color:var(--muted);margin-top:8px;line-height:1.55;
  padding-top:8px;border-top:1px solid var(--border)}
.params-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-top:8px}
.param{background:var(--surface2);border:1px solid var(--border);
  border-radius:var(--radius-sm);padding:6px 4px;text-align:center}
.param-name{font-size:8px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.param-val{font-family:var(--mono);font-size:12px;font-weight:600;margin-top:3px;color:var(--blue)}
.vf-seuils{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin-top:8px}
.vf-item{background:var(--surface2);border:1px solid var(--border);
  border-radius:var(--radius-sm);padding:5px;text-align:center}
.vf-item-lbl{font-size:8px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px}
.vf-item-val{font-family:var(--mono);font-size:11px;font-weight:600;margin-top:2px}
.conf-row{display:flex;align-items:center;gap:8px;margin-top:8px}
.conf-lbl{font-size:10px;color:var(--muted);white-space:nowrap}
.conf-bar{flex:1;height:5px;background:var(--border);border-radius:3px;overflow:hidden}
.conf-fill{height:100%;border-radius:3px;transition:width .8s ease}
.conf-pct{font-family:var(--mono);font-size:13px;font-weight:600;min-width:38px;text-align:right}
.apps-box{margin-top:8px;padding:8px 10px;background:var(--green-lt);
  border-radius:var(--radius-sm);border-left:2px solid var(--green)}
.apps-lbl{font-size:9px;color:var(--green);font-weight:600;text-transform:uppercase;letter-spacing:.8px}
.apps-txt{font-size:10px;color:var(--green-dk);margin-top:2px;line-height:1.5}
.baseline-info{display:flex;align-items:center;gap:6px;margin-top:6px;
  padding:5px 8px;background:var(--purple-lt);border:1px solid #C5C1F5;
  border-radius:var(--radius-sm);font-size:10px;color:var(--purple)}
.baseline-info i{font-size:13px}
.votes{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}
.vote-badge{font-size:9px;padding:2px 7px;border-radius:4px;font-weight:600;font-family:var(--mono)}
.vote-ok{background:var(--green-lt);color:var(--green-dk)}
.vote-warn{background:var(--amber-lt);color:var(--amber-dk)}
.cands{margin-top:8px;padding-top:8px;border-top:1px solid var(--border)}
.cand-title{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}
.cand-item{display:flex;align-items:center;gap:6px;padding:3px 0;
  border-bottom:1px solid var(--border);font-size:10px}
.cand-item:last-child{border:none}
.cand-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.cand-name{flex:1;color:var(--muted)}
.cand-bar{width:50px;height:3px;background:var(--border);border-radius:2px;overflow:hidden}
.cand-fill{height:100%;border-radius:2px}
.cand-score{font-family:var(--mono);font-size:10px;color:var(--muted);width:30px;text-align:right}
.hint{font-size:11px;color:var(--muted);text-align:center;margin-top:8px}
.shockley-row{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.shockley-row label{margin-top:0}
.shockley-eq{margin-top:6px;padding:5px 8px;background:var(--surface2);border:1px solid var(--border);
  border-radius:var(--radius-sm);font-family:var(--mono);font-size:10px;color:var(--muted);text-align:center}
.export-row{display:flex;gap:6px}
.export-row .btn{flex:1;font-size:11px;padding:7px}
.curve-btns{display:flex;gap:6px;flex-wrap:wrap;margin-left:auto}
.curve-btn{font-size:10px;padding:3px 8px;border-radius:var(--radius-sm);
  border:1px solid var(--border2);background:var(--surface);color:var(--muted);
  cursor:pointer;display:flex;align-items:center;gap:4px;transition:all .15s;font-family:var(--sans)}
.curve-btn:hover{background:var(--surface2);color:var(--text);border-color:var(--blue)}
.curve-btn i{font-size:13px}
.toast{position:fixed;bottom:18px;right:18px;z-index:999;
  padding:9px 16px;border-radius:var(--radius-sm);font-size:12px;font-weight:500;
  background:var(--surface);border:1px solid var(--border2);color:var(--text);
  transform:translateY(60px);opacity:0;transition:all .25s;pointer-events:none;box-shadow:0 4px 16px rgba(0,0,0,.08)}
.toast.show{transform:translateY(0);opacity:1}
.toast.ok{border-color:#C0DD97;color:var(--green-dk)}
.toast.err{border-color:#F7C1C1;color:var(--red-dk)}
.toast.info{border-color:#B5D4F4;color:var(--blue-dk)}
</style>
</head>
<body>
<header class="header">
  <div class="logo">
    <div class="logo-icon"><i class="ti ti-bolt"></i></div>
    <div>
      <div class="logo-name">Smart Diode Dashboard</div>
      <div class="logo-sub">ESP32 · MCP4725 · IA Identification</div>
    </div>
  </div>
  <div class="hdr-stats">
    <div class="hdr-stat">
      <div class="hdr-val" id="hv" style="color:var(--blue)">0.000<span style="font-size:10px;color:var(--muted)"> V</span></div>
      <div class="hdr-lbl">Tension</div>
    </div>
    <div class="hdr-stat">
      <div class="hdr-val" id="hi" style="color:var(--green)">0.000<span style="font-size:10px;color:var(--muted)"> mA</span></div>
      <div class="hdr-lbl">Courant</div>
    </div>
    <div class="hdr-stat">
      <div class="hdr-val" id="hpts" style="color:var(--muted)">0<span style="font-size:10px;color:var(--muted)"> pts</span></div>
      <div class="hdr-lbl">Points</div>
    </div>
    <div class="status-pill">
      <div class="sdot" id="sdot"></div>
      <span id="stxt">Idle</span>
    </div>
  </div>
</header>

<div class="layout">
  <!-- ══ GAUCHE ══ -->
  <div class="col">
    <div class="panel">
      <div class="panel-hd">
        <i class="ti ti-adjustments-horizontal"></i>
        <span class="panel-title">Contrôle</span>
      </div>
      <label>Composant</label>
      <select><option>Diode / LED</option></select>
      <label>V max (V)</label>
      <input type="number" id="vmax" value="3.3" step="0.1" min="0.5" max="5">
      <label>Pas (V)</label>
      <input type="number" id="vstep" value="0.02" step="0.01" min="0.005">
      <div style="margin-top:12px">
        <button class="btn btn-start" onclick="startSweep()"><i class="ti ti-player-play"></i> Start sweep</button>
        <button class="btn btn-stop"  onclick="stopSweep()"><i class="ti ti-player-stop"></i> Stop</button>
        <button class="btn"           onclick="resetAll()"><i class="ti ti-refresh"></i> Reset tout</button>
      </div>
    </div>
    <div class="panel">
      <div class="panel-hd">
        <i class="ti ti-bolt"></i>
        <span class="panel-title">Mesure live</span>
      </div>
      <div class="live-grid">
        <div class="live-box">
          <div class="live-val" id="lv" style="color:var(--blue)">0.000</div>
          <div class="live-lbl">Volts</div>
        </div>
        <div class="live-box">
          <div class="live-val" id="li" style="color:var(--green)">0.000</div>
          <div class="live-lbl">mA</div>
        </div>
      </div>
    </div>
    <div class="panel" style="flex:1;display:flex;flex-direction:column;min-height:0">
      <div class="panel-hd">
        <i class="ti ti-table"></i>
        <span class="panel-title">Données</span>
        <span id="pts-lbl" style="margin-left:auto;font-family:var(--mono);font-size:10px;color:var(--muted)">0 pts</span>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead><tr><th>#</th><th>U (V)</th><th>I (mA)</th></tr></thead>
          <tbody id="tbody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ══ CENTRE ══ -->
  <div class="col">
    <div class="panel" style="flex:1;display:flex;flex-direction:column">
      <div class="panel-hd">
        <i class="ti ti-chart-line"></i>
        <span class="panel-title">Courbe I = f(U)</span>
        <div class="curve-btns">
          <button class="curve-btn" onclick="clearMeasured()"><i class="ti ti-eraser"></i> Effacer mesure</button>
          <button class="curve-btn" onclick="clearTheory()"><i class="ti ti-line-dashed"></i> Effacer théorique</button>
        </div>
        <span style="font-size:9px;color:var(--hint);margin-left:6px">Scroll = zoom · Drag = pan</span>
      </div>
      <div class="chart-wrap">
        <canvas id="chart"></canvas>
      </div>
      <div>
        <div class="axes-grid">
          <div><label>X min</label><input type="number" id="xmin" value="0"   step="0.1"  oninput="applyAxes()"></div>
          <div><label>X max</label><input type="number" id="xmax" value="3.3" step="0.1"  oninput="applyAxes()"></div>
          <div><label>Y min</label><input type="number" id="ymin" value="0"   step="0.05" oninput="applyAxes()"></div>
          <div><label>Y max</label><input type="number" id="ymax" value="2"   step="0.1"  oninput="applyAxes()"></div>
        </div>
        <div class="axes-btns">
          <button class="btn" onclick="chart.resetZoom()"><i class="ti ti-zoom-reset"></i> Reset zoom</button>
          <button class="btn" onclick="autoScale()"><i class="ti ti-arrows-maximize"></i> Auto scale</button>
        </div>
      </div>
    </div>
    <div class="panel">
      <div class="panel-hd">
        <i class="ti ti-math-function"></i>
        <span class="panel-title">Shockley manuel</span>
      </div>
      <div class="shockley-row">
        <div><label>Is (nA)</label><input type="number" id="Is_v" value="10" step="0.1" oninput="updateShockley()"></div>
        <div><label>n</label><input type="number" id="n_v" value="1.8" step="0.05" oninput="updateShockley()"></div>
      </div>
      <label>Vt (mV)</label>
      <input type="number" id="Vt_v" value="25.85" step="0.1" oninput="updateShockley()">
      <div class="shockley-eq" id="shockley-eq">I = 10 nA · (e^(V / 1.8 · 25.85 mV) − 1)</div>
    </div>
  </div>

  <!-- ══ DROITE ══ -->
  <div class="col right-col">
    <div class="panel">
      <div class="panel-hd">
        <i class="ti ti-cpu"></i>
        <span class="panel-title">Identification IA</span>
      </div>
      <button class="btn btn-id" id="btn-id" onclick="identify()">
        <i class="ti ti-search"></i> Identifier diode / LED
      </button>
      <div class="hint" id="id-hint">Minimum 6 points requis</div>
      <div id="id-result" style="display:none">
        <div class="id-card" id="id-card">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px">
            <div>
              <div class="id-type" id="id-type">—</div>
              <div class="id-model" id="id-model">—</div>
            </div>
            <div id="id-dot" style="width:12px;height:12px;border-radius:50%;flex-shrink:0;margin-top:4px"></div>
          </div>
          <div class="id-desc" id="id-desc">—</div>
          <div class="vf-seuils">
            <div class="vf-item">
              <div class="vf-item-lbl">Vf @ 1 mA</div>
              <div class="vf-item-val" id="vf-1" style="color:var(--blue)">—</div>
            </div>
            <div class="vf-item">
              <div class="vf-item-lbl">Vf @ 5 mA</div>
              <div class="vf-item-val" id="vf-5" style="color:var(--green)">—</div>
            </div>
            <div class="vf-item">
              <div class="vf-item-lbl">Vf @ 10 mA</div>
              <div class="vf-item-val" id="vf-10" style="color:var(--amber)">—</div>
            </div>
          </div>
          <div class="params-grid">
            <div class="param"><div class="param-name">n idéalité</div><div class="param-val" id="p-n">—</div></div>
            <div class="param"><div class="param-name">Is</div><div class="param-val" id="p-is" style="font-size:9px">—</div></div>
            <div class="param"><div class="param-name">R²</div><div class="param-val" id="p-r2">—</div></div>
          </div>
          <!-- Bandeau baseline -->
          <div class="baseline-info" id="baseline-row" style="display:none">
            <i class="ti ti-filter"></i>
            <span>Baseline soustraite : <strong id="baseline-val">—</strong> mA</span>
          </div>
          <div class="votes" id="votes"></div>
          <div class="conf-row">
            <span class="conf-lbl">Confiance</span>
            <div class="conf-bar"><div class="conf-fill" id="conf-fill" style="width:0%"></div></div>
            <span class="conf-pct" id="conf-pct">—</span>
          </div>
          <div class="apps-box">
            <div class="apps-lbl">Applications</div>
            <div class="apps-txt" id="id-apps">—</div>
          </div>
          <div class="cands" id="cands"></div>
        </div>
      </div>
    </div>
    <div class="panel">
      <div class="panel-hd">
        <i class="ti ti-download"></i>
        <span class="panel-title">Export</span>
      </div>
      <div class="export-row">
        <button class="btn" onclick="window.location.href='/export_csv'"><i class="ti ti-file-type-csv"></i> CSV</button>
        <button class="btn" onclick="window.location.href='/export_pdf'"><i class="ti ti-file-type-pdf"></i> PDF</button>
      </div>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
let chart, currentRes = null, isRunning = false;

function toast(msg, type='info', ms=2500){
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className   = 'toast ' + type + ' show';
  clearTimeout(el._t);
  el._t = setTimeout(()=>{ el.className = 'toast'; }, ms);
}

function initChart(){
  const ctx = document.getElementById('chart').getContext('2d');
  chart = new Chart(ctx, {
    type: 'line',
    data: { datasets: [
      { label:'Mesure réelle', data:[], order:1,
        borderColor:'#378ADD', backgroundColor:'rgba(55,138,221,0.07)',
        pointRadius:2.5, pointHoverRadius:6, borderWidth:2, tension:.25, fill:true },
      { label:'Shockley manuel', data:[], order:3,
        borderColor:'#E24B4A', backgroundColor:'transparent',
        pointRadius:0, borderWidth:1.5, showLine:true, tension:.4,
        segment:{borderDash:[6,3]} },
      { label:'Théorique identifiée', data:[], order:2,
        borderColor:'#BA7517', backgroundColor:'transparent',
        pointRadius:0, borderWidth:2.5, showLine:true, tension:.4, hidden:true,
        segment:{borderDash:[4,3]} }
    ]},
    options:{
      responsive:true, maintainAspectRatio:false, animation:false, parsing:false,
      interaction:{ mode:'nearest', intersect:false, axis:'x' },
      plugins:{
        legend:{ labels:{ color:'#64748b', font:{size:10,family:"'Inter',sans-serif"},
          boxWidth:20, padding:12, filter:i=>!i.hidden } },
        tooltip:{
          backgroundColor:'#fff', borderColor:'#e2e8f0', borderWidth:1,
          titleColor:'#185FA5', bodyColor:'#1e293b', padding:10,
          callbacks:{
            title: i => 'U = ' + Number(i[0].parsed.x).toFixed(3) + ' V',
            label: i => i.dataset.label + ': ' + Number(i[0].parsed.y).toFixed(4) + ' mA'
          }
        },
        zoom:{
          zoom:{ wheel:{enabled:true,speed:.08}, pinch:{enabled:true}, mode:'xy' },
          pan:{ enabled:true, mode:'xy' }
        }
      },
      scales:{
        x:{ type:'linear', min:0, max:3.3,
          title:{display:true, text:'U (V)', color:'#64748b', font:{size:11}},
          ticks:{color:'#94a3b8', font:{size:10}, maxTicksLimit:10},
          grid:{color:'rgba(0,0,0,0.05)'} },
        y:{ min:0, max:2,
          title:{display:true, text:'I (mA)', color:'#64748b', font:{size:11}},
          ticks:{color:'#94a3b8', font:{size:10}},
          grid:{color:'rgba(0,0,0,0.05)'} }
      }
    }
  });
}

function shockleyPts(Is_nA, n, Vt_mV, xmax, steps=500){
  const Is = Is_nA * 1e-9, Vt = Vt_mV * 1e-3, pts = [];
  for(let i = 0; i <= steps; i++){
    const V = (xmax / steps) * i;
    const I = Is * (Math.exp(V / (n * Vt)) - 1) * 1000;
    if(I >= 0 && I < 1e6) pts.push({x:V, y:I});
  }
  return pts;
}

function updateShockley(){
  const Is = +document.getElementById('Is_v').value || 10;
  const n  = +document.getElementById('n_v').value  || 1.8;
  const Vt = +document.getElementById('Vt_v').value || 25.85;
  const xmax = +document.getElementById('xmax').value || 3.3;
  chart.data.datasets[1].data = shockleyPts(Is, n, Vt, xmax);
  chart.update('none');
  document.getElementById('shockley-eq').textContent =
    `I = ${Is} nA · (e^(V / ${n} · ${Vt} mV) − 1)`;
}

function drawTheory(res){
  const xmax = +document.getElementById('xmax').value || 3.3;
  chart.data.datasets[2].data        = shockleyPts(res.Is_nA, res.n, 25.85, xmax, 600);
  chart.data.datasets[2].borderColor = res.color;
  chart.data.datasets[2].label       = 'Théorique — ' + res.type;
  chart.data.datasets[2].hidden      = false;
  chart.update('none');
}

function applyAxes(){
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
  if(currentRes) drawTheory(currentRes);
}

function autoScale(){
  const d = chart.data.datasets[0].data;
  if(!d.length){ toast('Aucune donnée', 'err'); return; }
  const xm = Math.max(...d.map(p=>p.x)) * 1.08;
  const ym = Math.max(...d.map(p=>p.y)) * 1.20;
  document.getElementById('xmax').value = xm.toFixed(2);
  document.getElementById('ymax').value = ym.toFixed(2);
  applyAxes();
}

function clearMeasured(){
  chart.data.datasets[0].data = [];
  chart.update('none');
  toast('Courbe mesure effacée', 'info');
}

function clearTheory(){
  chart.data.datasets[2].data   = [];
  chart.data.datasets[2].hidden = true;
  chart.update('none');
  toast('Courbe théorique effacée', 'info');
}

function setStatus(s){
  const dot = document.getElementById('sdot');
  const txt = document.getElementById('stxt');
  dot.className = 'sdot';
  if(s === 'live'){ dot.classList.add('live'); txt.textContent = 'Live'; }
  else if(s === 'stop'){ dot.classList.add('stop'); txt.textContent = 'Stop'; }
  else { txt.textContent = 'Idle'; }
}

function startSweep(){
  fetch('/start').catch(()=>{}).finally(()=>{
    isRunning = true; setStatus('live');
    chart.data.datasets[0].data = [];
    chart.data.datasets[2].data = []; chart.data.datasets[2].hidden = true;
    currentRes = null;
    document.getElementById('tbody').innerHTML = '';
    document.getElementById('id-result').style.display = 'none';
    document.getElementById('id-hint').textContent = 'Minimum 6 points requis';
    document.getElementById('pts-lbl').textContent = '0 pts';
    chart.update('none');
    toast('Sweep démarré', 'info');
  });
}

function stopSweep(){
  fetch('/stop').catch(()=>{}).finally(()=>{
    isRunning = false; setStatus('stop');
    toast('Sweep arrêté', 'info');
  });
}

function resetAll(){
  fetch('/stop').catch(()=>{});
  fetch('/reset').catch(()=>{}).finally(()=>{
    isRunning = false; setStatus('idle');
    chart.data.datasets[0].data = [];
    chart.data.datasets[2].data = []; chart.data.datasets[2].hidden = true;
    currentRes = null;
    document.getElementById('tbody').innerHTML = '';
    document.getElementById('lv').textContent  = '0.000';
    document.getElementById('li').textContent  = '0.000';
    document.getElementById('hv').innerHTML    = '0.000<span style="font-size:10px;color:var(--muted)"> V</span>';
    document.getElementById('hi').innerHTML    = '0.000<span style="font-size:10px;color:var(--muted)"> mA</span>';
    document.getElementById('hpts').innerHTML  = '0<span style="font-size:10px;color:var(--muted)"> pts</span>';
    document.getElementById('pts-lbl').textContent = '0 pts';
    document.getElementById('id-result').style.display = 'none';
    document.getElementById('id-hint').textContent = 'Minimum 6 points requis';
    chart.update('none');
    toast('Données réinitialisées', 'info');
  });
}

function identify(){
  const btn = document.getElementById('btn-id');
  btn.disabled = true;
  btn.innerHTML = '<i class="ti ti-loader-2"></i> Analyse en cours...';
  fetch('/identify').then(r => r.json()).then(res => {
    btn.disabled = false;
    btn.innerHTML = '<i class="ti ti-search"></i> Identifier diode / LED';
    if(res.error){
      toast('⚠ ' + (res.error === 'not enough data' ? 'Minimum 6 points requis' : res.error), 'err', 3000);
      document.getElementById('id-hint').textContent =
        res.error === 'not enough data' ? 'Minimum 6 points requis' : res.error;
      return;
    }
    currentRes = res;
    document.getElementById('id-hint').textContent = '';
    document.getElementById('id-result').style.display = 'block';
    const card = document.getElementById('id-card');
    card.style.borderColor = res.color;
    card.style.boxShadow   = `0 0 0 3px ${res.color}20`;
    document.getElementById('id-dot').style.cssText =
      `background:${res.color};width:12px;height:12px;border-radius:50%;flex-shrink:0;margin-top:4px`;
    document.getElementById('id-type').textContent  = res.type;
    document.getElementById('id-type').style.color  = res.color;
    document.getElementById('id-model').textContent = res.model;
    document.getElementById('id-desc').textContent  = res.description;
    document.getElementById('id-apps').textContent  = res.applications;
    document.getElementById('vf-1').textContent  = res.vf_1mA  !== null ? res.vf_1mA  + ' V' : '—';
    document.getElementById('vf-5').textContent  = res.vf_5mA  !== null ? res.vf_5mA  + ' V' : '—';
    document.getElementById('vf-10').textContent = res.vf_10mA !== null ? res.vf_10mA + ' V' : '—';
    document.getElementById('p-n').textContent  = res.n;
    document.getElementById('p-is').textContent = res.Is_display;
    const r2 = res.r2_exp;
    const r2el = document.getElementById('p-r2');
    r2el.textContent = r2.toFixed(3);
    r2el.style.color = r2 > 0.95 ? 'var(--green)' : r2 > 0.85 ? 'var(--amber)' : 'var(--red)';
    // Affichage baseline
    if(res.baseline_mA !== undefined && res.baseline_mA > 0.001){
      document.getElementById('baseline-row').style.display = 'flex';
      document.getElementById('baseline-val').textContent = res.baseline_mA.toFixed(4);
    } else {
      document.getElementById('baseline-row').style.display = 'none';
    }
    const conf = res.confidence;
    const cc   = conf > 75 ? 'var(--green)' : conf > 45 ? 'var(--amber)' : 'var(--red)';
    document.getElementById('conf-pct').textContent = conf + ' %';
    document.getElementById('conf-pct').style.color = cc;
    const fill = document.getElementById('conf-fill');
    fill.style.width      = conf + '%';
    fill.style.background = conf > 75 ? '#3B6D11' : conf > 45 ? '#854F0B' : '#A32D2D';
    const votesEl = document.getElementById('votes');
    votesEl.innerHTML = '';
    (res.method_votes || []).forEach(v => {
      const sp = document.createElement('span');
      sp.className   = 'vote-badge ' + (v.ok ? 'vote-ok' : 'vote-warn');
      sp.textContent = v.label + ' → ' + v.result;
      votesEl.appendChild(sp);
    });
    if(res.scores && res.scores.length > 1){
      const maxSc = Math.max(1, res.scores[0].score);
      let html = '<div class="cand-title">Autres candidats</div>';
      res.scores.slice(1, 6).forEach(s => {
        const pct = Math.max(0, s.score / maxSc * 100).toFixed(0);
        html += `<div class="cand-item">
          <div class="cand-dot" style="background:${s.diode.color}"></div>
          <div class="cand-name">${s.diode.name}</div>
          <div class="cand-bar"><div class="cand-fill" style="width:${pct}%;background:${s.diode.color}"></div></div>
          <div class="cand-score">${Math.max(0, s.score).toFixed(1)}</div>
        </div>`;
      });
      document.getElementById('cands').innerHTML = html;
    }
    document.getElementById('Is_v').value = res.Is_nA.toFixed(4);
    document.getElementById('n_v').value  = res.n;
    updateShockley();
    drawTheory(res);
    toast('✓ ' + res.type + ' — confiance ' + conf + ' %', 'ok', 3000);
  }).catch(() => {
    btn.disabled = false;
    btn.innerHTML = '<i class="ti ti-search"></i> Identifier diode / LED';
    toast('Erreur connexion serveur', 'err');
  });
}

function updateLive(){
  fetch('/get_data').then(r => r.json()).then(data => {
    chart.data.datasets[0].data = data.map(d => ({x: +d.U, y: +d.I}));
    chart.update('none');
    const n = data.length;
    document.getElementById('pts-lbl').textContent = n + ' pts';
    document.getElementById('hpts').innerHTML = n + '<span style="font-size:10px;color:var(--muted)"> pts</span>';
    const sl = data.slice(-80);
    document.getElementById('tbody').innerHTML = sl.map((d, i) =>
      `<tr><td>${data.length - sl.length + i + 1}</td><td>${(+d.U).toFixed(3)}</td><td>${(+d.I).toFixed(3)}</td></tr>`
    ).join('');
    if(n > 0){
      const last = data[n - 1];
      const U = (+last.U).toFixed(3), I = (+last.I).toFixed(3);
      document.getElementById('lv').textContent = U;
      document.getElementById('li').textContent = I;
      document.getElementById('hv').innerHTML = U + '<span style="font-size:10px;color:var(--muted)"> V</span>';
      document.getElementById('hi').innerHTML = I + '<span style="font-size:10px;color:var(--muted)"> mA</span>';
    }
  }).catch(() => {});
}

window.onload = function(){
  initChart();
  updateShockley();
  setInterval(updateLive, 800);
};
</script>
</body>
</html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)