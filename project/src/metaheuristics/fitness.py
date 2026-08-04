from metaheuristics.generate_route import generate_route
from metaheuristics.route_cost import route_cost

def fitness(individue, metaheuristic, distances, time_windows, potholes_matrix, max_potholes):
    route = generate_route(individue, metaheuristic, distances, time_windows, potholes_matrix, max_potholes)
    rout_distance, vehicle_use = 0, 0
    capacities = metaheuristic.vehicle_capacities

    for vehicle_id, sub_route in enumerate(route):
        vehicle_use += 1
        vehicle_capacity = capacities[vehicle_id % len(capacities)]
        sub_route_distance, feasible = route_cost(
            sub_route, metaheuristic, distances, time_windows, potholes_matrix, max_potholes, vehicle_capacity)
        if not feasible:
            return float('inf'), vehicle_use
        rout_distance += sub_route_distance

    fitness_value = rout_distance
    if vehicle_use > metaheuristic.count_vehicle:
        fitness_value *= 1000000000000000
    return fitness_value, vehicle_use
