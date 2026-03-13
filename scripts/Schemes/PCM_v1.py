def pcm_strategy(r,usage,capacity):

    U = urgency(r,usage,capacity)

    if U < THETA_U:

        return

    if r.handoff_prob < THETA_P:

        return

    predicted = r.predicted_fog

    if predicted is None:

        return

    res = residual_chain(r)

    # Phase 1 predeployment

    for v in res:

        pass

    r.replica = predicted


def pcm_handoff(r):

    if hasattr(r,"replica"):

        r.fog = r.replica

        # Paper Eq 18

        return SESSION_STATE

    else:

        return rcm_migrate(r)  