from flask import Flask, request, jsonify
import math, io, datetime

app = Flask(__name__)

# ═══════════════════════════════════════════════════════════
#  DATA STORAGE
# ═══════════════════════════════════════════════════════════
diode_store      = []
bjt_store        = {}    # {"IB1": [{VCE, IC}, ...], ...}
pv_store         = []
running          = False
identified_diode = None
current_type     = "diode"
current_ib_label = "IB1"

# ═══════════════════════════════════════════════════════════
#  BASE DE DONNÉES DIODES & LED — COMPLÈTE
# ═══════════════════════════════════════════════════════════
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
        "model": "1N34A / 1N60 / OA91 / AA112", "color": "#9c27b0",
        "description": "Semiconducteur Ge — Vf très bas, courant de fuite élevé, sensible à la température.",
        "vf_1mA": 0.20, "vf_1mA_min": 0.08, "vf_1mA_max": 0.35,
        "vf_5mA": 0.28, "vf_5mA_min": 0.14, "vf_5mA_max": 0.44,
        "vf_10mA": 0.34, "vf_10mA_min": 0.18, "vf_10mA_max": 0.52,
        "vf_typ": 0.25, "vf_min": 0.10, "vf_max": 0.45,
        "Is_nA": 800.0, "n_typ": 1.0, "n_min": 0.7, "n_max": 1.2,
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
        "model": "1N4001 / 1N4004 / 1N4007 / 1N5408", "color": "#03a9f4",
        "description": "Diode Si redresseur robuste — courant élevé, standard industriel 50/60 Hz.",
        "vf_1mA": 0.58, "vf_1mA_min": 0.44, "vf_1mA_max": 0.72,
        "vf_5mA": 0.72, "vf_5mA_min": 0.58, "vf_5mA_max": 0.86,
        "vf_10mA": 0.80, "vf_10mA_min": 0.64, "vf_10mA_max": 0.95,
        "vf_typ": 0.72, "vf_min": 0.58, "vf_max": 0.90,
        "Is_nA": 10.0, "n_typ": 1.8, "n_min": 1.5, "n_max": 2.1,
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
        "model": "TSUS5202 / LD271 / SFH484 (λ≈850–950 nm)", "color": "#b71c1c",
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
        "model": "L-934ID / HLMP-4700 (λ≈620–680 nm)", "color": "#e53935",
        "description": "LED GaAsP/AlGaInP — rouge classique, Vf modéré.",
        "vf_1mA": 1.65, "vf_1mA_min": 1.30, "vf_1mA_max": 2.10,
        "vf_5mA": 1.90, "vf_5mA_min": 1.55, "vf_5mA_max": 2.30,
        "vf_10mA": 2.00, "vf_10mA_min": 1.65, "vf_10mA_max": 2.45,
        "vf_typ": 1.85, "vf_min": 1.45, "vf_max": 2.30,
        "Is_nA": 0.0008, "n_typ": 2.0, "n_min": 1.7, "n_max": 2.3,
        "slope_factor": 1.4, "curvature": 0.40, "tech": "led", "wavelength": 650,
        "applications": "Signalisation, afficheurs 7 segments, indicateurs de présence.",
    },
    {
        "id": "led_orange", "name": "LED Orange",
        "model": "HLMP-EL3C / L-53HD (λ≈600–620 nm)", "color": "#fb8c00",
        "description": "LED GaAsP — orange vif, bonne visibilité diurne.",
        "vf_1mA": 1.85, "vf_1mA_min": 1.60, "vf_1mA_max": 2.15,
        "vf_5mA": 2.05, "vf_5mA_min": 1.78, "vf_5mA_max": 2.35,
        "vf_10mA": 2.15, "vf_10mA_min": 1.85, "vf_10mA_max": 2.48,
        "vf_typ": 2.05, "vf_min": 1.80, "vf_max": 2.35,
        "Is_nA": 0.0003, "n_typ": 2.0, "n_min": 1.8, "n_max": 2.2,
        "slope_factor": 1.4, "curvature": 0.40, "tech": "led", "wavelength": 610,
        "applications": "Signalisation routière, afficheurs, panneaux d'information.",
    },
    {
        "id": "led_yellow", "name": "LED Jaune",
        "model": "TLHY5100 / L-53YD (λ≈570–600 nm)", "color": "#fdd835",
        "description": "LED GaAsP/GaP — jaune, bon rendement lumineux.",
        "vf_1mA": 1.90, "vf_1mA_min": 1.68, "vf_1mA_max": 2.20,
        "vf_5mA": 2.10, "vf_5mA_min": 1.88, "vf_5mA_max": 2.42,
        "vf_10mA": 2.20, "vf_10mA_min": 1.96, "vf_10mA_max": 2.55,
        "vf_typ": 2.10, "vf_min": 1.90, "vf_max": 2.45,
        "Is_nA": 0.0001, "n_typ": 2.0, "n_min": 1.8, "n_max": 2.2,
        "slope_factor": 1.4, "curvature": 0.40, "tech": "led", "wavelength": 585,
        "applications": "Indicateurs, signalisation, balises lumineuses.",
    },
    {
        "id": "led_green_std", "name": "LED Verte standard",
        "model": "TLHG5800 / L-53GD (λ≈525–565 nm, GaP)", "color": "#43a047",
        "description": "LED GaP — verte classique, rendement modéré.",
        "vf_1mA": 1.90, "vf_1mA_min": 1.68, "vf_1mA_max": 2.20,
        "vf_5mA": 2.10, "vf_5mA_min": 1.88, "vf_5mA_max": 2.42,
        "vf_10mA": 2.20, "vf_10mA_min": 1.96, "vf_10mA_max": 2.55,
        "vf_typ": 2.10, "vf_min": 1.90, "vf_max": 2.45,
        "Is_nA": 0.00005, "n_typ": 2.0, "n_min": 1.8, "n_max": 2.2,
        "slope_factor": 1.4, "curvature": 0.40, "tech": "led", "wavelength": 545,
        "applications": "Indicateurs, afficheurs, signalisation.",
    },
    {
        "id": "led_green_hb", "name": "LED Verte HB",
        "model": "TLHG640 / OVLGG4C7 (λ≈520–530 nm, InGaN)", "color": "#00c853",
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
        "model": "OVLBB4C7 / NSPB500S (λ≈450–480 nm)", "color": "#1e88e5",
        "description": "LED InGaN — bleue, technologie moderne, Vf élevé.",
        "vf_1mA": 2.85, "vf_1mA_min": 2.50, "vf_1mA_max": 3.30,
        "vf_5mA": 3.10, "vf_5mA_min": 2.75, "vf_5mA_max": 3.55,
        "vf_10mA": 3.25, "vf_10mA_min": 2.90, "vf_10mA_max": 3.70,
        "vf_typ": 3.10, "vf_min": 2.70, "vf_max": 3.60,
        "Is_nA": 0.0000005, "n_typ": 2.3, "n_min": 2.0, "n_max": 2.6,
        "slope_factor": 1.2, "curvature": 0.35, "tech": "led", "wavelength": 465,
        "applications": "Éclairage, écrans LCD, phares automobiles, indicateurs.",
    },
    {
        "id": "led_white", "name": "LED Blanche",
        "model": "NSPW500GS / VLHW4100 (phosphore + InGaN bleu)", "color": "#90caf9",
        "description": "LED InGaN bleue + phosphore jaune — lumière blanche, Vf similaire LED bleue.",
        "vf_1mA": 2.75, "vf_1mA_min": 2.50, "vf_1mA_max": 3.25,
        "vf_5mA": 3.00, "vf_5mA_min": 2.70, "vf_5mA_max": 3.50,
        "vf_10mA": 3.15, "vf_10mA_min": 2.82, "vf_10mA_max": 3.65,
        "vf_typ": 3.10, "vf_min": 2.80, "vf_max": 3.60,
        "Is_nA": 0.000001, "n_typ": 2.3, "n_min": 2.0, "n_max": 2.6,
        "slope_factor": 1.2, "curvature": 0.35, "tech": "led", "wavelength": 0,
        "applications": "Éclairage général, lampes LED, torches, rétroéclairage.",
    },
    {
        "id": "led_uv", "name": "LED Ultraviolette",
        "model": "VLMU3100 / TLD1500 (λ≈365–405 nm)", "color": "#7b1fa2",
        "description": "LED GaN — ultraviolet, Vf très élevé, usage spécialisé.",
        "vf_1mA": 3.30, "vf_1mA_min": 3.00, "vf_1mA_max": 3.85,
        "vf_5mA": 3.55, "vf_5mA_min": 3.22, "vf_5mA_max": 4.10,
        "vf_10mA": 3.70, "vf_10mA_min": 3.35, "vf_10mA_max": 4.28,
        "vf_typ": 3.60, "vf_min": 3.30, "vf_max": 4.20,
        "Is_nA": 0.0000005, "n_typ": 2.4, "n_min": 2.1, "n_max": 2.7,
        "slope_factor": 1.1, "curvature": 0.32, "tech": "led", "wavelength": 385,
        "applications": "Stérilisation UV, détection fluorescence, durcissement résine.",
    },
]

# ═══════════════════════════════════════════════════════════
#  IDENTIFICATION DIODE
# ═══════════════════════════════════════════════════════════
def identify_diode_from_curve(data):
    if len(data) < 6:
        return None
    data_s = sorted(data, key=lambda d: d['U'])
    u_vals = [d['U'] for d in data_s]
    i_vals = [d['I'] for d in data_s]
    Vt = 0.02585

    baseline_pts = [i for u, i in zip(u_vals, i_vals) if 0.0 <= u <= 0.2]
    baseline = (sum(baseline_pts) / len(baseline_pts)) if len(baseline_pts) >= 2 \
               else (baseline_pts[0] if baseline_pts else 0.0)
    i_vals = [max(0.0, i - baseline) for i in i_vals]
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

    pts_exp = [(u, i*1e-3) for u, i in zip(u_vals, i_vals)
               if i > i_max*0.03 and i < i_max*0.70 and u > 0.02]
    estimated_n  = 1.8
    estimated_Is = 10e-9
    r2_exp       = 0.0

    if len(pts_exp) >= 5:
        try:
            ln_i  = [math.log(max(p[1], 1e-20)) for p in pts_exp]
            v_arr = [p[0] for p in pts_exp]
            N = len(pts_exp)
            sv = sum(v_arr); sl = sum(ln_i)
            svl = sum(v*l for v, l in zip(v_arr, ln_i))
            sv2 = sum(v*v for v in v_arr)
            denom = N*sv2 - sv**2
            if abs(denom) > 1e-12:
                slope     = (N*svl - sv*sl) / denom
                intercept = (sl - slope*sv) / N
                n_calc    = 1.0 / (slope*Vt) if slope > 0 else 1.8
                if 0.5 < n_calc < 3.5:
                    estimated_n = round(n_calc, 4)
                Is_calc = math.exp(intercept)
                if 1e-20 < Is_calc < 1e-2:
                    estimated_Is = Is_calc
                mean_li = sl / N
                ss_tot  = sum((l - mean_li)**2 for l in ln_i)
                ss_res  = sum((l - (slope*v + intercept))**2 for v, l in zip(v_arr, ln_i))
                r2_exp  = max(0.0, 1.0 - ss_res / max(ss_tot, 1e-12))
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
                dist = abs(vf_1mA - typ) / max((hi-lo)/2.0, 0.01)
                score += 40.0 * max(0.0, 1.0 - dist**1.5)
            else:
                gap = min(abs(vf_1mA-lo), abs(vf_1mA-hi))
                score -= gap * 80.0
                if gap > 0.30:
                    veto = True
        if vf_5mA is not None:
            lo, hi, typ = diode["vf_5mA_min"], diode["vf_5mA_max"], diode["vf_5mA"]
            if lo <= vf_5mA <= hi:
                dist = abs(vf_5mA - typ) / max((hi-lo)/2.0, 0.01)
                score += 20.0 * max(0.0, 1.0 - dist**1.5)
            else:
                score -= min(abs(vf_5mA-lo), abs(vf_5mA-hi)) * 40.0
        if vf_10mA is not None:
            lo, hi, typ = diode["vf_10mA_min"], diode["vf_10mA_max"], diode["vf_10mA"]
            if lo <= vf_10mA <= hi:
                dist = abs(vf_10mA - typ) / max((hi-lo)/2.0, 0.01)
                score += 15.0 * max(0.0, 1.0 - dist**1.5)
            else:
                score -= min(abs(vf_10mA-lo), abs(vf_10mA-hi)) * 30.0
        n_lo, n_hi, n_typ = diode["n_min"], diode["n_max"], diode["n_typ"]
        if n_lo <= estimated_n <= n_hi:
            n_dist = abs(estimated_n - n_typ) / max((n_hi-n_lo)/2.0, 0.01)
            score += 15.0 * max(0.0, 1.0 - n_dist)
        else:
            score -= abs(estimated_n - n_typ) * 12.0
        try:
            score += max(0.0, 8.0 - abs(math.log10(max(estimated_Is, 1e-22)) -
                         math.log10(diode["Is_nA"]*1e-9)) * 3.0)
        except Exception:
            pass
        score += max(0.0, 5.0 - abs(onset_sharpness - diode.get("slope_factor", 2.0)) * 2.5)
        if r2_exp > 0.92 and n_lo <= estimated_n <= n_hi:
            score += 5.0 * r2_exp
        if vf_5mA is not None and diode["vf_5mA_min"] <= vf_5mA <= diode["vf_5mA_max"]:
            score += 2.0
        if veto:
            score = min(score, -10.0)
        scores.append({"diode": diode, "score": round(score, 2)})

    scores.sort(key=lambda x: x["score"], reverse=True)
    best       = scores[0]["diode"]
    best_score = scores[0]["score"]
    sec_score  = scores[1]["score"] if len(scores) > 1 else 0.0
    gap        = best_score - sec_score

    conf = min(95, max(15, int(best_score*0.75 + gap*0.50)))
    conf = min(97, conf + int(r2_exp*8))
    if vf_1mA is not None:
        if abs(vf_1mA - best["vf_1mA"]) < 0.02:  conf = min(99, conf+6)
        elif abs(vf_1mA - best["vf_1mA"]) < 0.06: conf = min(99, conf+3)

    method_votes = []
    if vf_1mA is not None:
        method_votes.append({"label":"Vf@1mA","result":f"{vf_1mA:.3f}V",
            "ok": best["vf_1mA_min"] <= vf_1mA <= best["vf_1mA_max"]})
    if vf_5mA is not None:
        method_votes.append({"label":"Vf@5mA","result":f"{vf_5mA:.3f}V",
            "ok": best["vf_5mA_min"] <= vf_5mA <= best["vf_5mA_max"]})
    if vf_10mA is not None:
        method_votes.append({"label":"Vf@10mA","result":f"{vf_10mA:.3f}V",
            "ok": best["vf_10mA_min"] <= vf_10mA <= best["vf_10mA_max"]})
    method_votes.append({"label":f"n={estimated_n:.3f}","result":best["name"],
        "ok": best["n_min"] <= estimated_n <= best["n_max"]})
    method_votes.append({"label":"baseline","result":f"{baseline:.4f}mA","ok":True})

    is_display = f"{estimated_Is*1e9:.4f} nA" if estimated_Is*1e9 >= 0.001 \
                 else f"{estimated_Is*1e12:.4f} pA"
    return {
        "type": best["name"], "model": best["model"], "id": best["id"],
        "color": best["color"], "description": best["description"],
        "applications": best.get("applications","—"),
        "tech": best.get("tech","diode"), "wavelength": best.get("wavelength",0),
        "vf_1mA":  round(vf_1mA, 3)  if vf_1mA  is not None else None,
        "vf_5mA":  round(vf_5mA, 3)  if vf_5mA  is not None else None,
        "vf_10mA": round(vf_10mA, 3) if vf_10mA is not None else None,
        "vf": round(vf_10pct,3), "vf_5pct":  round(vf_5pct,3),
        "vf_10pct": round(vf_10pct,3), "vf_20pct": round(vf_20pct,3),
        "vf_30pct": round(vf_30pct,3),
        "n": round(estimated_n,3), "Is_nA": round(estimated_Is*1e9,6),
        "Is_display": is_display, "r2_exp": round(r2_exp,4),
        "onset_sharpness": round(onset_sharpness,3),
        "confidence": conf, "baseline_mA": round(baseline,4),
        "scores": scores[:8], "method_votes": method_votes,
    }

# ═══════════════════════════════════════════════════════════
#  CALCULS BJT
# ═══════════════════════════════════════════════════════════
def compute_bjt_params():
    results = {}
    for label, pts in bjt_store.items():
        if len(pts) < 3:
            continue
        ic_vals  = [p['IC']  for p in pts]
        vce_vals = [p['VCE'] for p in pts]
        ic_max   = max(ic_vals)
        vce_at_max = vce_vals[ic_vals.index(ic_max)]
        # Early voltage via régression linéaire en zone active
        active = [(p['VCE'], p['IC']) for p in pts if 0.5 < p['VCE'] < 3.0 and p['IC'] > 0]
        va = None
        if len(active) >= 3:
            try:
                xs = [a[0] for a in active]; ys = [a[1] for a in active]
                N  = len(xs)
                sx = sum(xs); sy = sum(ys)
                sxy = sum(x*y for x,y in zip(xs,ys)); sx2 = sum(x*x for x in xs)
                denom = N*sx2 - sx**2
                if abs(denom) > 1e-12:
                    m = (N*sxy - sx*sy) / denom
                    b = (sy - m*sx) / N
                    if m > 1e-6:
                        va = round(-b/m, 2)
            except Exception:
                pass
        results[label] = {
            "ic_max":       round(ic_max, 4),
            "vce_at_ic_max": round(vce_at_max, 4),
            "early_voltage": va,
            "points":       len(pts),
        }
    return results

# ═══════════════════════════════════════════════════════════
#  CALCULS PV
# ═══════════════════════════════════════════════════════════
def compute_pv_params():
    if len(pv_store) < 5:
        return {}
    pts = sorted(pv_store, key=lambda p: p['V'])
    v_vals = [p['V'] for p in pts]
    i_vals = [p['I'] for p in pts]
    voc    = max(v_vals)
    isc    = max(i_vals)
    pmax   = 0.0; vmpp = 0.0; impp = 0.0
    for p in pts:
        pw = p['V'] * p['I']
        if pw > pmax:
            pmax = pw; vmpp = p['V']; impp = p['I']
    ff = round(pmax / (voc * isc) * 100, 2) if voc > 0 and isc > 0 else 0.0
    return {
        "voc":  round(voc,  4), "isc":  round(isc,  4),
        "pmax": round(pmax, 4), "vmpp": round(vmpp, 4),
        "impp": round(impp, 4), "ff":   ff,
    }

# ═══════════════════════════════════════════════════════════
#  ROUTES FLASK
# ═══════════════════════════════════════════════════════════
@app.route("/")
def home():
    return DASHBOARD_HTML

@app.route("/status")
def status():
    return jsonify({"running": running, "type": current_type})

@app.route("/start", methods=["GET", "POST"])
def start():
    global running, diode_store, bjt_store, pv_store, identified_diode
    global current_type, current_ib_label
    body = (request.get_json(silent=True) or {})
    body.update(request.args)
    t   = body.get("type", "diode")
    lbl = body.get("ib_label", "IB1")
    current_type     = t
    current_ib_label = lbl
    running = True
    if t == "diode":
        diode_store = []; identified_diode = None
    elif t == "bjt":
        bjt_store[lbl] = []
    elif t == "pv":
        pv_store = []
    return jsonify({"status": "running", "type": t})

@app.route("/stop")
def stop():
    global running
    running = False
    return jsonify({"status": "stopped"})

@app.route("/reset", methods=["GET", "POST"])
def reset():
    global diode_store, bjt_store, pv_store, identified_diode
    body = (request.get_json(silent=True) or {})
    body.update(request.args)
    t = body.get("type", "all")
    if t in ("diode", "all"):
        diode_store = []; identified_diode = None
    if t in ("bjt", "all"):
        bjt_store = {}
    if t in ("pv", "all"):
        pv_store = []
    return jsonify({"status": "reset", "type": t})

@app.route("/data", methods=["POST"])
def receive_data():
    global diode_store, bjt_store, pv_store
    if not running:
        return jsonify({"status": "stopped"})
    d = request.get_json(silent=True) or {}
    t = d.get("type", current_type)
    try:
        V = float(d.get("voltage", 0))
        I = float(d.get("current", 0))
    except (TypeError, ValueError):
        return jsonify({"status": "bad_data"}), 400

    if t in ("diode", "led"):
        if V >= 0 and I >= 0:
            diode_store.append({"U": round(V,4), "I": round(I,4)})
    elif t.startswith("transistor") or t == "bjt":
        lbl = d.get("ib_label", current_ib_label)
        if lbl not in bjt_store:
            bjt_store[lbl] = []
        if V >= 0 and I >= 0:
            bjt_store[lbl].append({"VCE": round(V,4), "IC": round(I,4)})
    elif t == "pv":
        if V >= 0 and I >= 0:
            pv_store.append({"V": round(V,4), "I": round(I,4)})
    return jsonify({"status": "ok"})

@app.route("/data_batch", methods=["POST"])
def receive_batch():
    global diode_store, bjt_store, pv_store
    if not running:
        return jsonify({"status": "stopped"})
    pts = request.get_json(silent=True)
    if not isinstance(pts, list) or len(pts) == 0:
        return jsonify({"error": "expected non-empty array"}), 400
    t = pts[0].get("type", current_type)
    count = 0
    for p in pts:
        try:
            V = float(p.get("voltage", 0)); I = float(p.get("current", 0))
        except (TypeError, ValueError):
            continue
        if V < 0 or I < 0:
            continue
        if t in ("diode", "led"):
            diode_store.append({"U": round(V,4), "I": round(I,4)})
        elif t.startswith("transistor") or t == "bjt":
            lbl = p.get("ib_label", current_ib_label)
            if lbl not in bjt_store: bjt_store[lbl] = []
            bjt_store[lbl].append({"VCE": round(V,4), "IC": round(I,4)})
        elif t == "pv":
            pv_store.append({"V": round(V,4), "I": round(I,4)})
        count += 1
    return jsonify({"status": "ok", "points": count})

@app.route("/get_data")
def get_data():
    return jsonify(diode_store)

@app.route("/get_bjt")
def get_bjt():
    return jsonify(bjt_store)

@app.route("/get_pv")
def get_pv():
    return jsonify({"points": pv_store, "params": compute_pv_params()})

@app.route("/identify")
def identify():
    global identified_diode
    if len(diode_store) < 6:
        return jsonify({"error": "not enough data"})
    result = identify_diode_from_curve(diode_store)
    if result is None:
        return jsonify({"error": "identification failed"})
    identified_diode = result
    return jsonify(result)

@app.route("/bjt_params")
def bjt_params_route():
    return jsonify(compute_bjt_params())

@app.route("/export_csv")
def export_csv():
    t = request.args.get("type", "diode")
    if t == "diode":
        csv = "U(V),I(mA)\n" + "".join(f"{d['U']},{d['I']}\n" for d in diode_store)
        fname = "mesures_diode.csv"
    elif t == "bjt":
        csv = "IB_label,VCE(V),IC(mA)\n"
        for lbl, pts in bjt_store.items():
            csv += "".join(f"{lbl},{p['VCE']},{p['IC']}\n" for p in pts)
        fname = "mesures_transistor.csv"
    else:
        csv = "V(V),I(mA),P(mW)\n"
        for p in pv_store:
            csv += f"{p['V']},{p['I']},{round(p['V']*p['I'],4)}\n"
        fname = "mesures_pv.csv"
    return csv, 200, {
        "Content-Type": "text/csv",
        "Content-Disposition": f"attachment; filename={fname}"
    }

# ═══════════════════════════════════════════════════════════
#  DASHBOARD HTML
# ═══════════════════════════════════════════════════════════
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ESP32 · Caractérisation Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.19.0/dist/tabler-icons.min.css">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/hammerjs@2.0.8/hammer.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>
<style>
:root{
  --bg:#f0f2f5;--s:#fff;--s2:#f8f9fc;
  --bd:#e2e8f0;--bd2:#cbd5e1;
  --tx:#1e293b;--mu:#64748b;--ht:#94a3b8;
  --bl:#185FA5;--bl-l:#E6F1FB;--bl-d:#0C447C;
  --gr:#2d7d32;--gr-l:#EAF5EA;--gr-d:#1b5e20;
  --re:#c62828;--re-l:#FFEBEE;--re-d:#b71c1c;
  --am:#e65100;--am-l:#FFF3E0;--am-d:#bf360c;
  --pu:#4527a0;--pu-l:#EDE7F6;
  --te:#00695c;--te-l:#E0F2F1;
  --so:#f59e0b;--so-l:#FFFBEB;
  --mono:'JetBrains Mono',monospace;--sans:'Inter',sans-serif;
  --r:10px;--rs:6px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:var(--bg);font-family:var(--sans);color:var(--tx);overflow-x:hidden}

/* HEADER */
.hdr{height:54px;display:flex;align-items:center;padding:0 20px;gap:14px;
  background:linear-gradient(135deg,#0C447C,#185FA5 55%,#1976D2);
  position:sticky;top:0;z-index:300;box-shadow:0 2px 12px rgba(0,0,0,.2)}
.hdr-logo{display:flex;align-items:center;gap:10px}
.hdr-icon{width:32px;height:32px;border-radius:8px;background:rgba(255,255,255,.15);
  display:flex;align-items:center;justify-content:center;color:#fff;font-size:18px}
.hdr-name{font-size:14px;font-weight:600;color:#fff}
.hdr-sub{font-size:9px;color:rgba(255,255,255,.6);margin-top:1px}
.hdr-r{margin-left:auto;display:flex;align-items:center;gap:18px}
.hdr-stat{text-align:right}
.hdr-v{font-family:var(--mono);font-size:14px;font-weight:600;color:#fff}
.hdr-l{font-size:8px;color:rgba(255,255,255,.55);letter-spacing:.8px;text-transform:uppercase}
.pill{display:flex;align-items:center;gap:5px;padding:4px 11px;border-radius:20px;
  background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);
  font-size:11px;color:rgba(255,255,255,.85);font-weight:500}
.dot{width:6px;height:6px;border-radius:50%;background:rgba(255,255,255,.35)}
.dot.live{background:#69f0ae;animation:pulse 1.2s infinite}
.dot.stop{background:#ff5252}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.3;transform:scale(.7)}}

/* TABS */
.tabs{display:flex;background:var(--s);border-bottom:2px solid var(--bd);
  padding:0 18px;gap:2px;position:sticky;top:54px;z-index:200;overflow-x:auto;scrollbar-width:none}
.tabs::-webkit-scrollbar{display:none}
.tab{display:flex;align-items:center;gap:7px;padding:13px 16px;border:none;
  background:transparent;color:var(--mu);font-family:var(--sans);font-size:12px;
  font-weight:500;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;
  white-space:nowrap;transition:all .15s}
.tab:hover{color:var(--tx);background:var(--s2)}
.tab.on{color:var(--bl);border-bottom-color:var(--bl);font-weight:600}
.tab i{font-size:15px}
.badge{font-size:9px;padding:2px 6px;border-radius:10px;background:var(--bl-l);
  color:var(--bl);font-weight:600;font-family:var(--mono)}

/* PAGE */
.page{display:none;padding:10px;gap:10px;animation:fi .2s ease}
.page.on{display:grid}
@keyframes fi{from{opacity:0;transform:translateY(3px)}to{opacity:1;transform:none}}
.p3{grid-template-columns:200px 1fr 260px}
.p2{grid-template-columns:210px 1fr}
.p1{grid-template-columns:1fr}

/* PANEL */
.panel{background:var(--s);border:1px solid var(--bd);border-radius:var(--r);padding:13px}
.ph{display:flex;align-items:center;gap:7px;margin-bottom:11px;padding-bottom:9px;border-bottom:1px solid var(--bd)}
.ph>i{font-size:16px;color:var(--bl)}
.pt{font-size:9px;font-weight:600;letter-spacing:1.2px;text-transform:uppercase;color:var(--mu)}
.col{display:flex;flex-direction:column;gap:10px}
.rcol{overflow-y:auto;max-height:calc(100vh - 112px);scrollbar-width:thin;scrollbar-color:var(--bd2) transparent}

/* FORM */
label{display:block;font-size:9px;font-weight:500;color:var(--mu);letter-spacing:.5px;
  text-transform:uppercase;margin-bottom:3px;margin-top:7px}
label:first-of-type{margin-top:0}
input,select{width:100%;padding:6px 9px;background:var(--s2);border:1px solid var(--bd2);
  border-radius:var(--rs);color:var(--tx);font-family:var(--mono);font-size:12px;
  outline:none;-moz-appearance:textfield;transition:border .15s}
input::-webkit-inner-spin-button{-webkit-appearance:none}
input:focus,select:focus{border-color:var(--bl);box-shadow:0 0 0 3px rgba(24,95,165,.1)}

/* BUTTONS */
.btn{width:100%;padding:7px 11px;border-radius:var(--rs);font-family:var(--sans);
  font-size:11px;font-weight:500;cursor:pointer;transition:all .15s;
  border:1px solid var(--bd2);background:var(--s);color:var(--tx);
  display:flex;align-items:center;justify-content:center;gap:6px}
.btn:hover{background:var(--s2);border-color:var(--bl)}
.btn:active{transform:scale(.97)}
.btn:disabled{opacity:.4;cursor:not-allowed;transform:none}
.btn+.btn{margin-top:5px}
.btn i{font-size:14px}
.b-go{background:var(--gr-l);color:var(--gr-d);border-color:#A5D6A7}
.b-go:hover{background:#C8E6C9}
.b-st{background:var(--re-l);color:var(--re-d);border-color:#FFCDD2}
.b-st:hover{background:#FFCDD2}
.b-id{background:var(--bl-l);color:var(--bl-d);border-color:#BBDEFB;padding:9px;font-size:12px;font-weight:600}
.b-id:hover:not(:disabled){background:#BBDEFB}
.b-am{background:var(--am-l);color:var(--am-d);border-color:#FFCC80}
.b-am:hover{background:#FFE0B2}

/* STAT BOXES */
.sg{display:grid;grid-template-columns:1fr 1fr;gap:5px}
.sb{background:var(--s2);border:1px solid var(--bd);border-radius:var(--rs);
  padding:9px;text-align:center}
.sv{font-family:var(--mono);font-size:17px;font-weight:600;line-height:1.1}
.sl{font-size:8px;color:var(--mu);margin-top:2px;letter-spacing:.5px;text-transform:uppercase}

/* CHART */
.cw{flex:1;position:relative;min-height:270px}
canvas{width:100%!important;height:100%!important}
.ax{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:5px;margin-top:7px}
.ax label{font-size:8px;margin-top:0}
.ax input{font-size:10px;padding:4px 6px}
.ca{display:flex;gap:5px;margin-top:5px}
.ca .btn{flex:1;font-size:9px;padding:4px 5px}

/* TABLE */
.tw{overflow-y:auto;max-height:155px;border:1px solid var(--bd);border-radius:var(--rs);
  scrollbar-width:thin;scrollbar-color:var(--bd2) transparent}
table{width:100%;border-collapse:collapse}
thead th{background:var(--s2);padding:4px 7px;color:var(--mu);font-size:8px;
  font-weight:600;text-transform:uppercase;letter-spacing:.8px;
  position:sticky;top:0;text-align:center;border-bottom:1px solid var(--bd);z-index:1}
tbody td{padding:3px 7px;text-align:center;border-bottom:1px solid var(--bd);
  font-family:var(--mono);font-size:10px;color:var(--mu)}
tbody tr:hover td{background:var(--s2);color:var(--tx)}

/* ID CARD */
.idc{border:1px solid var(--bd);border-radius:var(--rs);padding:11px;
  margin-top:9px;animation:fi .3s ease;transition:border-color .3s,box-shadow .3s}
.idt{font-size:14px;font-weight:600}.idm{font-size:9px;color:var(--mu);margin-top:2px}
.idd{font-size:10px;color:var(--mu);margin-top:7px;line-height:1.55;
  padding-top:7px;border-top:1px solid var(--bd)}
.vfr{display:grid;grid-template-columns:1fr 1fr 1fr;gap:3px;margin-top:7px}
.vfb{background:var(--s2);border:1px solid var(--bd);border-radius:var(--rs);padding:4px;text-align:center}
.vfl{font-size:7px;color:var(--mu);text-transform:uppercase;letter-spacing:.3px}
.vfv{font-family:var(--mono);font-size:10px;font-weight:600;margin-top:2px}
.pg{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;margin-top:7px}
.pb{background:var(--s2);border:1px solid var(--bd);border-radius:var(--rs);padding:5px;text-align:center}
.pbn{font-size:7px;color:var(--mu);text-transform:uppercase;letter-spacing:.4px}
.pbv{font-family:var(--mono);font-size:11px;font-weight:600;margin-top:2px;color:var(--bl)}
.cr{display:flex;align-items:center;gap:7px;margin-top:7px}
.cb{flex:1;height:4px;background:var(--bd);border-radius:2px;overflow:hidden}
.cf{height:100%;border-radius:2px;transition:width .8s ease}
.cp{font-family:var(--mono);font-size:12px;font-weight:600;min-width:36px;text-align:right}
.ab{margin-top:7px;padding:7px 9px;background:var(--gr-l);border-radius:var(--rs);border-left:2px solid var(--gr)}
.abl{font-size:8px;color:var(--gr);font-weight:600;text-transform:uppercase;letter-spacing:.8px}
.abt{font-size:9px;color:var(--gr-d);margin-top:2px;line-height:1.5}
.vts{display:flex;flex-wrap:wrap;gap:3px;margin-top:7px}
.vok{font-size:8px;padding:2px 6px;border-radius:3px;font-weight:600;font-family:var(--mono);background:var(--gr-l);color:var(--gr-d)}
.vwn{font-size:8px;padding:2px 6px;border-radius:3px;font-weight:600;font-family:var(--mono);background:var(--am-l);color:var(--am-d)}
.cds{margin-top:7px;padding-top:7px;border-top:1px solid var(--bd)}
.cdt{font-size:8px;color:var(--mu);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.cdi{display:flex;align-items:center;gap:5px;padding:2px 0;border-bottom:1px solid var(--bd);font-size:9px}
.cdi:last-child{border:none}
.cdd{width:6px;height:6px;border-radius:50%;flex-shrink:0}
.cdn{flex:1;color:var(--mu)}
.cdb{width:44px;height:3px;background:var(--bd);border-radius:2px;overflow:hidden}
.cdf{height:100%;border-radius:2px}
.cds2{font-family:var(--mono);font-size:9px;color:var(--mu);width:28px;text-align:right}

/* SHOCKLEY */
.shr{display:grid;grid-template-columns:1fr 1fr;gap:5px}
.shr label{margin-top:0}
.sheq{margin-top:5px;padding:5px 8px;background:var(--s2);border:1px solid var(--bd);
  border-radius:var(--rs);font-family:var(--mono);font-size:9px;color:var(--mu);text-align:center}

/* EXPORT */
.exr{display:flex;gap:5px}
.exr .btn{flex:1;font-size:10px;padding:6px}

/* BJT */
.bchips{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}
.bchip{font-size:10px;padding:3px 9px;border-radius:20px;border:1px solid var(--bd2);
  background:var(--s);color:var(--mu);cursor:pointer;transition:all .15s;font-family:var(--mono)}
.bchip.on{color:#fff;border-color:transparent}

/* PV */
.pvg{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:10px}
.pvk{background:linear-gradient(135deg,var(--s2),#fff);border:1px solid var(--bd);
  border-radius:var(--rs);padding:11px;text-align:center}
.pvkv{font-family:var(--mono);font-size:20px;font-weight:600;line-height:1}
.pvkl{font-size:8px;color:var(--mu);margin-top:3px;text-transform:uppercase;letter-spacing:.5px}
.pvk.voc .pvkv{color:var(--bl)}.pvk.isc .pvkv{color:var(--gr)}
.pvk.pm  .pvkv{color:var(--am)}.pvk.ff  .pvkv{color:var(--te)}
.pvk.vm  .pvkv{color:var(--pu)}.pvk.im  .pvkv{color:var(--re)}
.ffb{height:7px;background:var(--bd);border-radius:4px;overflow:hidden;margin-top:5px}
.fff{height:100%;border-radius:4px;background:linear-gradient(90deg,#00695c,#26a69a);transition:width 1s ease}

/* SUMMARY */
.smg{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:10px}
.smc{background:var(--s);border:1px solid var(--bd);border-radius:var(--r);padding:14px}
.smct{font-size:12px;font-weight:600;margin-bottom:10px;padding-bottom:8px;
  border-bottom:1px solid var(--bd);display:flex;align-items:center;gap:7px}
.smct i{font-size:15px;color:var(--bl)}
.smr{display:flex;justify-content:space-between;padding:5px 0;
  border-bottom:1px solid var(--bd);font-size:11px}
.smr:last-child{border:none}
.smk{color:var(--mu)}.smv{font-family:var(--mono);font-weight:500}

/* TOAST */
.toast{position:fixed;bottom:16px;right:16px;z-index:999;
  padding:8px 14px;border-radius:var(--rs);font-size:11px;font-weight:500;
  background:var(--s);border:1px solid var(--bd2);color:var(--tx);
  transform:translateY(50px);opacity:0;transition:all .22s;pointer-events:none;
  box-shadow:0 4px 16px rgba(0,0,0,.1)}
.toast.show{transform:translateY(0);opacity:1}
.toast.ok{border-color:#A5D6A7;color:var(--gr-d);background:var(--gr-l)}
.toast.err{border-color:#FFCDD2;color:var(--re-d);background:var(--re-l)}
.toast.info{border-color:#BBDEFB;color:var(--bl-d);background:var(--bl-l)}
</style>
</head>
<body>

<!-- HEADER -->
<header class="hdr">
  <div class="hdr-logo">
    <div class="hdr-icon"><i class="ti ti-circuit-cell"></i></div>
    <div>
      <div class="hdr-name">ESP32 · Caractérisation Dashboard</div>
      <div class="hdr-sub">MCP4725 · Diode / LED · Transistor NPN · Cellule PV</div>
    </div>
  </div>
  <div class="hdr-r">
    <div class="hdr-stat"><div class="hdr-v" id="hv">—</div><div class="hdr-l">Tension</div></div>
    <div class="hdr-stat"><div class="hdr-v" id="hi">—</div><div class="hdr-l">Courant</div></div>
    <div class="hdr-stat"><div class="hdr-v" id="hpts">0 pts</div><div class="hdr-l">Points</div></div>
    <div class="pill"><div class="dot" id="dot"></div><span id="stxt">Idle</span></div>
  </div>
</header>

<!-- TABS -->
<div class="tabs">
  <button class="tab on" onclick="sw('diode',this)"><i class="ti ti-bolt"></i> Diode / LED <span class="badge" id="bd-d">0</span></button>
  <button class="tab"    onclick="sw('bjt',this)"><i class="ti ti-cpu"></i> Transistor NPN <span class="badge" id="bd-b">0</span></button>
  <button class="tab"    onclick="sw('pv',this)"><i class="ti ti-sun"></i> Cellule PV <span class="badge" id="bd-p">0</span></button>
  <button class="tab"    onclick="sw('sum',this)"><i class="ti ti-report-analytics"></i> Résumé</button>
</div>

<!-- ══ PAGE DIODE ══ -->
<div class="page p3 on" id="pg-diode">
  <div class="col">
    <div class="panel">
      <div class="ph"><i class="ti ti-adjustments-horizontal"></i><span class="pt">Contrôle</span></div>
      <label>Type composant</label>
      <select id="d-comp"><option>Diode</option><option>LED</option></select>
      <label>V max (V)</label>
      <input type="number" id="d-vmax" value="3.3" step="0.1" min="0.5" max="5">
      <label>Pas (V)</label>
      <input type="number" id="d-step" value="0.02" step="0.005" min="0.005">
      <div style="margin-top:11px">
        <button class="btn b-go"  onclick="dStart()"><i class="ti ti-player-play"></i> Start sweep</button>
        <button class="btn b-st"  onclick="dStop()"><i class="ti ti-player-stop"></i> Stop</button>
        <button class="btn"       onclick="dReset()"><i class="ti ti-refresh"></i> Reset</button>
      </div>
    </div>
    <div class="panel">
      <div class="ph"><i class="ti ti-bolt"></i><span class="pt">Mesure live</span></div>
      <div class="sg">
        <div class="sb"><div class="sv" id="d-lv" style="color:var(--bl)">0.000</div><div class="sl">Vf (V)</div></div>
        <div class="sb"><div class="sv" id="d-li" style="color:var(--gr)">0.000</div><div class="sl">I (mA)</div></div>
      </div>
    </div>
    <div class="panel" style="flex:1">
      <div class="ph"><i class="ti ti-table"></i><span class="pt">Données</span>
        <span id="d-ptl" style="margin-left:auto;font-family:var(--mono);font-size:9px;color:var(--mu)">0 pts</span>
      </div>
      <div class="tw"><table><thead><tr><th>#</th><th>U (V)</th><th>I (mA)</th></tr></thead>
      <tbody id="d-tb"></tbody></table></div>
    </div>
  </div>
  <div class="col">
    <div class="panel" style="flex:1;display:flex;flex-direction:column">
      <div class="ph"><i class="ti ti-chart-line"></i><span class="pt">Courbe I = f(V)</span>
        <span style="font-size:8px;color:var(--ht);margin-left:auto">Scroll=zoom · Drag=pan</span>
      </div>
      <div class="cw"><canvas id="d-chart"></canvas></div>
      <div class="ax">
        <div><label>X min</label><input type="number" id="d-xn" value="0"   step="0.1"  oninput="dAx()"></div>
        <div><label>X max</label><input type="number" id="d-xx" value="3.3" step="0.1"  oninput="dAx()"></div>
        <div><label>Y min</label><input type="number" id="d-yn" value="0"   step="0.1"  oninput="dAx()"></div>
        <div><label>Y max</label><input type="number" id="d-yx" value="5"   step="0.5"  oninput="dAx()"></div>
      </div>
      <div class="ca">
        <button class="btn" onclick="dC.resetZoom()"><i class="ti ti-zoom-reset"></i> Zoom</button>
        <button class="btn" onclick="dAs()"><i class="ti ti-arrows-maximize"></i> Auto</button>
        <button class="btn" onclick="dChart.data.datasets[0].data=[];dChart.update('none');toast('Effacé','info')">
          <i class="ti ti-eraser"></i> Effacer</button>
      </div>
    </div>
    <div class="panel">
      <div class="ph"><i class="ti ti-math-function"></i><span class="pt">Shockley manuel</span></div>
      <div class="shr">
        <div><label>Is (nA)</label><input type="number" id="d-Is" value="10" step="0.1" oninput="dSh()"></div>
        <div><label>n</label><input type="number" id="d-n" value="1.8" step="0.05" oninput="dSh()"></div>
      </div>
      <label>Vt (mV)</label>
      <input type="number" id="d-Vt" value="25.85" step="0.1" oninput="dSh()">
      <div class="sheq" id="d-eq">I = 10 nA · (e^(V / 1.8 · 25.85 mV) − 1)</div>
    </div>
  </div>
  <div class="col rcol">
    <div class="panel">
      <div class="ph"><i class="ti ti-brain"></i><span class="pt">Identification IA</span></div>
      <button class="btn b-id" id="d-btn" onclick="dId()"><i class="ti ti-search"></i> Identifier le composant</button>
      <div style="font-size:10px;color:var(--mu);text-align:center;margin-top:6px" id="d-hint">Min. 6 points requis</div>
      <div id="d-res" style="display:none">
        <div class="idc" id="d-card">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:7px">
            <div><div class="idt" id="d-type">—</div><div class="idm" id="d-mod">—</div></div>
            <div id="d-dot" style="width:11px;height:11px;border-radius:50%;flex-shrink:0;margin-top:3px"></div>
          </div>
          <div class="idd" id="d-desc">—</div>
          <div class="vfr">
            <div class="vfb"><div class="vfl">Vf @ 1mA</div><div class="vfv" id="d-vf1" style="color:var(--bl)">—</div></div>
            <div class="vfb"><div class="vfl">Vf @ 5mA</div><div class="vfv" id="d-vf5" style="color:var(--gr)">—</div></div>
            <div class="vfb"><div class="vfl">Vf @ 10mA</div><div class="vfv" id="d-vf10" style="color:var(--am)">—</div></div>
          </div>
          <div class="pg">
            <div class="pb"><div class="pbn">n idéalité</div><div class="pbv" id="d-pn">—</div></div>
            <div class="pb"><div class="pbn">Is</div><div class="pbv" id="d-pis" style="font-size:8px">—</div></div>
            <div class="pb"><div class="pbn">R²</div><div class="pbv" id="d-pr2">—</div></div>
          </div>
          <div class="cr">
            <span style="font-size:9px;color:var(--mu)">Confiance</span>
            <div class="cb"><div class="cf" id="d-cfi" style="width:0%"></div></div>
            <span class="cp" id="d-cpct">—</span>
          </div>
          <div class="ab"><div class="abl">Applications</div><div class="abt" id="d-apps">—</div></div>
          <div class="vts" id="d-votes"></div>
          <div class="cds" id="d-cands"></div>
        </div>
      </div>
    </div>
    <div class="panel">
      <div class="ph"><i class="ti ti-download"></i><span class="pt">Export</span></div>
      <div class="exr">
        <button class="btn" onclick="location.href='/export_csv?type=diode'"><i class="ti ti-file-type-csv"></i> CSV</button>
      </div>
    </div>
  </div>
</div>

<!-- ══ PAGE BJT ══ -->
<div class="page p3" id="pg-bjt">
  <div class="col">
    <div class="panel">
      <div class="ph"><i class="ti ti-adjustments-horizontal"></i><span class="pt">Contrôle BJT</span></div>
      <label>Transistor</label>
      <select id="b-tr"><option>BC547</option><option>2N2222</option><option>BC337</option><option>Autre NPN</option></select>
      <label>Label courbe (I_B)</label>
      <input type="text" id="b-lbl" value="IB1" placeholder="IB1, IB2...">
      <label>V_CE max (V)</label>
      <input type="number" id="b-vmax" value="3.3" step="0.1" min="0.5" max="5">
      <label>Pas (V)</label>
      <input type="number" id="b-step" value="0.033" step="0.005" min="0.005">
      <div style="margin-top:11px">
        <button class="btn b-go"  onclick="bStart()"><i class="ti ti-player-play"></i> Acquérir courbe</button>
        <button class="btn b-st"  onclick="bStop()"><i class="ti ti-player-stop"></i> Stop</button>
        <button class="btn b-am"  onclick="bNext()"><i class="ti ti-plus"></i> Nouvelle courbe I_B</button>
        <button class="btn"       onclick="bReset()"><i class="ti ti-refresh"></i> Reset tout</button>
      </div>
      <div style="margin-top:9px">
        <div style="font-size:9px;color:var(--mu);text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px">Courbes enregistrées</div>
        <div class="bchips" id="b-chips"></div>
      </div>
    </div>
    <div class="panel">
      <div class="ph"><i class="ti ti-bolt"></i><span class="pt">Mesure live</span></div>
      <div class="sg">
        <div class="sb"><div class="sv" id="b-lv" style="color:var(--bl)">0.000</div><div class="sl">V_CE (V)</div></div>
        <div class="sb"><div class="sv" id="b-li" style="color:var(--gr)">0.000</div><div class="sl">I_C (mA)</div></div>
      </div>
    </div>
    <div class="panel">
      <div class="ph"><i class="ti ti-download"></i><span class="pt">Export</span></div>
      <div class="exr">
        <button class="btn" onclick="location.href='/export_csv?type=bjt'"><i class="ti ti-file-type-csv"></i> CSV</button>
      </div>
    </div>
  </div>
  <div class="col">
    <div class="panel" style="flex:1;display:flex;flex-direction:column">
      <div class="ph"><i class="ti ti-chart-line"></i><span class="pt">Famille I_C = f(V_CE)</span>
        <span style="font-size:8px;color:var(--ht);margin-left:auto">Scroll=zoom · Drag=pan</span>
      </div>
      <div class="cw"><canvas id="b-chart"></canvas></div>
      <div class="ax">
        <div><label>X min</label><input type="number" id="b-xn" value="0"   step="0.1" oninput="bAx()"></div>
        <div><label>X max</label><input type="number" id="b-xx" value="3.3" step="0.1" oninput="bAx()"></div>
        <div><label>Y min</label><input type="number" id="b-yn" value="0"   step="0.1" oninput="bAx()"></div>
        <div><label>Y max</label><input type="number" id="b-yx" value="5"   step="0.5" oninput="bAx()"></div>
      </div>
      <div class="ca">
        <button class="btn" onclick="bC.resetZoom()"><i class="ti ti-zoom-reset"></i> Zoom</button>
        <button class="btn" onclick="bAs()"><i class="ti ti-arrows-maximize"></i> Auto</button>
      </div>
    </div>
  </div>
  <div class="col rcol">
    <div class="panel">
      <div class="ph"><i class="ti ti-report"></i><span class="pt">Paramètres extraits</span></div>
      <div id="b-params" style="font-size:11px;color:var(--mu);text-align:center;padding:18px 0">
        Lancez une mesure pour voir les paramètres
      </div>
    </div>
    <div class="panel">
      <div class="ph"><i class="ti ti-info-circle"></i><span class="pt">Schéma circuit</span></div>
      <div style="font-size:10px;color:var(--mu);line-height:1.9;font-family:var(--mono);
        background:var(--s2);padding:8px;border-radius:var(--rs);border:1px solid var(--bd)">
        3.3V ──[R_C 1kΩ]──── GPIO36<br>
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│ Collecteur<br>
        MCP4725 ──[R_B 10kΩ]── Base<br>
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│ Émetteur<br>
        GPIO39 ──[R_sh 1Ω]──── GND<br>
        <br>
        <span style="color:var(--bl)">V_CE</span> = GPIO36 − GPIO39<br>
        <span style="color:var(--gr)">I_C</span>&nbsp; = V_GPIO39 / 1Ω
      </div>
    </div>
  </div>
</div>

<!-- ══ PAGE PV ══ -->
<div class="page p2" id="pg-pv">
  <div class="col">
    <div class="panel">
      <div class="ph"><i class="ti ti-adjustments-horizontal"></i><span class="pt">Contrôle PV</span></div>
      <label>Plage tension cellule</label>
      <select id="p-vt">
        <option value="1">≤ 3.3V (direct)</option>
        <option value="2.47">≤ 5V (diviseur ×2.47)</option>
      </select>
      <label>Pas gate MOSFET (V)</label>
      <input type="number" id="p-step" value="0.033" step="0.005" min="0.005">
      <div style="margin-top:11px">
        <button class="btn b-go"  onclick="pStart()"><i class="ti ti-player-play"></i> Start sweep</button>
        <button class="btn b-st"  onclick="pStop()"><i class="ti ti-player-stop"></i> Stop</button>
        <button class="btn"       onclick="pReset()"><i class="ti ti-refresh"></i> Reset</button>
      </div>
    </div>
    <div class="panel">
      <div class="ph"><i class="ti ti-sun" style="color:var(--so)"></i><span class="pt">Paramètres PV</span></div>
      <div class="pvg" style="grid-template-columns:1fr 1fr">
        <div class="pvk voc"><div class="pvkv" id="p-voc">—</div><div class="pvkl">V_OC (V)</div></div>
        <div class="pvk isc"><div class="pvkv" id="p-isc">—</div><div class="pvkl">I_SC (mA)</div></div>
        <div class="pvk pm" ><div class="pvkv" id="p-pm">—</div><div class="pvkl">P_max (mW)</div></div>
        <div class="pvk ff" ><div class="pvkv" id="p-ff">—</div><div class="pvkl">Fill Factor</div></div>
        <div class="pvk vm" ><div class="pvkv" id="p-vm">—</div><div class="pvkl">V_MPP (V)</div></div>
        <div class="pvk im" ><div class="pvkv" id="p-im">—</div><div class="pvkl">I_MPP (mA)</div></div>
      </div>
      <div style="font-size:9px;color:var(--mu);text-transform:uppercase;letter-spacing:.5px">Fill Factor</div>
      <div class="ffb"><div class="fff" id="p-ffb" style="width:0%"></div></div>
      <div style="display:flex;justify-content:space-between;margin-top:5px;font-size:9px;color:var(--mu)">
        <span style="color:var(--re-d)">0 %</span>
        <span style="color:var(--am-d)">65 %</span>
        <span style="color:var(--gr-d)">75 %+</span>
      </div>
    </div>
    <div class="panel">
      <div class="ph"><i class="ti ti-info-circle"></i><span class="pt">Schéma circuit</span></div>
      <div style="font-size:10px;color:var(--mu);line-height:1.9;font-family:var(--mono);
        background:var(--s2);padding:8px;border-radius:var(--rs);border:1px solid var(--bd)">
        PV(+) ──── GPIO33 ─── Drain<br>
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│ [IRLZ44N]<br>
        GPIO26(DAC2) ─[100Ω]─ Gate<br>
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│ Source<br>
        GPIO32 ──[R_sh 0.1Ω]── GND<br>
        PV(−) ─────────────── GND<br>
        <br>
        <span style="color:var(--so)">V_PV</span> = GPIO33<br>
        <span style="color:var(--gr)">I_PV</span> = GPIO32 / 0.1Ω
      </div>
    </div>
    <div class="panel">
      <div class="ph"><i class="ti ti-download"></i><span class="pt">Export</span></div>
      <div class="exr">
        <button class="btn" onclick="location.href='/export_csv?type=pv'"><i class="ti ti-file-type-csv"></i> CSV</button>
      </div>
    </div>
  </div>
  <div class="col">
    <div class="panel" style="display:flex;flex-direction:column">
      <div class="ph"><i class="ti ti-chart-line" style="color:var(--te)"></i><span class="pt">Courbe I(V)</span>
        <span style="font-size:8px;color:var(--ht);margin-left:auto">Scroll=zoom · Drag=pan</span>
      </div>
      <div class="cw" style="min-height:220px"><canvas id="p-iv"></canvas></div>
      <div class="ph" style="margin-top:12px"><i class="ti ti-chart-area" style="color:var(--am)"></i><span class="pt">Courbe P(V) — Puissance</span></div>
      <div class="cw" style="min-height:160px"><canvas id="p-pv"></canvas></div>
      <div class="ca" style="margin-top:8px">
        <button class="btn" onclick="pC1.resetZoom();pC2.resetZoom()"><i class="ti ti-zoom-reset"></i> Zoom</button>
        <button class="btn" onclick="pAs()"><i class="ti ti-arrows-maximize"></i> Auto</button>
      </div>
    </div>
  </div>
</div>

<!-- ══ PAGE RÉSUMÉ ══ -->
<div class="page p1" id="pg-sum">
  <div class="smg" id="sum-content">
    <div style="grid-column:1/-1;text-align:center;padding:50px;color:var(--mu)">
      <i class="ti ti-report-analytics" style="font-size:52px;opacity:.25;display:block;margin-bottom:14px"></i>
      Effectuez des mesures dans les onglets Diode, Transistor et Cellule PV, puis revenez ici.
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
// ──────────────────────────────────────────
//  UTILS
// ──────────────────────────────────────────
const BJT_COL = ['#185FA5','#e53935','#00897b','#7b1fa2','#e65100','#2e7d32'];
let activeTab = 'diode';
let dRes = null;

function toast(msg, type='info', ms=2500){
  const el = document.getElementById('toast');
  el.textContent = msg; el.className = 'toast '+type+' show';
  clearTimeout(el._t); el._t = setTimeout(()=>el.className='toast', ms);
}

function setStatus(s){
  const d=document.getElementById('dot'), t=document.getElementById('stxt');
  d.className='dot';
  if(s==='live'){d.classList.add('live');t.textContent='Live';}
  else if(s==='stop'){d.classList.add('stop');t.textContent='Stop';}
  else t.textContent='Idle';
}

function sw(id, btn){
  activeTab=id;
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('on'));
  document.querySelectorAll('.tab').forEach(b=>b.classList.remove('on'));
  document.getElementById('pg-'+id).classList.add('on');
  btn.classList.add('on');
  if(id==='sum') buildSum();
}

function mkChart(canvasId, xl, yl, datasets, ymax=5){
  return new Chart(document.getElementById(canvasId).getContext('2d'),{
    type:'line', data:{datasets},
    options:{
      responsive:true, maintainAspectRatio:false, animation:false, parsing:false,
      interaction:{mode:'nearest',intersect:false,axis:'x'},
      plugins:{
        legend:{labels:{color:'#64748b',font:{size:9,family:"'Inter',sans-serif"},boxWidth:16,padding:9}},
        tooltip:{backgroundColor:'#fff',borderColor:'#e2e8f0',borderWidth:1,
          titleColor:'#185FA5',bodyColor:'#1e293b',padding:9,
          callbacks:{
            title:i=>`${xl} = ${Number(i[0].parsed.x).toFixed(3)}`,
            label:i=>`${i.dataset.label}: ${Number(i[0].parsed.y).toFixed(4)}`
          }},
        zoom:{zoom:{wheel:{enabled:true,speed:.08},pinch:{enabled:true},mode:'xy'},
              pan:{enabled:true,mode:'xy'}}
      },
      scales:{
        x:{type:'linear',min:0,max:3.3,
           title:{display:true,text:xl,color:'#64748b',font:{size:10}},
           ticks:{color:'#94a3b8',font:{size:9},maxTicksLimit:10},
           grid:{color:'rgba(0,0,0,0.04)'}},
        y:{min:0,max:ymax,
           title:{display:true,text:yl,color:'#64748b',font:{size:10}},
           ticks:{color:'#94a3b8',font:{size:9}},
           grid:{color:'rgba(0,0,0,0.04)'}}
      }
    }
  });
}

function shPts(Is_nA,n,Vt_mV,xmax,steps=500){
  const Is=Is_nA*1e-9, Vt=Vt_mV*1e-3, pts=[];
  for(let i=0;i<=steps;i++){
    const V=(xmax/steps)*i, I=Is*(Math.exp(V/(n*Vt))-1)*1000;
    if(I>=0&&I<1e6) pts.push({x:V,y:I});
  }
  return pts;
}

// ──────────────────────────────────────────
//  DIODE
// ──────────────────────────────────────────
let dChart;

function dInit(){
  dChart = mkChart('d-chart','U (V)','I (mA)',[
    {label:'Mesure réelle',data:[],borderColor:'#378ADD',backgroundColor:'rgba(55,138,221,0.07)',
     pointRadius:2,borderWidth:2,tension:.25,fill:true},
    {label:'Shockley manuel',data:[],borderColor:'#E24B4A',backgroundColor:'transparent',
     pointRadius:0,borderWidth:1.5,showLine:true,segment:{borderDash:[6,3]}},
    {label:'Théorique',data:[],borderColor:'#BA7517',backgroundColor:'transparent',
     pointRadius:0,borderWidth:2.5,showLine:true,hidden:true,segment:{borderDash:[4,3]}}
  ]);
}

// alias for resetZoom
let dC;
function dChartRef(){dC=dChart;}

function dSh(){
  const Is=+document.getElementById('d-Is').value||10,
        n=+document.getElementById('d-n').value||1.8,
        Vt=+document.getElementById('d-Vt').value||25.85,
        xmax=+document.getElementById('d-xx').value||3.3;
  dChart.data.datasets[1].data=shPts(Is,n,Vt,xmax);
  dChart.update('none');
  document.getElementById('d-eq').textContent=`I = ${Is} nA · (e^(V / ${n} · ${Vt} mV) − 1)`;
}

function dTh(res){
  const xmax=+document.getElementById('d-xx').value||3.3;
  dChart.data.datasets[2].data=shPts(res.Is_nA,res.n,25.85,xmax,600);
  dChart.data.datasets[2].borderColor=res.color;
  dChart.data.datasets[2].label='Théorique — '+res.type;
  dChart.data.datasets[2].hidden=false;
  dChart.update('none');
}

function dAx(){
  dChart.options.scales.x.min=+document.getElementById('d-xn').value||0;
  dChart.options.scales.x.max=+document.getElementById('d-xx').value||3.3;
  dChart.options.scales.y.min=+document.getElementById('d-yn').value||0;
  dChart.options.scales.y.max=+document.getElementById('d-yx').value||5;
  dChart.update('none'); dSh(); if(dRes) dTh(dRes);
}

function dAs(){
  const d=dChart.data.datasets[0].data; if(!d.length){toast('Aucune donnée','err');return;}
  document.getElementById('d-xx').value=(Math.max(...d.map(p=>p.x))*1.1).toFixed(2);
  document.getElementById('d-yx').value=(Math.max(...d.map(p=>p.y))*1.2).toFixed(2);
  dAx();
}

function dStart(){
  fetch('/start?type=diode').then(()=>{
    setStatus('live');
    dChart.data.datasets[0].data=[];
    dChart.data.datasets[2].data=[]; dChart.data.datasets[2].hidden=true;
    dRes=null; document.getElementById('d-tb').innerHTML='';
    document.getElementById('d-res').style.display='none';
    document.getElementById('d-ptl').textContent='0 pts';
    dChart.update('none'); toast('Sweep diode démarré','info');
  });
}
function dStop(){fetch('/stop').then(()=>{setStatus('stop');toast('Arrêté','info');});}
function dReset(){
  fetch('/stop'); fetch('/reset?type=diode').then(()=>{
    setStatus('idle');
    dChart.data.datasets.forEach(ds=>{ds.data=[];});
    dChart.data.datasets[2].hidden=true; dRes=null;
    document.getElementById('d-tb').innerHTML='';
    document.getElementById('d-res').style.display='none';
    document.getElementById('d-ptl').textContent='0 pts';
    document.getElementById('bd-d').textContent='0';
    dChart.update('none'); toast('Reset diode','info');
  });
}

function dId(){
  const btn=document.getElementById('d-btn');
  btn.disabled=true; btn.innerHTML='<i class="ti ti-loader-2"></i> Analyse...';
  fetch('/identify').then(r=>r.json()).then(res=>{
    btn.disabled=false; btn.innerHTML='<i class="ti ti-search"></i> Identifier le composant';
    if(res.error){toast('⚠ '+(res.error==='not enough data'?'Min. 6 points requis':res.error),'err',3000);return;}
    dRes=res;
    document.getElementById('d-hint').textContent='';
    document.getElementById('d-res').style.display='block';
    const card=document.getElementById('d-card');
    card.style.borderColor=res.color; card.style.boxShadow=`0 0 0 3px ${res.color}20`;
    document.getElementById('d-dot').style.cssText=`background:${res.color};width:11px;height:11px;border-radius:50%;flex-shrink:0;margin-top:3px`;
    document.getElementById('d-type').textContent=res.type; document.getElementById('d-type').style.color=res.color;
    document.getElementById('d-mod').textContent=res.model;
    document.getElementById('d-desc').textContent=res.description;
    document.getElementById('d-apps').textContent=res.applications;
    document.getElementById('d-vf1').textContent=res.vf_1mA!==null?res.vf_1mA+' V':'—';
    document.getElementById('d-vf5').textContent=res.vf_5mA!==null?res.vf_5mA+' V':'—';
    document.getElementById('d-vf10').textContent=res.vf_10mA!==null?res.vf_10mA+' V':'—';
    document.getElementById('d-pn').textContent=res.n;
    document.getElementById('d-pis').textContent=res.Is_display;
    const r2=res.r2_exp, r2el=document.getElementById('d-pr2');
    r2el.textContent=r2.toFixed(3);
    r2el.style.color=r2>.95?'var(--gr)':r2>.85?'var(--am)':'var(--re)';
    const conf=res.confidence, cc=conf>75?'var(--gr)':conf>45?'var(--am)':'var(--re)';
    document.getElementById('d-cpct').textContent=conf+' %';
    document.getElementById('d-cpct').style.color=cc;
    const fill=document.getElementById('d-cfi');
    fill.style.width=conf+'%';
    fill.style.background=conf>75?'#2d7d32':conf>45?'#e65100':'#c62828';
    const vts=document.getElementById('d-votes'); vts.innerHTML='';
    (res.method_votes||[]).forEach(v=>{
      const s=document.createElement('span');
      s.className=v.ok?'vok':'vwn';
      s.textContent=v.label+' → '+v.result; vts.appendChild(s);
    });
    if(res.scores&&res.scores.length>1){
      const mx=Math.max(1,res.scores[0].score);
      let html='<div class="cdt">Autres candidats</div>';
      res.scores.slice(1,5).forEach(s=>{
        const pct=Math.max(0,s.score/mx*100).toFixed(0);
        html+=`<div class="cdi"><div class="cdd" style="background:${s.diode.color}"></div>
          <div class="cdn">${s.diode.name}</div>
          <div class="cdb"><div class="cdf" style="width:${pct}%;background:${s.diode.color}"></div></div>
          <div class="cds2">${Math.max(0,s.score).toFixed(1)}</div></div>`;
      });
      document.getElementById('d-cands').innerHTML=html;
    }
    document.getElementById('d-Is').value=res.Is_nA.toFixed(4);
    document.getElementById('d-n').value=res.n;
    dSh(); dTh(res);
    toast('✓ '+res.type+' — confiance '+res.confidence+' %','ok',3500);
  }).catch(()=>{
    btn.disabled=false; btn.innerHTML='<i class="ti ti-search"></i> Identifier le composant';
    toast('Erreur serveur','err');
  });
}

function dPoll(){
  fetch('/get_data').then(r=>r.json()).then(data=>{
    dChart.data.datasets[0].data=data.map(d=>({x:+d.U,y:+d.I}));
    dChart.update('none');
    const n=data.length;
    document.getElementById('d-ptl').textContent=n+' pts';
    document.getElementById('bd-d').textContent=n;
    document.getElementById('hpts').textContent=n+' pts';
    const sl=data.slice(-60);
    document.getElementById('d-tb').innerHTML=sl.map((d,i)=>
      `<tr><td>${data.length-sl.length+i+1}</td><td>${(+d.U).toFixed(3)}</td><td>${(+d.I).toFixed(3)}</td></tr>`
    ).join('');
    if(n>0){const l=data[n-1];
      document.getElementById('d-lv').textContent=(+l.U).toFixed(3);
      document.getElementById('d-li').textContent=(+l.I).toFixed(3);
      document.getElementById('hv').textContent=(+l.U).toFixed(3)+' V';
      document.getElementById('hi').textContent=(+l.I).toFixed(3)+' mA';
    }
  }).catch(()=>{});
}

// ──────────────────────────────────────────
//  BJT
// ──────────────────────────────────────────
let bChart, bIdx=0;

function bInit(){
  bChart = mkChart('b-chart','V_CE (V)','I_C (mA)',[],5);
}
let bC;

function bAx(){
  bChart.options.scales.x.min=+document.getElementById('b-xn').value||0;
  bChart.options.scales.x.max=+document.getElementById('b-xx').value||3.3;
  bChart.options.scales.y.min=+document.getElementById('b-yn').value||0;
  bChart.options.scales.y.max=+document.getElementById('b-yx').value||5;
  bChart.update('none');
}
function bAs(){
  let xm=0,ym=0;
  bChart.data.datasets.forEach(d=>d.data.forEach(p=>{if(p.x>xm)xm=p.x;if(p.y>ym)ym=p.y;}));
  document.getElementById('b-xx').value=(xm*1.1).toFixed(2);
  document.getElementById('b-yx').value=(ym*1.2).toFixed(2);
  bAx();
}

function bStart(){
  const lbl=document.getElementById('b-lbl').value||'IB'+(bIdx+1);
  fetch('/start',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({type:'bjt',ib_label:lbl})})
  .then(()=>{setStatus('live');toast('Acquisition '+lbl,'info');});
}
function bStop(){fetch('/stop').then(()=>{setStatus('stop');toast('Arrêté','info');bPoll();});}
function bNext(){bIdx++;document.getElementById('b-lbl').value='IB'+(bIdx+1);toast('Nouvelle courbe : IB'+(bIdx+1),'info');}
function bReset(){
  fetch('/stop');
  fetch('/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:'{"type":"bjt"}'}).then(()=>{
    setStatus('idle');bChart.data.datasets=[];bChart.update('none');
    document.getElementById('b-chips').innerHTML='';
    document.getElementById('b-params').innerHTML='<div style="font-size:11px;color:var(--mu);text-align:center;padding:18px 0">Lancez une mesure pour voir les paramètres</div>';
    document.getElementById('bd-b').textContent='0';
    bIdx=0; document.getElementById('b-lbl').value='IB1';
    toast('Reset BJT','info');
  });
}

function bPoll(){
  fetch('/get_bjt').then(r=>r.json()).then(data=>{
    const labels=Object.keys(data); let total=0;
    bChart.data.datasets=labels.map((lbl,i)=>{
      const pts=data[lbl]; total+=pts.length;
      return {label:lbl,data:pts.map(p=>({x:+p.VCE,y:+p.IC})),
        borderColor:BJT_COL[i%BJT_COL.length],
        backgroundColor:BJT_COL[i%BJT_COL.length]+'22',
        pointRadius:2,borderWidth:2,tension:.2,showLine:true};
    });
    bChart.update('none');
    document.getElementById('bd-b').textContent=total;
    document.getElementById('b-chips').innerHTML=labels.map((lbl,i)=>
      `<div class="bchip on" style="background:${BJT_COL[i%BJT_COL.length]}">${lbl} (${data[lbl].length}pts)</div>`
    ).join('');
    if(labels.length>0){
      const last=data[labels[labels.length-1]];
      if(last.length>0){const l=last[last.length-1];
        document.getElementById('b-lv').textContent=(+l.VCE).toFixed(3);
        document.getElementById('b-li').textContent=(+l.IC).toFixed(3);
        document.getElementById('hv').textContent=(+l.VCE).toFixed(3)+' V';
        document.getElementById('hi').textContent=(+l.IC).toFixed(3)+' mA';
        document.getElementById('hpts').textContent=total+' pts';
      }
    }
    fetch('/bjt_params').then(r=>r.json()).then(prms=>{
      if(!Object.keys(prms).length)return;
      let html='';
      Object.entries(prms).forEach(([lbl,p],i)=>{
        html+=`<div style="margin-bottom:9px;padding:8px;background:var(--s2);border-radius:var(--rs);border-left:3px solid ${BJT_COL[i%BJT_COL.length]}">
          <div style="font-size:11px;font-weight:600;color:${BJT_COL[i%BJT_COL.length]};margin-bottom:5px">${lbl}</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px">
            <div class="pb"><div class="pbn">I_C max</div><div class="pbv">${p.ic_max} mA</div></div>
            <div class="pb"><div class="pbn">V_CE @max</div><div class="pbv">${p.vce_at_ic_max} V</div></div>
            ${p.early_voltage!==null?`<div class="pb" style="grid-column:1/-1"><div class="pbn">Tension Early V_A</div><div class="pbv">${p.early_voltage} V</div></div>`:''}
          </div>
        </div>`;
      });
      document.getElementById('b-params').innerHTML=html;
    });
  }).catch(()=>{});
}

// ──────────────────────────────────────────
//  PV
// ──────────────────────────────────────────
let pC1, pC2;

function pInit(){
  pC1 = mkChart('p-iv','V_PV (V)','I_PV (mA)',[
    {label:'I(V) mesurée',data:[],borderColor:'#00897b',backgroundColor:'rgba(0,137,123,0.08)',
     pointRadius:2,borderWidth:2,tension:.25,fill:true}
  ],80);
  pC2 = mkChart('p-pv','V_PV (V)','P (mW)',[
    {label:'P(V) puissance',data:[],borderColor:'#e65100',backgroundColor:'rgba(230,81,0,0.08)',
     pointRadius:2,borderWidth:2,tension:.25,fill:true}
  ],300);
}

function pAs(){
  const d=pC1.data.datasets[0].data; if(!d.length)return;
  const xm=Math.max(...d.map(p=>p.x))*1.1,ym=Math.max(...d.map(p=>p.y))*1.2;
  pC1.options.scales.x.max=xm; pC1.options.scales.y.max=ym; pC1.update('none');
  pC2.options.scales.x.max=xm; pC2.update('none');
}

function pStart(){
  fetch('/start',{method:'POST',headers:{'Content-Type':'application/json'},body:'{"type":"pv"}'})
  .then(()=>{setStatus('live');
    pC1.data.datasets[0].data=[];pC2.data.datasets[0].data=[];
    pC1.update('none');pC2.update('none');toast('Sweep PV démarré','info');
  });
}
function pStop(){fetch('/stop').then(()=>{setStatus('stop');toast('Arrêté','info');});}
function pReset(){
  fetch('/stop');
  fetch('/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:'{"type":"pv"}'}).then(()=>{
    setStatus('idle');
    pC1.data.datasets[0].data=[];pC2.data.datasets[0].data=[];
    pC1.update('none');pC2.update('none');
    ['p-voc','p-isc','p-pm','p-ff','p-vm','p-im'].forEach(id=>document.getElementById(id).textContent='—');
    document.getElementById('p-ffb').style.width='0%';
    document.getElementById('bd-p').textContent='0';
    toast('Reset PV','info');
  });
}

function pPoll(){
  const coeff=parseFloat(document.getElementById('p-vt').value)||1;
  fetch('/get_pv').then(r=>r.json()).then(data=>{
    const pts=data.points||[];
    const corr=pts.map(p=>({x:+(p.V*coeff).toFixed(4),y:+p.I}));
    pC1.data.datasets[0].data=corr;
    pC2.data.datasets[0].data=corr.map(p=>({x:p.x,y:+(p.x*p.y/1000).toFixed(5)}));
    pC1.update('none');pC2.update('none');
    const n=pts.length;
    document.getElementById('bd-p').textContent=n;
    document.getElementById('hpts').textContent=n+' pts';
    if(n>0){const l=corr[corr.length-1];
      document.getElementById('hv').textContent=l.x.toFixed(3)+' V';
      document.getElementById('hi').textContent=l.y.toFixed(3)+' mA';
    }
    const pr=data.params||{};
    if(pr.voc){
      document.getElementById('p-voc').textContent=(pr.voc*coeff).toFixed(3);
      document.getElementById('p-isc').textContent=pr.isc.toFixed(3);
      document.getElementById('p-pm').textContent=pr.pmax.toFixed(3);
      document.getElementById('p-ff').textContent=pr.ff+' %';
      document.getElementById('p-vm').textContent=(pr.vmpp*coeff).toFixed(3);
      document.getElementById('p-im').textContent=pr.impp.toFixed(3);
      const ff=Math.min(100,pr.ff);
      document.getElementById('p-ffb').style.width=ff+'%';
    }
  }).catch(()=>{});
}

// ──────────────────────────────────────────
//  RÉSUMÉ
// ──────────────────────────────────────────
function buildSum(){
  let html='';
  // Diode
  html+=`<div class="smc"><div class="smct"><i class="ti ti-bolt"></i> Diode / LED</div>`;
  if(dRes){
    html+=`<div class="smr"><span class="smk">Type</span><span class="smv" style="color:${dRes.color}">${dRes.type}</span></div>
    <div class="smr"><span class="smk">Modèle</span><span class="smv">${dRes.model}</span></div>
    <div class="smr"><span class="smk">Vf @ 1mA</span><span class="smv">${dRes.vf_1mA!==null?dRes.vf_1mA+' V':'—'}</span></div>
    <div class="smr"><span class="smk">Vf @ 5mA</span><span class="smv">${dRes.vf_5mA!==null?dRes.vf_5mA+' V':'—'}</span></div>
    <div class="smr"><span class="smk">Vf @ 10mA</span><span class="smv">${dRes.vf_10mA!==null?dRes.vf_10mA+' V':'—'}</span></div>
    <div class="smr"><span class="smk">n idéalité</span><span class="smv">${dRes.n}</span></div>
    <div class="smr"><span class="smk">Is</span><span class="smv">${dRes.Is_display}</span></div>
    <div class="smr"><span class="smk">R²</span><span class="smv">${dRes.r2_exp}</span></div>
    <div class="smr"><span class="smk">Confiance IA</span><span class="smv">${dRes.confidence} %</span></div>`;
  } else {
    html+=`<div style="color:var(--mu);font-size:11px;padding:8px 0">Aucune mesure effectuée</div>`;
  }
  html+=`</div>`;
  // BJT async
  html+=`<div class="smc"><div class="smct"><i class="ti ti-cpu"></i> Transistor NPN</div>
    <div id="sum-bjt"><div style="color:var(--mu);font-size:11px">Chargement...</div></div></div>`;
  // PV
  const voc=document.getElementById('p-voc').textContent;
  const isc=document.getElementById('p-isc').textContent;
  const pm=document.getElementById('p-pm').textContent;
  const ff=document.getElementById('p-ff').textContent;
  const vm=document.getElementById('p-vm').textContent;
  const im=document.getElementById('p-im').textContent;
  html+=`<div class="smc"><div class="smct"><i class="ti ti-sun"></i> Cellule Photovoltaïque</div>`;
  if(voc!=='—'){
    html+=`<div class="smr"><span class="smk">V_OC</span><span class="smv">${voc} V</span></div>
    <div class="smr"><span class="smk">I_SC</span><span class="smv">${isc} mA</span></div>
    <div class="smr"><span class="smk">P_max</span><span class="smv">${pm} mW</span></div>
    <div class="smr"><span class="smk">V_MPP</span><span class="smv">${vm} V</span></div>
    <div class="smr"><span class="smk">I_MPP</span><span class="smv">${im} mA</span></div>
    <div class="smr"><span class="smk">Fill Factor</span><span class="smv">${ff}</span></div>`;
  } else {
    html+=`<div style="color:var(--mu);font-size:11px;padding:8px 0">Aucune mesure effectuée</div>`;
  }
  html+=`</div>`;
  document.getElementById('sum-content').innerHTML=html;
  // BJT async fill
  fetch('/bjt_params').then(r=>r.json()).then(params=>{
    const keys=Object.keys(params);
    const el=document.getElementById('sum-bjt');
    if(!el)return;
    if(!keys.length){el.innerHTML='<div style="color:var(--mu);font-size:11px;padding:8px 0">Aucune mesure effectuée</div>';return;}
    let h='';
    keys.forEach((lbl,i)=>{
      const p=params[lbl];
      h+=`<div class="smr"><span class="smk" style="color:${BJT_COL[i%BJT_COL.length]}">${lbl} — I_C max</span><span class="smv">${p.ic_max} mA</span></div>`;
      if(p.early_voltage!==null)
        h+=`<div class="smr"><span class="smk">${lbl} — V_Early</span><span class="smv">${p.early_voltage} V</span></div>`;
    });
    el.innerHTML=h;
  }).catch(()=>{});
}

// ──────────────────────────────────────────
//  GLOBAL POLL
// ──────────────────────────────────────────
function poll(){
  if(activeTab==='diode')     dPoll();
  else if(activeTab==='bjt')  bPoll();
  else if(activeTab==='pv')   pPoll();
}

window.onload=function(){
  dInit(); bInit(); pInit();
  // expose resetZoom aliases
  dC = dChart; bC = bChart;
  dSh();
  setInterval(poll, 900);
};
</script>
</body>
</html>"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)