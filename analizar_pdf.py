import fitz  # PyMuPDF

# Open the PDF file
pdf_document = "CALENDARIO CAMPEONATO DE LIGA FÚTBOL 7 PREBENJAMIN.pdf"
pdf = fitz.open(pdf_document)

# Extract text from each page
text = ""
for page_num in range(len(pdf)):
    page = pdf.load_page(page_num)
    text += page.get_text()

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
            parts = line.split(" ")
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

