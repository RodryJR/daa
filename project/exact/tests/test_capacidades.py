from exact_vrp import resolver
from util import instancia_minima, vehiculo, punto

TRES = [[0, 10, 20], [10, 0, 10], [20, 10, 0]]

def _dos_puntos(**producto):
    return [punto(id="a", productos=[dict(producto)]),
            punto(id="b", productos=[dict(producto)])]

def test_peso_obliga_a_dos_camiones():
    data = instancia_minima(
        matriz_distancias_km=TRES,
        vehiculos=[vehiculo(id="v1", capacidad_peso_kg=100),
                   vehiculo(id="v2", capacidad_peso_kg=100)],
        puntos=_dos_puntos(peso_kg=60, volumen_m3=0.1))
    sol = resolver(data)
    assert len(sol["rutas"]) == 2
    assert sol["rutas"][0]["peso_cargado_kg"] == 60.0

def test_volumen_obliga_a_dos_camiones():
    data = instancia_minima(
        matriz_distancias_km=TRES,
        vehiculos=[vehiculo(id="v1", capacidad_volumen_m3=1),
                   vehiculo(id="v2", capacidad_volumen_m3=1)],
        puntos=_dos_puntos(peso_kg=1, volumen_m3=0.6))
    sol = resolver(data)
    assert len(sol["rutas"]) == 2

def test_caben_juntos_si_hay_capacidad():
    data = instancia_minima(matriz_distancias_km=TRES,
                            vehiculos=[vehiculo(), vehiculo(id="v2")],
                            puntos=_dos_puntos(peso_kg=60, volumen_m3=0.6))
    assert len(resolver(data)["rutas"]) == 1
