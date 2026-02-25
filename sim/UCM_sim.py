import traci
import random
import uuid
import argparse
import csv
import os
from dataclasses import dataclass
from typing import List, Dict, Optional
from collections import defaultdict

# ================= CONFIG =================
SUMO_CFG = "sumo/config/sim.sumocfg"

# You can keep your 4 fogs; doc suggests larger networks later
FOG_NODES = {
    0: (350, 350),
    1: (1050, 350),
    2: (350, 1050),
    3: (1050, 1050),
}
FOG_RADIUS = 400

# Load sweep driver (probability scales with load)
BASE_REQUEST_PROB = 0.02

# Scheduler time steps
MAX_DURATION = 300  # for request lifetime sampling only

# Urgency weights (doc-compatible)
W_D, W_C, W_H, W_L = 0.4, 0.3, 0.2, 0.1

# Thresholds (doc suggests these ranges; tune later)
THETA_D = 0.7
THETA_L = 0.8

# Target selection cost weights (latency-load tradeoff)
ALPHA = 1.0
BETA = 1.0

# Heterogeneous service classes
SERVICE_CLASSES = ["safety", "control", "comfort", "infotainment"]

# Fog capacities (heterogeneous-ish; tune)
# CPU units ~ {12,16,20} style; memory in MB
FOG_CPU_CAPACITY = {0: 12, 1: 16, 2: 20, 3: 16}
FOG_MEM_CAPACITY = {0: 32000, 1: 48000, 2: 64000, 3: 48000}

# Energy model parameters (simple + non-linear)
IDLE_POWER_W = {f: 80.0 for f in FOG_NODES}   # W
MAX_POWER_W = {f: 280.0 for f in FOG_NODES}   # W
SLOT_LEN_S = 0.1  # 100ms slot (keep simple)
K1_J_PER_MB = 0.01
K2_J_PER_MIG = 0.1
# ==========================================


def get_fog(x, y) -> Optional[int]:
    for fid, (fx, fy) in FOG_NODES.items():
        if ((x - fx) ** 2 + (y - fy) ** 2) ** 0.5 <= FOG_RADIUS:
            return fid
    return None


def rtt_proxy_ms(vehicle_xy, fog_xy) -> float:
    # Simple RTT proxy: distance-based (ms). Replace with network model later.
    vx, vy = vehicle_xy
    fx, fy = fog_xy
    dist = ((vx - fx) ** 2 + (vy - fy) ** 2) ** 0.5
    return 5.0 + 0.02 * dist  # 5ms base + scaled distance


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


@dataclass
class VNF:
    cpu: float          # CPU units
    mem: float          # MB
    state_mb: float     # MB state size
    proc_steps: int     # processing time in steps


@dataclass
class Request:
    rid: str
    vid: str
    service_class: str
    criticality: float
    arr_step: int
    deadline_steps: int
    vnfs: List[VNF]

    # execution state
    k: int               # pointer: next VNF index (0..K-1)
    remaining: int       # remaining steps for current VNF
    fog: int             # current main fog
    last_fog: int        # for handoff risk


def sample_request(vid: str, fog: int, step: int) -> Request:
    rid = str(uuid.uuid4())[:8]
    cls = random.choice(SERVICE_CLASSES)

    # Class profiles (simple version; doc-aligned ranges)
    if cls == "safety":
        K = random.randint(4, 5)
        deadline = random.randint(1, 2)        # ~100–200ms if SLOT_LEN_S=0.1
        crit = 1.0
        cpu_rng = (1.0, 1.5)
        mem_rng = (256, 512)
        state_rng = (5, 20)
        proc_rng = (1, 2)
    elif cls == "control":
        K = random.randint(3, 4)
        deadline = random.randint(2, 3)        # ~200–300ms
        crit = 0.7
        cpu_rng = (0.7, 1.0)
        mem_rng = (128, 256)
        state_rng = (3, 12)
        proc_rng = (1, 3)
    elif cls == "comfort":
        K = random.randint(2, 3)
        deadline = random.randint(4, 7)        # ~400–700ms
        crit = 0.5
        cpu_rng = (0.4, 0.7)
        mem_rng = (64, 128)
        state_rng = (2, 8)
        proc_rng = (1, 4)
    else:  # infotainment
        K = random.randint(2, 3)
        deadline = random.randint(8, 15)       # ~800–1500ms
        crit = 0.3
        cpu_rng = (0.3, 0.6)
        mem_rng = (64, 128)
        state_rng = (2, 10)
        proc_rng = (1, 5)

    vnfs = []
    for _ in range(K):
        cpu = random.uniform(*cpu_rng)
        mem = random.uniform(*mem_rng)
        state = random.uniform(*state_rng)
        proc = random.randint(*proc_rng)
        vnfs.append(VNF(cpu=cpu, mem=mem, state_mb=state, proc_steps=proc))

    return Request(
        rid=rid,
        vid=vid,
        service_class=cls,
        criticality=crit,
        arr_step=step,
        deadline_steps=deadline,
        vnfs=vnfs,
        k=0,
        remaining=vnfs[0].proc_steps,
        fog=fog,
        last_fog=fog,
    )


def est_remaining_steps(r: Request) -> int:
    # remaining time = remaining current + sum future VNFs
    rem = r.remaining
    for i in range(r.k + 1, len(r.vnfs)):
        rem += r.vnfs[i].proc_steps
    return rem


def deadline_term(r: Request, step: int) -> float:
    # d_i: based on slack vs remaining work (doc style)
    elapsed = step - r.arr_step
    rem_deadline = r.deadline_steps - elapsed
    rem_work = est_remaining_steps(r)
    # if rem_deadline <= rem_work => high pressure
    if r.deadline_steps <= 0:
        return 1.0
    slack = rem_deadline - rem_work
    # map slack to 0..1 pressure
    return clamp01(1.0 - (slack / max(1, r.deadline_steps)))


def handoff_risk_term(r: Request) -> float:
    return 1.0 if r.last_fog != r.fog else 0.0


def fog_load(fid: int, fog_cpu_usage: Dict[int, float]) -> float:
    cap = FOG_CPU_CAPACITY[fid]
    return clamp01(fog_cpu_usage[fid] / max(1e-6, cap))


def compute_urgency(r: Request, step: int, fog_cpu_usage: Dict[int, float]) -> float:
    d = deadline_term(r, step)
    c = r.criticality
    h = handoff_risk_term(r)
    l = fog_load(r.fog, fog_cpu_usage)
    return W_D * d + W_C * c + W_H * h + W_L * l


def can_host_full_chain(fid: int, r: Request, fog_cpu_usage: Dict[int, float], fog_mem_usage: Dict[int, float]) -> bool:
    cpu_need = sum(v.cpu for v in r.vnfs)
    mem_need = sum(v.mem for v in r.vnfs)
    cpu_free = FOG_CPU_CAPACITY[fid] - fog_cpu_usage[fid]
    mem_free = FOG_MEM_CAPACITY[fid] - fog_mem_usage[fid]
    return (cpu_free >= cpu_need) and (mem_free >= mem_need)


def pick_target_fog(r: Request, step: int, fog_cpu_usage: Dict[int, float], fog_mem_usage: Dict[int, float],
                    veh_xy) -> Optional[int]:
    # Candidate set = fogs that can host FULL chain
    cands = [f for f in FOG_NODES if can_host_full_chain(f, r, fog_cpu_usage, fog_mem_usage)]
    if not cands:
        return None

    def cost(fid: int) -> float:
        rtt = rtt_proxy_ms(veh_xy, FOG_NODES[fid])
        load = fog_load(fid, fog_cpu_usage)
        return ALPHA * rtt + BETA * load

    best = min(cands, key=cost)
    return best


def power_w(fid: int, u: float) -> float:
    # quadratic utilization power (non-linear)
    idle = IDLE_POWER_W[fid]
    mx = MAX_POWER_W[fid]
    return idle + (mx - idle) * (u ** 2)


def start_sumo(gui=False):
    cmd = ["sumo-gui" if gui else "sumo", "-c", SUMO_CFG, "--start", "--quit-on-end"]
    traci.start(cmd)


def run_ucm(load=400, run_id=1, seed=None, gui=False):
    import sys
    print("RUNNING:", os.path.abspath(__file__))
    print("CWD:", os.getcwd())
    print("ARGV:", sys.argv)

    if seed is not None:
        random.seed(seed)

    REQUEST_PROB = (load / 400.0) * BASE_REQUEST_PROB

    step = 0
    prev_fog = {}

    active: Dict[str, Request] = {}
    fog_cpu_usage = {f: 0.0 for f in FOG_NODES}
    fog_mem_usage = {f: 0.0 for f in FOG_NODES}

    # metrics
    total_arrivals = 0
    blocked = 0
    dropped = 0
    success = 0
    total_mapped_vnfs = 0
    total_state_mb = 0.0
    migrated_vnfs = 0
    migrated_state_mb = 0.0
    delay_sum = 0.0
    energy_idle_j = 0.0
    energy_load_j = 0.0
    energy_mig_j = 0.0

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        step += 1

        vehicle_ids = traci.vehicle.getIDList()
        vehicle_set = set(vehicle_ids)

        # -------- mobility update (handoffs) --------
        for vid in vehicle_ids:
            x, y = traci.vehicle.getPosition(vid)
            fog = get_fog(x, y)
            if vid in prev_fog and prev_fog[vid] != fog:
                pass
            prev_fog[vid] = fog

            # -------- arrivals --------
            if fog is not None and random.random() < REQUEST_PROB:
                total_arrivals += 1
                r = sample_request(vid, fog, step)

                # admission: must fit full chain on current fog (baseline)
                if not can_host_full_chain(fog, r, fog_cpu_usage, fog_mem_usage):
                    blocked += 1
                    continue

                active[r.rid] = r
                # reserve footprint for full chain (simple)
                fog_cpu_usage[fog] += sum(v.cpu for v in r.vnfs)
                fog_mem_usage[fog] += sum(v.mem for v in r.vnfs)
                total_mapped_vnfs += len(r.vnfs)
                total_state_mb += sum(v.state_mb for v in r.vnfs)

        # -------- drop requests whose vehicles left the sim --------
        missing_ids = [rid for rid, r in active.items() if r.vid not in vehicle_set]
        for rid in missing_ids:
            r = active[rid]
            dropped += 1
            cpu_chain = sum(v.cpu for v in r.vnfs)
            mem_chain = sum(v.mem for v in r.vnfs)
            fog_cpu_usage[r.fog] -= cpu_chain
            fog_mem_usage[r.fog] -= mem_chain
            del active[rid]

        # -------- compute urgency + sort --------
        urg_list = []
        for r in active.values():
            U = compute_urgency(r, step, fog_cpu_usage)
            urg_list.append((U, r))
        urg_list.sort(key=lambda x: x[0], reverse=True)

        # -------- UCM scheme block (FULL-CHAIN migration) --------
        for U, r in urg_list:
            # trigger: d_i >= theta_d OR l_j >= theta_l
            d_i = deadline_term(r, step)
            l_i = fog_load(r.fog, fog_cpu_usage)
            if not (d_i >= THETA_D or l_i >= THETA_L):
                r.last_fog = r.fog
                continue

            # choose target that can host FULL chain
            try:
                vx, vy = traci.vehicle.getPosition(r.vid)
            except traci.exceptions.TraCIException:
                dropped += 1
                cpu_chain = sum(v.cpu for v in r.vnfs)
                mem_chain = sum(v.mem for v in r.vnfs)
                fog_cpu_usage[r.fog] -= cpu_chain
                fog_mem_usage[r.fog] -= mem_chain
                if r.rid in active:
                    del active[r.rid]
                continue
            target = pick_target_fog(r, step, fog_cpu_usage, fog_mem_usage, (vx, vy))
            if target is None or target == r.fog:
                r.last_fog = r.fog
                continue

            # migrate full chain: update accounting + move reservation footprint
            src = r.fog
            cpu_chain = sum(v.cpu for v in r.vnfs)
            mem_chain = sum(v.mem for v in r.vnfs)
            state_chain = sum(v.state_mb for v in r.vnfs)

            fog_cpu_usage[src] -= cpu_chain
            fog_mem_usage[src] -= mem_chain
            fog_cpu_usage[target] += cpu_chain
            fog_mem_usage[target] += mem_chain

            r.fog = target

            migrated_vnfs += len(r.vnfs)
            migrated_state_mb += state_chain
            # migration energy
            energy_mig_j += (K1_J_PER_MB * state_chain + K2_J_PER_MIG)

            r.last_fog = r.fog

        # -------- processing + deadline drops --------
        done_ids = []
        for rid, r in active.items():
            # deadline violation => drop in-service
            if (step - r.arr_step) > r.deadline_steps:
                dropped += 1
                done_ids.append(rid)
                continue

            # process 1 step on current VNF
            r.remaining -= 1
            if r.remaining <= 0:
                r.k += 1
                if r.k >= len(r.vnfs):
                    # completed
                    success += 1
                    delay_sum += (step - r.arr_step)
                    done_ids.append(rid)
                else:
                    r.remaining = r.vnfs[r.k].proc_steps

        # remove completed/dropped & free reservations
        for rid in done_ids:
            r = active[rid]
            cpu_chain = sum(v.cpu for v in r.vnfs)
            mem_chain = sum(v.mem for v in r.vnfs)
            fog_cpu_usage[r.fog] -= cpu_chain
            fog_mem_usage[r.fog] -= mem_chain
            del active[rid]

        # -------- energy idle+load per slot --------
        for f in FOG_NODES:
            u = clamp01(fog_cpu_usage[f] / max(1e-6, FOG_CPU_CAPACITY[f]))
            idle = IDLE_POWER_W[f]
            p = power_w(f, u)
            energy_idle_j += idle * SLOT_LEN_S
            energy_load_j += (p - idle) * SLOT_LEN_S

    avg_delay = (delay_sum / success) if success > 0 else 0.0

    traci.close()
    energy_total_j = energy_idle_j + energy_load_j + energy_mig_j
    return {
        "scheme": "UCM",
        "load": load,
        "run": run_id,
        "total_arrivals": total_arrivals,
        "blocked": blocked,
        "dropped": dropped,
        "success": success,
        "total_mapped_vnfs": total_mapped_vnfs,
        "migrated_vnfs": migrated_vnfs,
        "total_state_mb": round(total_state_mb, 4),
        "migrated_state_mb": round(migrated_state_mb, 4),
        "energy_idle_j": round(energy_idle_j, 4),
        "energy_load_j": round(energy_load_j, 4),
        "energy_mig_j": round(energy_mig_j, 4),
        "energy_total_j": round(energy_total_j, 4),
        "avg_delay_steps": round(avg_delay, 4),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UCM baseline (full-chain) per feedback doc.")
    parser.add_argument("--load", type=int, default=400)
    parser.add_argument("--run_id", type=int, default=1)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args()

    start_sumo(gui=args.gui)
    run_ucm(load=args.load, run_id=args.run_id, seed=args.seed, gui=args.gui)
import traci
import random
import uuid
import argparse
import csv
import os
from dataclasses import dataclass
from typing import List, Dict, Optional
from collections import defaultdict

# ================= CONFIG =================
SUMO_CFG = "sumo/config/sim.sumocfg"

# You can keep your 4 fogs; doc suggests larger networks later
FOG_NODES = {
    0: (350, 350),
    1: (1050, 350),
    2: (350, 1050),
    3: (1050, 1050),
}
FOG_RADIUS = 400

# Load sweep driver (probability scales with load)
BASE_REQUEST_PROB = 0.02

# Scheduler time steps
MAX_DURATION = 300  # for request lifetime sampling only

# Urgency weights (doc-compatible)
W_D, W_C, W_H, W_L = 0.4, 0.3, 0.2, 0.1

# Thresholds (doc suggests these ranges; tune later)
THETA_D = 0.7
THETA_L = 0.8

# Target selection cost weights (latency-load tradeoff)
ALPHA = 1.0
BETA = 1.0

# Heterogeneous service classes
SERVICE_CLASSES = ["safety", "control", "comfort", "infotainment"]

# Fog capacities (heterogeneous-ish; tune)
# CPU units ~ {12,16,20} style; memory in MB
FOG_CPU_CAPACITY = {0: 12, 1: 16, 2: 20, 3: 16}
FOG_MEM_CAPACITY = {0: 32000, 1: 48000, 2: 64000, 3: 48000}

# Energy model parameters (simple + non-linear)
IDLE_POWER_W = {f: 80.0 for f in FOG_NODES}   # W
MAX_POWER_W = {f: 280.0 for f in FOG_NODES}   # W
SLOT_LEN_S = 0.1  # 100ms slot (keep simple)
K1_J_PER_MB = 0.01
K2_J_PER_MIG = 0.1
# ==========================================


def get_fog(x, y) -> Optional[int]:
    for fid, (fx, fy) in FOG_NODES.items():
        if ((x - fx) ** 2 + (y - fy) ** 2) ** 0.5 <= FOG_RADIUS:
            return fid
    return None


def rtt_proxy_ms(vehicle_xy, fog_xy) -> float:
    # Simple RTT proxy: distance-based (ms). Replace with network model later.
    vx, vy = vehicle_xy
    fx, fy = fog_xy
    dist = ((vx - fx) ** 2 + (vy - fy) ** 2) ** 0.5
    return 5.0 + 0.02 * dist  # 5ms base + scaled distance


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


@dataclass
class VNF:
    cpu: float          # CPU units
    mem: float          # MB
    state_mb: float     # MB state size
    proc_steps: int     # processing time in steps


@dataclass
class Request:
    rid: str
    vid: str
    service_class: str
    criticality: float
    arr_step: int
    deadline_steps: int
    vnfs: List[VNF]

    # execution state
    k: int               # pointer: next VNF index (0..K-1)
    remaining: int       # remaining steps for current VNF
    fog: int             # current main fog
    last_fog: int        # for handoff risk


def sample_request(vid: str, fog: int, step: int) -> Request:
    rid = str(uuid.uuid4())[:8]
    cls = random.choice(SERVICE_CLASSES)

    # Class profiles (simple version; doc-aligned ranges)
    if cls == "safety":
        K = random.randint(4, 5)
        deadline = random.randint(1, 2)        # ~100–200ms if SLOT_LEN_S=0.1
        crit = 1.0
        cpu_rng = (1.0, 1.5)
        mem_rng = (256, 512)
        state_rng = (5, 20)
        proc_rng = (1, 2)
    elif cls == "control":
        K = random.randint(3, 4)
        deadline = random.randint(2, 3)        # ~200–300ms
        crit = 0.7
        cpu_rng = (0.7, 1.0)
        mem_rng = (128, 256)
        state_rng = (3, 12)
        proc_rng = (1, 3)
    elif cls == "comfort":
        K = random.randint(2, 3)
        deadline = random.randint(4, 7)        # ~400–700ms
        crit = 0.5
        cpu_rng = (0.4, 0.7)
        mem_rng = (64, 128)
        state_rng = (2, 8)
        proc_rng = (1, 4)
    else:  # infotainment
        K = random.randint(2, 3)
        deadline = random.randint(8, 15)       # ~800–1500ms
        crit = 0.3
        cpu_rng = (0.3, 0.6)
        mem_rng = (64, 128)
        state_rng = (2, 10)
        proc_rng = (1, 5)

    vnfs = []
    for _ in range(K):
        cpu = random.uniform(*cpu_rng)
        mem = random.uniform(*mem_rng)
        state = random.uniform(*state_rng)
        proc = random.randint(*proc_rng)
        vnfs.append(VNF(cpu=cpu, mem=mem, state_mb=state, proc_steps=proc))

    return Request(
        rid=rid,
        vid=vid,
        service_class=cls,
        criticality=crit,
        arr_step=step,
        deadline_steps=deadline,
        vnfs=vnfs,
        k=0,
        remaining=vnfs[0].proc_steps,
        fog=fog,
        last_fog=fog,
    )


def est_remaining_steps(r: Request) -> int:
    # remaining time = remaining current + sum future VNFs
    rem = r.remaining
    for i in range(r.k + 1, len(r.vnfs)):
        rem += r.vnfs[i].proc_steps
    return rem


def deadline_term(r: Request, step: int) -> float:
    # d_i: based on slack vs remaining work (doc style)
    elapsed = step - r.arr_step
    rem_deadline = r.deadline_steps - elapsed
    rem_work = est_remaining_steps(r)
    # if rem_deadline <= rem_work => high pressure
    if r.deadline_steps <= 0:
        return 1.0
    slack = rem_deadline - rem_work
    # map slack to 0..1 pressure
    return clamp01(1.0 - (slack / max(1, r.deadline_steps)))


def handoff_risk_term(r: Request) -> float:
    return 1.0 if r.last_fog != r.fog else 0.0


def fog_load(fid: int, fog_cpu_usage: Dict[int, float]) -> float:
    cap = FOG_CPU_CAPACITY[fid]
    return clamp01(fog_cpu_usage[fid] / max(1e-6, cap))


def compute_urgency(r: Request, step: int, fog_cpu_usage: Dict[int, float]) -> float:
    d = deadline_term(r, step)
    c = r.criticality
    h = handoff_risk_term(r)
    l = fog_load(r.fog, fog_cpu_usage)
    return W_D * d + W_C * c + W_H * h + W_L * l


def can_host_full_chain(fid: int, r: Request, fog_cpu_usage: Dict[int, float], fog_mem_usage: Dict[int, float]) -> bool:
    cpu_need = sum(v.cpu for v in r.vnfs)
    mem_need = sum(v.mem for v in r.vnfs)
    cpu_free = FOG_CPU_CAPACITY[fid] - fog_cpu_usage[fid]
    mem_free = FOG_MEM_CAPACITY[fid] - fog_mem_usage[fid]
    return (cpu_free >= cpu_need) and (mem_free >= mem_need)


def pick_target_fog(r: Request, step: int, fog_cpu_usage: Dict[int, float], fog_mem_usage: Dict[int, float],
                    veh_xy) -> Optional[int]:
    # Candidate set = fogs that can host FULL chain
    cands = [f for f in FOG_NODES if can_host_full_chain(f, r, fog_cpu_usage, fog_mem_usage)]
    if not cands:
        return None

    def cost(fid: int) -> float:
        rtt = rtt_proxy_ms(veh_xy, FOG_NODES[fid])
        load = fog_load(fid, fog_cpu_usage)
        return ALPHA * rtt + BETA * load

    best = min(cands, key=cost)
    return best


def power_w(fid: int, u: float) -> float:
    # quadratic utilization power (non-linear)
    idle = IDLE_POWER_W[fid]
    mx = MAX_POWER_W[fid]
    return idle + (mx - idle) * (u ** 2)


def start_sumo(gui=False):
    cmd = ["sumo-gui" if gui else "sumo", "-c", SUMO_CFG, "--start", "--quit-on-end"]
    traci.start(cmd)


def run_ucm(load=400, run_id=1, seed=None, gui=False):
    import sys
    print("RUNNING:", os.path.abspath(__file__))
    print("CWD:", os.getcwd())
    print("ARGV:", sys.argv)

    if seed is not None:
        random.seed(seed)

    REQUEST_PROB = (load / 400.0) * BASE_REQUEST_PROB

    step = 0
    prev_fog = {}

    active: Dict[str, Request] = {}
    fog_cpu_usage = {f: 0.0 for f in FOG_NODES}
    fog_mem_usage = {f: 0.0 for f in FOG_NODES}

    # metrics
    total_arrivals = 0
    blocked = 0
    dropped = 0
    success = 0
    total_mapped_vnfs = 0
    total_state_mb = 0.0
    migrated_vnfs = 0
    migrated_state_mb = 0.0
    delay_sum = 0.0
    energy_idle_j = 0.0
    energy_load_j = 0.0
    energy_mig_j = 0.0

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        step += 1

        vehicle_ids = traci.vehicle.getIDList()
        vehicle_set = set(vehicle_ids)

        # -------- mobility update (handoffs) --------
        for vid in vehicle_ids:
            x, y = traci.vehicle.getPosition(vid)
            fog = get_fog(x, y)
            if vid in prev_fog and prev_fog[vid] != fog:
                pass
            prev_fog[vid] = fog

            # -------- arrivals --------
            if fog is not None and random.random() < REQUEST_PROB:
                total_arrivals += 1
                r = sample_request(vid, fog, step)

                # admission: must fit full chain on current fog (baseline)
                if not can_host_full_chain(fog, r, fog_cpu_usage, fog_mem_usage):
                    blocked += 1
                    continue

                active[r.rid] = r
                # reserve footprint for full chain (simple)
                fog_cpu_usage[fog] += sum(v.cpu for v in r.vnfs)
                fog_mem_usage[fog] += sum(v.mem for v in r.vnfs)
                total_mapped_vnfs += len(r.vnfs)
                total_state_mb += sum(v.state_mb for v in r.vnfs)

        # -------- drop requests whose vehicles left the sim --------
        missing_ids = [rid for rid, r in active.items() if r.vid not in vehicle_set]
        for rid in missing_ids:
            r = active[rid]
            dropped += 1
            cpu_chain = sum(v.cpu for v in r.vnfs)
            mem_chain = sum(v.mem for v in r.vnfs)
            fog_cpu_usage[r.fog] -= cpu_chain
            fog_mem_usage[r.fog] -= mem_chain
            del active[rid]

        # -------- compute urgency + sort --------
        urg_list = []
        for r in active.values():
            U = compute_urgency(r, step, fog_cpu_usage)
            urg_list.append((U, r))
        urg_list.sort(key=lambda x: x[0], reverse=True)

        # -------- UCM scheme block (FULL-CHAIN migration) --------
        for U, r in urg_list:
            # trigger: d_i >= theta_d OR l_j >= theta_l
            d_i = deadline_term(r, step)
            l_i = fog_load(r.fog, fog_cpu_usage)
            if not (d_i >= THETA_D or l_i >= THETA_L):
                r.last_fog = r.fog
                continue

            # choose target that can host FULL chain
            try:
                vx, vy = traci.vehicle.getPosition(r.vid)
            except traci.exceptions.TraCIException:
                dropped += 1
                cpu_chain = sum(v.cpu for v in r.vnfs)
                mem_chain = sum(v.mem for v in r.vnfs)
                fog_cpu_usage[r.fog] -= cpu_chain
                fog_mem_usage[r.fog] -= mem_chain
                if r.rid in active:
                    del active[r.rid]
                continue
            target = pick_target_fog(r, step, fog_cpu_usage, fog_mem_usage, (vx, vy))
            if target is None or target == r.fog:
                r.last_fog = r.fog
                continue

            # migrate full chain: update accounting + move reservation footprint
            src = r.fog
            cpu_chain = sum(v.cpu for v in r.vnfs)
            mem_chain = sum(v.mem for v in r.vnfs)
            state_chain = sum(v.state_mb for v in r.vnfs)

            fog_cpu_usage[src] -= cpu_chain
            fog_mem_usage[src] -= mem_chain
            fog_cpu_usage[target] += cpu_chain
            fog_mem_usage[target] += mem_chain

            r.fog = target

            migrated_vnfs += len(r.vnfs)
            migrated_state_mb += state_chain
            # migration energy
            energy_mig_j += (K1_J_PER_MB * state_chain + K2_J_PER_MIG)

            r.last_fog = r.fog

        # -------- processing + deadline drops --------
        done_ids = []
        for rid, r in active.items():
            # deadline violation => drop in-service
            if (step - r.arr_step) > r.deadline_steps:
                dropped += 1
                done_ids.append(rid)
                continue

            # process 1 step on current VNF
            r.remaining -= 1
            if r.remaining <= 0:
                r.k += 1
                if r.k >= len(r.vnfs):
                    # completed
                    success += 1
                    delay_sum += (step - r.arr_step)
                    done_ids.append(rid)
                else:
                    r.remaining = r.vnfs[r.k].proc_steps

        # remove completed/dropped & free reservations
        for rid in done_ids:
            r = active[rid]
            cpu_chain = sum(v.cpu for v in r.vnfs)
            mem_chain = sum(v.mem for v in r.vnfs)
            fog_cpu_usage[r.fog] -= cpu_chain
            fog_mem_usage[r.fog] -= mem_chain
            del active[rid]

        # -------- energy idle+load per slot --------
        for f in FOG_NODES:
            u = clamp01(fog_cpu_usage[f] / max(1e-6, FOG_CPU_CAPACITY[f]))
            idle = IDLE_POWER_W[f]
            p = power_w(f, u)
            energy_idle_j += idle * SLOT_LEN_S
            energy_load_j += (p - idle) * SLOT_LEN_S

    avg_delay = (delay_sum / success) if success > 0 else 0.0

    traci.close()
    energy_total_j = energy_idle_j + energy_load_j + energy_mig_j
    return {
        "scheme": "UCM",
        "load": load,
        "run": run_id,
        "total_arrivals": total_arrivals,
        "blocked": blocked,
        "dropped": dropped,
        "success": success,
        "total_mapped_vnfs": total_mapped_vnfs,
        "migrated_vnfs": migrated_vnfs,
        "total_state_mb": round(total_state_mb, 4),
        "migrated_state_mb": round(migrated_state_mb, 4),
        "energy_idle_j": round(energy_idle_j, 4),
        "energy_load_j": round(energy_load_j, 4),
        "energy_mig_j": round(energy_mig_j, 4),
        "energy_total_j": round(energy_total_j, 4),
        "avg_delay_steps": round(avg_delay, 4),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UCM baseline (full-chain) per feedback doc.")
    parser.add_argument("--load", type=int, default=400)
    parser.add_argument("--run_id", type=int, default=1)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args()

    start_sumo(gui=args.gui)
    run_ucm(load=args.load, run_id=args.run_id, seed=args.seed, gui=args.gui)
