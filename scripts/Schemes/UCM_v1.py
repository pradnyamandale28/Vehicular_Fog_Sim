"""
UCM (Urgency-Aware Chain Migration) - Baseline Scheme
Migrates full VNF chains when urgency thresholds are exceeded
"""

import traci
import random
import uuid
import argparse
from dataclasses import dataclass
from typing import List, Dict, Optional

# ================= CONFIG =================
SUMO_CFG = "sumo/config/sim.sumocfg"

# 24 fog nodes in 4x6 grid (realistic large network)
FOG_NODES = {}
grid_x = [200, 600, 1000, 1400, 1800, 2200]
grid_y = [200, 600, 1000, 1400]
fid = 0
for y in grid_y:
    for x in grid_x:
        FOG_NODES[fid] = (x, y)
        fid += 1

FOG_RADIUS = 350  # meters coverage

# Load scaling
BASE_REQUEST_PROB = 0.0002  # Will be scaled by load parameter

# Urgency weights
W_D, W_C, W_H, W_L = 0.4, 0.3, 0.2, 0.1

# Thresholds
THETA_D = 0.7  # Deadline pressure threshold
THETA_L = 0.8  # Load threshold
CRITICAL_DEADLINE_THRESHOLD = 0.95  # For migration failure drops

# Target selection weights
ALPHA = 1.0  # RTT weight
BETA = 1.0   # Load weight

# Service classes
SERVICE_CLASSES = ["safety", "control", "comfort", "infotainment"]

# Heterogeneous fog capacities (12-20 CPU units, 32-64 GB memory)
FOG_CPU_CAPACITY = {}
FOG_MEM_CAPACITY = {}
for f in FOG_NODES:
    FOG_CPU_CAPACITY[f] = random.choice([12, 16, 20])
    FOG_MEM_CAPACITY[f] = random.choice([32000, 48000, 64000])  # MB

# Energy model (realistic edge server powers)
IDLE_POWER_W = {}
MAX_POWER_W = {}
for f in FOG_NODES:
    IDLE_POWER_W[f] = random.uniform(70, 90)
    MAX_POWER_W[f] = random.uniform(250, 320)

SLOT_LEN_S = 0.02  # 20ms time slot
K1_J_PER_MB = 0.01  # Energy per MB migrated
K2_J_PER_MIG = 0.1  # Fixed energy per migration

# Mobility parameters
N_MAX_HOPS = 6

# ==========================================


def get_fog(x, y) -> Optional[int]:
    """Find fog node covering position (x, y)"""
    for fid, (fx, fy) in FOG_NODES.items():
        if ((x - fx) ** 2 + (y - fy) ** 2) ** 0.5 <= FOG_RADIUS:
            return fid
    return None


def rtt_proxy_ms(vehicle_xy, fog_xy) -> float:
    """Estimate RTT based on distance"""
    vx, vy = vehicle_xy
    fx, fy = fog_xy
    dist = ((vx - fx) ** 2 + (vy - fy) ** 2) ** 0.5
    return 5.0 + 0.02 * dist


def clamp01(x: float) -> float:
    """Clamp value to [0, 1]"""
    return max(0.0, min(1.0, x))


@dataclass
class VNF:
    """Virtual Network Function specification"""
    cpu: float          # CPU units
    mem: float          # MB
    state_mb: float     # State size in MB
    proc_steps: int     # Processing time in steps


@dataclass
class Request:
    """Service Function Chain request"""
    rid: str
    vid: str
    service_class: str
    criticality: float
    arr_step: int
    deadline_steps: int
    vnfs: List[VNF]
    
    # Execution state
    k: int              # Current VNF index (next to execute)
    remaining: int      # Remaining steps for current VNF
    fog: int            # Current fog node
    last_fog: int       # Previous fog (for handoff risk)
    
    # Mobility
    n_hops: int         # Expected number of hops
    p_handoff: float    # Handoff probability


def sample_request(vid: str, fog: int, step: int) -> Request:
    """Generate a random request based on service class"""
    rid = str(uuid.uuid4())[:8]
    cls = random.choice(SERVICE_CLASSES)
    
    # Service class profiles (from feedback doc)
    if cls == "safety":
        K = random.randint(4, 5)
        deadline = random.randint(3, 5)  # 60-100ms at 20ms slots
        crit = 1.0
        cpu_rng = (1.0, 1.5)
        mem_rng = (256, 512)
        state_rng = (5, 20)
        proc_rng = (1, 2)
        n_hops = random.randint(0, 2)
    elif cls == "control":
        K = random.randint(3, 4)
        deadline = random.randint(5, 10)  # 100-200ms
        crit = 0.7
        cpu_rng = (0.7, 1.0)
        mem_rng = (128, 256)
        state_rng = (3, 12)
        proc_rng = (1, 3)
        n_hops = random.randint(0, 3)
    elif cls == "comfort":
        K = random.randint(2, 3)
        deadline = random.randint(15, 30)  # 300-600ms
        crit = 0.5
        cpu_rng = (0.4, 0.7)
        mem_rng = (64, 128)
        state_rng = (2, 8)
        proc_rng = (1, 4)
        n_hops = random.randint(1, 4)
    else:  # infotainment
        K = random.randint(2, 3)
        deadline = random.randint(40, 75)  # 800-1500ms
        crit = 0.3
        cpu_rng = (0.3, 0.6)
        mem_rng = (64, 128)
        state_rng = (2, 10)
        proc_rng = (1, 5)
        n_hops = random.randint(2, 5)
    
    # Generate VNF chain
    vnfs = []
    for _ in range(K):
        vnfs.append(
            VNF(
                cpu=random.uniform(*cpu_rng),
                mem=random.uniform(*mem_rng),
                state_mb=random.uniform(*state_rng),
                proc_steps=random.randint(*proc_rng),
            )
        )
    
    # Compute handoff probability based on expected hops
    if n_hops == 0:
        p_handoff = 0.0
    elif n_hops == 1:
        p_handoff = 0.3
    elif n_hops in [2, 3]:
        p_handoff = 0.6
    else:
        p_handoff = 0.85
    
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
        n_hops=n_hops,
        p_handoff=p_handoff,
    )


def est_remaining_steps(r: Request) -> int:
    """Estimate remaining processing time"""
    rem = r.remaining
    for i in range(r.k + 1, len(r.vnfs)):
        rem += r.vnfs[i].proc_steps
    return rem


def deadline_term(r: Request, step: int) -> float:
    """Compute deadline pressure term d_i"""
    elapsed = step - r.arr_step
    rem_deadline = r.deadline_steps - elapsed
    rem_work = est_remaining_steps(r)
    
    if r.deadline_steps <= 0:
        return 1.0
    
    slack = rem_deadline - rem_work
    return clamp01(1.0 - (slack / max(1, r.deadline_steps)))


def handoff_risk_term(r: Request) -> float:
    """Compute handoff risk term h_i"""
    return r.p_handoff * (r.n_hops / max(1, N_MAX_HOPS))


def fog_load(fid: int, fog_cpu_usage: Dict[int, float]) -> float:
    """Compute normalized fog load l_j"""
    return clamp01(fog_cpu_usage[fid] / max(1e-6, FOG_CPU_CAPACITY[fid]))


def compute_urgency(r: Request, step: int, fog_cpu_usage: Dict[int, float]) -> float:
    """Compute urgency score U_i"""
    d = deadline_term(r, step)
    c = r.criticality
    h = handoff_risk_term(r)
    l = fog_load(r.fog, fog_cpu_usage)
    return W_D * d + W_C * c + W_H * h + W_L * l


def can_host_full_chain(fid: int, r: Request, fog_cpu_usage: Dict[int, float], 
                        fog_mem_usage: Dict[int, float]) -> bool:
    """Check if fog can host FULL chain (UCM requirement)"""
    cpu_need = sum(v.cpu for v in r.vnfs)
    mem_need = sum(v.mem for v in r.vnfs)
    cpu_free = FOG_CPU_CAPACITY[fid] - fog_cpu_usage[fid]
    mem_free = FOG_MEM_CAPACITY[fid] - fog_mem_usage[fid]
    return (cpu_free >= cpu_need) and (mem_free >= mem_need)


def pick_target_fog(r: Request, step: int, fog_cpu_usage: Dict[int, float], 
                    fog_mem_usage: Dict[int, float], veh_xy) -> Optional[int]:
    """Select best target fog for FULL chain migration"""
    cands = [f for f in FOG_NODES if can_host_full_chain(f, r, fog_cpu_usage, fog_mem_usage)]
    
    if not cands:
        return None
    
    def cost(fid: int) -> float:
        rtt = rtt_proxy_ms(veh_xy, FOG_NODES[fid])
        load = fog_load(fid, fog_cpu_usage)
        return ALPHA * rtt + BETA * load
    
    return min(cands, key=cost)


def power_w(fid: int, u: float) -> float:
    """Compute power consumption with quadratic utilization model"""
    idle = IDLE_POWER_W[fid]
    mx = MAX_POWER_W[fid]
    return idle + (mx - idle) * (u ** 2)


def start_sumo(gui=False):
    """Start SUMO simulation"""
    cmd = ["sumo-gui" if gui else "sumo", "-c", SUMO_CFG, "--start", "--quit-on-end"]
    traci.start(cmd)


def run_ucm(load=400, run_id=1, seed=None, gui=False):
    """
    Run UCM simulation with improved saturation behavior
    
    Args:
        load: Target number of active requests
        run_id: Run identifier
        seed: Random seed
        gui: Enable SUMO GUI
    
    Returns:
        Dictionary of performance metrics
    """
    if seed is not None:
        random.seed(seed)
    
    # Scale request probability based on load
    REQUEST_PROB = (load / 400.0) * BASE_REQUEST_PROB
    
    step = 0
    prev_fog = {}
    
    active: Dict[str, Request] = {}
    fog_cpu_usage = {f: 0.0 for f in FOG_NODES}
    fog_mem_usage = {f: 0.0 for f in FOG_NODES}
    
    # Metrics
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
        
        # ========== ARRIVALS WITH MULTI-FOG ADMISSION ==========
        for vid in vehicle_ids:
            x, y = traci.vehicle.getPosition(vid)
            fog = get_fog(x, y)
            prev_fog[vid] = fog
            
            if fog is not None and random.random() < REQUEST_PROB:
                total_arrivals += 1
                r = sample_request(vid, fog, step)
                
                # FIX 1: Search ALL fogs for admission, not just arrival fog
                target_fog = None
                if can_host_full_chain(fog, r, fog_cpu_usage, fog_mem_usage):
                    target_fog = fog
                else:
                    # Search for alternative fog
                    candidates = [f for f in FOG_NODES 
                                if can_host_full_chain(f, r, fog_cpu_usage, fog_mem_usage)]
                    if candidates:
                        # Pick least loaded candidate
                        target_fog = min(candidates, key=lambda f: fog_load(f, fog_cpu_usage))
                
                if target_fog is None:
                    # System is fully saturated
                    blocked += 1
                    continue
                
                # Admit request to target fog
                active[r.rid] = r
                r.fog = target_fog
                
                # Reserve resources for FULL chain (UCM characteristic)
                cpu_chain = sum(v.cpu for v in r.vnfs)
                mem_chain = sum(v.mem for v in r.vnfs)
                fog_cpu_usage[target_fog] += cpu_chain
                fog_mem_usage[target_fog] += mem_chain
                
                total_mapped_vnfs += len(r.vnfs)
                total_state_mb += sum(v.state_mb for v in r.vnfs)
        
        # ========== DROP IF VEHICLE LEFT ==========
        missing_ids = [rid for rid, r in active.items() if r.vid not in vehicle_set]
        for rid in missing_ids:
            r = active[rid]
            dropped += 1
            
            cpu_chain = sum(v.cpu for v in r.vnfs)
            mem_chain = sum(v.mem for v in r.vnfs)
            fog_cpu_usage[r.fog] -= cpu_chain
            fog_mem_usage[r.fog] -= mem_chain
            del active[rid]
        
        # ========== FIX 2: OVERLOAD EVICTION ==========
        for fid in FOG_NODES:
            while (fog_cpu_usage[fid] > FOG_CPU_CAPACITY[fid] or 
                   fog_mem_usage[fid] > FOG_MEM_CAPACITY[fid]):
                
                # Find lowest-urgency request on this fog
                victims = [r for r in active.values() if r.fog == fid]
                if not victims:
                    break
                
                victim = min(victims, key=lambda r: compute_urgency(r, step, fog_cpu_usage))
                
                # Evict victim
                dropped += 1
                cpu_chain = sum(v.cpu for v in victim.vnfs)
                mem_chain = sum(v.mem for v in victim.vnfs)
                fog_cpu_usage[fid] -= cpu_chain
                fog_mem_usage[fid] -= mem_chain
                del active[victim.rid]
        
        # ========== COMPUTE URGENCY AND SORT ==========
        urg_list = []
        for r in active.values():
            U = compute_urgency(r, step, fog_cpu_usage)
            urg_list.append((U, r))
        urg_list.sort(key=lambda x: x[0], reverse=True)
        
        # ========== UCM MIGRATION LOGIC ==========
        for U, r in urg_list:
            d_i = deadline_term(r, step)
            l_i = fog_load(r.fog, fog_cpu_usage)
            
            # Trigger condition
            if not (d_i >= THETA_D or l_i >= THETA_L):
                r.last_fog = r.fog
                continue
            
            # Find target for FULL chain
            try:
                vx, vy = traci.vehicle.getPosition(r.vid)
            except traci.exceptions.TraCIException:
                # Vehicle disappeared
                dropped += 1
                cpu_chain = sum(v.cpu for v in r.vnfs)
                mem_chain = sum(v.mem for v in r.vnfs)
                fog_cpu_usage[r.fog] -= cpu_chain
                fog_mem_usage[r.fog] -= mem_chain
                if r.rid in active:
                    del active[r.rid]
                continue
            
            target = pick_target_fog(r, step, fog_cpu_usage, fog_mem_usage, (vx, vy))
            
            # FIX 3: Handle migration failure
            if target is None:
                # No fog has capacity for full chain
                if d_i >= CRITICAL_DEADLINE_THRESHOLD:
                    # Critical deadline - cannot complete, drop
                    dropped += 1
                    cpu_chain = sum(v.cpu for v in r.vnfs)
                    mem_chain = sum(v.mem for v in r.vnfs)
                    fog_cpu_usage[r.fog] -= cpu_chain
                    fog_mem_usage[r.fog] -= mem_chain
                    del active[r.rid]
                    continue
                else:
                    # Try to finish on current fog
                    r.last_fog = r.fog
                    continue
            
            if target == r.fog:
                r.last_fog = r.fog
                continue
            
            # Migrate FULL chain (UCM characteristic)
            src = r.fog
            cpu_chain = sum(v.cpu for v in r.vnfs)
            mem_chain = sum(v.mem for v in r.vnfs)
            state_chain = sum(v.state_mb for v in r.vnfs)
            
            # Move resource reservation
            fog_cpu_usage[src] -= cpu_chain
            fog_mem_usage[src] -= mem_chain
            fog_cpu_usage[target] += cpu_chain
            fog_mem_usage[target] += mem_chain
            
            r.fog = target
            
            # Migration metrics (FULL chain)
            migrated_vnfs += len(r.vnfs)
            migrated_state_mb += state_chain
            
            # Migration energy
            energy_mig_j += (K1_J_PER_MB * state_chain + K2_J_PER_MIG)
            
            r.last_fog = r.fog
        
        # ========== PROCESSING ==========
        done_ids = []
        for rid, r in active.items():
            # Deadline check
            if (step - r.arr_step) > r.deadline_steps:
                dropped += 1
                done_ids.append(rid)
                continue
            
            # Process current VNF
            r.remaining -= 1
            if r.remaining <= 0:
                r.k += 1
                
                # UCM: Hold resources for full chain until complete
                # (No progressive release - this is UCM's characteristic)
                
                if r.k >= len(r.vnfs):
                    # Request completed
                    success += 1
                    delay_sum += (step - r.arr_step)
                    done_ids.append(rid)
                else:
                    r.remaining = r.vnfs[r.k].proc_steps
        
        # Remove completed/dropped requests
        for rid in done_ids:
            r = active[rid]
            cpu_chain = sum(v.cpu for v in r.vnfs)
            mem_chain = sum(v.mem for v in r.vnfs)
            fog_cpu_usage[r.fog] -= cpu_chain
            fog_mem_usage[r.fog] -= mem_chain
            del active[rid]
        
        # ========== ENERGY COMPUTATION ==========
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
    p = argparse.ArgumentParser(description="UCM (Urgency-Aware Chain Migration) simulator")
    p.add_argument("--load", type=int, default=400)
    p.add_argument("--run_id", type=int, default=1)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--gui", action="store_true")
    args = p.parse_args()
    
    start_sumo(gui=args.gui)
    results = run_ucm(load=args.load, run_id=args.run_id, seed=args.seed, gui=args.gui)
    
    print("\n=== UCM Results ===")
    for key, value in results.items():
        print(f"{key}: {value}")