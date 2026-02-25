# vehicular-fog-simulation/src/simulation/main.py

import simulation_environment

def main():
    # Initialize the simulation environment
    env = simulation_environment.SimulationEnvironment()

    # Set up the simulation parameters
    env.setup_parameters()

    # Start the simulation
    env.run_simulation()

    # Collect and save results
    env.save_results()

if __name__ == "__main__":
    main()