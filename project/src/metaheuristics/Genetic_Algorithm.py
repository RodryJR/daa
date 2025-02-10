import random
import copy
import heapq
from fitness import fitness
from cross_over import cross_over
from generate_route import generate_route

class GeneticAlgorithm:
    def __init__(self, clients, clients_id, vehicle_capacities, count_vehicle, depots):
        self.clients = clients
        self.clients_id = clients_id
        self.vehicle_capacities = vehicle_capacities
        self.count_vehicle = count_vehicle
        self.depots = depots  

    def mutation(self, clients_id):
        start, stop = sorted(random.sample(range(len(clients_id)), 2))
        cromo = clients_id[:start] + \
            clients_id[stop:start-1:-1] + clients_id[stop+1:]
        return cromo
    
    def get_nearest_depot(self, customer_id, distances):
        '''
        Devuelve el depósito más cercano a un cliente.
        '''
        return min(self.depots, key=lambda depot: distances[depot][customer_id])
    
def genetic_algorithm(metaheuristic, k, ngen, size, ratio_cross, prob_mutate, distances, time_windows, potholes_matrix, max_potholes):
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
            heapq.heapify(population)
            heap = heapq.nsmallest(n, population, key=lambda x: fitness(x, metaheuristic, distances, time_windows, potholes_matrix, max_potholes))
            return heap
        
        def tournament_selection(metaheuristic, population, n, k):
            winners = []
            for _ in range(n):
                elements = random.sample(population, k)
                winners.append(min(elements, key=lambda x: fitness(x, metaheuristic, distances, time_windows, potholes_matrix, max_potholes)))
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

    population = initial_population(metaheuristic, size)
    n_parents = round(size * ratio_cross)
    n_parents = n_parents if n_parents % 2 == 0 else n_parents - 1
    n_directs = size - n_parents
    
    for _ in range(ngen):
        population = new_generation(metaheuristic, k, population, n_parents, n_directs, prob_mutate)
    
    best_chromosome = min(population, key=lambda x: fitness(x, metaheuristic, distances, time_windows, potholes_matrix, max_potholes))
    final_route = generate_route(best_chromosome, metaheuristic)
    cost = fitness(best_chromosome, metaheuristic, distances, time_windows, potholes_matrix, max_potholes)
    
    return best_chromosome, cost, final_route