def test_ortools_disponible():
    from ortools.sat.python import cp_model
    assert hasattr(cp_model, "CpModel")

def test_paquete_importable():
    import exact_vrp
    assert exact_vrp is not None
    from exact_vrp import ErrorInstancia
    assert ErrorInstancia is not None
