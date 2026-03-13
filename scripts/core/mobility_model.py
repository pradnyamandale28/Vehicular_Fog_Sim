import traci

def predict_next_fog(vid,current_fog,fog_nodes):

    try:

        x,y=traci.vehicle.getPosition(vid)

        best=None
        best_dist=1e9

        for fid,(fx,fy) in fog_nodes.items():

            if fid==current_fog:
                continue

            dist=((x-fx)**2+(y-fy)**2)**0.5

            if dist<best_dist:

                best_dist=dist
                best=fid

        return best

    except:

        return None