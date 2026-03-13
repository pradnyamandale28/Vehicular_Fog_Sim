def scm_split(r,neighbors,usage,capacity):

    if fog_load(r.fog,usage,capacity) < THETA_SPLIT:

        return rcm_migrate(r)

    best = min(
        neighbors,
        key=lambda n:fog_load(n,usage,capacity)
    )

    K = len(r.vnfs)

    k = r.k

    split=None

    for m in range(k+1,K):

        head = r.vnfs[k:m]

        tail = r.vnfs[m:]

        if head and tail:

            split=m

    if split is None:

        return rcm_migrate(r)

    tail = r.vnfs[split:]

    # Paper Eq 20

    volume=sum(v.image for v in tail)+SESSION_STATE

    r.tail_fog=best

    return volume