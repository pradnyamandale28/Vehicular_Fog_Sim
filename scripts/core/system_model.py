from dataclasses import dataclass
from typing import List

@dataclass
class VNF:

    cpu: float
    mem: float
    state_mb: float
    proc_steps: int


@dataclass
class Request:

    rid:str
    vid:str

    vnfs:List[VNF]

    k:int
    remaining:int

    fog:int

    deadline:int
    arrival:int

    criticality:float

    n_hops:int
    p_handoff:float


def residual_chain(r):

    return r.vnfs[r.k:]


def remaining_steps(r):

    steps = r.remaining

    for v in r.vnfs[r.k+1:]:

        steps += v.proc_steps

    return steps


def fog_load(fid,usage,capacity):

    return min(1.0, usage[fid]/capacity[fid]) 