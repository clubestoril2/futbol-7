import fitz  # PyMuPDF
import re

# Open the PDF file
pdf_document = "CALENDARIO CAMPEONATO DE LIGA FÚTBOL 7 PREBENJAMIN.pdf"
pdf_document = 'pdfs/1315433-CALENDARIO CAMPEONATO DE LIGA FÚTBOL 7 PREBENJAMIN.pdf'
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
data = {}

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
            data[key] = value
            i += 1  # Saltar la siguiente línea ya que está combinada
    i += 1

# Imprimir los datos estructurados
print(data)


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

exit(0)



# Split the text by "JORNADA" to separate each matchday
jornadas = text.split("JORNADA")[1:]

# Initialize HTML content
html_content = "<html><body>"



# Process each jornada
for jornada in jornadas:
    lines = jornada.strip().split("\n")
    jornada_num = lines[0].strip()
    date = lines[1].split()[-3]  # Extract the date from the first match line
    html_content += f"<h2>Jornada {jornada_num} ({date})</h2>"
    html_content += "<table border='1'><tr><th>Partido</th><th>Hora</th><th>Ubicación</th></tr>"
    
    for line in lines[1:]:
        if line.strip():
            parts = line.split()
            if len(parts) >= 3:
                match = " ".join(parts[:-3])
                time = parts[-2]
                location = parts[-1]
                html_content += f"<tr><td>{match}</td><td>{time}</td><td>{location}</td></tr>"
    
    html_content += "</table>"

html_content += "</body></html>"

# Save the HTML content to a file
with open("calendario.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("HTML file 'calendario.html' has been created.")

