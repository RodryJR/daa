def generate_route(individue, metaheuristic, distances, time_windows, potholes_matrix, max_potholes):
    '''
    Particiona el tour gigante en sub rutas consecutivas con el algoritmo
    Split (Prins, 2004): una programación dinámica sobre los puntos de corte
    encuentra la partición de costo mínimo que respeta capacidad, ventanas de
    tiempo, límite de baches y cantidad de vehículos. Si ninguna partición es
    factible cae al particionado greedy por capacidad original (fitness la
    penalizará).
    '''
    n = len(individue)
    if n == 0:
        return []

    INF = float('inf')
    capacity = min(metaheuristic.vehicle_capacities)
    max_routes = min(metaheuristic.count_vehicle, n)

    # Costo de cada ruta candidata individue[i:j], extendiendo el segmento
    # cliente a cliente. Toda violación (capacidad, baches, ventana) solo
    # puede empeorar al extender, así que corta la extensión.
    segments = []
    for i in range(n):
        start_depot = metaheuristic.get_nearest_depot(individue[i], distances)
        last = start_depot
        vehicle_load, current_time, total_potholes, path_distance = 0, 0, 0, 0
        for j in range(i, n):
            customer_id = individue[j]
            vehicle_load += metaheuristic.clients[customer_id]['demand']
            if vehicle_load > capacity:
                break

            distance = distances[last][customer_id]
            current_time += distance
            total_potholes += potholes_matrix[last][customer_id]
            if total_potholes > max_potholes:
                break

            earliest, latest = time_windows[customer_id]
            if current_time < earliest:
                current_time = earliest
            if current_time > latest:
                break

            path_distance += distance
            last = customer_id
            return_home = distances[last][metaheuristic.get_nearest_depot(last, distances)]
            segments.append((i, j + 1, path_distance + return_home))

    # V[k][j]: costo mínimo de repartir individue[:j] en k rutas. Los
    # segmentos vienen ordenados por i, así que V[k][i] ya es definitivo
    # cuando se relajan las rutas que comienzan en i.
    V = [[INF] * (n + 1) for _ in range(max_routes + 1)]
    parent = [[-1] * (n + 1) for _ in range(max_routes + 1)]
    V[0][0] = 0
    for i, j, cost in segments:
        for used in range(max_routes):
            if V[used][i] == INF:
                continue
            new_cost = V[used][i] + cost
            if new_cost < V[used + 1][j]:
                V[used + 1][j] = new_cost
                parent[used + 1][j] = i

    best_k = min(range(1, max_routes + 1), key=lambda used: V[used][n])
    if V[best_k][n] == INF:
        return _greedy_route(individue, metaheuristic)

    route = []
    j, used = n, best_k
    while j > 0:
        i = parent[used][j]
        route.append(individue[i:j])
        j, used = i, used - 1
    route.reverse()
    return route


def _greedy_route(individue, metaheuristic):
    '''
    Particionado original: llena cada vehículo hasta agotar su capacidad.
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
