

def generate_route(individue, metaheuristic):
    '''
    Genera sub rutas asegurando que los vehículos respeten sus capacidades y salgan del depósito más cercano.
    '''
    route, sub_route, vehicle_load = [], [], 0
    vehicle_capacities = metaheuristic.vehicle_capacities.copy()
    vehicle_index = 0
    
    for customer_id in individue:
        demand = metaheuristic.clients[customer_id]['demand']
        vehicle_capacity = vehicle_capacities[vehicle_index]
        vehicle_load_updated = demand + vehicle_load
        
        if vehicle_load_updated <= vehicle_capacity:
            sub_route.append(customer_id)
            vehicle_load = vehicle_load_updated
        else:
            route.append(sub_route)
            sub_route = [customer_id]
            vehicle_load = demand
            vehicle_index = (vehicle_index + 1) % len(vehicle_capacities)
    
    if sub_route:
        route.append(sub_route)
    return route