from metaheuristics.route_cost import route_cost

def two_opt(route, metaheuristic, distances, time_windows, potholes_matrix, max_potholes):
    '''
    Mejora cada sub-ruta invirtiendo segmentos (2-opt) hasta que no exista
    mejora, sin romper la factibilidad. Devuelve las sub-rutas mejoradas.
    '''
    capacity = min(metaheuristic.vehicle_capacities)
    improved_route = []

    for sub_route in route:
        best = list(sub_route)
        best_cost, feasible = route_cost(
            best, metaheuristic, distances, time_windows, potholes_matrix, max_potholes, capacity)
        if not feasible:
            improved_route.append(best)
            continue

        improved = True
        while improved:
            improved = False
            for start in range(len(best) - 1):
                for stop in range(start + 1, len(best)):
                    candidate = best[:start] + best[start:stop+1][::-1] + best[stop+1:]
                    cost, ok = route_cost(
                        candidate, metaheuristic, distances, time_windows, potholes_matrix, max_potholes, capacity)
                    if ok and cost < best_cost - 1e-9:
                        best, best_cost = candidate, cost
                        improved = True
        improved_route.append(best)

    return improved_route
