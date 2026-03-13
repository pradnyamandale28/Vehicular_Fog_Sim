def ucm_migrate(r, fog_usage, fog_capacity, candidate_fogs):

    """
    Algorithm 1 UCM
    """

    d = deadline_pressure(r)

    l = fog_load(r.fog,fog_usage,fog_capacity)

    if d < THETA_D and l < THETA_L:

        return

    target = min(
        candidate_fogs,
        key=lambda n: communication_delay(r)+fog_load(n,fog_usage,fog_capacity)
    )

    if target == r.fog:

        return

    # migrate FULL chain

    for v in r.vnfs:

        pass

    # Paper Eq 16
    volume = sum(v.image for v in r.vnfs) + SESSION_STATE

    r.fog = target

    return volume