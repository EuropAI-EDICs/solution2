# Gebruik een Python-base image
FROM python:3.13-slim

# Werkdirectory instellen
WORKDIR /app

# Kopieer requirements.txt en installeer dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopieer de rest van de applicatie
COPY . .

# Streamlit-app starten
CMD ["streamlit", "run", "elastic_demo.py", "--server.port=8501", "--server.address=0.0.0.0"]