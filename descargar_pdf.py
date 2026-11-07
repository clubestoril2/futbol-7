import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin, unquote


# URL de la página que deseas obtener
url = 'https://www.mostoles.es/MostolesDeporte/es/campeonatos-municipales-deporte-infantil/futbol-7/clasificaciones-resultados/clasificaciones-resultados-serie-basica'
url = 'https://www.mostoles.es/MostolesDeporte/es/campeonatos-municipales-deporte-infantil/futbol-7/calendario/calendario-serie-basica'

# Realizar la solicitud HTTPS
response = requests.get(url)
response.raise_for_status()  # Verificar que la solicitud fue exitosa

# Parsear el contenido HTML
soup = BeautifulSoup(response.content, 'html.parser')

# Encontrar todos los elementos <li> con la clase específica
a_elements = soup.find_all('a', class_='cmResourceLink')

# Crear una carpeta para almacenar los PDFs si no existe
if not os.path.exists('pdfs'):
    os.makedirs('pdfs')

# Encabezado con agente de usuario personalizado
headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
}

# Descargar cada PDF
for a_tag in a_elements:
    pdf_url = urljoin(url, a_tag['href'])
    print(pdf_url)
    pdf_name = unquote(os.path.basename(pdf_url))
    pdf_path = os.path.join('pdfs', pdf_name)
        
    pdf_response = requests.get(pdf_url, headers=headers)
    pdf_response.raise_for_status()  # Verificar que la solicitud fue exitosa

    with open(pdf_path, 'wb') as pdf_file:
        pdf_file.write(pdf_response.content)
        print(f'Descargado: {pdf_name}')

print('Descarga completa.')

