"""Genera datos FICTICIOS para previsualizar la web sin acceso al BOE.

    RC_DATA_DIR=/tmp/demo python scripts/datos_ejemplo.py
Nunca se ejecuta en producción: el workflow diario usa el BORME real.
"""
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nacenempresas import almacen, parser, sectores  # noqa: E402

random.seed(7)
RAICES = ["Azahar", "Mirador", "Brisa", "Alcor", "Nogal", "Faro", "Atalaya", "Olivo", "Cierzo", "Lumen",
          "Vereda", "Ribera", "Sendero", "Cobalto", "Albor", "Marea", "Cumbre", "Trigal", "Altamira", "Vela"]
ACT = {
    "hosteleria": ("Gastro", "La explotación de bares, cafeterías y restaurantes, y servicios de catering"),
    "construccion": ("Reformas", "Construcción, reformas integrales de viviendas y locales, fontanería e instalaciones eléctricas"),
    "inmobiliaria": ("Inmuebles", "La compraventa, promoción y arrendamiento de bienes inmuebles"),
    "tecnologia": ("Digital", "Desarrollo de software, aplicaciones y servicios informáticos"),
    "consultoria": ("Consultores", "Asesoramiento y consultoría de gestión empresarial"),
    "transporte": ("Logística", "Transporte de mercancías por carretera y servicios de logística"),
    "salud": ("Salud", "Clínica de fisioterapia y servicios sanitarios"),
    "comercio": ("Comercial", "Comercio al por menor y al por mayor de artículos para el hogar"),
    "belleza": ("Estética", "Peluquería, estética y venta de productos cosméticos"),
    "energia": ("Solar", "Instalación de placas solares fotovoltaicas y autoconsumo"),
}
PROV = {"28": ("Madrid", 40), "08": ("Barcelona", 34), "46": ("Valencia", 15), "29": ("Málaga", 12),
        "41": ("Sevilla", 10), "03": ("Alicante", 11), "30": ("Murcia", 6), "50": ("Zaragoza", 5),
        "48": ("Bilbao", 5), "35": ("Las Palmas de Gran Canaria", 4),
        "38": ("Santa Cruz de Tenerife", 4)}

hoy = date.today()
for i in range(28, -1, -1):
    d = hoy - timedelta(days=i)
    if d.weekday() >= 5:
        continue
    regs = []
    for cod, (muni, media) in PROV.items():
        for _ in range(max(1, int(random.gauss(media / 2, 2)))):
            sec = random.choice(list(ACT))
            pref, obj = ACT[sec]
            nom = f"{pref.upper()} {random.choice(RAICES).upper()} {random.randint(10, 99)} SL"
            s, todos = sectores.clasifica(obj)
            regs.append({
                "numero": random.randint(100000, 999999), "denominacion": nom, "forma_juridica": "SL",
                "provincia_codigo": cod, "provincia": muni, "fecha_publicacion": d.isoformat(),
                "borme_id": f"BORME-A-EJEMPLO-{cod}", "url_pdf": "https://www.boe.es/",
                "actos": ["Constitución", "Nombramientos"], "es_constitucion": True,
                "eventos": [{"tipo": "constitucion", "acto": "Constitución", "senal": "oportunidad",
                             "objeto_social": obj, "domicilio": f"C/ EJEMPLO {random.randint(1, 90)} ({muni.upper()})",
                             "municipio": muni, "capital": random.choice([3000.0, 3000.0, 1.0, 6000.0, 10000.0]),
                             "sector": s, "sectores": todos, "organo_administracion": ["Adm. Unico"]}]})
    const = regs
    almacen.guardar_dia(d.isoformat(), {
        "fecha": d.isoformat(), "total_constituciones": len(const), "total_actos": len(const) * 3,
        "por_provincia": {}, "por_sector": {}, "eventos": {},
        "constituciones": [parser.ficha_publica(r) for r in const]},
        {"fecha": d.isoformat(), "registros": regs, "calidad": {}})
print("Datos de ejemplo generados en", almacen.RAIZ)
