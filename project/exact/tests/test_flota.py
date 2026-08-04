from exact_vrp import resolver
from util import instancia_minima, vehiculo, punto

TRES = [[0, 10, 20], [10, 0, 10], [20, 10, 0]]

def test_fijo_alto_junta_los_puntos_en_un_camion():
    data = instancia_minima(
        matriz_distancias_km=TRES,
        vehiculos=[vehiculo(id="v1", salario_fijo=5), vehiculo(id="v2", salario_fijo=5)],
        puntos=[punto(id="a"), punto(id="b")])
    sol = resolver(data)
    # 1 camion: 40 km * 0.1 = 4.0 + 5 fijo = 9.0; 2 camiones: 6.0 + 10 = 16.0
    assert sol["costo_total"] == 9.0
    assert len(sol["rutas"]) == 1 and len(sol["vehiculos_sin_usar"]) == 1
    assert sol["desglose"]["salarios_fijos"] == 5.0

def test_elige_el_camion_de_menor_consumo():
    data = instancia_minima(
        vehiculos=[vehiculo(id="tragon", consumo_litros_km=0.3),
                   vehiculo(id="eficiente", consumo_litros_km=0.1)])
    sol = resolver(data)
    assert sol["rutas"][0]["vehiculo"] == "eficiente"

def test_salario_por_km_en_desglose():
    data = instancia_minima(vehiculos=[vehiculo(salario_por_km=0.5)])
    sol = resolver(data)  # 20 km: combustible 2.0, salario_km 10.0
    assert sol["desglose"]["salarios_km"] == 10.0
    assert sol["costo_total"] == 12.0
