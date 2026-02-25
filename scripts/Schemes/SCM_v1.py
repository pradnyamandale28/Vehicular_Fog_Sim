"""
SCM (Split-Chain Migration) - Advanced Adaptive Scheme
Splits residual chain across two fogs under high load for better load balancing
"""

import traci
import random
import uuid
import argparse
from dataclasses import dataclass
from typing import List, Dict, Optional

# ================= CONFIG =================
SUMO_CFG = "sumo/config/sim.sumocfg"

# 24 fog nodes in 4x6 grid
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
BASE_REQUEST_PROB = 0.0002

# Urgency weights
W_D, W_C, W_H, W_L = 0.4, 0.3, 0.2, 0.1

# Thresholds
THETA_D = 0.7
THETA_L = 0.8
THETA_SPLIT = 0.85  # SCM: Load threshold to trigger splitting
CRITICAL_DEADLINE_THRESHOLD = 0.95

# Target selection weights
ALPHA = 1.0  # RTT weight
BETA = 1.0   # Load weight

# SCM-specific: Inter-fog split selection weights
GAMMA = 1.0  # Inter-fog latency weight
DELTA = 1.0  # Target fog load weight

# Service classes
SERVICE_CLASSES = ["safety", "control", "comfort", "infotainment"]

# Heterogeneous fog capacities
FOG_CPU_CAPACITY = {}
FOG_MEM_CAPACITY = {}
for f in FOG_NODES:
    FOG_CPU_CAPACITY[f] = random.choice([12, 16, 20])
    FOG_MEM_CAPACITY[f] = random.choice([32000, 48000, 64000])

# Energy model
IDLE_POWER_W = {}
MAX_POWER_W = {}
for f in FOG_NODES:
    IDLE_POWER_W[f] = random.uniform(70, 90)
    MAX_POWER_W[f] = random.uniform(250, 320)

SLOT_LEN_S = 0.02
K1_J_PER_MB = 0.01
K2_J_PER_MIG = 0.1

# Mobility parameters
N_MAX_HOPS = 6

# ==========================================


def get_fog(x, y) -> Optional[int]:
    """Find fog node covering position (x, y)"""
    for fid, (fx, fy) in FOG_NODES.items():
        if ((x - fx) ** 2 + (y - fy) ** 2) ** 0.5 <= FOG_RADIUS:
            return fid
    return None


def get_fog_neighbors(fid: int) -> List[int]:
    """
    Get neighboring fog nodes (within reasonable distance)
    For grid topology: neighbors are adjacent nodes
    """
    fx, fy = FOG_NODES[fid]
    neighbors = []
    
    for other_fid, (ox, oy) in FOG_NODES.items():
        if other_fid == fid:
            continue
        
        dist = ((fx - ox) ** 2 + (fy - oy) ** 2) ** 0.5
        
        # Consider as neighbor if within 2x fog radius (adjacent or close)
        if dist <= 2.5 * FOG_RADIUS:
            neighbors.append(other_fid)
    
    return neighbors


def inter_fog_latency_ms(fog_a: int, fog_b: int) -> float:
    """Estimate inter-fog communication latency"""
    ax, ay = FOG_NODES[fog_a]
    bx, by = FOG_NODES[fog_b]
    dist = ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
    # Lower latency than vehicle-to-fog (fiber links)
    return 2.0 + 0.01 * dist


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
    cpu: float
    mem: float
    state_mb: float
    proc_steps: int


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
    k: int
    remaining: int
    fog: int  # Primary fog (where head is)
    last_fog: int
    
    # SCM-specific: Track if chain is split
    is_split: bool
    split_index: Optional[int]  # If split, where does tail start?
    tail_fog: Optional[int]     # If split, where is tail hosted?
    
    # Mobility
    n_hops: int
    p_handoff: float


def sample_request(vid: str, fog: int, step: int) -> Request:
    """Generate a random request based on service class"""
    rid = str(uuid.uuid4())[:8]
    cls = random.choice(SERVICE_CLASSES)
    
    # Service class profiles
    if cls == "safety":
        K = random.randint(4, 5)
        deadline = random.randint(3, 5)
        crit = 1.0
        cpu_rng = (1.0, 1.5)
        mem_rng = (256, 512)
        state_rng = (5, 20)
        proc_rng = (1, 2)
        n_hops = random.randint(0, 2)
    elif cls == "control":
        K = random.randint(3, 4)
        deadline = random.randint(5, 10)
        crit = 0.7
        cpu_rng = (0.7, 1.0)
        mem_rng = (128, 256)
        state_rng = (3, 12)
        proc_rng = (1, 3)
        n_hops = random.randint(0, 3)
    elif cls == "comfort":
        K = random.randint(2, 3)
        deadline = random.randint(15, 30)
        crit = 0.5
        cpu_rng = (0.4, 0.7)
        mem_rng = (64, 128)
        state_rng = (2, 8)
        proc_rng = (1, 4)
        n_hops = random.randint(1, 4)
    else:  # infotainment
        K = random.randint(2, 3)
        deadline = random.randint(40, 75)
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
    
    # Compute handoff probability
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
        is_split=False,
        split_index=None,
        tail_fog=None,
        n_hops=n_hops,
        p_handoff=p_handoff,
    )


def residual_vnfs(r: Request) -> List[VNF]:
    """Get residual (remaining) VNF chain"""
    k = max(0, min(r.k, len(r.vnfs)))
    return r.vnfs[k:]


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


def can_host_residual(fid: int, r: Request, fog_cpu_usage: Dict[int, float], 
                      fog_mem_usage: Dict[int, float]) -> bool:
    """Check if fog can host RESIDUAL chain"""
    res = residual_vnfs(r)
    cpu_need = sum(v.cpu for v in res)
    mem_need = sum(v.mem for v in res)
    cpu_free = FOG_CPU_CAPACITY[fid] - fog_cpu_usage[fid]
    mem_free = FOG_MEM_CAPACITY[fid] - fog_mem_usage[fid]
    return (cpu_free >= cpu_need) and (mem_free >= mem_need)


def can_host_vnf_list(fid: int, vnf_list: List[VNF], 
                     fog_cpu_usage: Dict[int, float], 
                     fog_mem_usage: Dict[int, float]) -> bool:
    """Check if fog can host a specific list of VNFs"""
    cpu_need = sum(v.cpu for v in vnf_list)
    mem_need = sum(v.mem for v in vnf_list)
    cpu_free = FOG_CPU_CAPACITY[fid] - fog_cpu_usage[fid]
    mem_free = FOG_MEM_CAPACITY[fid] - fog_mem_usage[fid]
    return (cpu_free >= cpu_need) and (mem_free >= mem_need)


def pick_target_residual(r: Request, step: int, fog_cpu_usage: Dict[int, float], 
                        fog_mem_usage: Dict[int, float], veh_xy) -> Optional[int]:
    """Select best target fog for RESIDUAL chain migration"""
    cands = [f for f in FOG_NODES if can_host_residual(f, r, fog_cpu_usage, fog_mem_usage)]
    
    if not cands:
        return None
    
    def cost(fid: int) -> float:
        rtt = rtt_proxy_ms(veh_xy, FOG_NODES[fid])
        load = fog_load(fid, fog_cpu_usage)
        return ALPHA * rtt + BETA * load
    
    return min(cands, key=cost)


def try_split_chain(r: Request, fog_a: int, fog_cpu_usage: Dict[int, float],
                   fog_mem_usage: Dict[int, float]) -> Optional[tuple]:
    """
    SCM KEY FUNCTION: Try to split residual chain across two fogs
    
    Returns: (fog_b, split_index) if split is possible, None otherwise
    Where:
        fog_b: neighbor fog to host tail segment
        split_index: index where split occurs (head=[k:s], tail=[s:K])
    """
    # Get residual chain
    res = residual_vnfs(r)
    if len(res) <= 1:
        # Can't split a single VNF
        return None
    
    # Get neighbors with capacity
    neighbors = get_fog_neighbors(fog_a)
    if not neighbors:
        return None
    
    # Filter neighbors with some free capacity
    viable_neighbors = [n for n in neighbors 
                       if fog_cpu_usage[n] < 0.9 * FOG_CPU_CAPACITY[n]]
    
    if not viable_neighbors:
        return None
    
    # Select best neighbor (minimize inter-fog latency + load)
    def neighbor_cost(fid: int) -> float:
        latency = inter_fog_latency_ms(fog_a, fid)
        load = fog_load(fid, fog_cpu_usage)
        return GAMMA * latency + DELTA * load
    
    fog_b = min(viable_neighbors, key=neighbor_cost)
    
    # Try to find a valid split point
    # Work backwards from tail to find first valid split
    K = len(r.vnfs)
    k = r.k
    
    for split_idx in range(K, k, -1):  # Try K, K-1, ..., k+1
        head = r.vnfs[k:split_idx]
        tail = r.vnfs[split_idx:K]
        
        if len(tail) == 0:
            continue
        
        # Check if head fits on fog_a and tail fits on fog_b
        head_fits = can_host_vnf_list(fog_a, head, fog_cpu_usage, fog_mem_usage)
        tail_fits = can_host_vnf_list(fog_b, tail, fog_cpu_usage, fog_mem_usage)
        
        if head_fits and tail_fits:
            return (fog_b, split_idx)
    
    # No valid split found
    return None


def power_w(fid: int, u: float) -> float:
    """Compute power consumption with quadratic utilization model"""
    idle = IDLE_POWER_W[fid]
    mx = MAX_POWER_W[fid]
    return idle + (mx - idle) * (u ** 2)


def start_sumo(gui=False):
    """Start SUMO simulation"""
    cmd = ["sumo-gui" if gui else "sumo", "-c", SUMO_CFG, "--start", "--quit-on-end"]
    traci.start(cmd)


def run_scm(load=400, run_id=1, seed=None, gui=False):
    """
    Run SCM simulation with split-chain migration under high load
    
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
    split_count = 0  # SCM-specific metric
    
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
                
                # Multi-fog admission search
                target_fog = None
                if can_host_residual(fog, r, fog_cpu_usage, fog_mem_usage):
                    target_fog = fog
                else:
                    candidates = [f for f in FOG_NODES 
                                if can_host_residual(f, r, fog_cpu_usage, fog_mem_usage)]
                    if candidates:
                        target_fog = min(candidates, key=lambda f: fog_load(f, fog_cpu_usage))
                
                if target_fog is None:
                    blocked += 1
                    continue
                
                # Admit request
                active[r.rid] = r
                r.fog = target_fog
                
                # Reserve resources for residual chain
                res = residual_vnfs(r)
                cpu_res = sum(v.cpu for v in res)
                mem_res = sum(v.mem for v in res)
                fog_cpu_usage[target_fog] += cpu_res
                fog_mem_usage[target_fog] += mem_res
                
                total_mapped_vnfs += len(r.vnfs)
                total_state_mb += sum(v.state_mb for v in r.vnfs)
        
        # ========== DROP IF VEHICLE LEFT ==========
        missing_ids = [rid for rid, r in active.items() if r.vid not in vehicle_set]
        for rid in missing_ids:
            r = active[rid]
            dropped += 1
            
            # Free resources from all hosting fogs
            if r.is_split:
                # Free head from primary fog
                head = r.vnfs[r.k:r.split_index]
                fog_cpu_usage[r.fog] -= sum(v.cpu for v in head)
                fog_mem_usage[r.fog] -= sum(v.mem for v in head)
                
                # Free tail from tail fog
                tail = r.vnfs[r.split_index:]
                fog_cpu_usage[r.tail_fog] -= sum(v.cpu for v in tail)
                fog_mem_usage[r.tail_fog] -= sum(v.mem for v in tail)
            else:
                # Free residual from single fog
                res = residual_vnfs(r)
                fog_cpu_usage[r.fog] -= sum(v.cpu for v in res)
                fog_mem_usage[r.fog] -= sum(v.mem for v in res)
            
            del active[rid]
        
        # ========== OVERLOAD EVICTION ==========
        for fid in FOG_NODES:
            while (fog_cpu_usage[fid] > FOG_CPU_CAPACITY[fid] or 
                   fog_mem_usage[fid] > FOG_MEM_CAPACITY[fid]):
                
                victims = [r for r in active.values() 
                          if r.fog == fid or (r.is_split and r.tail_fog == fid)]
                if not victims:
                    break
                
                victim = min(victims, key=lambda r: compute_urgency(r, step, fog_cpu_usage))
                
                dropped += 1
                
                # Free victim's resources
                if victim.is_split:
                    head = victim.vnfs[victim.k:victim.split_index]
                    fog_cpu_usage[victim.fog] -= sum(v.cpu for v in head)
                    fog_mem_usage[victim.fog] -= sum(v.mem for v in head)
                    
                    tail = victim.vnfs[victim.split_index:]
                    fog_cpu_usage[victim.tail_fog] -= sum(v.cpu for v in tail)
                    fog_mem_usage[victim.tail_fog] -= sum(v.mem for v in tail)
                else:
                    res = residual_vnfs(victim)
                    fog_cpu_usage[victim.fog] -= sum(v.cpu for v in res)
                    fog_mem_usage[victim.fog] -= sum(v.mem for v in res)
                
                del active[victim.rid]
        
        # ========== COMPUTE URGENCY AND SORT ==========
        urg_list = []
        for r in active.values():
            U = compute_urgency(r, step, fog_cpu_usage)
            urg_list.append((U, r))
        urg_list.sort(key=lambda x: x[0], reverse=True)
        
        # ========== SCM MIGRATION LOGIC ==========
        for U, r in urg_list:
            d_i = deadline_term(r, step)
            l_i = fog_load(r.fog, fog_cpu_usage)
            
            # Trigger condition
            if not (d_i >= THETA_D or l_i >= THETA_L):
                r.last_fog = r.fog
                continue
            
            # Get vehicle position
            try:
                vx, vy = traci.vehicle.getPosition(r.vid)
            except traci.exceptions.TraCIException:
                # Vehicle disappeared
                dropped += 1
                
                if r.is_split:
                    head = r.vnfs[r.k:r.split_index]
                    fog_cpu_usage[r.fog] -= sum(v.cpu for v in head)
                    fog_mem_usage[r.fog] -= sum(v.mem for v in head)
                    
                    tail = r.vnfs[r.split_index:]
                    fog_cpu_usage[r.tail_fog] -= sum(v.cpu for v in tail)
                    fog_mem_usage[r.tail_fog] -= sum(v.mem for v in tail)
                else:
                    res = residual_vnfs(r)
                    fog_cpu_usage[r.fog] -= sum(v.cpu for v in res)
                    fog_mem_usage[r.fog] -= sum(v.mem for v in res)
                
                if r.rid in active:
                    del active[r.rid]
                continue
            
            # SCM DECISION: Should we try splitting?
            if l_i >= THETA_SPLIT and not r.is_split:
                # Current fog heavily loaded - try to split
                
                split_result = try_split_chain(r, r.fog, fog_cpu_usage, fog_mem_usage)
                
                if split_result is not None:
                    fog_b, split_idx = split_result
                    
                    # Perform split migration
                    res = residual_vnfs(r)
                    head = r.vnfs[r.k:split_idx]
                    tail = r.vnfs[split_idx:]
                    
                    # Free old residual reservation
                    cpu_res = sum(v.cpu for v in res)
                    mem_res = sum(v.mem for v in res)
                    fog_cpu_usage[r.fog] -= cpu_res
                    fog_mem_usage[r.fog] -= mem_res
                    
                    # Reserve head on current fog
                    cpu_head = sum(v.cpu for v in head)
                    mem_head = sum(v.mem for v in head)
                    fog_cpu_usage[r.fog] += cpu_head
                    fog_mem_usage[r.fog] += mem_head
                    
                    # Reserve tail on neighbor fog
                    cpu_tail = sum(v.cpu for v in tail)
                    mem_tail = sum(v.mem for v in tail)
                    fog_cpu_usage[fog_b] += cpu_tail
                    fog_mem_usage[fog_b] += mem_tail
                    
                    # Update request state
                    r.is_split = True
                    r.split_index = split_idx
                    r.tail_fog = fog_b
                    
                    # Migration metrics (only tail migrated)
                    migrated_vnfs += len(tail)
                    migrated_state_mb += sum(v.state_mb for v in tail)
                    energy_mig_j += (K1_J_PER_MB * sum(v.state_mb for v in tail) + K2_J_PER_MIG)
                    
                    split_count += 1
                    r.last_fog = r.fog
                    continue
            
            # If split not applicable or failed, try regular RCM migration
            if not r.is_split:
                target = pick_target_residual(r, step, fog_cpu_usage, fog_mem_usage, (vx, vy))
                
                if target is None:
                    # Migration failure
                    if d_i >= CRITICAL_DEADLINE_THRESHOLD:
                        dropped += 1
                        res = residual_vnfs(r)
                        fog_cpu_usage[r.fog] -= sum(v.cpu for v in res)
                        fog_mem_usage[r.fog] -= sum(v.mem for v in res)
                        del active[r.rid]
                        continue
                    else:
                        r.last_fog = r.fog
                        continue
                
                if target == r.fog:
                    r.last_fog = r.fog
                    continue
                
                # Migrate residual chain (RCM-style)
                src = r.fog
                res = residual_vnfs(r)
                cpu_res = sum(v.cpu for v in res)
                mem_res = sum(v.mem for v in res)
                state_res = sum(v.state_mb for v in res)
                
                fog_cpu_usage[src] -= cpu_res
                fog_mem_usage[src] -= mem_res
                fog_cpu_usage[target] += cpu_res
                fog_mem_usage[target] += mem_res
                
                r.fog = target
                
                migrated_vnfs += len(res)
                migrated_state_mb += state_res
                energy_mig_j += (K1_J_PER_MB * state_res + K2_J_PER_MIG)
                
                r.last_fog = r.fog
        
        # ========== PROCESSING WITH PROGRESSIVE RESOURCE RELEASE ==========
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
                # VNF completed - progressive resource release
                finished_vnf = r.vnfs[r.k]
                
                # Determine which fog hosted this VNF
                if r.is_split and r.k >= r.split_index:
                    # This VNF was on tail fog
                    fog_cpu_usage[r.tail_fog] -= finished_vnf.cpu
                    fog_mem_usage[r.tail_fog] -= finished_vnf.mem
                else:
                    # This VNF was on primary fog
                    fog_cpu_usage[r.fog] -= finished_vnf.cpu
                    fog_mem_usage[r.fog] -= finished_vnf.mem
                
                r.k += 1
                
                # Check if split boundary reached
                if r.is_split and r.k == r.split_index:
                    # Completed head, now processing tail
                    # Tail continues on tail_fog
                    pass
                
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
            
            # Free any remaining resources
            if r.k < len(r.vnfs):
                if r.is_split:
                    # Free remaining head
                    if r.k < r.split_index:
                        head = r.vnfs[r.k:r.split_index]
                        fog_cpu_usage[r.fog] -= sum(v.cpu for v in head)
                        fog_mem_usage[r.fog] -= sum(v.mem for v in head)
                    
                    # Free remaining tail
                    if r.k < len(r.vnfs):
                        tail_start = max(r.k, r.split_index)
                        tail = r.vnfs[tail_start:]
                        fog_cpu_usage[r.tail_fog] -= sum(v.cpu for v in tail)
                        fog_mem_usage[r.tail_fog] -= sum(v.mem for v in tail)
                else:
                    res = residual_vnfs(r)
                    fog_cpu_usage[r.fog] -= sum(v.cpu for v in res)
                    fog_mem_usage[r.fog] -= sum(v.mem for v in res)
            
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
        "scheme": "SCM",
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
        "split_count": split_count,
        "energy_idle_j": round(energy_idle_j, 4),
        "energy_load_j": round(energy_load_j, 4),
        "energy_mig_j": round(energy_mig_j, 4),
        "energy_total_j": round(energy_total_j, 4),
        "avg_delay_steps": round(avg_delay, 4),
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="SCM (Split-Chain Migration) simulator")
    p.add_argument("--load", type=int, default=400)
    p.add_argument("--run_id", type=int, default=1)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--gui", action="store_true")
    args = p.parse_args()
    
    start_sumo(gui=args.gui)
    results = run_scm(load=args.load, run_id=args.run_id, seed=args.seed, gui=args.gui)
    
    print("\n=== SCM Results ===")
    for key, value in results.items():
        print(f"{key}: {value}")