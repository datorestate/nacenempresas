"""Adaptación a Canarias: municipios cortados por el BORME, islas y filtros por isla."""
from nacenempresas import canarias, parser, sectores, suscriptores


def test_municipios_cortados_y_tildes():
    assert parser._municipio("C/ MAYOR 1 (PALMAS DE GRAN CANARIA (LAS") == "Las Palmas De Gran Canaria"
    assert canarias.municipio("Las", "35") == "Las Palmas de Gran Canaria"
    assert canarias.municipio("Santa Maria De Guia De Gran", "35") == "Santa María de Guía de Gran Canaria"
    assert canarias.municipio("Mogan", "35") == "Mogán"
    assert canarias.municipio("San Nicolas De Tolentino", "35") == "La Aldea de San Nicolás"
    assert canarias.municipio("Madrid", "28") == "Madrid"


def test_islas():
    assert canarias.isla("San Bartolome", "35") == "lanzarote"
    assert canarias.isla("San Bartolome De Tirajana", "35") == "gran-canaria"
    assert canarias.isla("Guia De Isora", "38") == "tenerife"
    assert canarias.isla("Valverde", "38") == "el-hierro"
    assert canarias.isla("Los Llanos De Aridane", "38") == "la-palma"


def test_alta_por_isla():
    assert suscriptores.provincias_e_islas("iLZ", "basico") == (["35"], ["lanzarote"])
    assert suscriptores.provincias_e_islas("p38", "basico") == (["38"], [])
    assert suscriptores.provincias_e_islas("pCN", "basico") == (["35", "38"], [])
    # Pro: "Tenerife" sin "isla" es la provincia; Lanzarote es isla
    assert suscriptores.provincias_e_islas("Lanzarote, Tenerife", "pro") == (["38", "35"], ["lanzarote"])
    # La provincia entera manda sobre la isla
    assert suscriptores.provincias_e_islas("Las Palmas, Lanzarote", "pro") == (["35"], [])


def test_filtro_isla_en_avisos():
    from nacenempresas import avisos
    sub = suscriptores.Suscriptor(id="x", email="a@b.c", plan="basico", provincias=["35"], islas=["lanzarote"])
    r = lambda muni: {"provincia_codigo": "35", "es_constitucion": True, "denominacion": "X SL",
                      "eventos": [{"tipo": "constitucion", "municipio": muni, "sectores": []}]}
    assert avisos.coincide(r("Arrecife"), sub)
    assert not avisos.coincide(r("Telde"), sub)


def test_sectores_canarios():
    assert sectores.clasifica("Actividades de producción cinematográfica y de vídeo")[0] == "audiovisual"
    assert sectores.clasifica("Carácter auxiliar respecto de las actividades de sus miembros")[0] == "financiero"
    assert sectores.clasifica("El código de actividad económica (CNAE) correspondiente", "6622")[0] == "financiero"
    assert sectores.clasifica("Actividad principal CNAE 5915")[0] == "audiovisual"
