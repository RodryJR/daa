def route_cost(sub_route, metaheuristic, distances, time_windows, potholes_matrix, max_potholes, vehicle_capacity):
    '''
    Costo (distancia) de una sub-ruta depósito -> clientes -> depósito.
    Devuelve (costo, factible); la ruta es infactible si viola la capacidad,
    una ventana de tiempo o el límite de baches.
    '''
    if not sub_route:
        return 0.0, True

    vehicle_load, current_time, total_potholes, total_distance = 0, 0, 0, 0
    last_customer_id = metaheuristic.get_nearest_depot(sub_route[0], distances)

    for customer_id in sub_route:
        vehicle_load += metaheuristic.clients[customer_id]['demand']
        if vehicle_load > vehicle_capacity:
            return float('inf'), False

        distance = distances[last_customer_id][customer_id]
        current_time += distance
        total_potholes += potholes_matrix[last_customer_id][customer_id]

        if total_potholes > max_potholes:
            return float('inf'), False

        earliest, latest = time_windows[customer_id]
        if current_time < earliest:
            current_time = earliest
        if current_time > latest:
            return float('inf'), False

        total_distance += distance
        last_customer_id = customer_id

    total_distance += distances[last_customer_id][metaheuristic.get_nearest_depot(last_customer_id, distances)]
    return total_distance, True
