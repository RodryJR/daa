def diagnosticar(inst):
    '''
    Pre-chequeos de factibilidad. Devuelve mensajes accionables; lista vacia
    si la instancia pasa todos.
    '''
    errores = []

    for p in inst.puntos:
        if all(p.peso_g > v.capacidad_peso_g or p.volumen_l > v.capacidad_volumen_l
               for v in inst.vehiculos):
            errores.append(
                f"el punto {p.id} ({p.peso_g/1000} kg, {p.volumen_l/1000} m3) "
                f"no cabe en ningun vehiculo")

    peso_total = sum(p.peso_g for p in inst.puntos)
    vol_total = sum(p.volumen_l for p in inst.puntos)
    peso_flota = sum(v.capacidad_peso_g for v in inst.vehiculos)
    vol_flota = sum(v.capacidad_volumen_l for v in inst.vehiculos)
    if peso_total > peso_flota or vol_total > vol_flota:
        errores.append(
            f"la demanda total ({peso_total/1000:g} kg, {vol_total/1000:g} m3) "
            f"excede la capacidad agregada de la flota "
            f"({peso_flota/1000:g} kg, {vol_flota/1000:g} m3)")

    for p in inst.puntos:
        for ini, fin in p.ventanas:
            if fin >= inst.horizonte_min:
                errores.append(f"el punto {p.id} tiene una ventana fuera del horizonte")
                break
        if p.ventanas and p.limite_min is not None and p.limite_min < min(v[0] for v in p.ventanas):
            errores.append(
                f"la fecha_limite del punto {p.id} es anterior a todas sus ventanas")

    for idx, p in enumerate(inst.puntos, start=1):
        llegada_min = min(v.turno_ini + round(inst.dist_km[0][idx] / v.velocidad_kmh * 60)
                          for v in inst.vehiculos)
        tope = p.limite_min if p.limite_min is not None else inst.horizonte_min - 1
        if p.ventanas:
            tope = min(tope, max(fin for _, fin in p.ventanas))
        if llegada_min > tope:
            errores.append(
                f"ningun vehiculo alcanza el punto {p.id} a tiempo "
                f"(llegada minima posible: minuto {llegada_min})")

    return errores
