from exact_vrp import resolver
from util import instancia_minima, vehiculo, punto

# base, A en x=30, B en x=60; vel 60 km/h => 0-A 30', A-B 30', 0-B 60'
DOS = [[0, 30, 60], [30, 0, 30], [60, 30, 0]]

def _data(**kw):
    base = instancia_minima(
        matriz_distancias_km=DOS,
        vehiculos=[vehiculo()],
        puntos=[punto(id="a"), punto(id="b")])
    base.update(kw)
    return base

def test_ventana_invierte_el_orden():
    # sin salario por hora la llegada exacta no esta fijada por el optimo:
    # solo se asegura el orden (la hora se fija en el test del salario).
    data = _data()
    data["puntos"][0]["ventanas"] = [{"desde": "10:00", "hasta": "10:30"}]
    data["puntos"][1]["ventanas"] = [{"desde": "08:00", "hasta": "09:00"}]
    sol = resolver(data)
    orden = [p["punto"] for p in sol["rutas"][0]["paradas"]]
    assert orden == ["b", "a"]

def test_salario_por_hora_cuenta_la_duracion():
    data = _data(vehiculos=[vehiculo(salario_por_hora=60)])
    data["puntos"][0]["ventanas"] = [{"desde": "10:00", "hasta": "10:30"}]
    data["puntos"][1]["ventanas"] = [{"desde": "08:00", "hasta": "09:00"}]
    sol = resolver(data)
    # salida 8:00, b a las 9:00, a a las 10:00, regreso 10:30 => 2.5 h * 60
    assert sol["desglose"]["salarios_horas"] == 150.0
    assert sol["rutas"][0]["sale_de_base"] == {"hora": "08:00"}
    assert sol["rutas"][0]["regresa_a_base"] == {"hora": "10:30"}

def test_descarga_desplaza_la_siguiente_llegada():
    # ventana puntual en "a" + salario por hora: todos los tiempos quedan
    # fijados por el optimo (salida 00:00, a las 00:30, b lo antes posible).
    data = _data(vehiculos=[vehiculo(salario_por_hora=60)])
    data["puntos"][0]["tiempo_descarga_min"] = 15
    data["puntos"][0]["ventanas"] = [{"desde": "00:30", "hasta": "00:30"}]
    sol = resolver(data)
    paradas = {p["punto"]: p for p in sol["rutas"][0]["paradas"]}
    assert paradas["a"]["fin_descarga"] == {"hora": "00:45"}
    assert paradas["b"]["llegada"] == {"hora": "01:15"}
    assert sol["fin_ultima_entrega"] == {"hora": "01:15"}

def test_turno_acota_la_ruta():
    data = _data(vehiculos=[vehiculo(turno={"desde": "09:00", "hasta": "11:00"})])
    sol = resolver(data)
    assert sol["rutas"][0]["sale_de_base"]["hora"] >= "09:00"
    assert sol["rutas"][0]["regresa_a_base"]["hora"] <= "11:00"

def test_descarga_al_final_del_horizonte_es_factible():
    # la ventana acota el inicio de la descarga: llegar 23:50-23:55 con 10
    # minutos de descarga es valido aunque la descarga termine pasado el
    # horizonte; sin margen en makespan esto daba INFACTIBLE
    data = _data(puntos=[punto(id="a", tiempo_descarga_min=10)],
                 matriz_distancias_km=[[0, 30], [30, 0]])
    data["puntos"][0]["ventanas"] = [{"desde": "23:50", "hasta": "23:55"}]
    sol = resolver(data)
    assert sol["estado"] == "OPTIMO"
    hora = sol["rutas"][0]["paradas"][0]["llegada"]["hora"]
    assert "23:50" <= hora <= "23:55"

def test_cierre_pasada_la_medianoche_marca_dia_siguiente():
    # con salario por hora, el solver fija llegada 23:50, salida 23:20 y
    # regreso 00:30 del dia siguiente
    data = _data(vehiculos=[vehiculo(salario_por_hora=60)],
                 puntos=[punto(id="a", tiempo_descarga_min=10)],
                 matriz_distancias_km=[[0, 30], [30, 0]])
    data["puntos"][0]["ventanas"] = [{"desde": "23:50", "hasta": "23:50"}]
    sol = resolver(data)
    assert sol["estado"] == "OPTIMO"
    assert sol["rutas"][0]["sale_de_base"] == {"hora": "23:20"}
    assert sol["rutas"][0]["regresa_a_base"] == {"hora": "00:30", "dia_siguiente": True}


def test_horas_de_ruta_exactas_sin_salario_por_hora():
    # sin salario por hora nada del objetivo fija salida/fin: antes de la
    # restriccion espejo, CP-SAT reporta salida = turno_ini (00:00) en vez
    # de la hora real, aunque la llegada a cada punto este fijada por una
    # ventana puntual (verificado empiricamente contra el modelo sin el
    # fix: ver fix-wave-report.md, hallazgo 1). Ambos puntos con ventana
    # de un solo instante (desde == hasta) para que el orden quede forzado
    # por factibilidad de la cadena de llegadas (no por un empate de
    # costo, que seria fragil) y el horario completo quede determinado
    # sin ambiguedad una vez aplicado el fix:
    #   b fijo a las 01:30 (viaje directo base->b = 60': hay 30' de
    #   holgura frente al viaje directo, asi que "salida" tiene libertad
    #   real antes del fix); a fijo a las 02:40 (b->a = 30', asi que
    #   a-antes-de-b es infactible: exigiria b >= 03:10, mas tarde que su
    #   ventana). Horario real: sale 00:30 (llegada b 01:30 menos viaje
    #   60'), llega a b 01:30, llega a a 02:40, regresa 03:10 (llegada a
    #   + descarga 0 + regreso 30').
    data = _data()
    data["puntos"][0]["ventanas"] = [{"desde": "02:40", "hasta": "02:40"}]  # a
    data["puntos"][1]["ventanas"] = [{"desde": "01:30", "hasta": "01:30"}]  # b
    sol = resolver(data)
    assert sol["estado"] == "OPTIMO"
    orden = [p["punto"] for p in sol["rutas"][0]["paradas"]]
    assert orden == ["b", "a"]
    assert sol["rutas"][0]["sale_de_base"] == {"hora": "00:30"}
    assert sol["rutas"][0]["regresa_a_base"] == {"hora": "03:10"}


def test_cierre_pasado_el_horizonte_semanal_no_crashea():
    data = _data(vehiculos=[vehiculo(salario_por_hora=60)],
                 puntos=[punto(id="a", tiempo_descarga_min=10)],
                 matriz_distancias_km=[[0, 30], [30, 0]])
    data["modo"] = "varios_dias"
    data["horizonte_dias"] = 7
    data["puntos"][0]["ventanas"] = [{"dia": "domingo", "desde": "23:50", "hasta": "23:50"}]
    sol = resolver(data)
    assert sol["estado"] == "OPTIMO"
    paradas = sol["rutas"][0]["paradas"]
    assert paradas[0]["fin_descarga"] == {"dia": "lunes", "hora": "00:00", "semana_siguiente": True}
