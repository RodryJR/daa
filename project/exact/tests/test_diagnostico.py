from exact_vrp.instancia import parsear_instancia
from exact_vrp.diagnostico import diagnosticar
from util import instancia_minima, vehiculo, punto


def _diag(data):
    return diagnosticar(parsear_instancia(data))

def test_instancia_sana_sin_errores():
    assert _diag(instancia_minima()) == []

def test_punto_que_no_cabe_en_ningun_vehiculo():
    data = instancia_minima()
    data["puntos"][0]["productos"] = [{"peso_kg": 5000, "volumen_m3": 0.1}]
    errores = _diag(data)
    assert len(errores) == 1 and "p1" in errores[0] and "no cabe" in errores[0]

def test_demanda_total_excede_flota():
    data = instancia_minima(
        matriz_distancias_km=[[0, 1, 1], [1, 0, 1], [1, 1, 0]],
        puntos=[punto(id="p1", productos=[{"peso_kg": 800, "volumen_m3": 1}]),
                punto(id="p2", productos=[{"peso_kg": 800, "volumen_m3": 1}])])
    assert any("excede" in e for e in _diag(data))

def test_limite_anterior_a_ventanas():
    data = instancia_minima()
    data["puntos"][0]["ventanas"] = [{"desde": "10:00", "hasta": "12:00"}]
    data["puntos"][0]["fecha_limite"] = {"hora": "09:00"}
    assert any("fecha_limite" in e and "p1" in e for e in _diag(data))

def test_ventana_fuera_del_horizonte():
    data = instancia_minima(modo="varios_dias", horizonte_dias=2)
    data["puntos"][0]["ventanas"] = [{"dia": "viernes", "desde": "09:00", "hasta": "10:00"}]
    assert any("horizonte" in e for e in _diag(data))

def test_punto_inalcanzable_en_sus_ventanas():
    data = instancia_minima(matriz_distancias_km=[[0, 300], [300, 0]])
    data["puntos"][0]["ventanas"] = [{"desde": "00:00", "hasta": "01:00"}]
    assert any("alcanza" in e for e in _diag(data))
