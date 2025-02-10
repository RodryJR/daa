from generate_route import generate_route

def fitness(individue, metaheuristic, distances, time_windows, potholes_matrix, max_potholes):
    route = generate_route(individue, metaheuristic)
    sub_route_distance, rout_distance, vehicle_use = 0, 0, 0
    
    for vehicle_id, sub_route in enumerate(route):
        vehicle_use += 1
        vehicle_capacity = metaheuristic.vehicle_capacities[vehicle_id]
        last_customer_id = metaheuristic.get_nearest_depot(sub_route[0], distances)
        sub_route_distance = 0
        vehicle_load = 0
        current_time = 0
        total_potholes = 0
        
        for customer_id in sub_route:
            demand = metaheuristic.clients[customer_id]['demand']
            if vehicle_load + demand > vehicle_capacity:
                return float('inf'), vehicle_use
            
            vehicle_load += demand
            distance = distances[last_customer_id][customer_id]
            current_time += distance
            total_potholes += potholes_matrix[last_customer_id][customer_id]
            
            if total_potholes > max_potholes:
                return float('inf'), vehicle_use
            
            earliest, latest = time_windows[customer_id]
            if current_time < earliest:
                current_time = earliest
            if current_time > latest:
                return float('inf'), vehicle_use
            
            sub_route_distance += distance
            last_customer_id = customer_id
        
        rout_distance += sub_route_distance + distances[last_customer_id][metaheuristic.get_nearest_depot(last_customer_id, distances)]
    
    fitness_value = rout_distance
    if vehicle_use > metaheuristic.count_vehicle:
        fitness_value *= 1000000000000000
    return fitness_value, vehicle_use