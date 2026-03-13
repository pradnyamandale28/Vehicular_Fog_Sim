from core.system_model import remaining_steps,fog_load

W_D=0.4
W_C=0.3
W_H=0.2
W_L=0.1

N_MAX_HOPS=6


def deadline_pressure(r,step):

    elapsed = step-r.arrival

    rem_deadline=r.deadline-elapsed

    rem_work=remaining_steps(r)

    slack=rem_deadline-rem_work

    if r.deadline<=0:

        return 1

    return max(0,min(1,1-(slack/max(1,r.deadline))))


def continuity_risk(r):

    return r.p_handoff*(len(r.vnfs[r.k:])/len(r.vnfs))


def compute_urgency(r,step,usage,capacity):

    d=deadline_pressure(r,step)

    c=r.criticality

    h=continuity_risk(r)

    l=fog_load(r.fog,usage,capacity)

    return W_D*d + W_C*c + W_H*h + W_L*l