import random
import copy
import heapq
from metaheuristics.fitness import fitness
from metaheuristics.cross_over import cross_over
from metaheuristics.generate_route import generate_route
from metaheuristics.local_search import two_opt

class GeneticAlgorithm:
    def __init__(self, clients, clients_id, vehicle_capacities, count_vehicle, depots):
        self.clients = clients
        self.clients_id = clients_id
        self.vehicle_capacities = vehicle_capacities
        self.count_vehicle = count_vehicle
        self.depots = depots  

    def mutation(self, clients_id):
        start, stop = sorted(random.sample(range(len(clients_id)), 2))
        clients_id[start:stop+1] = clients_id[start:stop+1][::-1]
        return clients_id
    
    def get_nearest_depot(self, customer_id, distances):
        '''
        Devuelve el depósito más cercano a un cliente.
        '''
        return min(self.depots, key=lambda depot: distances[depot][customer_id])
    
def genetic_algorithm(metaheuristic, k, ngen, size, ratio_cross, prob_mutate, distances, time_windows, potholes_matrix, max_potholes):
    memo = {}

    def evaluate(individue):
        '''
        fitness memoizado por contenido del cromosoma: los elitistas y los
        ganadores de torneo se reevalúan muchas veces por generación.
        '''
        key = tuple(individue)
        result = memo.get(key)
        if result is None:
            if len(memo) > 200000:
                memo.clear()
            result = fitness(individue, metaheuristic, distances, time_windows, potholes_matrix, max_potholes)
            memo[key] = result
        return result

    def initial_population(metaheuristic, size):
        population = []
        individue = metaheuristic.clients_id
        for _ in range(size):
            random.shuffle(individue)
            aux = copy.deepcopy(individue)
            population.append(aux)
        return population

    def new_generation(metaheuristic, k, population, n_parents, n_directs, prob_mutate):
        def selection(metaheuristic, population, n):
            return heapq.nsmallest(n, population, key=evaluate)

        def tournament_selection(metaheuristic, population, n, k):
            winners = []
            for _ in range(n):
                elements = random.sample(population, k)
                winners.append(min(elements, key=evaluate))
            return winners

        def cross_parents(parents):
            childs = []
            for i in range(0, len(parents), 2):
                childs.extend(cross_over(parents[i], parents[i + 1]))
            return childs

        def mutate(metaheuristic, population, prob):
            for i in population:
                if random.random() < prob:
                    metaheuristic.mutation(i)
            return population

        directs = selection(metaheuristic, population, n_directs)
        crosses = cross_parents(tournament_selection(metaheuristic, population, n_parents, k))
        mutations = mutate(metaheuristic, crosses, prob_mutate)
        return directs + mutations

    def polish(individue):
        '''
        Pule un individuo con 2-opt sobre sus sub-rutas y devuelve el mejor
        entre el original y el pulido. Se aplica solo al final: hacerlo por
        generación acelera la convergencia prematura y empeora los resultados.
        '''
        routes = generate_route(individue, metaheuristic, distances, time_windows, potholes_matrix, max_potholes)
        polished_routes = two_opt(routes, metaheuristic, distances, time_windows, potholes_matrix, max_potholes)
        polished = [customer for sub_route in polished_routes for customer in sub_route]
        return polished if evaluate(polished) < evaluate(individue) else individue

    population = initial_population(metaheuristic, size)
    n_parents = round(size * ratio_cross)
    n_parents = n_parents if n_parents % 2 == 0 else n_parents - 1
    n_directs = size - n_parents

    for _ in range(ngen):
        population = new_generation(metaheuristic, k, population, n_parents, n_directs, prob_mutate)
    
    best_chromosome = polish(min(population, key=evaluate))
    final_route = generate_route(best_chromosome, metaheuristic, distances, time_windows, potholes_matrix, max_potholes)
    cost = evaluate(best_chromosome)
    
    return best_chromosome, cost, final_route