#!/usr/bin/env python3
"""Extrae los calendarios de fútbol 7 del Ayuntamiento de Móstoles a JSON.

Uso:
    futbol7_datos.py actualizar --destino DIR [--url URL]
        Descarga los PDF de calendarios publicados en la web municipal,
        los convierte y actualiza los JSON de temporada en DIR.

    futbol7_datos.py pdf --destino DIR FICHERO.pdf [FICHERO.pdf ...]
        Convierte PDF locales (por ejemplo de temporadas pasadas).

Cada temporada se guarda en DIR/<aaaa-aa>.json y DIR/index.json lista las
temporadas disponibles. Si se ejecuta dentro de GitHub Actions, escribe en
GITHUB_OUTPUT las variables `temporadas` (ids modificados, separados por
espacios) y `mensaje` (texto para el commit).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urljoin

# Páginas municipales con los PDF de calendarios de la serie básica (deporte
# infantil). El Ayuntamiento los ha publicado unas temporadas en la página
# «Calendario» y otras en la subpágina «Calendario Serie Básica».
URL_BASE = (
    "https://www.mostoles.es/MostolesDeporte/es/"
    "campeonatos-municipales-deporte-infantil/futbol-7/calendario"
)
URLS_CALENDARIO = [URL_BASE, URL_BASE + "/calendario-serie-basica"]
URL_CALENDARIO = URLS_CALENDARIO[-1]
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

NOMBRES_CATEGORIA = {
    "prebenjamin": "Prebenjamín",
    "benjamin": "Benjamín",
    "alevin": "Alevín",
    "infantil": "Infantil",
    "cadete": "Cadete",
    "juvenil": "Juvenil",
}
ORDEN_CATEGORIA = list(NOMBRES_CATEGORIA)

RE_PARTIDO = re.compile(
    r"^\d+\s+(?P<local>.+?)\s+-\s+(?P<visitante>.+?)\s+"
    r"(?P<fecha>\d{2}/\d{2}/\d{4})\s+(?P<hora>\d{2}:\d{2})\s*(?P<campo>.*)$"
)
# Descansos: «EQUIPO - ** DESCANSA **», «EQUIPO - ** JORNADA DE DESCANSO **»,
# «EQUIPO - DESCANSA 16/11/2019» o «DESCANSA - EQUIPO 16/11/2019» (formatos antiguos).
RE_DESCANSA = re.compile(
    r"^\d+\s+(?P<local>.+?)\s+-\s+(?P<visitante>.+?)(?:\s+(?P<fecha>\d{2}/\d{2}/\d{4}))?\s*$"
)
RE_ES_DESCANSO = re.compile(r"^(\*\*\s*)?(DESCANSA|JORNADA DE DESCANSO)(\s*\*\*)?$", re.I)
RE_JORNADA = re.compile(r"^JORNADA\s+(?P<numero>\d+)")
RE_FASE = re.compile(r"(?P<numero>\d)ª\s+(?P<tipo>FASE|VUELTA)", re.I)
RE_GRUPO = re.compile(r"GRUPO\s+(?P<numero>\d+)", re.I)


def sin_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def id_categoria(nombre: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", sin_acentos(nombre).lower()).strip("-")


def normalizar_campo(campo: str) -> str:
    """'IKER CASILLAS CAMPO 2 ZONA A' -> 'Campo 2 zona A'."""
    campo = campo.replace('"', "").replace("'", "")
    campo = re.sub(r"\bIKER(\s+CASILLAS)?\b", "", campo, flags=re.I)
    campo = re.sub(r"\s+", " ", campo).strip()
    if not campo:
        return ""
    palabras = campo.split(" ")
    salida = []
    for i, p in enumerate(palabras):
        if i == 0:
            salida.append(p.capitalize())
        elif len(p) == 1 or p.isdigit():
            salida.append(p.upper())
        else:
            salida.append(p.lower())
    return " ".join(salida)


def fecha_iso(fecha_es: str) -> str:
    d, m, a = fecha_es.split("/")
    return f"{a}-{m}-{d}"


def temporada_de_fecha(fecha: str) -> tuple[str, str]:
    """'2025-11-15' -> ('2025-26', '2025/26')."""
    anio, mes = int(fecha[:4]), int(fecha[5:7])
    inicio = anio if mes >= 7 else anio - 1
    fin = (inicio + 1) % 100
    return f"{inicio}-{fin:02d}", f"{inicio}/{fin:02d}"


def texto_pdf(ruta: Path) -> tuple[str, dict]:
    import pymupdf  # importación tardía para que `--help` no lo exija

    with pymupdf.open(ruta) as pdf:
        texto = "".join(pagina.get_text() for pagina in pdf)
        meta = dict(pdf.metadata or {})
    return texto, meta


def fecha_metadato(valor: str | None) -> str | None:
    """'D:20251021135244+02'00'' -> '2025-10-21'."""
    if not valor:
        return None
    m = re.search(r"(\d{4})(\d{2})(\d{2})", valor)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def detectar_categoria(cabecera: dict[str, str]) -> str | None:
    """Id de la categoría a partir de «Categoría:» o, en PDF antiguos, de «Competición:»/«Grupo:»."""
    explicita = cabecera.get("Categoría") or cabecera.get("Categoria")
    if explicita:
        cid = id_categoria(explicita)
        if cid in NOMBRES_CATEGORIA:
            return cid
    for clave in ("Competición", "Competicion", "Grupo", "Fase"):
        texto = sin_acentos(cabecera.get(clave, "")).upper()
        for cid in ORDEN_CATEGORIA:
            if re.search(r"\b" + cid.upper() + r"\b", texto):
                return cid
    return None


def detectar_fase(cabecera: dict[str, str]) -> dict | None:
    """{'numero': 2, 'tipo': 'vuelta', 'nombre': '2ª vuelta'} o None."""
    for clave in ("Competición", "Competicion", "Grupo", "Fase"):
        m = RE_FASE.search(cabecera.get(clave, ""))
        if m:
            tipo = m.group("tipo").lower()
            return {"numero": int(m.group("numero")), "tipo": tipo, "nombre": f"{m.group('numero')}ª {tipo}"}
    return None


def detectar_grupo(cabecera: dict[str, str]) -> int | None:
    for clave in ("Grupo", "Competición", "Competicion"):
        m = RE_GRUPO.search(cabecera.get(clave, ""))
        if m:
            return int(m.group("numero"))
    return None


def analizar_pdf(ruta: Path, url: str | None = None) -> dict | None:
    """Devuelve el calendario (categoría, fase, grupo y jornadas) y la temporada deducida.

    Devuelve None si el PDF no es de una categoría de la serie básica.
    """
    texto, meta = texto_pdf(ruta)
    lineas = [linea.strip() for linea in texto.splitlines()]

    cabecera: dict[str, str] = {}
    for i, linea in enumerate(lineas):
        if RE_JORNADA.match(linea):
            break
        if linea.endswith(":") and i + 1 < len(lineas):
            cabecera.setdefault(linea[:-1], lineas[i + 1])

    categoria = detectar_categoria(cabecera)
    if categoria is None:
        print(f"Se omite {ruta.name}: no es de una categoría de la serie básica", file=sys.stderr)
        return None
    fase = detectar_fase(cabecera)
    grupo = detectar_grupo(cabecera)

    cid = categoria
    nombre = NOMBRES_CATEGORIA[categoria]
    if fase:
        cid += f"-{fase['tipo'][0]}{fase['numero']}"
        nombre += f" · {fase['nombre']}"
    if grupo:
        cid += f"-g{grupo}"
        nombre += f" · grupo {grupo}"

    jornadas: dict[int, list[dict]] = {}
    actual: int | None = None
    for linea in lineas:
        m = RE_JORNADA.match(linea)
        if m:
            actual = int(m.group("numero"))
            jornadas.setdefault(actual, [])
            continue
        if actual is None:
            continue
        m = RE_PARTIDO.match(linea)
        if m:
            jornadas[actual].append(
                {
                    "local": m.group("local").strip(),
                    "visitante": m.group("visitante").strip(),
                    "fecha": fecha_iso(m.group("fecha")),
                    "hora": m.group("hora"),
                    "campo": normalizar_campo(m.group("campo")),
                }
            )
            continue
        m = RE_DESCANSA.match(linea)
        if m:
            local, visitante = m.group("local").strip(), m.group("visitante").strip()
            equipo = None
            if RE_ES_DESCANSO.match(visitante):
                equipo = local
            elif RE_ES_DESCANSO.match(local):
                equipo = visitante
            if equipo:
                descanso = {"local": equipo, "descansa": True}
                if m.group("fecha"):
                    descanso["fecha"] = fecha_iso(m.group("fecha"))
                jornadas[actual].append(descanso)

    lista_jornadas = []
    fechas_todas: list[str] = []
    for numero in sorted(jornadas):
        partidos = jornadas[numero]
        fechas = sorted(p["fecha"] for p in partidos if p.get("fecha") and not p.get("descansa"))
        if not fechas:
            fechas = sorted(p["fecha"] for p in partidos if p.get("fecha"))
        fechas_todas += fechas
        lista_jornadas.append(
            {
                "numero": numero,
                "fecha": fechas[0] if fechas else None,
                "partidos": partidos,
            }
        )
    if not fechas_todas:
        raise ValueError(f"No se han encontrado partidos en {ruta.name}")

    tid, tnombre = temporada_de_fecha(min(fechas_todas))
    categoria = {
        "id": cid,
        "nombre": nombre,
        "categoria": categoria,
        "categoria_nombre": NOMBRES_CATEGORIA[categoria],
        "fase": fase["nombre"] if fase else None,
        "grupo": grupo,
        "competicion": cabecera.get("Competición") or cabecera.get("Competicion"),
        "pdf": url,
        "pdf_fecha": fecha_metadato(meta.get("creationDate")),
        "jornadas": lista_jornadas,
    }
    return {"temporada_id": tid, "temporada": tnombre, "categoria": categoria}


def descargar_pdfs(urls: list[str], carpeta: Path) -> list[tuple[Path, str]]:
    """Descarga los PDF de calendario enlazados desde las páginas indicadas."""
    import requests
    from bs4 import BeautifulSoup

    sesion = requests.Session()
    sesion.headers["User-Agent"] = USER_AGENT
    resultado = []
    vistos: set[str] = set()
    for url in urls:
        respuesta = sesion.get(url, timeout=60)
        respuesta.raise_for_status()
        sopa = BeautifulSoup(respuesta.content, "html.parser")
        for enlace in sopa.find_all("a", class_="cmResourceLink"):
            href = enlace.get("href") or ""
            if not href.lower().endswith(".pdf"):
                continue
            pdf_url = urljoin(url, href)
            nombre = unquote(os.path.basename(pdf_url))
            if "CALENDARIO" not in sin_acentos(nombre).upper() or pdf_url in vistos:
                continue
            vistos.add(pdf_url)
            destino = carpeta / nombre
            datos = sesion.get(pdf_url, timeout=120)
            datos.raise_for_status()
            destino.write_bytes(datos.content)
            print(f"Descargado {nombre}", file=sys.stderr)
            resultado.append((destino, pdf_url))
    return resultado


def cargar_json(ruta: Path) -> dict | None:
    if not ruta.exists():
        return None
    with ruta.open(encoding="utf-8") as f:
        return json.load(f)


def guardar_json(ruta: Path, datos: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
        f.write("\n")


def sin_marca(temporada: dict) -> dict:
    copia = dict(temporada)
    copia.pop("actualizado", None)
    return copia


def integrar(resultados: list[dict], destino: Path, fuente: str | None) -> list[dict]:
    """Funde las categorías analizadas en los JSON de temporada. Devuelve las temporadas cambiadas."""
    hoy = dt.date.today().isoformat()
    por_temporada: dict[str, list[dict]] = {}
    nombres: dict[str, str] = {}
    for r in resultados:
        por_temporada.setdefault(r["temporada_id"], []).append(r["categoria"])
        nombres[r["temporada_id"]] = r["temporada"]

    cambiadas = []
    for tid, categorias in por_temporada.items():
        ruta = destino / f"{tid}.json"
        anterior = cargar_json(ruta)
        nuevo = {
            "temporada_id": tid,
            "temporada": nombres[tid],
            "fuente": fuente or (anterior or {}).get("fuente"),
            "actualizado": (anterior or {}).get("actualizado", hoy),
            "categorias": list((anterior or {}).get("categorias", [])),
        }
        existentes = {c["id"]: c for c in nuevo["categorias"]}
        for c in categorias:
            existentes[c["id"]] = c
        nuevo["categorias"] = sorted(
            existentes.values(),
            key=lambda c: (
                ORDEN_CATEGORIA.index(c.get("categoria", c["id"])) if c.get("categoria", c["id"]) in ORDEN_CATEGORIA else 99,
                c.get("fase") or "",
                c.get("grupo") or 0,
                c["id"],
            ),
        )
        if anterior is None or sin_marca(anterior) != sin_marca(nuevo):
            nuevo["actualizado"] = hoy
            guardar_json(ruta, nuevo)
            cambiadas.append(nuevo)
            print(f"Temporada {nuevo['temporada']}: datos actualizados", file=sys.stderr)
        else:
            print(f"Temporada {nuevo['temporada']}: sin cambios", file=sys.stderr)

    actualizar_indice(destino)
    return cambiadas


def actualizar_indice(destino: Path) -> None:
    temporadas = []
    for ruta in sorted(destino.glob("????-??.json")):
        datos = cargar_json(ruta) or {}
        temporadas.append(
            {
                "id": datos.get("temporada_id", ruta.stem),
                "nombre": datos.get("temporada", ruta.stem),
                "fichero": ruta.name,
                "actualizado": datos.get("actualizado"),
            }
        )
    indice = {"temporadas": temporadas}
    ruta_indice = destino / "index.json"
    if cargar_json(ruta_indice) != indice:
        guardar_json(ruta_indice, indice)


def mensaje_commit(cambiadas: list[dict]) -> str:
    nombres = [t["temporada"] for t in cambiadas]
    if len(nombres) == 1:
        return f"actualizada temporada {nombres[0]}"
    return "actualizadas temporadas " + ", ".join(nombres[:-1]) + f" y {nombres[-1]}"


def escribir_salida_actions(cambiadas: list[dict]) -> None:
    salida = os.environ.get("GITHUB_OUTPUT")
    if not salida:
        return
    with open(salida, "a", encoding="utf-8") as f:
        f.write("temporadas=" + " ".join(t["temporada_id"] for t in cambiadas) + "\n")
        f.write(("mensaje=" + mensaje_commit(cambiadas) if cambiadas else "mensaje=") + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="orden", required=True)

    p_act = sub.add_parser("actualizar", help="descargar de la web municipal y actualizar los JSON")
    p_act.add_argument("--destino", type=Path, required=True, help="carpeta con los JSON de temporada")
    p_act.add_argument("--url", action="append", help="página con los PDF de calendarios (repetible); por defecto las dos municipales")

    p_pdf = sub.add_parser("pdf", help="convertir PDF locales")
    p_pdf.add_argument("--destino", type=Path, required=True)
    p_pdf.add_argument("--fuente", default=URL_BASE, help="URL que se anota como origen de los datos")
    p_pdf.add_argument("ficheros", nargs="+", type=Path)

    args = parser.parse_args(argv)

    if args.orden == "actualizar":
        urls = args.url or URLS_CALENDARIO
        with tempfile.TemporaryDirectory() as tmp:
            pdfs = descargar_pdfs(urls, Path(tmp))
            if not pdfs:
                print("No se ha encontrado ningún PDF de calendario", file=sys.stderr)
                return 1
            resultados = [analizar_pdf(ruta, url) for ruta, url in pdfs]
        cambiadas = integrar([r for r in resultados if r], args.destino, URL_BASE)
    else:
        resultados = [analizar_pdf(ruta) for ruta in args.ficheros]
        cambiadas = integrar([r for r in resultados if r], args.destino, args.fuente)

    escribir_salida_actions(cambiadas)
    if cambiadas:
        print(mensaje_commit(cambiadas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
