def rcm_migrate(r,usage,capacity,candidates):

    d = deadline_pressure(r)

    l = fog_load(r.fog,usage,capacity)

    if d < THETA_D and l < THETA_L:

        return

    res = residual_chain(r)

    if not res:

        return

    target = min(
        candidates,
        key=lambda n: communication_delay(r)+fog_load(n,usage,capacity)
    )

    if target == r.fog:

        return

    for v in res:

        pass

    # Paper Eq 17

    volume = sum(v.image for v in res) + SESSION_STATE

    r.fog = target

    return volume