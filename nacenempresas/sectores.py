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
        "viviendas turisticas", "agencia de viajes", "turismo", "turistic"]),
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
        "compraventa de"]),
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
        "arquitectura", "ingenieria", "recursos humanos", "intermediacion"]),
    "marketing": ("Marketing, publicidad y medios", [
        "marketing", "publicidad", "comunicacion", "diseno grafico", "organizacion de eventos",
        "audiovisual", "fotograf", "redes sociales", "produccion musical", "editorial"]),
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
        "seguros", "correduria", "criptoactivos"]),
}

OTROS = ("otros", "Otros sectores")


def clasifica(objeto_social: str) -> tuple[str, list[str]]:
    """Devuelve (sector principal, todos los sectores detectados)."""
    if not objeto_social:
        return OTROS[0], []
    t = " " + normaliza(objeto_social) + " "
    puntos = {}
    for clave, (_, palabras) in SECTORES.items():
        n = sum(t.count(p) for p in palabras)
        if n:
            puntos[clave] = n
    if not puntos:
        return OTROS[0], []
    orden = sorted(puntos, key=lambda k: (-puntos[k], list(SECTORES).index(k)))
    return orden[0], orden


def nombre_sector(clave: str) -> str:
    if clave == OTROS[0]:
        return OTROS[1]
    return SECTORES[clave][0]


def todos():
    return [(k, v[0]) for k, v in SECTORES.items()] + [OTROS]
