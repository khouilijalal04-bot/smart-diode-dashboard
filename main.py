from flask import Flask, request, jsonify
import math
import threading

app = Flask(__name__)

# ===============================
# THREAD SAFE STORAGE
# ===============================
data_store = []
lock = threading.Lock()

running = False
identified_diode = None


# ===============================
# DIODE DATABASE
# ===============================
DIODE_DATABASE = [
    {"id":"schottky","name":"Schottky","model":"BAT46","vf_min":0.1,"vf_max":0.35,"n":1.1,"Is_nA":100,"color":"#ff9800","description":"Low Vf diode"},
    {"id":"silicon_low","name":"Silicon Signal","model":"1N4148","vf_min":0.4,"vf_max":0.6,"n":1.5,"Is_nA":10,"color":"#2196f3","description":"Fast switching diode"},
    {"id":"silicon_std","name":"Silicon Standard","model":"1N4007","vf_min":0.55,"vf_max":0.8,"n":1.8,"Is_nA":10,"color":"#3fa9ff","description":"Power rectifier"},
]


# ===============================
# CLEAN PHYSICS MODEL
# ===============================
def estimate_shockley(points):
    if len(points) < 8:
        return 1.8, 1e-8

    Vt = 0.02585

    valid = [(u, i) for u, i in points if i > 0 and u > 0.05]
    if len(valid) < 6:
        return 1.8, 1e-8

    u1, i1 = valid[len(valid)//3]
    u2, i2 = valid[2*len(valid)//3]

    try:
        n = (u2 - u1) / (Vt * math.log(i2 / i1))
        n = max(0.8, min(n, 2.5))

        Is = i1 / math.exp(u1 / (n * Vt))
        return round(n, 2), max(Is, 1e-15)

    except:
        return 1.8, 1e-8


# ===============================
# IDENTIFICATION
# ===============================
def identify_diode(data):
    u = [d["U"] for d in data]
    i = [d["I"] for d in data]

    i_max = max(i)
    if i_max <= 0:
        return None

    vf = next((u[k] for k in range(len(i)) if i[k] >= 0.1*i_max), u[-1])

    n, Is = estimate_shockley(list(zip(u, i)))

    best = None
    best_score = -999

    for d in DIODE_DATABASE:
        score = 0

        if d["vf_min"] <= vf <= d["vf_max"]:
            score += 60
        else:
            score -= abs(vf - d["vf_min"]) * 50

        score += max(0, 20 - abs(n - d["n"]) * 15)

        is_ratio = abs(math.log10(Is + 1e-15) - math.log10(d["Is_nA"] * 1e-9))
        score += max(0, 10 - is_ratio * 5)

        if score > best_score:
            best_score = score
            best = d

    confidence = int(max(30, min(99, best_score)))

    return {
        "type": best["name"],
        "model": best["model"],
        "vf": round(vf, 3),
        "n": n,
        "Is_nA": Is * 1e9,
        "confidence": confidence,
        "color": best["color"],
        "description": best["description"]
    }


# ===============================
# ROUTES
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
    global data_store, identified_diode
    with lock:
        data_store = []
    identified_diode = None
    return jsonify({"status": "reset"})


@app.route("/data", methods=["POST"])
def data():
    global data_store
    if not running:
        return jsonify({"status": "stopped"})

    d = request.json
    U = float(d.get("voltage", 0))
    I = float(d.get("current", 0))

    with lock:
        data_store.append({"U": U, "I": I})

    return jsonify({"ok": True})


@app.route("/get_data")
def get_data():
    with lock:
        return jsonify(data_store)


@app.route("/identify")
def identify():
    global identified_diode

    with lock:
        if len(data_store) < 8:
            return jsonify({"error": "not enough data"})

        result = identify_diode(data_store)
        identified_diode = result

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)