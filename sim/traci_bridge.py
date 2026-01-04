import traci
import random
import uuid

# ================== CONFIG ==================
SUMO_CFG = "sumo/config/sim.sumocfg"

FOG_NODES = {
    0: (350, 350),
    1: (1050, 350),
    2: (350, 1050),
    3: (1050, 1050),
}
FOG_RADIUS = 400

REQUEST_PROB = 0.02
MAX_DURATION = 300

# Urgency weights
W_D = 0.4   # deadline
W_C = 0.3   # criticality
W_H = 0.2   # handoff risk
W_L = 0.1   # fog load

# Migration thresholds
THETA_D = 0.7   # deadline pressure
THETA_L = 0.7   # fog load
# ============================================


# ================== HELPERS ==================
def get_fog(x, y):
    for fid, (fx, fy) in FOG_NODES.items():
        if ((x - fx) ** 2 + (y - fy) ** 2) ** 0.5 <= FOG_RADIUS:
            return fid
    return None


def deadline_pressure(r, t):
    return max(0.0, 1.0 - (r.end - t) / MAX_DURATION)


def handoff_risk(r, current_fog):
    return 1.0 if r.last_fog != current_fog else 0.0


def fog_load_factor(fog_id, fog_load):
    return min(1.0, fog_load.get(fog_id, 0) / 10.0)


def select_target_fog(current_fog, fog_load):
    # pick least-loaded neighboring fog
    candidates = [(fid, l) for fid, l in fog_load.items() if fid != current_fog]
    candidates.sort(key=lambda x: x[1])
    return candidates[0][0] if candidates else current_fog
# ============================================


# ================== DATA MODEL ==================
class Request:
    def __init__(self, vid, fog_id, t):
        self.id = str(uuid.uuid4())[:8]
        self.vid = vid
        self.fog = fog_id
        self.start = t
        self.end = t + random.randint(50, MAX_DURATION)

        self.criticality = random.choice([0, 1])  # 1 = safety
        self.last_fog = fog_id
# ===============================================


def start_sumo():
    traci.start([
        "sumo-gui",
        "-c", SUMO_CFG,
        "--start",
        "--quit-on-end"
    ])


def run():
    step = 0
    prev_fog = {}
    active_requests = {}
    fog_load = {fid: 0 for fid in FOG_NODES}

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        step += 1

        # ---------- Mobility + Handoffs ----------
        for vid in traci.vehicle.getIDList():
            x, y = traci.vehicle.getPosition(vid)
            fog = get_fog(x, y)

            if vid in prev_fog and prev_fog[vid] != fog:
                print(f"HANDOFF {vid}: {prev_fog[vid]} -> {fog}")

            prev_fog[vid] = fog

            # ---------- Request Arrival ----------
            if random.random() < REQUEST_PROB:
                r = Request(vid, fog, step)
                active_requests[r.id] = r
                fog_load[fog] += 1
                print(f"NEW_REQ {r.id} vid={vid} fog={fog}")

        # ---------- Request Completion ----------
        finished = []
        for rid, r in active_requests.items():
            if step >= r.end:
                finished.append(rid)

        for rid in finished:
            fog_load[active_requests[rid].fog] -= 1
            del active_requests[rid]

        # ---------- Urgency Computation ----------
        urgency_list = []
        for r in active_requests.values():
            d = deadline_pressure(r, step)
            c = r.criticality
            h = handoff_risk(r, r.fog)
            l = fog_load_factor(r.fog, fog_load)

            U = W_D * d + W_C * c + W_H * h + W_L * l
            urgency_list.append((U, r))

            r.last_fog = r.fog

        urgency_list.sort(key=lambda x: x[0], reverse=True)

        # ---------- UCM: Full-Chain Migration ----------
        for U, r in urgency_list:
            d = deadline_pressure(r, step)
            l = fog_load_factor(r.fog, fog_load)

            if d >= THETA_D or l >= THETA_L:
                target = select_target_fog(r.fog, fog_load)
                if target != r.fog:
                    print(f"MIGRATE(UCM) req={r.id} {r.fog} -> {target}")
                    fog_load[r.fog] -= 1
                    r.fog = target
                    fog_load[target] += 1

        # ---------- Light Debug ----------
        if step % 50 == 0:
            print(f"[t={step}] active={len(active_requests)}")

    traci.close()


if __name__ == "__main__":
    start_sumo()
    run()
