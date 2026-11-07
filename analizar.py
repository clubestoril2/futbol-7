import fitz  # PyMuPDF
import re

# Open the PDF file
#pdf_document = "CALENDARIO CAMPEONATO DE LIGA FÚTBOL 7 PREBENJAMIN.pdf"
#pdf_document = 'pdfs/1315433-CALENDARIO CAMPEONATO DE LIGA FÚTBOL 7 PREBENJAMIN.pdf'
#pdf_document = 'pdfs/1315434-CALENDARIO CAMPEONATO DE LIGA FÚTBOL 7 BENJAMIN.pdf'
#pdf_document = 'pdfs/1315435-CALENDARIO CAMPEONATO DE LIGA FÚTBOL 7 ALEVIN.pdf'
pdf_document = 'pdfs/1315436-CALENDARIO CAMPEONATO DE LIGA FÚTBOL 7 INFANTIL.pdf'
pdf = fitz.open(pdf_document)

# Extract text from each page
text = ""
for page_num in range(len(pdf)):
    page = pdf.load_page(page_num)
    text += page.get_text()

#print(text);

# Dividir el texto en líneas
lines = text.strip().split('\n')

# Inicializar el diccionario para los datos estructurados
evento = {}

# Procesar las líneas
i = 0
while i < len(lines):
    line = lines[i].strip()
    if line.startswith("JORNADA"):
        break
    if line.endswith(':'):
        key = line[:-1]  # Eliminar el ':'
        if i + 1 < len(lines):
            value = lines[i + 1].strip()
            evento[key] = value
            i += 1  # Saltar la siguiente línea ya que está combinada
    i += 1

# Imprimir los datos estructurados
print(evento)


# Expresión regular para líneas que comienzan con "JORNADA" o con un número seguido de equipos y fecha
pattern = re.compile(r'^(JORNADA \d+|\d+\s+\w.* - [\w*])')

# Filtrar las líneas que coinciden con la expresión regular
filtered_lines = [line for line in lines if pattern.match(line)]

# Unir las líneas filtradas en un solo texto
filtered_text = '\n'.join(filtered_lines)

print(filtered_text)



# Diccionario para almacenar la información estructurada
data = {}
current_jornada = None

# Expresión regular para líneas que contienen información de los partidos
match_pattern = re.compile(r'^\d+\s+(.*?)\s+-\s+(.*?)\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})\s+(.*)$')
descanso_pattern = re.compile(r'^\d+\s+(.*?)\s+-\s+\*\* DESCANSA \*\*$')

# Procesar las líneas
for line in lines:
    line = line.strip()
    if line.startswith("JORNADA"):
        current_jornada = line
        data[current_jornada] = []
    elif current_jornada:
        match = match_pattern.match(line)
        descanso = descanso_pattern.match(line)
        if match:
            equipo1, equipo2, fecha, campo = match.groups()
            data[current_jornada].append({
                "A": equipo1.strip(),
                "B": equipo2.strip(),
                "fecha": fecha,
                "campo": campo
            })
        elif descanso:
            equipo1 = descanso.groups()[0]
            data[current_jornada].append({
                "A": equipo1.strip(),
                "B": "** DESCANSA **",
                "fecha": None,
                "campo": None
            })

# Imprimir los datos estructurados
import json
print(json.dumps(data, indent=4, ensure_ascii=False))

import html

campo_pattern = r'\b(?:IKER|IKER CASILLAS)\b\s*'
# Función para generar la tabla HTML escapando caracteres potencialmente dañinos
def generate_html_table(data):
    html_output = ""
    for jornada, matches in data.items():
        html_output += f"<h3>{html.escape(jornada)} ({html.escape(evento['Categoría'].lower().replace('min', 'mín'))})</h3>\n"
        html_output += "<table>\n"
        html_output += "<tr><th>Equipo</th><th>Equipo</th><th>Fecha y Hora</th><th>Campo</th></tr>\n"
        for match in matches:
            class_a = ' class="estoril"' if "ESTORIL" in match["A"].upper() else ""
            class_b = ' class="estoril"' if "ESTORIL" in match["B"].upper() else ""
            equipo_a = html.escape(match["A"])
            equipo_b = html.escape(match["B"])
            fecha = html.escape(match["fecha"]) if match["fecha"] else "&nbsp;"
            campo = html.escape(re.sub(campo_pattern, "", match["campo"], flags=re.IGNORECASE)) if match["campo"] else "&nbsp;"
            html_output += f"<tr><td{class_a}>{equipo_a}</td><td{class_b}>{equipo_b}</td><td>{fecha}</td><td>{campo}</td></tr>\n"
        html_output += '</table>'
    return html_output

html = generate_html_table(data)
print(html)

