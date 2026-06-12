from flask import Flask, request, jsonify
import math, io, datetime

app = Flask(__name__)

# ═══════════════════════════════════════════════
#  DATA STORAGE
# ═══════════════════════════════════════════════
data_store       = []          # diode: [{U, I}]
bjt_store        = {}          # transistor: { "IB1": [{Vce, Ic}], "IB2": [...] }
running          = False
current_type     = "diode"     # "diode" ou "bjt"
current_ib_label = "IB1"
identified_diode = None
bjt_params       = {}          # β, Vbe, saturation, etc.

# ═══════════════════════════════════════════════
#  BASE DE DONNÉES DES DIODES
# ═══════════════════════════════════════════════
DIODE_DATABASE = [
    {
        "id": "schottky", "name": "Schottky",
        "model": "BAT46 / 1N5817 / SS14", "color": "#ff9800",
        "description": "Jonction métal-semiconducteur — chute de tension très faible, commutation ultra-rapide.",
        "vf_1mA": 0.18, "vf_1mA_min": 0.08, "vf_1mA_max": 0.32,
        "vf_5mA": 0.25, "vf_5mA_min": 0.12, "vf_5mA_max": 0.40,
        "vf_10mA": 0.30, "vf_10mA_min": 0.16, "vf_10mA_max": 0.45,
        "vf_typ": 0.22, "vf_min": 0.08, "vf_max": 0.38,
        "Is_nA": 120.0, "n_typ": 1.05, "n_min": 0.8, "n_max": 1.3,
        "slope_factor": 3.5, "curvature": 0.85, "tech": "diode",
        "applications": "Redressement HF, protection inverse, détecteurs RF, OR-ing d'alimentations.",
    },
    {
        "id": "germanium", "name": "Germanium",
        "model": "1N60 / OA91 / AA112", "color": "#9c27b0",
        "description": "Semiconducteur Ge — Vf très bas, courant de fuite élevé, sensible à la température.",
        "vf_1mA": 0.22, "vf_1mA_min": 0.10, "vf_1mA_max": 0.38,
        "vf_5mA": 0.30, "vf_5mA_min": 0.16, "vf_5mA_max": 0.46,
        "vf_10mA": 0.35, "vf_10mA_min": 0.20, "vf_10mA_max": 0.52,
        "vf_typ": 0.27, "vf_min": 0.12, "vf_max": 0.45,
        "Is_nA": 600.0, "n_typ": 1.0, "n_min": 0.8, "n_max": 1.2,
        "slope_factor": 3.2, "curvature": 0.80, "tech": "diode",
        "applications": "Détection AM, démodulation, circuits vintage, radio à galène.",
    },
    {
        "id": "silicon_signal", "name": "Silicium signal",
        "model": "1N4148 / 1N914 / BAV99", "color": "#2196f3",
        "description": "Diode Si signal rapide — polyvalente, switching ns, très répandue.",
        "vf_1mA": 0.48, "vf_1mA_min": 0.35, "vf_1mA_max": 0.62,
        "vf_5mA": 0.58, "vf_5mA_min": 0.44, "vf_5mA_max": 0.72,
        "vf_10mA": 0.65, "vf_10mA_min": 0.50, "vf_10mA_max": 0.80,
        "vf_typ": 0.52, "vf_min": 0.38, "vf_max": 0.62,
        "Is_nA": 8.0, "n_typ": 1.5, "n_min": 1.2, "n_max": 1.8,
        "slope_factor": 2.8, "curvature": 0.72, "tech": "diode",
        "applications": "Switching logique, démodulation, protection ESD, redressement signal.",
    },
    {
        "id": "silicon_rect", "name": "Silicium redresseur",
        "model": "1N4001–1N4007 / 1N5408", "color": "#03a9f4",
        "description": "Diode Si redresseur robuste — courant élevé, standard industriel 50/60 Hz.",
        "vf_1mA": 0.55, "vf_1mA_min": 0.42, "vf_1mA_max": 0.70,
        "vf_5mA": 0.68, "vf_5mA_min": 0.55, "vf_5mA_max": 0.82,
        "vf_10mA": 0.75, "vf_10mA_min": 0.60, "vf_10mA_max": 0.90,
        "vf_typ": 0.70, "vf_min": 0.55, "vf_max": 0.85,
        "Is_nA": 12.0, "n_typ": 1.8, "n_min": 1.5, "n_max": 2.1,
        "slope_factor": 2.2, "curvature": 0.62, "tech": "diode",
        "applications": "Redressement 50 Hz, pont de Graetz, alimentation secteur, protection.",
    },
    {
        "id": "zener", "name": "Zener",
        "model": "BZX55 / 1N47xx / BZV55", "color": "#ff5722",
        "description": "Diode à avalanche — région directe semblable au Si, mais usage en inverse.",
        "vf_1mA": 0.55, "vf_1mA_min": 0.42, "vf_1mA_max": 0.72,
        "vf_5mA": 0.68, "vf_5mA_min": 0.52, "vf_5mA_max": 0.84,
        "vf_10mA": 0.76, "vf_10mA_min": 0.58, "vf_10mA_max": 0.92,
        "vf_typ": 0.65, "vf_min": 0.50, "vf_max": 0.80,
        "Is_nA": 6.0, "n_typ": 1.9, "n_min": 1.6, "n_max": 2.2,
        "slope_factor": 2.0, "curvature": 0.58, "tech": "diode",
        "applications": "Régulation tension, référence de tension, écrêtage, protection surtension.",
    },
    {
        "id": "led_ir", "name": "LED Infrarouge",
        "model": "TSUS5202 / LD271 / SFH484  (λ≈850–950 nm)", "color": "#b71c1c",
        "description": "LED GaAs/GaAlAs — émission infrarouge invisible, Vf bas pour une LED.",
        "vf_1mA": 0.95, "vf_1mA_min": 0.75, "vf_1mA_max": 1.25,
        "vf_5mA": 1.10, "vf_5mA_min": 0.88, "vf_5mA_max": 1.40,
        "vf_10mA": 1.20, "vf_10mA_min": 0.95, "vf_10mA_max": 1.55,
        "vf_typ": 1.10, "vf_min": 0.80, "vf_max": 1.45,
        "Is_nA": 0.002, "n_typ": 1.9, "n_min": 1.7, "n_max": 2.1,
        "slope_factor": 1.5, "curvature": 0.45, "tech": "led", "wavelength": 900,
        "applications": "Télécommandes IR, capteurs de proximité, barrières optiques, IRDA.",
    },
    {
        "id": "led_red", "name": "LED Rouge",
        "model": "L-934ID / HLMP-4700  (λ≈620–680 nm)", "color": "#e53935",
        "description": "LED GaAsP/AlGaInP — rouge classique, Vf modéré.",
        "vf_1mA": 1.65, "vf_1mA_min": 1.40, "vf_1mA_max": 2.00,
        "vf_5mA": 1.85, "vf_5mA_min": 1.58, "vf_5mA_max": 2.18,
        "vf_10mA": 1.95, "vf_10mA_min": 1.65, "vf_10mA_max": 2.30,
        "vf_typ": 1.85, "vf_min": 1.55, "vf_max": 2.20,
        "Is_nA": 0.0008, "n_typ": 2.0, "n_min": 1.8, "n_max": 2.2,
        "slope_factor": 1.4, "curvature": 0.40, "tech": "led", "wavelength": 650,
        "applications": "Signalisation, afficheurs 7 segments, indicateurs de présence.",
    },
    {
        "id": "led_green_hb", "name": "LED Verte haute luminosité",
        "model": "TLHG640 / OVLGG4C7  (λ≈520–530 nm, InGaN)", "color": "#00c853",
        "description": "LED InGaN — verte haute luminosité, Vf légèrement plus élevé.",
        "vf_1mA": 2.40, "vf_1mA_min": 2.15, "vf_1mA_max": 2.70,
        "vf_5mA": 2.60, "vf_5mA_min": 2.35, "vf_5mA_max": 2.88,
        "vf_10mA": 2.70, "vf_10mA_min": 2.44, "vf_10mA_max": 3.00,
        "vf_typ": 2.60, "vf_min": 2.35, "vf_max": 2.90,
        "Is_nA": 0.00001, "n_typ": 2.1, "n_min": 1.9, "n_max": 2.3,
        "slope_factor": 1.3, "curvature": 0.38, "tech": "led", "wavelength": 525,
        "applications": "Éclairage, rétroéclairage, signalisation haute visibilité.",
    },
    {
        "id": "led_blue", "name": "LED Bleue",
        "model": "OVLBB4C7 / NSPB500S  (λ≈450–480 nm)", "color": "#1e88e5",
        "description": "LED InGaN — bleue, technologie moderne, Vf élevé.",
        "vf_1mA": 2.70, "vf_1mA_min": 2.45, "vf_1mA_max": 3.20,
        "vf_5mA": 2.95, "vf_5mA_min": 2.65, "vf_5mA_max": 3.45,
        "vf_10mA": 3.10, "vf_10mA_min": 2.78, "vf_10mA_max": 3.60,
        "vf_typ": 3.00, "vf_min": 2.70, "vf_max": 3.50,
        "Is_nA": 0.000002, "n_typ": 2.2, "n_min": 2.0, "n_max": 2.5,
        "slope_factor": 1.2, "curvature": 0.35, "tech": "led", "wavelength": 465,
        "applications": "Éclairage, écrans LCD, phares automobiles, indicateurs.",
    },
    {
        "id": "led_white", "name": "LED Blanche",
        "model": "NSPW500GS / VLHW4100  (phosphore + InGaN bleu)", "color": "#90caf9",
        "description": "LED InGaN bleue + phosphore jaune — lumière blanche, Vf similaire à la LED bleue.",
        "vf_1mA": 2.75, "vf_1mA_min": 2.50, "vf_1mA_max": 3.25,
        "vf_5mA": 3.00, "vf_5mA_min": 2.70, "vf_5mA_max": 3.50,
        "vf_10mA": 3.15, "vf_10mA_min": 2.82, "vf_10mA_max": 3.65,
        "vf_typ": 3.10, "vf_min": 2.80, "vf_max": 3.60,
        "Is_nA": 0.000001, "n_typ": 2.3, "n_min": 2.0, "n_max": 2.6,
        "slope_factor": 1.2, "curvature": 0.35, "tech": "led", "wavelength": 0,
        "applications": "Éclairage général, lampes LED, torches, rétroéclairage.",
    },
]

# ═══════════════════════════════════════════════
#  IDENTIFICATION DIODE (algorithme multi-méthodes)
# ═══════════════════════════════════════════════
def identify_diode_from_curve(data):
    if len(data) < 6:
        return None
    data_s  = sorted(data, key=lambda d: d['U'])
    u_vals  = [d['U'] for d in data_s]
    i_vals  = [d['I'] for d in data_s]
    Vt = 0.02585
    i_max = max(i_vals)
    if i_max <= 0:
        return None

    def interp_vf_abs(thr):
        for k in range(len(u_vals)):
            if i_vals[k] >= thr:
                if k > 0 and (i_vals[k] - i_vals[k-1]) > 1e-9:
                    dv = u_vals[k] - u_vals[k-1]
                    di = i_vals[k] - i_vals[k-1]
                    return u_vals[k-1] + (thr - i_vals[k-1]) * dv / di
                return u_vals[k]
        return None

    def interp_vf_pct(pct):
        target = i_max * pct
        for k in range(len(u_vals)):
            if i_vals[k] >= target:
                if k > 0 and (i_vals[k] - i_vals[k-1]) > 1e-9:
                    dv = u_vals[k] - u_vals[k-1]
                    di = i_vals[k] - i_vals[k-1]
                    return u_vals[k-1] + (target - i_vals[k-1]) * dv / di
                return u_vals[k]
        return u_vals[-1]

    vf_1mA  = interp_vf_abs(1.0)
    vf_5mA  = interp_vf_abs(5.0)
    vf_10mA = interp_vf_abs(10.0)
    vf_5pct  = max(0.0, interp_vf_pct(0.05))
    vf_10pct = max(0.0, interp_vf_pct(0.10))
    vf_20pct = max(0.0, interp_vf_pct(0.20))
    vf_30pct = max(0.0, interp_vf_pct(0.30))

    pts_exp = [(u, i * 1e-3) for u, i in zip(u_vals, i_vals)
               if i > i_max * 0.03 and i < i_max * 0.70 and u > 0.02]
    estimated_n = 1.8
    estimated_Is = 10e-9
    r2_exp = 0.0
    if len(pts_exp) >= 5:
        try:
            ln_i  = [math.log(max(p[1], 1e-20)) for p in pts_exp]
            v_arr = [p[0] for p in pts_exp]
            N = len(pts_exp)
            sv = sum(v_arr); sl = sum(ln_i)
            svl = sum(v * l for v, l in zip(v_arr, ln_i))
            sv2 = sum(v * v for v in v_arr)
            denom = N * sv2 - sv ** 2
            if abs(denom) > 1e-12:
                slope = (N * svl - sv * sl) / denom
                intercept = (sl - slope * sv) / N
                n_calc = 1.0 / (slope * Vt) if slope > 0 else 1.8
                if 0.5 < n_calc < 3.5:
                    estimated_n = round(n_calc, 4)
                Is_calc = math.exp(intercept)
                if 1e-20 < Is_calc < 1e-2:
                    estimated_Is = Is_calc
                mean_li = sl / N
                ss_tot = sum((l - mean_li) ** 2 for l in ln_i)
                ss_res = sum((l - (slope * v + intercept)) ** 2 for v, l in zip(v_arr, ln_i))
                r2_exp = max(0.0, 1.0 - ss_res / max(ss_tot, 1e-12))
        except Exception:
            pass

    onset_sharpness = (vf_30pct - vf_5pct) / max(vf_5pct, 0.01)
    scores = []
    for diode in DIODE_DATABASE:
        score = 0.0
        veto  = False
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
        if vf_5mA is not None:
            lo, hi, typ = diode["vf_5mA_min"], diode["vf_5mA_max"], diode["vf_5mA"]
            if lo <= vf_5mA <= hi:
                dist = abs(vf_5mA - typ) / max((hi - lo) / 2.0, 0.01)
                score += 20.0 * max(0.0, 1.0 - dist ** 1.5)
            else:
                score -= min(abs(vf_5mA - lo), abs(vf_5mA - hi)) * 40.0
        if vf_10mA is not None:
            lo, hi, typ = diode["vf_10mA_min"], diode["vf_10mA_max"], diode["vf_10mA"]
            if lo <= vf_10mA <= hi:
                dist = abs(vf_10mA - typ) / max((hi - lo) / 2.0, 0.01)
                score += 15.0 * max(0.0, 1.0 - dist ** 1.5)
            else:
                score -= min(abs(vf_10mA - lo), abs(vf_10mA - hi)) * 30.0
        n_typ, n_min, n_max = diode["n_typ"], diode["n_min"], diode["n_max"]
        if n_min <= estimated_n <= n_max:
            score += 15.0 * max(0.0, 1.0 - abs(estimated_n - n_typ) / max((n_max - n_min) / 2.0, 0.01))
        else:
            score -= abs(estimated_n - n_typ) * 12.0
        try:
            log_is_meas = math.log10(max(estimated_Is, 1e-22))
            log_is_ref  = math.log10(diode["Is_nA"] * 1e-9)
            score += max(0.0, 8.0 - abs(log_is_meas - log_is_ref) * 3.0)
        except Exception:
            pass
        score += max(0.0, 5.0 - abs(onset_sharpness - diode.get("slope_factor", 2.0)) * 2.5)
        if r2_exp > 0.92 and n_min <= estimated_n <= n_max:
            score += 5.0 * r2_exp
        if veto:
            score = min(score, -10.0)
        scores.append({"diode": diode, "score": round(score, 2)})

    scores.sort(key=lambda x: x["score"], reverse=True)
    best = scores[0]["diode"]
    best_score = scores[0]["score"]
    gap = best_score - (scores[1]["score"] if len(scores) > 1 else 0.0)
    conf = min(95, max(15, int(best_score * 0.75 + gap * 0.50)))
    conf = min(97, conf + int(r2_exp * 8))
    if vf_1mA is not None:
        if abs(vf_1mA - best["vf_1mA"]) < 0.02:
            conf = min(99, conf + 6)
        elif abs(vf_1mA - best["vf_1mA"]) < 0.06:
            conf = min(99, conf + 3)

    method_votes = []
    if vf_1mA is not None:
        method_votes.append({"label": "Vf@1mA", "result": f"{vf_1mA:.3f}V",
                              "ok": best["vf_1mA_min"] <= vf_1mA <= best["vf_1mA_max"]})
    if vf_5mA is not None:
        method_votes.append({"label": "Vf@5mA", "result": f"{vf_5mA:.3f}V",
                              "ok": best["vf_5mA_min"] <= vf_5mA <= best["vf_5mA_max"]})
    if vf_10mA is not None:
        method_votes.append({"label": "Vf@10mA", "result": f"{vf_10mA:.3f}V",
                              "ok": best["vf_10mA_min"] <= vf_10mA <= best["vf_10mA_max"]})
    n_ok = best["n_min"] <= estimated_n <= best["n_max"]
    method_votes.append({"label": f"n={estimated_n:.3f}", "result": best["name"], "ok": n_ok})

    is_display = (f"{estimated_Is * 1e9:.4f} nA" if estimated_Is * 1e9 >= 0.001
                  else f"{estimated_Is * 1e12:.4f} pA")

    return {
        "type": best["name"], "model": best["model"], "id": best["id"],
        "color": best["color"], "description": best["description"],
        "applications": best.get("applications", "—"),
        "tech": best.get("tech", "diode"), "wavelength": best.get("wavelength", 0),
        "vf_1mA":  round(vf_1mA,  3) if vf_1mA  is not None else None,
        "vf_5mA":  round(vf_5mA,  3) if vf_5mA  is not None else None,
        "vf_10mA": round(vf_10mA, 3) if vf_10mA is not None else None,
        "vf": round(vf_10pct, 3), "vf_5pct": round(vf_5pct, 3),
        "vf_10pct": round(vf_10pct, 3), "vf_20pct": round(vf_20pct, 3),
        "vf_30pct": round(vf_30pct, 3),
        "n": round(estimated_n, 3), "Is_nA": round(estimated_Is * 1e9, 6),
        "Is_display": is_display, "r2_exp": round(r2_exp, 4),
        "onset_sharpness": round(onset_sharpness, 3),
        "confidence": conf, "scores": scores[:8], "method_votes": method_votes,
    }

# ═══════════════════════════════════════════════
#  ANALYSE TRANSISTOR 2N2222
# ═══════════════════════════════════════════════
def analyze_bjt(bjt_data):
    """
    Extrait β (hFE), Vce_sat, Ic_max, zones de fonctionnement
    depuis la famille de courbes Ic=f(Vce) pour différents IB
    """
    if not bjt_data:
        return {}

    result = {
        "curves": {},
        "beta_values": {},
        "beta_avg": None,
        "vce_sat": None,
        "ic_max": 0,
        "zones": {},
        "ib_labels": list(bjt_data.keys()),
    }

    all_ic_max = []
    beta_list  = []

    # IB nominaux 2N2222 (µA) par label
    ib_nominal = {
        "IB1": 10, "IB2": 20, "IB3": 40,
        "IB4": 60, "IB5": 80, "IB6": 100,
    }

    for label, pts in bjt_data.items():
        if not pts:
            continue
        pts_s = sorted(pts, key=lambda p: p["Vce"])
        vce_vals = [p["Vce"] for p in pts_s]
        ic_vals  = [p["Ic"]  for p in pts_s]

        ic_max_curve = max(ic_vals) if ic_vals else 0
        all_ic_max.append(ic_max_curve)

        # β = Ic_plateau / IB
        ib_uA = ib_nominal.get(label, 20)
        ic_plateau = ic_max_curve * 0.9  # valeur plateau ≈ 90% du max
        beta = (ic_plateau / (ib_uA * 1e-3)) if ib_uA > 0 else None
        if beta and 10 < beta < 1000:
            beta_list.append(beta)
            result["beta_values"][label] = round(beta, 1)

        # Vce_sat : tension où Ic atteint 90% du plateau
        vce_sat = None
        for k in range(len(vce_vals)):
            if ic_vals[k] >= ic_plateau * 0.90:
                vce_sat = vce_vals[k]
                break
        result["curves"][label] = {
            "vce": vce_vals, "ic": ic_vals,
            "ic_max": ic_max_curve,
            "vce_sat": round(vce_sat, 3) if vce_sat else None,
            "ib_uA": ib_uA,
        }

    if all_ic_max:
        result["ic_max"] = round(max(all_ic_max), 3)
    if beta_list:
        result["beta_avg"] = round(sum(beta_list) / len(beta_list), 1)
    if result["curves"]:
        vce_sats = [c["vce_sat"] for c in result["curves"].values() if c["vce_sat"]]
        if vce_sats:
            result["vce_sat"] = round(min(vce_sats), 3)

    # Zones opératoires pour la dernière courbe
    result["zones"] = {
        "saturation": "Vce < 0.3 V — transistor saturé (interrupteur fermé)",
        "lineaire":   "0.3 V < Vce < Vce_max — zone active (amplification)",
        "blocage":    "IB = 0 — transistor bloqué (interrupteur ouvert)",
    }
    return result

# ═══════════════════════════════════════════════
#  ROUTES FLASK
# ═══════════════════════════════════════════════
@app.route("/")
def home():
    return DASHBOARD_HTML

@app.route("/status")
def status():
    return jsonify({
        "running": running,
        "type": current_type,
        "ib_label": current_ib_label,
    })

@app.route("/start", methods=["GET", "POST"])
def start():
    global running, data_store, bjt_store, identified_diode, bjt_params
    global current_type, current_ib_label
    body = request.get_json(silent=True) or {}
    current_type     = body.get("type", "diode")
    current_ib_label = body.get("ib_label", "IB1")
    reset_data       = body.get("reset", True)
    if reset_data:
        data_store       = []
        bjt_store        = {}
        identified_diode = None
        bjt_params       = {}
    running = True
    return jsonify({"status": "running", "type": current_type})

@app.route("/stop")
def stop():
    global running
    running = False
    return jsonify({"status": "stopped"})

@app.route("/reset")
def reset():
    global data_store, bjt_store, identified_diode, bjt_params, running
    data_store       = []
    bjt_store        = {}
    identified_diode = None
    bjt_params       = {}
    running          = False
    return jsonify({"status": "reset"})

@app.route("/set_mode", methods=["POST"])
def set_mode():
    global current_type, current_ib_label
    body = request.get_json(silent=True) or {}
    current_type     = body.get("type", "diode")
    current_ib_label = body.get("ib_label", "IB1")
    return jsonify({"status": "ok", "type": current_type, "ib_label": current_ib_label})

@app.route("/data", methods=["POST"])
def receive_data():
    global data_store, bjt_store
    if not running:
        return jsonify({"status": "stopped"})
    d = request.json
    t = d.get("type", current_type)
    if t == "bjt":
        vce = float(d.get("voltage", 0))
        ic  = float(d.get("current", 0))
        lbl = d.get("ib_label", current_ib_label)
        if vce >= 0 and ic >= 0:
            if lbl not in bjt_store:
                bjt_store[lbl] = []
            bjt_store[lbl].append({"Vce": round(vce, 4), "Ic": round(ic, 4)})
    else:
        U = float(d.get("voltage", 0))
        I = float(d.get("current", 0))
        if U >= 0 and I >= 0:
            data_store.append({"U": round(U, 4), "I": round(I, 4)})
    return jsonify({"status": "ok"})

@app.route("/get_data")
def get_data():
    return jsonify(data_store)

@app.route("/get_bjt")
def get_bjt():
    return jsonify(bjt_store)

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

@app.route("/analyze_bjt")
def analyze_bjt_route():
    global bjt_params
    if not bjt_store:
        return jsonify({"error": "no BJT data"})
    result = analyze_bjt(bjt_store)
    bjt_params = result
    return jsonify(result)

@app.route("/export_csv")
def export_csv():
    mode = request.args.get("mode", "diode")
    if mode == "bjt":
        lines = ["label,Vce(V),Ic(mA)\n"]
        for lbl, pts in bjt_store.items():
            for p in pts:
                lines.append(f"{lbl},{p['Vce']},{p['Ic']}\n")
        csv_data = "".join(lines)
        fname = "mesures_transistor.csv"
    else:
        csv_data = "U(V),I(mA)\n" + "".join(f"{d['U']},{d['I']}\n" for d in data_store)
        fname = "mesures_diode.csv"
    return csv_data, 200, {
        "Content-Type": "text/csv",
        "Content-Disposition": f"attachment; filename={fname}"
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

    mode = request.args.get("mode", "diode")
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                             rightMargin=2*cm, leftMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    elements = []
    T  = lambda txt, sty: Paragraph(txt, sty)
    HR = lambda: HRFlowable(width="100%", thickness=0.8,
                             color=colors.HexColor('#1e6ab0'), spaceAfter=10)
    s_title   = ParagraphStyle('t', fontSize=20, textColor=colors.HexColor('#0a2342'),
                                fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=4)
    s_sub     = ParagraphStyle('s', fontSize=10, textColor=colors.HexColor('#1e6ab0'),
                                fontName='Helvetica', alignment=TA_CENTER, spaceAfter=2)
    s_date    = ParagraphStyle('d', fontSize=9, textColor=colors.grey,
                                fontName='Helvetica', alignment=TA_CENTER, spaceAfter=12)
    s_section = ParagraphStyle('sc', fontSize=12, textColor=colors.HexColor('#0a2342'),
                                fontName='Helvetica-Bold', spaceAfter=6, spaceBefore=10)
    s_foot    = ParagraphStyle('f', fontSize=8, textColor=colors.grey,
                                fontName='Helvetica', alignment=TA_CENTER)

    now = datetime.datetime.now().strftime("%d/%m/%Y à %H:%M:%S")

    def styled_table(data, col_w):
        t = Table(data, colWidths=col_w)
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#0a2342')),
            ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.HexColor('#eef4fb'), colors.white]),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#b0c8e0')),
            ('TOPPADDING', (0,0), (-1,-1), 7),
            ('BOTTOMPADDING', (0,0), (-1,-1), 7),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
        ]))
        return t

    if mode == "bjt":
        elements += [T("SMART DIODE DASHBOARD", s_title),
                     T("Rapport Transistor 2N2222 — Famille de courbes Ic = f(Vce)", s_sub),
                     T(f"Généré le : {now}", s_date), HR()]
        if bjt_params:
            elements.append(T("Paramètres extraits — 2N2222", s_section))
            bp = bjt_params
            rows = [
                ["β (hFE) moyen", str(bp.get("beta_avg", "—"))],
                ["Ic max mesuré", f"{bp.get('ic_max', 0):.3f} mA"],
                ["Vce_sat estimé", f"{bp.get('vce_sat', 0):.3f} V" if bp.get('vce_sat') else "—"],
                ["Courbes IB mesurées", ", ".join(bp.get("ib_labels", []))],
                ["Zone saturation", "Vce < 0.3 V"],
                ["Zone linéaire", "0.3 V < Vce < Vce_max"],
            ]
            elements += [styled_table(rows, [5.5*cm, 10.5*cm]), Spacer(1, 0.4*cm)]
        if bjt_store:
            elements.append(T("Famille de courbes Ic = f(Vce)", s_section))
            fig, ax = plt.subplots(figsize=(7.5, 4.5))
            palette = ['#185FA5','#E55A2B','#3B8C3B','#8B2FC9','#C9861B','#C92B2B']
            for i, (lbl, pts) in enumerate(bjt_store.items()):
                if pts:
                    pts_s = sorted(pts, key=lambda p: p["Vce"])
                    vce = [p["Vce"] for p in pts_s]
                    ic  = [p["Ic"]  for p in pts_s]
                    ax.plot(vce, ic, color=palette[i % len(palette)],
                            linewidth=2, marker='o', markersize=2.5, label=lbl)
            ax.set_xlabel("Vce (V)", fontsize=10)
            ax.set_ylabel("Ic (mA)", fontsize=10)
            ax.set_title("2N2222 — Ic = f(Vce)", fontsize=11, color='#0a2342', fontweight='bold')
            ax.legend(fontsize=9); ax.grid(True, color='#e0e8f0', linewidth=0.5)
            ax.axvline(x=0.3, color='orange', linestyle='--', linewidth=1, alpha=0.7, label='Vce_sat ≈ 0.3V')
            ax.set_facecolor('#f8fbff'); fig.patch.set_facecolor('white')
            plt.tight_layout()
            img_buf = io.BytesIO()
            plt.savefig(img_buf, format='png', dpi=150, bbox_inches='tight')
            plt.close(); img_buf.seek(0)
            elements += [Image(img_buf, width=15*cm, height=9*cm), Spacer(1, 0.4*cm)]
    else:
        elements += [T("SMART DIODE DASHBOARD", s_title),
                     T("Rapport de Mesures Expérimentales — Diode/LED", s_sub),
                     T(f"Généré le : {now}", s_date), HR()]
        if identified_diode:
            elements.append(T("Identification du Composant", s_section))
            id_ = identified_diode
            rows = [
                ["Type identifié", f"{id_['type']} ({id_['model']})"],
                ["Description", id_["description"]],
                ["Applications", id_.get("applications", "—")],
                ["Vf à 1 mA", f"{id_['vf_1mA']} V" if id_['vf_1mA'] is not None else "—"],
                ["Vf à 5 mA", f"{id_['vf_5mA']} V" if id_['vf_5mA'] is not None else "—"],
                ["Vf à 10 mA", f"{id_['vf_10mA']} V" if id_['vf_10mA'] is not None else "—"],
                ["Facteur d'idéalité n", str(id_["n"])],
                ["Courant de saturation Is", id_.get("Is_display", "—")],
                ["R² régression", str(id_.get("r2_exp", "—"))],
                ["Confiance", f"{id_['confidence']} %"],
            ]
            elements += [styled_table(rows, [5.5*cm, 10.5*cm]), Spacer(1, 0.4*cm)]
        if data_store:
            elements.append(T("Courbe Caractéristique I = f(U)", s_section))
            u_vals = [d['U'] for d in data_store]
            i_vals = [d['I'] for d in data_store]
            fig, ax = plt.subplots(figsize=(7.5, 4))
            ax.plot(u_vals, i_vals, color='#1e6ab0', linewidth=2.5,
                    marker='o', markersize=3, label='Mesure réelle')
            if identified_diode:
                Is = identified_diode['Is_nA'] * 1e-9
                n  = identified_diode['n']; Vt = 0.02585
                v_t = [i * max(u_vals, default=3.3) / 300 for i in range(301)]
                i_t = [min(Is * (math.exp(v / (n * Vt)) - 1) * 1000,
                           max(i_vals) * 2) for v in v_t]
                ax.plot(v_t, i_t, color=identified_diode.get('color', '#ff9800'),
                        linewidth=2, linestyle='--', label=f"Shockley — {identified_diode['type']}")
                ax.legend(fontsize=9)
            ax.set_xlabel("U (V)", fontsize=10); ax.set_ylabel("I (mA)", fontsize=10)
            ax.set_title("Courbe I = f(U)", fontsize=11, color='#0a2342', fontweight='bold')
            ax.grid(True, color='#e0e8f0', linewidth=0.5)
            ax.set_facecolor('#f8fbff'); fig.patch.set_facecolor('white')
            plt.tight_layout()
            img_buf = io.BytesIO()
            plt.savefig(img_buf, format='png', dpi=150, bbox_inches='tight')
            plt.close(); img_buf.seek(0)
            elements += [Image(img_buf, width=15*cm, height=8*cm), Spacer(1, 0.4*cm)]

    elements += [HR(), T("Smart Diode Dashboard — ESP32 + MCP4725 — Rapport automatique", s_foot)]
    doc.build(elements)
    buffer.seek(0)
    fname = "rapport_transistor.pdf" if mode == "bjt" else "rapport_diode.pdf"
    return buffer.read(), 200, {
        "Content-Type": "application/pdf",
        "Content-Disposition": f"attachment; filename={fname}"
    }


# ═══════════════════════════════════════════════
#  DASHBOARD HTML
# ═══════════════════════════════════════════════
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Smart Component Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.19.0/dist/tabler-icons.min.css">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/hammerjs@2.0.8/hammer.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>
<style>
:root{
  --bg:#0f1117;--surface:#181c27;--surface2:#1e2334;--surface3:#252b3d;
  --border:#2a3045;--border2:#3a4460;
  --text:#e8ecf4;--muted:#7a88aa;--hint:#4a5570;
  --blue:#4a9eff;--blue-dk:#1a5fbb;--blue-lt:rgba(74,158,255,.12);
  --green:#3ddc84;--green-dk:#1a8a4a;--green-lt:rgba(61,220,132,.12);
  --red:#ff5f6d;--red-dk:#cc2233;--red-lt:rgba(255,95,109,.12);
  --amber:#ffb347;--amber-lt:rgba(255,179,71,.12);--amber-dk:#b36a00;
  --purple:#a78bfa;--purple-lt:rgba(167,139,250,.12);
  --cyan:#38bdf8;--cyan-lt:rgba(56,189,248,.12);
  --mono:'JetBrains Mono',monospace;--sans:'Inter',sans-serif;
  --r:10px;--r-sm:6px;--r-xs:4px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:var(--bg);font-family:var(--sans);color:var(--text);overflow-x:hidden}
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:3px}

/* ── MODE SWITCHER ── */
.mode-bar{
  height:52px;display:flex;align-items:center;gap:0;
  background:var(--surface);border-bottom:1px solid var(--border);
  position:sticky;top:0;z-index:200;padding:0 16px;
}
.logo{display:flex;align-items:center;gap:10px;margin-right:24px}
.logo-icon{width:30px;height:30px;background:linear-gradient(135deg,var(--blue),var(--purple));
  border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:15px}
.logo-name{font-size:13px;font-weight:700;letter-spacing:.3px;color:var(--text)}
.logo-sub{font-size:9px;color:var(--muted);margin-top:1px}
.mode-tabs{display:flex;gap:2px;background:var(--surface2);border-radius:var(--r-sm);
  padding:3px;border:1px solid var(--border)}
.mode-tab{padding:5px 18px;border-radius:var(--r-xs);font-size:12px;font-weight:500;
  cursor:pointer;transition:all .2s;color:var(--muted);display:flex;align-items:center;gap:6px;
  border:none;background:transparent}
.mode-tab i{font-size:14px}
.mode-tab:hover{color:var(--text);background:var(--surface3)}
.mode-tab.active{background:var(--blue-dk);color:#fff;box-shadow:0 2px 8px rgba(74,158,255,.25)}
.mode-tab.active.bjt{background:linear-gradient(135deg,#8B2FC9,#5B2FC9)}
.hdr-right{display:flex;align-items:center;gap:16px;margin-left:auto}
.hdr-stat{text-align:right}
.hdr-val{font-family:var(--mono);font-size:14px;font-weight:600}
.hdr-lbl{font-size:8px;color:var(--muted);letter-spacing:.8px;text-transform:uppercase;margin-top:1px}
.status-pill{display:flex;align-items:center;gap:6px;padding:4px 12px;border-radius:20px;
  background:var(--surface2);border:1px solid var(--border2);font-size:11px;
  font-weight:500;color:var(--muted);min-width:75px;justify-content:center}
.sdot{width:6px;height:6px;border-radius:50%;background:var(--hint);transition:all .3s}
.sdot.live{background:var(--green);animation:pulse 1.2s infinite}
.sdot.stop{background:var(--red)}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.3;transform:scale(.7)}}

/* ── LAYOUT ── */
.layout{display:grid;grid-template-columns:200px 1fr 260px;gap:8px;
  padding:8px;min-height:calc(100vh - 52px)}
.col{display:flex;flex-direction:column;gap:8px}

/* ── PANEL ── */
.panel{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--r);padding:12px}
.panel-hd{display:flex;align-items:center;gap:7px;margin-bottom:10px;
  padding-bottom:8px;border-bottom:1px solid var(--border)}
.panel-hd i{font-size:15px;color:var(--blue)}
.panel-hd i.bjt-icon{color:var(--purple)}
.panel-title{font-size:9px;font-weight:600;letter-spacing:1.2px;
  text-transform:uppercase;color:var(--muted)}

/* ── FORM ── */
label{display:block;font-size:9px;font-weight:500;color:var(--muted);
  letter-spacing:.5px;text-transform:uppercase;margin-bottom:3px;margin-top:8px}
label:first-of-type{margin-top:0}
input[type="number"],select{
  width:100%;padding:6px 10px;background:var(--surface2);
  border:1px solid var(--border2);border-radius:var(--r-sm);
  color:var(--text);font-family:var(--mono);font-size:12px;
  transition:border .15s;-moz-appearance:textfield;outline:none}
input::-webkit-inner-spin-button{-webkit-appearance:none}
input:focus,select:focus{border-color:var(--blue);box-shadow:0 0 0 3px rgba(74,158,255,.1)}
select option{background:var(--surface2)}

/* ── BUTTONS ── */
.btn{
  width:100%;padding:7px 12px;border-radius:var(--r-sm);font-family:var(--sans);
  font-size:11px;font-weight:500;cursor:pointer;transition:all .15s;
  display:flex;align-items:center;justify-content:center;gap:5px;
  border:1px solid var(--border2);background:var(--surface2);color:var(--text)
}
.btn:hover{border-color:var(--blue);background:var(--surface3);color:var(--text)}
.btn:active{transform:scale(.98)}
.btn:disabled{opacity:.4;cursor:not-allowed;transform:none}
.btn+.btn{margin-top:5px}
.btn i{font-size:14px}
.btn-start{background:var(--green-lt);color:var(--green);border-color:rgba(61,220,132,.3)}
.btn-start:hover{background:rgba(61,220,132,.2);border-color:var(--green)}
.btn-stop{background:var(--red-lt);color:var(--red);border-color:rgba(255,95,109,.3)}
.btn-stop:hover{background:rgba(255,95,109,.2);border-color:var(--red)}
.btn-id{background:var(--blue-lt);color:var(--blue);border-color:rgba(74,158,255,.3);padding:9px 12px;font-size:12px}
.btn-id:hover:not(:disabled){background:rgba(74,158,255,.2);border-color:var(--blue)}
.btn-bjt{background:var(--purple-lt);color:var(--purple);border-color:rgba(167,139,250,.3);padding:9px 12px;font-size:12px}
.btn-bjt:hover:not(:disabled){background:rgba(167,139,250,.2);border-color:var(--purple)}

/* ── IB SELECTOR ── */
.ib-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin-top:6px}
.ib-btn{padding:4px 6px;border-radius:var(--r-xs);font-size:10px;font-weight:600;
  font-family:var(--mono);cursor:pointer;transition:all .15s;text-align:center;
  border:1px solid var(--border2);background:var(--surface2);color:var(--muted)}
.ib-btn:hover{border-color:var(--purple);color:var(--purple)}
.ib-btn.active{background:var(--purple-lt);border-color:var(--purple);color:var(--purple)}
.ib-btn.done{background:rgba(61,220,132,.08);border-color:var(--green);color:var(--green)}

/* ── LIVE ── */
.live-grid{display:grid;grid-template-columns:1fr 1fr;gap:5px}
.live-box{background:var(--surface2);border:1px solid var(--border);
  border-radius:var(--r-sm);padding:7px;text-align:center}
.live-val{font-family:var(--mono);font-size:18px;font-weight:600;line-height:1}
.live-lbl{font-size:8px;color:var(--muted);margin-top:2px;letter-spacing:.5px;text-transform:uppercase}

/* ── TABLE ── */
.tbl-wrap{flex:1;overflow-y:auto;max-height:155px;border:1px solid var(--border);
  border-radius:var(--r-sm)}
table{width:100%;border-collapse:collapse}
thead th{background:var(--surface2);padding:5px 8px;color:var(--muted);font-size:8px;
  font-weight:600;text-transform:uppercase;letter-spacing:.8px;
  position:sticky;top:0;text-align:center;border-bottom:1px solid var(--border);z-index:1}
tbody td{padding:3px 8px;text-align:center;border-bottom:1px solid var(--border);
  font-family:var(--mono);font-size:10px;color:var(--muted)}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover td{background:var(--surface2);color:var(--text)}

/* ── CHART ── */
.chart-wrap{flex:1;position:relative;min-height:300px;background:var(--surface2);
  border-radius:var(--r-sm);padding:8px}
.axes-grid{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:5px;margin-top:8px}
.axes-grid label{font-size:8px;margin-top:0}
.axes-grid input{font-size:11px;padding:4px 7px}
.axes-btns{display:flex;gap:5px;margin-top:5px}
.axes-btns .btn{flex:1;font-size:10px;padding:5px}
.curve-btns{display:flex;gap:5px;flex-wrap:wrap;margin-left:auto}
.curve-btn{font-size:9px;padding:3px 7px;border-radius:var(--r-xs);
  border:1px solid var(--border2);background:var(--surface2);color:var(--muted);
  cursor:pointer;display:flex;align-items:center;gap:3px;transition:all .15s;font-family:var(--sans)}
.curve-btn:hover{color:var(--text);border-color:var(--blue)}

/* ── BJT PARAMS DISPLAY ── */
.bjt-params-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-top:8px}
.bjt-param{background:var(--surface2);border:1px solid var(--border);
  border-radius:var(--r-sm);padding:7px;text-align:center}
.bjt-param-val{font-family:var(--mono);font-size:17px;font-weight:700;line-height:1;color:var(--purple)}
.bjt-param-lbl{font-size:8px;color:var(--muted);margin-top:3px;text-transform:uppercase;letter-spacing:.5px}
.zones-box{margin-top:8px;border:1px solid var(--border);border-radius:var(--r-sm);overflow:hidden}
.zone-row{display:flex;align-items:center;gap:8px;padding:6px 10px;border-bottom:1px solid var(--border);font-size:10px}
.zone-row:last-child{border-bottom:none}
.zone-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.zone-name{font-weight:600;min-width:70px}
.zone-desc{color:var(--muted)}
.ib-legend{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}
.ib-leg-item{display:flex;align-items:center;gap:4px;padding:3px 7px;
  border-radius:var(--r-xs);border:1px solid var(--border);background:var(--surface2);
  font-size:9px;font-family:var(--mono)}
.ib-leg-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.beta-row{display:flex;align-items:center;gap:8px;margin-top:6px;
  padding:8px 10px;background:var(--purple-lt);border:1px solid rgba(167,139,250,.3);
  border-radius:var(--r-sm)}
.beta-val{font-family:var(--mono);font-size:22px;font-weight:700;color:var(--purple)}
.beta-lbl{font-size:10px;color:var(--muted)}

/* ── RIGHT PANEL ── */
.right-col{overflow-y:auto;max-height:calc(100vh - 68px)}
.id-card{border:1px solid var(--border);border-radius:var(--r-sm);
  padding:11px;margin-top:10px;animation:fadeUp .3s ease}
@keyframes fadeUp{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:translateY(0)}}
.id-type{font-size:15px;font-weight:600;line-height:1.2}
.id-model{font-size:9px;color:var(--muted);margin-top:2px}
.id-desc{font-size:10px;color:var(--muted);margin-top:7px;line-height:1.55;
  padding-top:7px;border-top:1px solid var(--border)}
.params-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin-top:7px}
.param{background:var(--surface2);border:1px solid var(--border);
  border-radius:var(--r-sm);padding:5px 4px;text-align:center}
.param-name{font-size:7px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.param-val{font-family:var(--mono);font-size:11px;font-weight:600;margin-top:3px;color:var(--blue)}
.vf-seuils{display:grid;grid-template-columns:repeat(3,1fr);gap:3px;margin-top:7px}
.vf-item{background:var(--surface2);border:1px solid var(--border);
  border-radius:var(--r-sm);padding:4px;text-align:center}
.vf-item-lbl{font-size:7px;color:var(--muted);text-transform:uppercase;letter-spacing:.3px}
.vf-item-val{font-family:var(--mono);font-size:11px;font-weight:600;margin-top:1px}
.conf-row{display:flex;align-items:center;gap:7px;margin-top:7px}
.conf-lbl{font-size:9px;color:var(--muted);white-space:nowrap}
.conf-bar{flex:1;height:4px;background:var(--border);border-radius:3px;overflow:hidden}
.conf-fill{height:100%;border-radius:3px;transition:width .8s ease}
.conf-pct{font-family:var(--mono);font-size:12px;font-weight:600;min-width:36px;text-align:right}
.apps-box{margin-top:7px;padding:7px 9px;background:var(--green-lt);
  border-radius:var(--r-sm);border-left:2px solid var(--green)}
.apps-lbl{font-size:8px;color:var(--green);font-weight:600;text-transform:uppercase;letter-spacing:.8px}
.apps-txt{font-size:9px;color:rgba(61,220,132,.8);margin-top:2px;line-height:1.5}
.votes{display:flex;flex-wrap:wrap;gap:3px;margin-top:7px}
.vote-badge{font-size:8px;padding:2px 6px;border-radius:3px;font-weight:600;font-family:var(--mono)}
.vote-ok{background:var(--green-lt);color:var(--green)}
.vote-warn{background:var(--amber-lt);color:var(--amber)}
.cands{margin-top:7px;padding-top:7px;border-top:1px solid var(--border)}
.cand-title{font-size:8px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.cand-item{display:flex;align-items:center;gap:5px;padding:2px 0;
  border-bottom:1px solid var(--border);font-size:9px}
.cand-item:last-child{border:none}
.cand-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0}
.cand-name{flex:1;color:var(--muted)}
.cand-bar{width:45px;height:3px;background:var(--border);border-radius:2px;overflow:hidden}
.cand-fill{height:100%;border-radius:2px}
.cand-score{font-family:var(--mono);font-size:9px;color:var(--muted);width:28px;text-align:right}
.hint{font-size:10px;color:var(--muted);text-align:center;margin-top:7px;padding:8px;
  background:var(--surface2);border-radius:var(--r-sm);border:1px dashed var(--border2)}
.shockley-row{display:grid;grid-template-columns:1fr 1fr;gap:5px}
.shockley-row label{margin-top:0}
.shockley-eq{margin-top:5px;padding:5px 8px;background:var(--surface2);border:1px solid var(--border);
  border-radius:var(--r-sm);font-family:var(--mono);font-size:9px;color:var(--muted);text-align:center}
.export-row{display:flex;gap:5px}
.export-row .btn{flex:1;font-size:10px;padding:6px}
.divider{height:1px;background:var(--border);margin:6px 0}

/* ── VIEW TOGGLE (diode/bjt) ── */
.view-diode .bjt-only{display:none}
.view-bjt .diode-only{display:none}
.view-bjt .panel-hd i.panel-icon{color:var(--purple)}

/* ── TOAST ── */
.toast{position:fixed;bottom:16px;right:16px;z-index:999;
  padding:8px 14px;border-radius:var(--r-sm);font-size:11px;font-weight:500;
  background:var(--surface);border:1px solid var(--border2);color:var(--text);
  transform:translateY(60px);opacity:0;transition:all .25s;pointer-events:none;
  box-shadow:0 4px 20px rgba(0,0,0,.4)}
.toast.show{transform:translateY(0);opacity:1}
.toast.ok{border-color:rgba(61,220,132,.5);color:var(--green)}
.toast.err{border-color:rgba(255,95,109,.5);color:var(--red)}
.toast.info{border-color:rgba(74,158,255,.5);color:var(--blue)}

/* ── CHIP ── */
.chip{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;
  border-radius:20px;font-size:9px;font-weight:600;font-family:var(--mono)}
.chip-blue{background:var(--blue-lt);color:var(--blue);border:1px solid rgba(74,158,255,.3)}
.chip-purple{background:var(--purple-lt);color:var(--purple);border:1px solid rgba(167,139,250,.3)}
</style>
</head>
<body>

<!-- ══ MODE BAR ══ -->
<header class="mode-bar">
  <div class="logo">
    <div class="logo-icon">⚡</div>
    <div>
      <div class="logo-name">Smart Component Lab</div>
      <div class="logo-sub">ESP32 · MCP4725 · 2N2222</div>
    </div>
  </div>

  <div class="mode-tabs">
    <button class="mode-tab active" id="tab-diode" onclick="switchMode('diode')">
      <i class="ti ti-circle-half-2"></i> Diode / LED
    </button>
    <button class="mode-tab" id="tab-bjt" onclick="switchMode('bjt')">
      <i class="ti ti-cpu"></i> Transistor 2N2222
    </button>
  </div>

  <div class="hdr-right">
    <div class="hdr-stat">
      <div class="hdr-val" id="hv" style="color:var(--blue)">0.000<span style="font-size:9px;color:var(--muted)"> V</span></div>
      <div class="hdr-lbl">Tension</div>
    </div>
    <div class="hdr-stat">
      <div class="hdr-val" id="hi" style="color:var(--green)">0.000<span style="font-size:9px;color:var(--muted)"> mA</span></div>
      <div class="hdr-lbl">Courant</div>
    </div>
    <div class="hdr-stat">
      <div class="hdr-val" id="hpts" style="color:var(--muted)">0<span style="font-size:9px;color:var(--muted)"> pts</span></div>
      <div class="hdr-lbl">Points</div>
    </div>
    <div class="status-pill">
      <div class="sdot" id="sdot"></div>
      <span id="stxt">Idle</span>
    </div>
  </div>
</header>

<!-- ══ LAYOUT ══ -->
<div class="layout view-diode" id="main-layout">

  <!-- ══ COLONNE GAUCHE ══ -->
  <div class="col">

    <!-- Contrôle Diode -->
    <div class="panel diode-only" id="ctrl-diode">
      <div class="panel-hd">
        <i class="ti ti-circle-half-2 panel-icon"></i>
        <span class="panel-title">Diode / LED</span>
      </div>
      <label>V max sweep (V)</label>
      <input type="number" id="vmax" value="3.3" step="0.1" min="0.5" max="5">
      <label>Pas (V)</label>
      <input type="number" id="vstep" value="0.02" step="0.01" min="0.005">
      <div style="margin-top:10px">
        <button class="btn btn-start" onclick="startDiode()"><i class="ti ti-player-play"></i> Start sweep</button>
        <button class="btn btn-stop"  onclick="stopSweep()"><i class="ti ti-player-stop"></i> Stop</button>
        <button class="btn"           onclick="resetAll()"><i class="ti ti-refresh"></i> Reset tout</button>
      </div>
    </div>

    <!-- Contrôle BJT -->
    <div class="panel bjt-only" id="ctrl-bjt">
      <div class="panel-hd">
        <i class="ti ti-cpu bjt-icon panel-icon"></i>
        <span class="panel-title">Transistor 2N2222</span>
      </div>
      <label>Courbe active (IB)</label>
      <div class="ib-grid" id="ib-btns">
        <button class="ib-btn active" id="ibBtn-IB1" onclick="selectIb('IB1')">IB1<br><span style="font-size:8px;opacity:.7">10µA</span></button>
        <button class="ib-btn" id="ibBtn-IB2" onclick="selectIb('IB2')">IB2<br><span style="font-size:8px;opacity:.7">20µA</span></button>
        <button class="ib-btn" id="ibBtn-IB3" onclick="selectIb('IB3')">IB3<br><span style="font-size:8px;opacity:.7">40µA</span></button>
        <button class="ib-btn" id="ibBtn-IB4" onclick="selectIb('IB4')">IB4<br><span style="font-size:8px;opacity:.7">60µA</span></button>
        <button class="ib-btn" id="ibBtn-IB5" onclick="selectIb('IB5')">IB5<br><span style="font-size:8px;opacity:.7">80µA</span></button>
        <button class="ib-btn" id="ibBtn-IB6" onclick="selectIb('IB6')">IB6<br><span style="font-size:8px;opacity:.7">100µA</span></button>
      </div>
      <label>Vce max (V)</label>
      <input type="number" id="vmax-bjt" value="5" step="0.5" min="0.5" max="10">
      <label>Pas (V)</label>
      <input type="number" id="vstep-bjt" value="0.05" step="0.01" min="0.01">
      <div style="margin-top:10px">
        <button class="btn btn-start" onclick="startBjt()"><i class="ti ti-player-play"></i> Mesurer courbe</button>
        <button class="btn btn-stop"  onclick="stopSweep()"><i class="ti ti-player-stop"></i> Stop</button>
        <button class="btn btn-bjt"   onclick="analyzeBjt()"><i class="ti ti-math-function"></i> Analyser β / zones</button>
        <button class="btn"           onclick="resetAll()"><i class="ti ti-refresh"></i> Reset tout</button>
      </div>
    </div>

    <!-- Live -->
    <div class="panel">
      <div class="panel-hd">
        <i class="ti ti-bolt panel-icon"></i>
        <span class="panel-title">Live</span>
        <span id="pts-lbl" style="margin-left:auto;font-family:var(--mono);font-size:9px;color:var(--muted)">0 pts</span>
      </div>
      <div class="live-grid">
        <div class="live-box">
          <div class="live-val" id="lv" style="color:var(--blue)">0.000</div>
          <div class="live-lbl" id="lv-lbl">Volts (U)</div>
        </div>
        <div class="live-box">
          <div class="live-val" id="li" style="color:var(--green)">0.000</div>
          <div class="live-lbl" id="li-lbl">mA (I)</div>
        </div>
      </div>
    </div>

    <!-- Table -->
    <div class="panel" style="flex:1;display:flex;flex-direction:column;min-height:0">
      <div class="panel-hd">
        <i class="ti ti-table panel-icon"></i>
        <span class="panel-title">Données</span>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead><tr>
            <th>#</th>
            <th id="col1-hd">U (V)</th>
            <th id="col2-hd">I (mA)</th>
          </tr></thead>
          <tbody id="tbody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ══ COLONNE CENTRE ══ -->
  <div class="col">

    <!-- Graphique principal -->
    <div class="panel" style="flex:1;display:flex;flex-direction:column">
      <div class="panel-hd">
        <i class="ti ti-chart-line panel-icon"></i>
        <span class="panel-title" id="chart-title">Courbe I = f(U)</span>
        <div class="curve-btns">
          <button class="curve-btn diode-only" onclick="clearMeasured()"><i class="ti ti-eraser"></i> Mesure</button>
          <button class="curve-btn diode-only" onclick="clearTheory()"><i class="ti ti-line-dashed"></i> Théo.</button>
          <button class="curve-btn bjt-only"   onclick="clearBjt()"><i class="ti ti-eraser"></i> Tout effacer</button>
        </div>
        <span style="font-size:8px;color:var(--hint);margin-left:5px">Scroll=zoom · Drag=pan</span>
      </div>
      <div class="chart-wrap">
        <canvas id="chart" role="img"></canvas>
      </div>

      <!-- Légende IB (BJT only) -->
      <div class="ib-legend bjt-only" id="ib-legend"></div>

      <div>
        <div class="axes-grid">
          <div><label>X min</label><input type="number" id="xmin" value="0" step="0.1" oninput="applyAxes()"></div>
          <div><label>X max</label><input type="number" id="xmax" value="3.3" step="0.1" oninput="applyAxes()"></div>
          <div><label>Y min</label><input type="number" id="ymin" value="0" step="0.05" oninput="applyAxes()"></div>
          <div><label>Y max</label><input type="number" id="ymax" value="2" step="0.1" oninput="applyAxes()"></div>
        </div>
        <div class="axes-btns">
          <button class="btn" onclick="chart.resetZoom()"><i class="ti ti-zoom-reset"></i> Reset zoom</button>
          <button class="btn" onclick="autoScale()"><i class="ti ti-arrows-maximize"></i> Auto</button>
        </div>
      </div>
    </div>

    <!-- Shockley (diode only) -->
    <div class="panel diode-only">
      <div class="panel-hd">
        <i class="ti ti-math-function panel-icon"></i>
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

    <!-- BJT params (bjt only) -->
    <div class="panel bjt-only" id="bjt-params-panel">
      <div class="panel-hd">
        <i class="ti ti-chart-bar bjt-icon panel-icon"></i>
        <span class="panel-title">Paramètres 2N2222</span>
      </div>
      <div class="bjt-params-grid">
        <div class="bjt-param">
          <div class="bjt-param-val" id="b-beta">—</div>
          <div class="bjt-param-lbl">β (hFE)</div>
        </div>
        <div class="bjt-param">
          <div class="bjt-param-val" id="b-icmax" style="color:var(--cyan)">—</div>
          <div class="bjt-param-lbl">Ic max (mA)</div>
        </div>
        <div class="bjt-param">
          <div class="bjt-param-val" id="b-vsat" style="color:var(--amber)">—</div>
          <div class="bjt-param-lbl">Vce_sat (V)</div>
        </div>
      </div>
      <div style="margin-top:8px">
        <div class="beta-row" id="beta-row" style="display:none">
          <div>
            <div class="beta-val" id="beta-big">—</div>
            <div class="beta-lbl">Gain en courant β = Ic / Ib</div>
          </div>
          <div style="margin-left:auto;text-align:right">
            <div style="font-size:9px;color:var(--muted)">2N2222 typique</div>
            <div style="font-family:var(--mono);font-size:11px;color:var(--purple)">75 – 300 hFE</div>
          </div>
        </div>
      </div>
      <div class="zones-box" style="margin-top:8px">
        <div class="zone-row">
          <div class="zone-dot" style="background:var(--amber)"></div>
          <div class="zone-name" style="color:var(--amber)">Saturation</div>
          <div class="zone-desc">Vce &lt; 0.3 V — interrupteur fermé</div>
        </div>
        <div class="zone-row">
          <div class="zone-dot" style="background:var(--blue)"></div>
          <div class="zone-name" style="color:var(--blue)">Zone active</div>
          <div class="zone-desc">Amplification — Ic = β · Ib</div>
        </div>
        <div class="zone-row">
          <div class="zone-dot" style="background:var(--hint)"></div>
          <div class="zone-name" style="color:var(--hint)">Blocage</div>
          <div class="zone-desc">Ib = 0 — interrupteur ouvert</div>
        </div>
      </div>
    </div>
  </div>

  <!-- ══ COLONNE DROITE ══ -->
  <div class="col right-col">

    <!-- Identification Diode (diode only) -->
    <div class="panel diode-only">
      <div class="panel-hd">
        <i class="ti ti-sparkles panel-icon"></i>
        <span class="panel-title">Identification IA</span>
      </div>
      <button class="btn btn-id" id="btn-id" onclick="identify()">
        <i class="ti ti-search"></i> Identifier diode / LED
      </button>
      <div class="hint" id="id-hint">Minimum 6 points requis</div>
      <div id="id-result" style="display:none">
        <div class="id-card" id="id-card">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:6px">
            <div>
              <div class="id-type" id="id-type">—</div>
              <div class="id-model" id="id-model">—</div>
            </div>
            <div id="id-dot" style="width:10px;height:10px;border-radius:50%;flex-shrink:0;margin-top:4px"></div>
          </div>
          <div class="id-desc" id="id-desc">—</div>
          <div class="vf-seuils">
            <div class="vf-item"><div class="vf-item-lbl">Vf @ 1 mA</div><div class="vf-item-val" id="vf-1" style="color:var(--blue)">—</div></div>
            <div class="vf-item"><div class="vf-item-lbl">Vf @ 5 mA</div><div class="vf-item-val" id="vf-5" style="color:var(--green)">—</div></div>
            <div class="vf-item"><div class="vf-item-lbl">Vf @ 10 mA</div><div class="vf-item-val" id="vf-10" style="color:var(--amber)">—</div></div>
          </div>
          <div class="params-grid">
            <div class="param"><div class="param-name">n idéalité</div><div class="param-val" id="p-n">—</div></div>
            <div class="param"><div class="param-name">Is</div><div class="param-val" id="p-is" style="font-size:8px">—</div></div>
            <div class="param"><div class="param-name">R²</div><div class="param-val" id="p-r2">—</div></div>
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

    <!-- BJT Info (bjt only) -->
    <div class="panel bjt-only">
      <div class="panel-hd">
        <i class="ti ti-info-circle bjt-icon panel-icon"></i>
        <span class="panel-title">Guide 2N2222</span>
      </div>
      <div style="font-size:10px;color:var(--muted);line-height:1.7">
        <div style="margin-bottom:6px">
          <span class="chip chip-purple">NPN Si</span>
          <span style="margin-left:6px;font-size:9px">Transistor bipolaire jonction</span>
        </div>
        <div class="divider"></div>
        <div><b style="color:var(--text)">β (hFE)</b> = 75–300 — gain courant</div>
        <div><b style="color:var(--text)">Vce_max</b> = 40 V</div>
        <div><b style="color:var(--text)">Ic_max</b> = 600 mA</div>
        <div><b style="color:var(--text)">Vbe_on</b> ≈ 0.6–0.7 V</div>
        <div><b style="color:var(--text)">f_T</b> = 300 MHz</div>
        <div class="divider"></div>
        <div style="font-size:9px;margin-top:2px">
          <b style="color:var(--purple)">Procédure de mesure :</b><br>
          1. Sélectionner une courbe IB<br>
          2. Cliquer "Mesurer courbe"<br>
          3. Attendre la fin du sweep<br>
          4. Répéter pour chaque IB<br>
          5. Cliquer "Analyser β / zones"
        </div>
      </div>
    </div>

    <!-- Export -->
    <div class="panel">
      <div class="panel-hd">
        <i class="ti ti-download panel-icon"></i>
        <span class="panel-title">Export</span>
      </div>
      <div class="export-row">
        <button class="btn" onclick="exportCSV()"><i class="ti ti-file-type-csv"></i> CSV</button>
        <button class="btn" onclick="exportPDF()"><i class="ti ti-file-type-pdf"></i> PDF</button>
      </div>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
// ── State ──────────────────────────────────────
let chart, currentRes = null, isRunning = false;
let activeMode = 'diode';   // 'diode' | 'bjt'
let activeIb   = 'IB1';
let bjtData    = {};        // { IB1: [{x,y}], IB2: [...] }
let bjtParams  = null;

const IB_COLORS = {
  IB1:'#4a9eff', IB2:'#ff6b6b', IB3:'#3ddc84',
  IB4:'#ffb347', IB5:'#a78bfa', IB6:'#38bdf8'
};
const IB_UA = {IB1:10, IB2:20, IB3:40, IB4:60, IB5:80, IB6:100};

// ── Toast ─────────────────────────────────────
function toast(msg, type='info', ms=2500){
  const el = document.getElementById('toast');
  el.textContent = msg; el.className = 'toast ' + type + ' show';
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.className = 'toast'; }, ms);
}

// ── Mode switch ────────────────────────────────
function switchMode(mode) {
  activeMode = mode;
  const layout = document.getElementById('main-layout');
  layout.className = 'layout view-' + mode;

  document.getElementById('tab-diode').className = 'mode-tab' + (mode === 'diode' ? ' active' : '');
  document.getElementById('tab-bjt').className   = 'mode-tab' + (mode === 'bjt'   ? ' active bjt' : '');

  const title = document.getElementById('chart-title');
  if (mode === 'bjt') {
    title.textContent = 'Ic = f(Vce) — Famille de courbes';
    document.getElementById('xmax').value = '5';
    document.getElementById('ymax').value = '30';
    document.getElementById('col1-hd').textContent = 'Vce (V)';
    document.getElementById('col2-hd').textContent = 'Ic (mA)';
    document.getElementById('lv-lbl').textContent  = 'Volts (Vce)';
    document.getElementById('li-lbl').textContent  = 'mA (Ic)';
    applyAxes();
    rebuildBjtChart();
  } else {
    title.textContent = 'Courbe I = f(U)';
    document.getElementById('xmax').value = '3.3';
    document.getElementById('ymax').value = '2';
    document.getElementById('col1-hd').textContent = 'U (V)';
    document.getElementById('col2-hd').textContent = 'I (mA)';
    document.getElementById('lv-lbl').textContent  = 'Volts (U)';
    document.getElementById('li-lbl').textContent  = 'mA (I)';
    applyAxes();
  }
}

// ── IB selector ───────────────────────────────
function selectIb(label) {
  activeIb = label;
  document.querySelectorAll('.ib-btn').forEach(b => b.classList.remove('active'));
  const btn = document.getElementById('ibBtn-' + label);
  if (btn) btn.classList.add('active');
  fetch('/set_mode', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({type: 'bjt', ib_label: label})
  }).catch(() => {});
  toast('Courbe ' + label + ' (' + IB_UA[label] + ' µA) sélectionnée', 'info');
}

// ── Chart init ────────────────────────────────
function initChart(){
  const ctx = document.getElementById('chart').getContext('2d');
  chart = new Chart(ctx, {
    type: 'line',
    data: { datasets: [
      { label:'Mesure', data:[], order:1,
        borderColor:'#4a9eff', backgroundColor:'rgba(74,158,255,0.07)',
        pointRadius:2, borderWidth:2, tension:.3, fill:true },
      { label:'Shockley', data:[], order:3,
        borderColor:'#ff6b6b', backgroundColor:'transparent',
        pointRadius:0, borderWidth:1.5, showLine:true, tension:.4,
        segment:{borderDash:[6,3]} },
      { label:'Théorique', data:[], order:2,
        borderColor:'#ffb347', backgroundColor:'transparent',
        pointRadius:0, borderWidth:2, showLine:true, tension:.4, hidden:true,
        segment:{borderDash:[4,3]} }
    ]},
    options:{
      responsive:true, maintainAspectRatio:false, animation:false, parsing:false,
      interaction:{ mode:'nearest', intersect:false, axis:'x' },
      plugins:{
        legend:{ labels:{ color:'#7a88aa', font:{size:9,family:"'Inter',sans-serif"},
          boxWidth:18, padding:10, filter:i => !i.hidden } },
        tooltip:{
          backgroundColor:'#181c27', borderColor:'#3a4460', borderWidth:1,
          titleColor:'#4a9eff', bodyColor:'#e8ecf4', padding:8,
          callbacks:{
            title: i => {
              const x = Number(i[0].parsed.x).toFixed(3);
              return activeMode === 'bjt' ? 'Vce = ' + x + ' V' : 'U = ' + x + ' V';
            },
            label: i => {
              const y = Number(i[0].parsed.y).toFixed(4);
              const prefix = activeMode === 'bjt' ? 'Ic' : 'I';
              return (i[0].dataset.ibLabel || i[0].dataset.label || prefix) + ': ' + y + ' mA';
            }
          }
        },
        zoom:{
          zoom:{ wheel:{enabled:true,speed:.08}, pinch:{enabled:true}, mode:'xy' },
          pan:{ enabled:true, mode:'xy' }
        }
      },
      scales:{
        x:{ type:'linear', min:0, max:3.3,
          title:{display:true, text:'U (V)', color:'#7a88aa', font:{size:10}},
          ticks:{color:'#4a5570', font:{size:9}, maxTicksLimit:10},
          grid:{color:'rgba(255,255,255,0.04)'}
        },
        y:{ min:0, max:2,
          title:{display:true, text:'I (mA)', color:'#7a88aa', font:{size:10}},
          ticks:{color:'#4a5570', font:{size:9}},
          grid:{color:'rgba(255,255,255,0.04)'}
        }
      }
    }
  });
}

// ── Rebuild BJT chart (multi-courbes) ─────────
function rebuildBjtChart(){
  // Garder 3 datasets fixes (diode) + ajouter dynamiquement les courbes BJT
  // Pour BJT on remplace tout
  const labels = Object.keys(IB_COLORS);
  const datasets = [];

  labels.forEach(lbl => {
    const pts = bjtData[lbl] || [];
    datasets.push({
      label: lbl + ' (' + IB_UA[lbl] + ' µA)',
      ibLabel: lbl,
      data: pts,
      borderColor: IB_COLORS[lbl],
      backgroundColor: 'transparent',
      pointRadius: pts.length < 50 ? 2 : 0,
      borderWidth: 2,
      tension: .3,
      showLine: true,
      hidden: pts.length === 0,
    });
  });

  chart.data.datasets = datasets;
  chart.options.scales.x.title.text = 'Vce (V)';
  chart.options.scales.y.title.text = 'Ic (mA)';
  chart.update('none');
  updateIbLegend();
}

// ── Rebuild Diode chart ───────────────────────
function rebuildDiodeChart(){
  chart.data.datasets = [
    { label:'Mesure', data:[], order:1,
      borderColor:'#4a9eff', backgroundColor:'rgba(74,158,255,0.07)',
      pointRadius:2, borderWidth:2, tension:.3, fill:true },
    { label:'Shockley', data:[], order:3,
      borderColor:'#ff6b6b', backgroundColor:'transparent',
      pointRadius:0, borderWidth:1.5, showLine:true, tension:.4,
      segment:{borderDash:[6,3]} },
    { label:'Théorique', data:[], order:2,
      borderColor:'#ffb347', backgroundColor:'transparent',
      pointRadius:0, borderWidth:2, showLine:true, tension:.4, hidden:true,
      segment:{borderDash:[4,3]} }
  ];
  chart.options.scales.x.title.text = 'U (V)';
  chart.options.scales.y.title.text = 'I (mA)';
  chart.update('none');
}

// ── IB Legend ─────────────────────────────────
function updateIbLegend(){
  const el = document.getElementById('ib-legend');
  let html = '';
  Object.keys(IB_COLORS).forEach(lbl => {
    const has = bjtData[lbl] && bjtData[lbl].length > 0;
    if (has) {
      html += `<div class="ib-leg-item">
        <div class="ib-leg-dot" style="background:${IB_COLORS[lbl]}"></div>
        ${lbl} · ${IB_UA[lbl]}µA
      </div>`;
    }
  });
  el.innerHTML = html;
}

// ── Shockley ──────────────────────────────────
function shockleyPts(Is_nA, n, Vt_mV, xmax, steps=500){
  const Is = Is_nA*1e-9, Vt = Vt_mV*1e-3, pts = [];
  for(let i = 0; i <= steps; i++){
    const V = (xmax/steps)*i;
    const I = Is*(Math.exp(V/(n*Vt))-1)*1000;
    if(I >= 0 && I < 1e6) pts.push({x:V, y:I});
  }
  return pts;
}

function updateShockley(){
  if(activeMode !== 'diode') return;
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

// ── Axes ──────────────────────────────────────
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
  if(activeMode === 'diode') { updateShockley(); if(currentRes) drawTheory(currentRes); }
}

function autoScale(){
  let allX = [], allY = [];
  if (activeMode === 'bjt') {
    Object.values(bjtData).forEach(pts => {
      pts.forEach(p => { allX.push(p.x); allY.push(p.y); });
    });
  } else {
    const d = chart.data.datasets[0].data;
    d.forEach(p => { allX.push(p.x); allY.push(p.y); });
  }
  if(!allX.length){ toast('Aucune donnée', 'err'); return; }
  const xm = Math.max(...allX)*1.08, ym = Math.max(...allY)*1.20;
  document.getElementById('xmax').value = xm.toFixed(2);
  document.getElementById('ymax').value = ym.toFixed(2);
  applyAxes();
}

// ── Status ────────────────────────────────────
function setStatus(s){
  const dot = document.getElementById('sdot'), txt = document.getElementById('stxt');
  dot.className = 'sdot';
  if(s === 'live'){ dot.classList.add('live'); txt.textContent = 'Live'; }
  else if(s === 'stop'){ dot.classList.add('stop'); txt.textContent = 'Stop'; }
  else { txt.textContent = 'Idle'; }
}

// ── Controls ──────────────────────────────────
function startDiode(){
  fetch('/start', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({type:'diode', reset:true})
  }).catch(()=>{}).finally(()=>{
    isRunning = true; setStatus('live');
    if(activeMode === 'diode'){
      rebuildDiodeChart();
      currentRes = null;
      document.getElementById('id-result').style.display = 'none';
      document.getElementById('id-hint').textContent = 'Minimum 6 points requis';
    }
    document.getElementById('tbody').innerHTML = '';
    document.getElementById('pts-lbl').textContent = '0 pts';
    toast('Sweep diode démarré', 'ok');
  });
}

function startBjt(){
  fetch('/start', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({type:'bjt', ib_label: activeIb, reset:false})
  }).catch(()=>{}).finally(()=>{
    isRunning = true; setStatus('live');
    toast('Mesure ' + activeIb + ' (' + IB_UA[activeIb] + ' µA) démarrée', 'ok');
    // marquer le bouton comme "en cours"
    const btn = document.getElementById('ibBtn-' + activeIb);
    if(btn) btn.style.borderColor = 'var(--blue)';
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
    bjtData = {}; bjtParams = null;
    rebuildDiodeChart();
    currentRes = null;
    document.getElementById('tbody').innerHTML = '';
    ['lv','li'].forEach(id => document.getElementById(id).textContent = '0.000');
    ['hv','hi'].forEach((id,i) => {
      document.getElementById(id).innerHTML = '0.000<span style="font-size:9px;color:var(--muted)"> ' + (i?'mA':'V') + '</span>';
    });
    document.getElementById('hpts').innerHTML = '0<span style="font-size:9px;color:var(--muted)"> pts</span>';
    document.getElementById('pts-lbl').textContent = '0 pts';
    document.getElementById('id-result').style.display = 'none';
    document.getElementById('id-hint').textContent = 'Minimum 6 points requis';
    // reset ib buttons
    document.querySelectorAll('.ib-btn').forEach(b => { b.className = 'ib-btn'; b.style.borderColor = ''; });
    document.getElementById('ibBtn-IB1').classList.add('active');
    // reset bjt params
    ['b-beta','b-icmax','b-vsat','beta-big'].forEach(id => document.getElementById(id).textContent = '—');
    document.getElementById('beta-row').style.display = 'none';
    document.getElementById('ib-legend').innerHTML = '';
    if(activeMode === 'bjt') rebuildBjtChart();
    toast('Tout réinitialisé', 'info');
  });
}

// ── Analyze BJT ───────────────────────────────
function analyzeBjt(){
  const btn = document.querySelector('.btn-bjt');
  if(btn){ btn.disabled = true; btn.innerHTML = '<i class="ti ti-loader-2"></i> Analyse...'; }
  fetch('/analyze_bjt').then(r => r.json()).then(res => {
    if(btn){ btn.disabled = false; btn.innerHTML = '<i class="ti ti-math-function"></i> Analyser β / zones'; }
    if(res.error){ toast('⚠ ' + res.error, 'err'); return; }
    bjtParams = res;
    const beta = res.beta_avg;
    document.getElementById('b-beta').textContent   = beta ? beta.toFixed(0) : '—';
    document.getElementById('b-icmax').textContent  = res.ic_max ? res.ic_max.toFixed(2) : '—';
    document.getElementById('b-vsat').textContent   = res.vce_sat ? res.vce_sat.toFixed(3) : '—';
    if (beta) {
      document.getElementById('beta-big').textContent = beta.toFixed(0);
      document.getElementById('beta-row').style.display = 'flex';
    }
    toast('β = ' + (beta ? beta.toFixed(0) : '?') + ' — analyse OK', 'ok', 3000);
  }).catch(() => {
    if(btn){ btn.disabled = false; btn.innerHTML = '<i class="ti ti-math-function"></i> Analyser β / zones'; }
    toast('Erreur analyse BJT', 'err');
  });
}

// ── Clear ─────────────────────────────────────
function clearMeasured(){
  chart.data.datasets[0].data = []; chart.update('none');
  toast('Courbe mesure effacée', 'info');
}
function clearTheory(){
  chart.data.datasets[2].data = []; chart.data.datasets[2].hidden = true;
  chart.update('none'); toast('Courbe théorique effacée', 'info');
}
function clearBjt(){
  bjtData = {};
  fetch('/reset').catch(()=>{});
  rebuildBjtChart();
  document.getElementById('tbody').innerHTML = '';
  document.getElementById('pts-lbl').textContent = '0 pts';
  document.querySelectorAll('.ib-btn').forEach(b => { b.className = 'ib-btn'; b.style.borderColor = ''; });
  document.getElementById('ibBtn-IB1').classList.add('active');
  ['b-beta','b-icmax','b-vsat','beta-big'].forEach(id => document.getElementById(id).textContent = '—');
  document.getElementById('beta-row').style.display = 'none';
  toast('Courbes BJT effacées', 'info');
}

// ── Identification Diode ───────────────────────
function identify(){
  const btn = document.getElementById('btn-id');
  btn.disabled = true;
  btn.innerHTML = '<i class="ti ti-loader-2"></i> Analyse...';
  fetch('/identify').then(r => r.json()).then(res => {
    btn.disabled = false;
    btn.innerHTML = '<i class="ti ti-search"></i> Identifier diode / LED';
    if(res.error){
      toast('⚠ ' + (res.error === 'not enough data' ? 'Minimum 6 points requis' : res.error), 'err', 3000);
      document.getElementById('id-hint').textContent = res.error === 'not enough data' ? 'Minimum 6 points requis' : res.error;
      return;
    }
    currentRes = res;
    document.getElementById('id-hint').textContent = '';
    document.getElementById('id-result').style.display = 'block';
    const card = document.getElementById('id-card');
    card.style.borderColor = res.color;
    card.style.boxShadow   = `0 0 0 3px ${res.color}18`;
    document.getElementById('id-dot').style.cssText =
      `background:${res.color};width:10px;height:10px;border-radius:50%;flex-shrink:0;margin-top:4px`;
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
    const conf = res.confidence;
    const cc   = conf > 75 ? 'var(--green)' : conf > 45 ? 'var(--amber)' : 'var(--red)';
    document.getElementById('conf-pct').textContent = conf + ' %';
    document.getElementById('conf-pct').style.color = cc;
    const fill = document.getElementById('conf-fill');
    fill.style.width      = conf + '%';
    fill.style.background = conf > 75 ? '#3ddc84' : conf > 45 ? '#ffb347' : '#ff5f6d';
    const votesEl = document.getElementById('votes');
    votesEl.innerHTML = '';
    (res.method_votes || []).forEach(v => {
      const sp = document.createElement('span');
      sp.className = 'vote-badge ' + (v.ok ? 'vote-ok' : 'vote-warn');
      sp.textContent = v.label + ' → ' + v.result;
      votesEl.appendChild(sp);
    });
    if(res.scores && res.scores.length > 1){
      const maxSc = Math.max(1, res.scores[0].score);
      let html = '<div class="cand-title">Autres candidats</div>';
      res.scores.slice(1,5).forEach(s => {
        const pct = Math.max(0, s.score / maxSc * 100).toFixed(0);
        html += `<div class="cand-item">
          <div class="cand-dot" style="background:${s.diode.color}"></div>
          <div class="cand-name">${s.diode.name}</div>
          <div class="cand-bar"><div class="cand-fill" style="width:${pct}%;background:${s.diode.color}"></div></div>
          <div class="cand-score">${Math.max(0,s.score).toFixed(1)}</div>
        </div>`;
      });
      document.getElementById('cands').innerHTML = html;
    }
    document.getElementById('Is_v').value = res.Is_nA.toFixed(4);
    document.getElementById('n_v').value  = res.n;
    updateShockley(); drawTheory(res);
    toast('✓ ' + res.type + ' — confiance ' + conf + ' %', 'ok', 3000);
  }).catch(() => {
    btn.disabled = false;
    btn.innerHTML = '<i class="ti ti-search"></i> Identifier diode / LED';
    toast('Erreur connexion serveur', 'err');
  });
}

// ── Export ────────────────────────────────────
function exportCSV(){ window.location.href = '/export_csv?mode=' + activeMode; }
function exportPDF(){ window.location.href = '/export_pdf?mode=' + activeMode; }

// ── Polling ───────────────────────────────────
let lastPts = 0;

function updateLive(){
  if(activeMode === 'diode'){
    fetch('/get_data').then(r => r.json()).then(data => {
      if(activeMode !== 'diode') return;
      chart.data.datasets[0].data = data.map(d => ({x:+d.U, y:+d.I}));
      chart.update('none');
      const n = data.length;
      document.getElementById('pts-lbl').textContent = n + ' pts';
      document.getElementById('hpts').innerHTML = n + '<span style="font-size:9px;color:var(--muted)"> pts</span>';
      const sl = data.slice(-60);
      document.getElementById('tbody').innerHTML = sl.map((d,i) =>
        `<tr><td>${data.length-sl.length+i+1}</td><td>${(+d.U).toFixed(3)}</td><td>${(+d.I).toFixed(3)}</td></tr>`
      ).join('');
      if(n > 0){
        const last = data[n-1];
        const U = (+last.U).toFixed(3), I = (+last.I).toFixed(3);
        document.getElementById('lv').textContent = U;
        document.getElementById('li').textContent = I;
        document.getElementById('hv').innerHTML  = U + '<span style="font-size:9px;color:var(--muted)"> V</span>';
        document.getElementById('hi').innerHTML  = I + '<span style="font-size:9px;color:var(--muted)"> mA</span>';
      }
    }).catch(()=>{});
  } else {
    // Mode BJT : polling get_bjt
    fetch('/get_bjt').then(r => r.json()).then(data => {
      if(activeMode !== 'bjt') return;
      let changed = false;
      let totalPts = 0;
      Object.keys(data).forEach(lbl => {
        const pts = data[lbl].map(p => ({x:p.Vce, y:p.Ic}));
        totalPts += pts.length;
        const old = bjtData[lbl] || [];
        if(pts.length !== old.length){ changed = true; bjtData[lbl] = pts; }
      });
      if(changed){
        rebuildBjtChart();
        // Update header
        document.getElementById('pts-lbl').textContent = totalPts + ' pts';
        document.getElementById('hpts').innerHTML = totalPts + '<span style="font-size:9px;color:var(--muted)"> pts</span>';
        // Marquer boutons IB "done"
        Object.keys(data).forEach(lbl => {
          const btn = document.getElementById('ibBtn-' + lbl);
          if(btn && data[lbl].length > 0 && lbl !== activeIb){
            btn.classList.remove('active');
            btn.classList.add('done');
            btn.style.borderColor = '';
          }
        });
        // Live val = last point du IB actif
        const activePts = bjtData[activeIb] || [];
        if(activePts.length > 0){
          const last = activePts[activePts.length-1];
          document.getElementById('lv').textContent = last.x.toFixed(3);
          document.getElementById('li').textContent = last.y.toFixed(3);
          document.getElementById('hv').innerHTML  = last.x.toFixed(3) + '<span style="font-size:9px;color:var(--muted)"> V</span>';
          document.getElementById('hi').innerHTML  = last.y.toFixed(3) + '<span style="font-size:9px;color:var(--muted)"> mA</span>';
        }
        // Table : afficher dernière courbe active
        const sl = activePts.slice(-60);
        document.getElementById('tbody').innerHTML = sl.map((p,i) =>
          `<tr><td>${activePts.length-sl.length+i+1}</td><td>${p.x.toFixed(3)}</td><td>${p.y.toFixed(3)}</td></tr>`
        ).join('');
      }
    }).catch(()=>{});
  }
}

// ── Init ──────────────────────────────────────
window.onload = function(){
  initChart();
  updateShockley();
  setInterval(updateLive, 900);
};
</script>
</body>
</html>"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)