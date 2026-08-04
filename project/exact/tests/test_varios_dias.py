from exact_vrp import resolver
from util import instancia_minima, vehiculo, punto

def _semanal(**kw):
    base = instancia_minima(modo="varios_dias", horizonte_dias=7,
                            vehiculos=[vehiculo()], puntos=[punto(id="a")])
    base.update(kw)
    return base

def test_entrega_el_dia_de_la_ventana():
    data = _semanal()
    data["puntos"][0]["ventanas"] = [{"dia": "jueves", "desde": "09:00", "hasta": "12:00"}]
    sol = resolver(data)
    assert sol["rutas"][0]["paradas"][0]["llegada"]["dia"] == "jueves"

def test_turno_del_camion_decide_el_dia():
    data = _semanal()
    data["puntos"][0]["ventanas"] = [
        {"dia": "martes", "desde": "09:00", "hasta": "12:00"},
        {"dia": "jueves", "desde": "09:00", "hasta": "12:00"}]
    data["vehiculos"][0]["turno"] = {"dia": "jueves", "desde": "08:00", "hasta": "17:00"}
    sol = resolver(data)
    assert sol["rutas"][0]["paradas"][0]["llegada"]["dia"] == "jueves"

def test_fecha_limite_fuerza_el_dia_temprano():
    data = _semanal()
    data["puntos"][0]["ventanas"] = [
        {"dia": "martes", "desde": "09:00", "hasta": "12:00"},
        {"dia": "viernes", "desde": "09:00", "hasta": "12:00"}]
    data["puntos"][0]["fecha_limite"] = {"dia": "miercoles", "hora": "12:00"}
    sol = resolver(data)
    assert sol["rutas"][0]["paradas"][0]["llegada"]["dia"] == "martes"

def test_salida_reporta_dia_y_hora():
    sol = resolver(_semanal())
    assert set(sol["rutas"][0]["sale_de_base"].keys()) == {"dia", "hora"}
