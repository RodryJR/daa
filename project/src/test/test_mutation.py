import copy
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metaheuristics import Genetic_Algorithm as ga_mod
from metaheuristics.Genetic_Algorithm import GeneticAlgorithm, genetic_algorithm


def make_instance(n=10):
    clients = {i: {"demand": 1.0} for i in range(1, n + 1)}
    return GeneticAlgorithm(clients, list(range(1, n + 1)), [100, 100, 100], 3, [0])


def test_mutation_modifica_el_cromosoma():
    # mutate() en new_generation llama `metaheuristic.mutation(i)` descartando
    # el retorno, así que la mutación solo tiene efecto si modifica `i` in place.
    ga = make_instance()
    individuo = list(range(1, 11))
    antes = copy.deepcopy(individuo)
    random.seed(42)
    ga.mutation(individuo)
    assert individuo != antes, (
        "mutation() no tuvo efecto: construye una lista nueva y el llamador la descarta"
    )


def test_mutation_conserva_los_clientes_en_todo_punto_de_corte():
    # El cromosoma es una permutación: mutar no puede perder ni duplicar clientes,
    # incluido el caso start == 0 (donde el slice [stop:start-1:-1] queda vacío).
    ga = make_instance()
    n = 10
    original_sample = ga_mod.random.sample
    try:
        for start in range(n - 1):
            for stop in range(start + 1, n):
                ga_mod.random.sample = lambda seq, k, s=start, e=stop: [s, e]
                resultado = ga.mutation(list(range(1, n + 1)))
                assert sorted(resultado) == list(range(1, n + 1)), (
                    f"se pierden clientes con start={start}, stop={stop}: {resultado}"
                )
    finally:
        ga_mod.random.sample = original_sample


def test_mutation_invierte_el_segmento():
    ga = make_instance()
    original_sample = ga_mod.random.sample
    try:
        ga_mod.random.sample = lambda seq, k: [2, 5]
        resultado = ga.mutation([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        assert resultado == [1, 2, 6, 5, 4, 3, 7, 8, 9, 10], (
            f"inversión incorrecta: {resultado}"
        )
    finally:
        ga_mod.random.sample = original_sample


def test_genetic_algorithm_produce_rutas_validas():
    # Regresión: tras ejecutar el GA completo, las rutas deben cubrir cada
    # cliente exactamente una vez y el costo debe ser finito.
    n = 6
    ga = make_instance(n)
    distances = [[abs(i - j) for j in range(n + 1)] for i in range(n + 1)]
    time_windows = {i: (0, 10**6) for i in range(1, n + 1)}
    potholes = [[0] * (n + 1) for _ in range(n + 1)]
    _, cost, rutas = genetic_algorithm(
        ga, 2, 20, 30, 0.85, 0.5, distances, time_windows, potholes, 50
    )
    visitados = sorted(c for sub in rutas for c in sub)
    assert visitados == list(range(1, n + 1)), f"rutas inválidas: {rutas}"
    assert cost[0] != float("inf"), f"costo infinito: {cost}"


if __name__ == "__main__":
    tests = [
        test_mutation_modifica_el_cromosoma,
        test_mutation_conserva_los_clientes_en_todo_punto_de_corte,
        test_mutation_invierte_el_segmento,
        test_genetic_algorithm_produce_rutas_validas,
    ]
    fallos = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            fallos += 1
            print(f"FAIL {t.__name__}: {e}")
    sys.exit(1 if fallos else 0)
