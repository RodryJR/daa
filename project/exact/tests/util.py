def vehiculo(**kw):
    base = {"id": "v1", "capacidad_peso_kg": 1000, "capacidad_volumen_m3": 10,
            "consumo_litros_km": 0.1, "velocidad_kmh": 60}
    base.update(kw)
    return base

def punto(**kw):
    base = {"id": "p1", "productos": [{"peso_kg": 10, "volumen_m3": 0.1}]}
    base.update(kw)
    return base

def instancia_minima(**kw):
    base = {
        "modo": "un_dia",
        "matriz_distancias_km": [[0, 10], [10, 0]],
        "precio_combustible_litro": 1.0,
        "vehiculos": [vehiculo()],
        "puntos": [punto()],
    }
    base.update(kw)
    return base
