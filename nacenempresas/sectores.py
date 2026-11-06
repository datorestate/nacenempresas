"""Clasificación orientativa del objeto social en sectores comerciales.

No sustituye al CNAE: sirve para que un cliente filtre "hostelería en Málaga"
sin tener que escribir palabras clave.
"""
from .provincias import normaliza

SECTORES = {
    "hosteleria": ("Hostelería y restauración", [
        "restaura", "bar ", "bares", "cafeter", "hosteler", "catering", "comidas",
        "bebidas", "cocina", "pizzer", "heladeria", "panaderia", "pasteleria", "take away"]),
    "turismo": ("Turismo y alojamiento", [
        "hotel", "alojamiento", "apartamentos turisticos", "vivienda de uso turistico",
        "viviendas turisticas", "agencia de viajes", "agencias de viajes", "operadores turisticos",
        "turismo", "turistic", "excursiones", "actividades nauticas"]),
    "construccion": ("Construcción y reformas", [
        "construccion", "reforma", "obras", "albanil", "fontaner", "edificacion",
        "rehabilitacion", "pintura", "carpinter", "instalaciones electricas",
        "climatizacion", "cerrajer", "impermeabiliz", "demolicion", "excavacion"]),
    "inmobiliaria": ("Inmobiliaria", [
        "inmobiliari", "bienes inmuebles", "arrendamiento de inmuebles",
        "alquiler de inmuebles", "compraventa de inmuebles", "promocion inmobiliaria",
        "solares", "fincas", "arrendamiento de viviendas", "alquiler de viviendas"]),
    "comercio": ("Comercio y distribución", [
        "venta al por menor", "comercio al por menor", "comercio al por mayor",
        "venta al por mayor", "al por mayor", "al por menor", "distribucion",
        "importacion", "exportacion", "comercio electronico", "tienda", "e-commerce",
        "compraventa de", "vending", "maquinas expendedoras"]),
    "transporte": ("Transporte y logística", [
        "transporte", "mensajer", "logistic", "mudanza", "taxi", "vtc", "almacenaje",
        "paqueteria", "reparto"]),
    "tecnologia": ("Tecnología y software", [
        "software", "informatic", "aplicaciones", "tecnolog", "programacion",
        "desarrollo web", "inteligencia artificial", "telecomunicacion", "ciberseguridad",
        "plataformas digitales", "saas", "hardware"]),
    "consultoria": ("Consultoría y servicios profesionales", [
        "consultor", "asesoramiento", "asesoria", "gestion empresarial",
        "servicios administrativos", "contabilidad", "auditoria", "juridic", "abogad",
        "arquitectura", "ingenieria", "recursos humanos", "intermediacion", "abogacia"]),
    "marketing": ("Marketing, publicidad y medios", [
        "marketing", "publicidad", "comunicacion", "diseno grafico", "organizacion de eventos",
        "fotograf", "redes sociales", "editorial"]),
    "audiovisual": ("Cine, audiovisual y espectáculos", [
        "cinematograf", "audiovisual", "produccion de video", "programas de television", "postproduccion",
        "rodaje", "peliculas", "series de television", "produccion musical", "artes escenicas",
        "espectaculos", "actividades recreativas", "entretenimiento", "animacion 3d"]),
    "salud": ("Salud y bienestar", [
        "clinica", "sanitari", "medic", "odontolog", "dental", "fisioterap", "psicolog",
        "farmac", "veterinar", "nutricion", "enfermeria", "optica", "residencia de mayores",
        "dependencia"]),
    "belleza": ("Belleza y estética", [
        "peluquer", "estetica", "belleza", "cosmetic", "barber", "unas", "tatuaje"]),
    "deporte": ("Deporte y fitness", [
        "gimnasio", "deport", "fitness", "entrenamiento personal", "yoga", "pilates",
        "crossfit", "padel"]),
    "educacion": ("Educación y formación", [
        "formacion", "educacion", "academia", "ensenanza", "escuela", "idiomas",
        "guarderia", "clases particulares", "centro educativo"]),
    "industria": ("Industria y fabricación", [
        "fabricacion", "industria", "manufactur", "metalurg", "maquinaria",
        "mecanizado", "carpinteria metalica", "soldadura", "envasado", "impresion 3d"]),
    "agricultura": ("Agricultura, ganadería y alimentación", [
        "agricol", "agrari", "ganader", "cultivo", "forestal", "pesca", "vitivinicol",
        "aceite", "alimentacion", "hortofruticol", "invernadero"]),
    "energia": ("Energía y medio ambiente", [
        "energia", "fotovoltaic", "renovable", "placas solares", "eficiencia energetica",
        "autoconsumo", "residuos", "reciclaje", "medioambient", "puntos de recarga"]),
    "automocion": ("Automoción", [
        "vehiculos", "automovil", "taller mecanico", "coches", "motocicleta", "neumatico",
        "recambios", "concesionario", "chapa y pintura", "lavado de vehiculos"]),
    "limpieza": ("Limpieza, mantenimiento y jardinería", [
        "limpieza", "mantenimiento de edificios", "jardiner", "control de plagas",
        "lavanderia", "conserjeria", "mantenimiento integral"]),
    "financiero": ("Holdings, inversión y finanzas", [
        "holding", "tenencia de participaciones", "participaciones sociales", "inversion",
        "gestion de patrimonio", "valores mobiliarios", "patrimonial", "servicios financieros",
        "seguros", "correduria", "criptoactivos", "participaciones en el capital", "corredores de seguros",
        "agrupacion de interes economico", "actividades de sus miembros"]),
}

OTROS = ("otros", "Otros sectores")

# Si el objeto social no aclara la actividad, se usa la división del CNAE (2 dígitos)
_CNAE = [((1, 3), "agricultura"), ((5, 9), "industria"), ((10, 12), "agricultura"), ((13, 33), "industria"),
         ((35, 39), "energia"), ((41, 43), "construccion"), ((45, 45), "automocion"), ((46, 47), "comercio"),
         ((49, 53), "transporte"), ((55, 55), "turismo"), ((56, 56), "hosteleria"), ((58, 58), "marketing"),
         ((59, 60), "audiovisual"), ((61, 63), "tecnologia"), ((64, 66), "financiero"), ((68, 68), "inmobiliaria"),
         ((69, 71), "consultoria"), ((72, 72), "tecnologia"), ((73, 73), "marketing"), ((74, 74), "consultoria"),
         ((75, 75), "salud"), ((77, 77), "transporte"), ((78, 78), "consultoria"), ((79, 79), "turismo"),
         ((80, 80), "limpieza"), ((81, 81), "limpieza"), ((82, 82), "consultoria"), ((85, 85), "educacion"),
         ((86, 88), "salud"), ((90, 92), "audiovisual"), ((93, 93), "deporte"), ((95, 95), "tecnologia"),
         ((96, 96), "belleza")]


def sector_cnae(cnae: str | None) -> str | None:
    try:
        div = int(str(cnae).replace(".", "")[:2])
    except (TypeError, ValueError):
        return None
    return next((s for (a, b), s in _CNAE if a <= div <= b), None)


def clasifica(objeto_social: str, cnae: str | None = None) -> tuple[str, list[str]]:
    """Devuelve (sector principal, todos los sectores detectados)."""
    if not objeto_social:
        s = sector_cnae(cnae)
        return (s, [s]) if s else (OTROS[0], [])
    t = " " + normaliza(objeto_social) + " "
    puntos = {}
    for clave, (_, palabras) in SECTORES.items():
        n = sum(t.count(p) for p in palabras)
        if n:
            puntos[clave] = n
    if not puntos:
        s = sector_cnae(cnae)
        if not s:  # "CNAE 5915" o "actividad 6622" dentro del propio objeto social
            import re
            m = re.search(r"(?:cnae|actividad|codigo)\D{0,25}(\d{2})[\.\s]?\d{0,2}", t)
            s = sector_cnae(m.group(1)) if m else None
        return (s, [s]) if s else (OTROS[0], [])
    orden = sorted(puntos, key=lambda k: (-puntos[k], list(SECTORES).index(k)))
    return orden[0], orden


def nombre_sector(clave: str) -> str:
    if clave == OTROS[0]:
        return OTROS[1]
    return SECTORES[clave][0]


def todos():
    return [(k, v[0]) for k, v in SECTORES.items()] + [OTROS]
