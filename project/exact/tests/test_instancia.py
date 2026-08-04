import pytest
from exact_vrp.instancia import (ErrorInstancia, parsear_instancia,
                                 hora_a_minutos, minuto_absoluto)
from util import instancia_minima, vehiculo, punto


def test_hora_a_minutos():
    assert hora_a_minutos("08:30") == 510
    with pytest.raises(ErrorInstancia):
        hora_a_minutos("25:00")
    with pytest.raises(ErrorInstancia):
        hora_a_minutos("0830")

def test_minuto_absoluto_varios_dias():
    assert minuto_absoluto("martes", "09:00", "varios_dias", "x") == 1440 + 540

def test_minuto_absoluto_un_dia_rechaza_dia():
    with pytest.raises(ErrorInstancia):
        minuto_absoluto("martes", "09:00", "un_dia", "x")

def test_parsea_minima_con_defaults():
    inst = parsear_instancia(instancia_minima())
    assert inst.horizonte_min == 1440
    assert inst.objetivo == "costo"
    v = inst.vehiculos[0]
    assert (v.salario_fijo_cent, v.salario_por_km, v.salario_cent_min) == (0, 0.0, 0)
    assert v.regresa_a_base is True
    assert (v.turno_ini, v.turno_fin) == (0, 1440)
    p = inst.puntos[0]
    assert (p.peso_g, p.volumen_l) == (10000, 100)
    assert p.ventanas == [] and p.limite_min is None and p.descarga_min == 0

def test_convierte_unidades_y_ventanas():
    data = instancia_minima(modo="varios_dias", horizonte_dias=7)
    data["vehiculos"][0]["salario_fijo"] = 12.5
    data["vehiculos"][0]["salario_por_hora"] = 60
    data["puntos"][0]["ventanas"] = [{"dia": "martes", "desde": "09:00", "hasta": "13:00"}]
    data["puntos"][0]["fecha_limite"] = {"dia": "miercoles", "hora": "18:00"}
    inst = parsear_instancia(data)
    assert inst.vehiculos[0].salario_fijo_cent == 1250
    assert inst.vehiculos[0].salario_cent_min == 100
    assert inst.puntos[0].ventanas == [(1440 + 540, 1440 + 780)]
    assert inst.puntos[0].limite_min == 2 * 1440 + 1080

@pytest.mark.parametrize("romper,mensaje", [
    (lambda d: d.update(modo="mensual"), "modo"),
    (lambda d: d.update(matriz_distancias_km=[[0, 1], [1, 0], [0, 0]]), "matriz"),
    (lambda d: d.update(matriz_distancias_km=[[0, -1], [1, 0]]), "matriz"),
    (lambda d: d.update(matriz_distancias_km=[[5, 1], [1, 0]]), "diagonal"),
    (lambda d: d.update(vehiculos=[]), "vehiculo"),
    (lambda d: d.update(puntos=[]), "punto"),
    (lambda d: d["puntos"][0].update(productos=[]), "producto"),
    (lambda d: d["vehiculos"][0].update(velocidad_kmh=0), "velocidad"),
    (lambda d: d["vehiculos"][0].update(id="p1x") or d["vehiculos"].append(dict(d["vehiculos"][0])), "repetido"),
    (lambda d: d["puntos"][0].update(ventanas=[{"desde": "10:00", "hasta": "09:00"}]), "ventana"),
])
def test_validaciones(romper, mensaje):
    data = instancia_minima()
    romper(data)
    with pytest.raises(ErrorInstancia) as e:
        parsear_instancia(data)
    assert mensaje in str(e.value).lower()
