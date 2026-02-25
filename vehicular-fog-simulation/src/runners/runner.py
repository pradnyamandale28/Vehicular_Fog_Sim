from simulation.main import run_simulation

def main():
    # Define simulation parameters
    parameters = {
        'fog_density': 0.5,
        'vehicle_count': 100,
        'simulation_time': 60,  # in seconds
    }

    # Run the simulation
    results = run_simulation(parameters)

    # Process and display results
    print("Simulation Results:")
    print(results)

if __name__ == "__main__":
    main()