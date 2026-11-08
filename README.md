# Calendarios de fútbol 7 del Club Deportivo Estoril II

Herramientas para publicar en la web del club los calendarios de los
campeonatos municipales de fútbol 7 del Ayuntamiento de Móstoles
(categorías prebenjamín, benjamín, alevín e infantil), en los que participa
la [escuela de fútbol 7](https://www.clubestoril2.es/escuelas-y-actividades/escuela-de-futbol-7/)
del club.

Antes el proyecto generaba un HTML estático que había que copiar y pegar a
mano en la página del club. Ahora los datos se extraen automáticamente, se
publican como JSON en GitHub Pages y una pequeña aplicación JavaScript los
pinta en la página del club con filtros de temporada, categoría y jornada.

## Cómo funciona

```
Web del Ayuntamiento (PDF)  ──►  scripts/futbol7_datos.py  ──►  rama futbol7-app (data/*.json)
                                 (GitHub Actions, a diario)              │
                                                                         ▼
                                                     GitHub Pages: https://futbol7-app.www.clubestoril2.es/
                                                                         │
                                                                         ▼
                    página del club: <div id="futbol7-app"> + futbol7.js + futbol7.css
```

### Rama `master` (este código)

| Fichero | Contenido |
| --- | --- |
| `scripts/futbol7_datos.py` | Descarga los PDF de calendarios de la web municipal, los convierte a JSON y actualiza los ficheros de temporada. |
| `.github/workflows/actualizar-datos.yml` | Flujo diario que ejecuta el script contra la rama `futbol7-app` y, si hay cambios, hace commit y lanza el despliegue. |
| `requirements.txt` | Dependencias de Python (PyMuPDF, requests, BeautifulSoup). |
| `.claude/launch.json` | Servidor estático local para probar la aplicación. |

### Rama `futbol7-app` (desvinculada)

Contiene únicamente lo que se publica en GitHub Pages:

| Fichero | Contenido |
| --- | --- |
| `futbol7.js` | Aplicación: carga los JSON y pinta los calendarios con filtros. Sin dependencias. |
| `futbol7.css` | Estilos mínimos (grupos de filtros y resaltados). Botones, tablas, avisos y textos secundarios usan las clases del tema del club (`ce-boton`, `ce-tabla`, `ce-aviso`, `ce-meta`, `ce-oculto`), así que fuera de la web del club hay que cargar también las hojas del tema, como hace `index.html`. |
| `data/index.json` | Lista de temporadas disponibles. |
| `data/<aaaa-aa>.json` | Calendarios de una temporada (por ejemplo `2025-26.json`). |
| `index.html` | Página de ejemplo y comprobación en <https://futbol7-app.www.clubestoril2.es/>. |
| `.github/workflows/desplegar.yml` | Despliegue en GitHub Pages con cada push a la rama (sin Jekyll). |
| `.nojekyll` | Evita el procesado con Jekyll. |

### Formato de los JSON de temporada

```json
{
 "temporada_id": "2025-26",
 "temporada": "2025/26",
 "fuente": "https://www.mostoles.es/MostolesDeporte/es/campeonatos-municipales-deporte-infantil/futbol-7/calendario/calendario-serie-basica",
 "actualizado": "2026-11-08",
 "categorias": [
  {
   "id": "benjamin-f1-g2",
   "nombre": "Benjamín · 1ª fase · grupo 2",
   "categoria": "benjamin",
   "categoria_nombre": "Benjamín",
   "fase": "1ª fase",
   "grupo": 2,
   "competicion": "FÚTBOL 7/1ª FASE DE LIGA/BENJAMIN",
   "pdf": "https://www.mostoles.es/.../1402945-CALENDARIO ... ALEVÍN 25-26.pdf",
   "pdf_fecha": "2025-10-23",
   "jornadas": [
    {
     "numero": 1,
     "fecha": "2025-11-07",
     "partidos": [
      {"local": "CD MÓSTOLES CF", "visitante": "CD MÓSTOLES URJC", "fecha": "2025-11-07", "hora": "17:50", "campo": "Campo 2 zona A"},
      {"local": "CDE TECHNITEAM \"D\"", "descansa": true}
     ]
    }
   ]
  }
 ]
}
```

- Cada entrada de `categorias` es un calendario (un PDF): la categoría base
  (`categoria`) más, si los hay, la fase o vuelta (`fase`) y el grupo
  (`grupo`); `id` los combina (`benjamin-f1-g2`, `alevin-v2-g3`). Una
  temporada sin fases ni grupos tiene una entrada por categoría con
  `id` igual a `categoria`.
- La temporada se deduce de la fecha del primer partido (de julio a junio).
- `campo` se normaliza quitando el nombre del complejo deportivo (Iker Casillas)
  y las comillas: `IKER CASILLAS CAMPO 2 ZONA A` → `Campo 2 zona A`.
- Cuando el Ayuntamiento vuelve a publicar un PDF (cambios de fechas, equipos
  nuevos, etc.) la categoría se sustituye entera. `actualizado` solo cambia
  cuando cambian los datos.

## La aplicación en una página

Es lo que lleva la página [Escuela de fútbol 7](https://www.clubestoril2.es/escuelas-y-actividades/escuela-de-futbol-7/)
del club (contenido de la página, editor clásico):

```html
<link rel="stylesheet" href="https://clubestoril2.github.io/futbol-7/futbol7.css">
<div id="futbol7-app" data-nivel="2"></div>
<script src="https://clubestoril2.github.io/futbol-7/futbol7.js" defer></script>
```

Mientras no exista el DNS del dominio propio se usa la URL de `github.io`;
cuando se configure `futbol7-app.www.clubestoril2.es` bastará con cambiar
las dos URL (la antigua seguirá funcionando por redirección).

La aplicación genera dos bloques:

1. **Jornada actual**: la próxima jornada de cada categoría de la temporada
   en curso (la primera cuyos partidos aún no se han jugado, el día de la
   jornada incluido). No aparece si la temporada ha terminado.
2. **Buscador de encuentros**: los filtros y, debajo, **todos los calendarios
   de todas las categorías** de la temporada actual (o de la última
   publicada), de modo que los buscadores puedan indexar el contenido
   completo. Los filtros llevan la clase `ce-no-imprimir` del tema y no se
   imprimen.

Los filtros son:

- **Temporada**: obligatoria; la seleccionada aparece resaltada.
- **Categoría**: opcional; pulsar de nuevo la deselecciona.
- **Jornada**: opcional; cada botón muestra el número y la fecha en formato
  `10/nov` (si varía entre categorías, el intervalo `07/nov – 15/nov`).
  El botón **Ninguna** vacía el buscador y lo excluye de la impresión, para
  imprimir solo la jornada actual.

Combinando filtros se obtiene, por ejemplo, la jornada 1 de todas las
categorías de una temporada. El estado se refleja en la URL
(`#t=2025-26&c=alevin&j=3`, o `j=ninguna`) para poder enlazar una selección concreta. Cada
categoría tiene como ancla su identificador (`#prebenjamin`, `#benjamin`,
`#alevin`, `#infantil`) y cada jornada `#alevin-j3`.

Atributos opcionales del contenedor:

| Atributo | Uso |
| --- | --- |
| `data-base="https://…/"` | Raíz donde está la carpeta `data/`. Por defecto, la carpeta del script. |
| `data-temporada="2025-26"` | Temporada inicial. Por defecto, la actual o la última disponible. |
| `data-nivel="2"` | Nivel del primer encabezado que genera (`h2` «Jornada actual» y «Buscador de encuentros», `h3` temporada, `h4` categorías, `h5` jornadas). |
| `data-hoy="2026-01-24"` | Fecha que se toma como «hoy» para calcular la jornada actual. Solo para pruebas. |

Los equipos del club (`ESTORIL` en el nombre) se resaltan con la clase
`f7-estoril`.

## Actualización de los datos

El flujo `Actualizar datos` se ejecuta cada día (y a mano desde la pestaña
*Actions*):

1. Descarga la rama `master` (scripts) y la rama `futbol7-app` (datos).
2. Lee las páginas [Calendario](https://www.mostoles.es/MostolesDeporte/es/campeonatos-municipales-deporte-infantil/futbol-7/calendario)
   y [Calendario Serie Básica](https://www.mostoles.es/MostolesDeporte/es/campeonatos-municipales-deporte-infantil/futbol-7/calendario/calendario-serie-basica)
   del Ayuntamiento (ha usado una u otra según la temporada), descarga los
   PDF cuyo nombre contiene `CALENDARIO`, descarta los que no son de una
   categoría de la serie básica (ligas de adultos) y convierte el resto.
   Un PDF de una fase o grupo nuevos se añade a la temporada sin borrar
   los anteriores.
3. Si algún JSON cambia, hace commit en `futbol7-app` con el mensaje
   `AAAA-MM-DD actualizada temporada AAAA/AA` y lo sube.
4. Lanza el flujo `Desplegar en GitHub Pages` de la rama `futbol7-app`
   (los push hechos con el token de Actions no disparan otros flujos por sí
   solos, por eso se lanza explícitamente).

Los push manuales a `futbol7-app` (cambios en el JavaScript o la CSS) se
despliegan solos.

### Ejecución manual

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
git worktree add app futbol7-app
```

```bash
.venv/bin/python -I scripts/futbol7_datos.py actualizar --destino app/data
```

Para convertir PDF guardados de temporadas anteriores:

```bash
.venv/bin/python -I scripts/futbol7_datos.py pdf --destino app/data "CALENDARIO ... PREBENJAMIN.pdf"
```

Para probar la aplicación en local sirva la carpeta `app` con cualquier
servidor estático, por ejemplo:

```bash
python3 -m http.server 8765 --directory app
```

## Publicación en GitHub Pages

- Origen de Pages: *GitHub Actions* (flujo `desplegar.yml` de la rama `futbol7-app`).
- URL actual: <https://clubestoril2.github.io/futbol-7/>.
- Dominio personalizado previsto: `futbol7-app.www.clubestoril2.es`. Necesita en el
  DNS de `clubestoril2.es` un registro `CNAME futbol7-app.www → clubestoril2.github.io`
  y después fijarlo en Pages:
  `gh api -X PUT repos/clubestoril2/futbol-7/pages -f cname=futbol7-app.www.clubestoril2.es`.
- El entorno `github-pages` del repositorio debe permitir desplegar desde la
  rama `futbol7-app` (ya añadido en la política de ramas del entorno).
- GitHub Pages envía `Access-Control-Allow-Origin: *`, pero el subdominio
  propio evita además cualquier problema de CORS o de políticas de contenido
  en la web del club.

## Temporadas disponibles

| Temporada | Origen | Contenido |
| --- | --- | --- |
| 2019/20 | Archivo de Internet (capturas de 2020) | Prebenjamín e infantil completos; benjamín y alevín solo la 2ª vuelta (alevín en tres grupos). Competición interrumpida por la pandemia. |
| 2024/25 | PDF guardados en el repositorio original | 1ª fase de las cuatro categorías. La 2ª fase (benjamín por grupos) no se pudo recuperar: la única captura archivada es un error 404. |
| 2025/26 | Web municipal | Las cuatro categorías. |
| 2026/27 | Web municipal (página «Calendario») | 1ª fase; benjamín en tres grupos. Se completará solo cuando se publiquen las siguientes fases. |

No existen capturas de 2017/18 (solo de la página, no de los PDF), 2018/19
ni de 2020/21 a 2023/24. Si aparecen PDF de esas temporadas se incorporan
con el comando `pdf`.

## Historial

- 2024: scripts `analizar*.py` y `descargar_pdf.py` que generaban
  `calendario.html` para pegarlo a mano (véase el historial de git).
- 2026: extracción automática a JSON, rama `futbol7-app`, GitHub Actions y
  aplicación JavaScript con filtros.
