import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metaheuristics import cross_over as co_mod
from metaheuristics.cross_over import cross_over
from metaheuristics.Genetic_Algorithm import GeneticAlgorithm
from metaheuristics.fitness import fitness
from metaheuristics.generate_route import generate_route

VENTANA_LIBRE = (0, 10**6)


def sin_baches(n):
    return [[0] * n for _ in range(n)]


def con_puntos_de_corte(point1, point2, fn):
    original_sample = co_mod.random.sample
    co_mod.random.sample = lambda seq, k: [point1, point2]
    try:
        return fn()
    finally:
        co_mod.random.sample = original_sample


def test_hijo1_hereda_segmento_de_p1_y_orden_de_p2():
    p1 = [1, 2, 3, 4, 5, 6, 7, 8]
    p2 = [8, 7, 6, 5, 4, 3, 2, 1]
    hijo1, _ = con_puntos_de_corte(2, 4, lambda: cross_over(p1, p2))
    assert hijo1 == [3, 4, 5, 8, 7, 6, 2, 1], f"hijo1 incorrecto: {hijo1}"


def test_hijo2_hereda_segmento_de_p2_y_orden_de_p1():
    # Simétrico al hijo 1: segmento del padre 2, relleno en el orden del padre 1.
    # Con el bug, temp2 se construye solo con genes de p1 y el hijo 2 no
    # recombina nada.
    p1 = [1, 2, 3, 4, 5, 6, 7, 8]
    p2 = [8, 7, 6, 5, 4, 3, 2, 1]
    _, hijo2 = con_puntos_de_corte(2, 4, lambda: cross_over(p1, p2))
    assert hijo2 == [6, 5, 4, 1, 2, 3, 7, 8], f"hijo2 incorrecto: {hijo2}"


def test_hijos_son_permutaciones():
    random.seed(7)
    for _ in range(200):
        p1 = random.sample(range(1, 32), 31)
        p2 = random.sample(range(1, 32), 31)
        h1, h2 = cross_over(p1, p2)
        assert sorted(h1) == sorted(p1), f"hijo1 no es permutación: {h1}"
        assert sorted(h2) == sorted(p1), f"hijo2 no es permutación: {h2}"


def test_fitness_no_explota_con_mas_rutas_que_vehiculos():
    # 4 clientes de demanda 6 con capacidad 10 fuerzan 4 sub-rutas y solo hay
    # 2 vehículos: fitness debe penalizar, no lanzar IndexError.
    clients = {i: {"demand": 6.0} for i in range(1, 5)}
    ga = GeneticAlgorithm(clients, [1, 2, 3, 4], [10, 10], 2, [0])
    distances = [[abs(i - j) for j in range(5)] for i in range(5)]
    time_windows = {i: (0, 10**6) for i in range(1, 5)}
    potholes = [[0] * 5 for _ in range(5)]
    valor, vehiculos = fitness([1, 2, 3, 4], ga, distances, time_windows, potholes, 50)
    assert vehiculos > 2, f"se esperaban más rutas que vehículos, hubo {vehiculos}"
    assert valor == float("inf") or valor > 1e12, (
        f"debe penalizarse el exceso de vehículos, fitness={valor}"
    )


def test_split_elige_la_particion_optima():
    # Dos clientes pegados al depósito pero lejos entre sí: caben juntos en un
    # vehículo (greedy los uniría, costo 102) pero lo óptimo son dos rutas
    # (costo 4). El Split debe elegir la partición de costo mínimo.
    clients = {1: {"demand": 5.0}, 2: {"demand": 5.0}}
    ga = GeneticAlgorithm(clients, [1, 2], [10, 10], 2, [0])
    distances = [[0, 1, 1], [1, 0, 100], [1, 100, 0]]
    tw = {1: VENTANA_LIBRE, 2: VENTANA_LIBRE}
    rutas = generate_route([1, 2], ga, distances, tw, sin_baches(3), 50)
    assert rutas == [[1], [2]], f"partición subóptima: {rutas}"
    valor, vehiculos = fitness([1, 2], ga, distances, tw, sin_baches(3), 50)
    assert (valor, vehiculos) == (4.0, 2), f"fitness no usa el split: {(valor, vehiculos)}"


def test_split_respeta_la_capacidad():
    # Juntarlos costaría 4 y separarlos 4 también no: d(1,2)=2 hace tentador
    # unirlos, pero 6+6 excede la capacidad 10.
    clients = {1: {"demand": 6.0}, 2: {"demand": 6.0}}
    ga = GeneticAlgorithm(clients, [1, 2], [10, 10], 2, [0])
    distances = [[0, 1, 1], [1, 0, 2], [1, 2, 0]]
    tw = {1: VENTANA_LIBRE, 2: VENTANA_LIBRE}
    rutas = generate_route([1, 2], ga, distances, tw, sin_baches(3), 50)
    assert rutas == [[1], [2]], f"viola la capacidad: {rutas}"


def test_split_respeta_las_ventanas_de_tiempo():
    # En una sola ruta el cliente 2 se visita en t=11, fuera de su ventana
    # (0, 5); el Split debe separarlo aunque unirlos dé menos distancia.
    clients = {1: {"demand": 1.0}, 2: {"demand": 1.0}}
    ga = GeneticAlgorithm(clients, [1, 2], [100, 100], 2, [0])
    distances = [[0, 1, 1], [1, 0, 10], [1, 10, 0]]
    tw = {1: VENTANA_LIBRE, 2: (0, 5)}
    rutas = generate_route([1, 2], ga, distances, tw, sin_baches(3), 50)
    assert rutas == [[1], [2]], f"viola la ventana de tiempo: {rutas}"


def test_split_respeta_el_limite_de_vehiculos():
    # Tres rutas individuales costarían 6, pero solo hay 2 vehículos: el Split
    # debe devolver a lo sumo 2 rutas (la mejor partición en 2 cuesta 104).
    clients = {i: {"demand": 1.0} for i in range(1, 4)}
    ga = GeneticAlgorithm(clients, [1, 2, 3], [100, 100], 2, [0])
    distances = [
        [0, 1, 1, 1],
        [1, 0, 100, 100],
        [1, 100, 0, 100],
        [1, 100, 100, 0],
    ]
    tw = {i: VENTANA_LIBRE for i in range(1, 4)}
    rutas = generate_route([1, 2, 3], ga, distances, tw, sin_baches(4), 50)
    assert len(rutas) <= 2, f"usa más vehículos de los disponibles: {rutas}"
    assert sorted(c for r in rutas for c in r) == [1, 2, 3], f"pierde clientes: {rutas}"
    valor, vehiculos = fitness([1, 2, 3], ga, distances, tw, sin_baches(4), 50)
    assert (valor, vehiculos) == (104.0, 2), f"costo inesperado: {(valor, vehiculos)}"


def test_split_particiona_consecutivo_y_sin_perder_clientes():
    # Propiedad: el resultado siempre es una partición consecutiva del tour
    # gigante (concatenar las rutas reproduce el cromosoma) y cada ruta
    # respeta la capacidad, también cuando cae al fallback greedy.
    random.seed(11)
    n = 10
    for _ in range(50):
        demands = {i: {"demand": float(random.randint(1, 9))} for i in range(1, n + 1)}
        ga = GeneticAlgorithm(demands, list(range(1, n + 1)), [15] * 5, 5, [0])
        distances = [[0.0] * (n + 1) for _ in range(n + 1)]
        for i in range(n + 1):
            for j in range(i + 1, n + 1):
                d = float(random.randint(1, 50))
                distances[i][j] = distances[j][i] = d
        tour = random.sample(range(1, n + 1), n)
        tw = {i: VENTANA_LIBRE for i in range(1, n + 1)}
        rutas = generate_route(tour, ga, distances, tw, sin_baches(n + 1), 50)
        assert [c for r in rutas for c in r] == tour, f"no es partición consecutiva: {rutas} vs {tour}"
        for r in rutas:
            carga = sum(demands[c]["demand"] for c in r)
            assert carga <= 15, f"ruta con sobrecarga {carga}: {r}"


def test_two_opt_desenreda_la_ruta():
    from metaheuristics.local_search import two_opt
    # Clientes en línea recta (cliente i en x=i, depósito en 0): el orden
    # [2,1,3,4] cuesta 10 y el orden natural [1,2,3,4] cuesta 8.
    clients = {i: {"demand": 1.0} for i in range(1, 5)}
    ga = GeneticAlgorithm(clients, [1, 2, 3, 4], [100], 1, [0])
    distances = [[abs(i - j) for j in range(5)] for i in range(5)]
    tw = {i: VENTANA_LIBRE for i in range(1, 5)}
    mejorada = two_opt([[2, 1, 3, 4]], ga, distances, tw, sin_baches(5), 50)
    assert mejorada == [[1, 2, 3, 4]], f"2-opt no desenredó la ruta: {mejorada}"


def test_two_opt_conserva_clientes_y_no_empeora():
    from metaheuristics.local_search import two_opt
    from metaheuristics.route_cost import route_cost
    random.seed(3)
    n = 12
    clients = {i: {"demand": 1.0} for i in range(1, n + 1)}
    ga = GeneticAlgorithm(clients, list(range(1, n + 1)), [100, 100], 2, [0])
    distances = [[0.0] * (n + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        for j in range(i + 1, n + 1):
            d = float(random.randint(1, 60))
            distances[i][j] = distances[j][i] = d
    tw = {i: VENTANA_LIBRE for i in range(1, n + 1)}
    for _ in range(20):
        tour = random.sample(range(1, n + 1), n)
        rutas = [tour[:6], tour[6:]]
        costo_antes = sum(
            route_cost(r, ga, distances, tw, sin_baches(n + 1), 50, 100)[0] for r in rutas
        )
        mejoradas = two_opt(rutas, ga, distances, tw, sin_baches(n + 1), 50)
        costo_despues = sum(
            route_cost(r, ga, distances, tw, sin_baches(n + 1), 50, 100)[0] for r in mejoradas
        )
        for antes, despues in zip(rutas, mejoradas):
            assert sorted(antes) == sorted(despues), f"2-opt perdió clientes: {antes} -> {despues}"
        assert costo_despues <= costo_antes + 1e-9, f"2-opt empeoró: {costo_antes} -> {costo_despues}"


if __name__ == "__main__":
    tests = [
        test_hijo1_hereda_segmento_de_p1_y_orden_de_p2,
        test_hijo2_hereda_segmento_de_p2_y_orden_de_p1,
        test_hijos_son_permutaciones,
        test_fitness_no_explota_con_mas_rutas_que_vehiculos,
        test_split_elige_la_particion_optima,
        test_split_respeta_la_capacidad,
        test_split_respeta_las_ventanas_de_tiempo,
        test_split_respeta_el_limite_de_vehiculos,
        test_split_particiona_consecutivo_y_sin_perder_clientes,
        test_two_opt_desenreda_la_ruta,
        test_two_opt_conserva_clientes_y_no_empeora,
    ]
    fallos = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:
            fallos += 1
            print(f"FAIL {t.__name__}: {type(e).__name__}: {e}")
    sys.exit(1 if fallos else 0)
