from exact_vrp import resolver
from util import instancia_minima, vehiculo, punto

DOS = [[0, 10, 20], [10, 0, 10], [20, 10, 0]]

def _data(objetivo):
    data = instancia_minima(
        matriz_distancias_km=DOS, objetivo=objetivo,
        vehiculos=[vehiculo()],
        puntos=[punto(id="a", tiempo_descarga_min=30), punto(id="b")])
    return data

def test_lexicografico_desempata_por_makespan():
    # a->b y b->a cuestan igual (40 km); a->b termina en 00:50, b->a en 01:00
    sol = resolver(_data("costo_luego_tiempo"))
    assert sol["costo_total"] == 4.0
    assert sol["fin_ultima_entrega"] == {"hora": "00:50"}

def test_objetivo_tiempo_minimiza_makespan():
    sol = resolver(_data("tiempo"))
    assert sol["fin_ultima_entrega"] == {"hora": "00:50"}
    assert sol["costo_total"] == 4.0  # costo real reportado aunque no se optimice
