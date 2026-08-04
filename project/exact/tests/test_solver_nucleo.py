from exact_vrp import resolver
from util import instancia_minima, vehiculo, punto

LINEA = [[0, 10, 20, 30], [10, 0, 10, 25], [20, 10, 0, 10], [30, 25, 10, 0]]

def test_tsp_en_linea_optimo():
    data = instancia_minima(
        matriz_distancias_km=LINEA,
        vehiculos=[vehiculo()],
        puntos=[punto(id="a"), punto(id="b"), punto(id="c")])
    sol = resolver(data)
    assert sol["estado"] == "OPTIMO"
    assert sol["costo_total"] == 6.0
    assert sol["desglose"]["combustible"] == 6.0
    ruta = sol["rutas"][0]
    orden = [par["punto"] for par in ruta["paradas"]]
    assert orden in (["a", "b", "c"], ["c", "b", "a"])
    assert ruta["km"] == 60.0 and ruta["litros"] == 6.0
    assert sol["vehiculos_sin_usar"] == []

def test_infactible_por_diagnostico():
    data = instancia_minima()
    data["puntos"][0]["productos"] = [{"peso_kg": 5000, "volumen_m3": 0.1}]
    sol = resolver(data)
    assert sol["estado"] == "INFACTIBLE" and "no cabe" in sol["motivo"]
