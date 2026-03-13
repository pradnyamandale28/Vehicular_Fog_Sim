# Migration Schemes Pseudo Code

## Common Simulation Framework

```
INITIALIZE:
    REQUEST_PROB ← (load / 400.0) * BASE_REQUEST_PROB
    step ← 0
    prev_fog ← {}  // track vehicle's previous fog node
    active ← {}    // active requests
    fog_load ← {f: 0.0 for all fog nodes}
    metrics ← {requests: 0, handoffs: 0, migrations: 0}

WHILE simulation is running:
    step ← step + 1
    
    // ========== MOBILITY TRACKING ==========
    FOR each vehicle vid:
        (x, y) ← getPosition(vid)
        fog ← getFogNode(x, y)  // find fog node in range
        
        IF vid moved from one fog to another:
            metrics["handoffs"] ← metrics["handoffs"] + 1
        
        prev_fog[vid] ← fog
    
    // ========== REQUEST ARRIVAL ==========
    FOR each vehicle vid in fog coverage:
        IF random() < REQUEST_PROB:
            r ← createRequest(vid, fog, step)
            active[r.id] ← r
            fog_load[fog] ← fog_load[fog] + 1.0
            metrics["requests"] ← metrics["requests"] + 1
            // NOTE: No capacity check - all requests accepted
    
    // ========== REQUEST COMPLETION ==========
    FOR each request r in active:
        IF step >= r.end:
            fog_load[r.fog] ← fog_load[r.fog] - completion_cost
            REMOVE r from active
    
    // ========== URGENCY CALCULATION (Common) ==========
    urgency_list ← []
    FOR each request r in active:
        d ← deadline_pressure(r, step)      // deadline urgency
        c ← r.criticality                   // criticality (0 or 1)
        h ← handoff_risk(r)                 // handoff risk
        l ← fog_load_factor(r.fog, fog_load) // load factor
        
        U ← W_D*d + W_C*c + W_H*h + W_L*l  // weighted urgency
        urgency_list.append((U, r))
    
    SORT urgency_list by U (descending)
    
    // ========== SCHEME-SPECIFIC MIGRATION LOGIC ==========
    // (See individual schemes below)
    
END WHILE
```

---

## Scheme 1: UCM (Unified Chain Migration)

### Request Model
```
Request {
    id, vid, fog, start, end, criticality, last_fog
}
```

### Migration Logic
```
FOR each (U, r) in urgency_list (sorted by urgency):
    l ← fog_load_factor(r.fog, fog_load)
    
    IF U >= THETA_U OR l >= THETA_L:
        target ← selectTargetFog(r.fog, fog_load)  // least loaded
        
        IF target ≠ r.fog:
            // Migrate entire chain
            fog_load[r.fog] ← fog_load[r.fog] - 1.0
            r.fog ← target
            fog_load[target] ← fog_load[target] + 1.0
            metrics["ucm_migrations"] ← metrics["ucm_migrations"] + 1
    
    r.last_fog ← r.fog
```

### Completion
```
IF request r completes:
    fog_load[r.fog] ← fog_load[r.fog] - 1.0
```

### Migration Cost
- **Cost per migration**: 1.0 (full chain migration)

---

## Scheme 2: RCM (Residual Chain Migration)

### Request Model
```
Request {
    id, vid, fog, start, end, criticality, last_fog
}
```

### Migration Logic
```
FOR each (U, r) in urgency_list (sorted by urgency):
    l ← fog_load_factor(r.fog, fog_load)
    
    IF U >= THETA_U OR l >= THETA_L:
        target ← selectTargetFog(r.fog, fog_load)  // least loaded
        
        IF target ≠ r.fog:
            // Migrate residual chain (partial migration)
            fog_load[r.fog] ← fog_load[r.fog] - RESIDUAL_FACTOR
            r.fog ← target
            fog_load[target] ← fog_load[target] + RESIDUAL_FACTOR
            metrics["rcm_migrations"] ← metrics["rcm_migrations"] + 1
    
    r.last_fog ← r.fog
```

### Completion
```
IF request r completes:
    fog_load[r.fog] ← fog_load[r.fog] - 1.0
```

### Migration Cost
- **Cost per migration**: 0.5 (RESIDUAL_FACTOR = 0.5)

---

## Scheme 3: PCM (Predictive Chain Migration)

### Request Model
```
Request {
    id, vid, fog, start, end, criticality, last_fog,
    predicted_fog, pre_deployed
}
```

### Migration Logic
```
FOR each (U, r) in urgency_list (sorted by urgency):
    
    // ========== PREDICTIVE PRE-DEPLOYMENT ==========
    IF NOT r.pre_deployed:
        (vid_x, vid_y) ← getVehiclePosition(r.vid)
        vid_fog ← getFogNode(vid_x, vid_y)
        
        IF vid_fog == r.fog:
            predicted ← predictTargetFog(vid_x, vid_y, r.fog)  // proximity-based
            
            IF predicted ≠ NULL:
                l ← fog_load_factor(r.fog, fog_load)
                
                IF U >= THETA_U OR l >= THETA_L:
                    // Pre-deploy to predicted target
                    r.predicted_fog ← predicted
                    r.pre_deployed ← TRUE
                    fog_load[predicted] ← fog_load[predicted] + PRE_DEPLOY_FACTOR
                    metrics["pre_deployments"] ← metrics["pre_deployments"] + 1
    
    // ========== MIGRATION HANDLING ==========
    l ← fog_load_factor(r.fog, fog_load)
    
    IF U >= THETA_U OR l >= THETA_L:
        target ← selectTargetFog(r.fog, fog_load)  // least loaded
        
        IF target ≠ r.fog:
            IF r.pre_deployed AND r.predicted_fog == target:
                // Prediction successful: migrate only state
                fog_load[r.fog] ← fog_load[r.fog] - STATE_MIG_FACTOR
                fog_load[target] ← fog_load[target] + STATE_MIG_FACTOR
                // Pre-deployment cost already accounted
                metrics["state_migrations"] ← metrics["state_migrations"] + 1
            ELSE:
                // Prediction failed or no prediction: fallback to residual
                IF r.pre_deployed:
                    // Remove pre-deployment cost
                    fog_load[r.predicted_fog] ← fog_load[r.predicted_fog] - PRE_DEPLOY_FACTOR
                
                fog_load[r.fog] ← fog_load[r.fog] - RESIDUAL_FACTOR
                fog_load[target] ← fog_load[target] + RESIDUAL_FACTOR
                r.pre_deployed ← FALSE
                r.predicted_fog ← NULL
                metrics["residual_migrations"] ← metrics["residual_migrations"] + 1
            
            r.fog ← target
    
    r.last_fog ← r.fog
```

### Completion
```
IF request r completes:
    fog_load[r.fog] ← fog_load[r.fog] - 1.0
    
    IF r.pre_deployed AND r.predicted_fog ≠ NULL:
        fog_load[r.predicted_fog] ← fog_load[r.predicted_fog] - PRE_DEPLOY_FACTOR
```

### Migration Costs
- **Pre-deployment cost**: 0.3 (PRE_DEPLOY_FACTOR)
- **State migration cost**: 0.2 (STATE_MIG_FACTOR) - only if prediction succeeds
- **Residual migration cost**: 0.5 (RESIDUAL_FACTOR) - if prediction fails

---

## Scheme 4: SCM (Split Chain Migration)

### Request Model
```
Request {
    id, vid, fog_head, fog_tail, start, end, criticality
}
// fog_head: stays at original fog
// fog_tail: can migrate to other fogs
```

### Migration Logic
```
FOR each (U, r) in urgency_list (sorted by urgency):
    l ← fog_load_factor(r.fog_head, fog_load)
    
    IF U >= THETA_U OR l >= THETA_L:
        target ← selectTargetFog(r.fog_tail, fog_load)  // least loaded
        
        IF target ≠ r.fog_tail:
            // Migrate ONLY tail (head stays)
            fog_load[r.fog_tail] ← fog_load[r.fog_tail] - TAIL_FACTOR
            r.fog_tail ← target
            fog_load[target] ← fog_load[target] + TAIL_FACTOR
            metrics["scm_migrations"] ← metrics["scm_migrations"] + 1
```

### Completion
```
IF request r completes:
    fog_load[r.fog_head] ← fog_load[r.fog_head] - HEAD_FACTOR
    fog_load[r.fog_tail] ← fog_load[r.fog_tail] - TAIL_FACTOR
```

### Migration Cost
- **Head stays**: 0.6 (HEAD_FACTOR)
- **Tail migrates**: 0.4 (TAIL_FACTOR)

---

## Common Helper Functions

### Urgency Calculation
```
deadline_pressure(r, t):
    RETURN max(0.0, 1.0 - (r.end - t) / MAX_DURATION)

fog_load_factor(fid, fog_load):
    RETURN min(1.0, fog_load[fid] / 10.0)  // normalized to [0, 1]

selectTargetFog(current, fog_load):
    candidates ← all fog nodes except current
    SORT candidates by fog_load (ascending)
    RETURN candidate with minimum load
```

### PCM-Specific Helper
```
predictTargetFog(x, y, current_fog):
    min_dist ← INFINITY
    predicted ← NULL
    
    FOR each fog node fid ≠ current_fog:
        dist ← distance((x, y), fog_node_position[fid])
        IF dist < min_dist:
            min_dist ← dist
            predicted ← fid
    
    RETURN predicted
```

---

## Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `W_D` | 0.4 | Deadline weight |
| `W_C` | 0.3 | Criticality weight |
| `W_H` | 0.2 | Handoff risk weight |
| `W_L` | 0.1 | Load factor weight |
| `THETA_U` | 0.6 | Urgency threshold |
| `THETA_L` | 0.7 | Load threshold |
| `RESIDUAL_FACTOR` | 0.5 | RCM migration cost |
| `PRE_DEPLOY_FACTOR` | 0.3 | PCM pre-deployment cost |
| `STATE_MIG_FACTOR` | 0.2 | PCM state migration cost |
| `HEAD_FACTOR` | 0.6 | SCM head portion |
| `TAIL_FACTOR` | 0.4 | SCM tail portion |

---

## Migration Cost Comparison

| Scheme | Migration Cost | Notes |
|--------|----------------|-------|
| **UCM** | 1.0 | Full chain migration |
| **RCM** | 0.5 | Residual chain migration |
| **PCM** | 0.2 (best case) | State migration if prediction succeeds |
| **PCM** | 0.5 (worst case) | Residual migration if prediction fails |
| **SCM** | 0.4 | Only tail migrates |

---

## Notes

1. **No Capacity Limits**: All schemes accept all requests regardless of fog node load
2. **No Request Rejection**: Requests are never dropped or rejected
3. **Handoffs**: Counted separately from migrations (vehicle mobility vs. service migration)
4. **Load Factor**: Uses 10.0 as normalization factor, but this is NOT a capacity limit

