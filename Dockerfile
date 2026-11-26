# RetailLens image: runs the pipeline and/or the Streamlit dashboard (SYNTHETIC DATA)
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# install dependencies first so this layer is cached between code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY sql/ sql/
COPY app/ app/

EXPOSE 8530
# default: start the dashboard; docker-compose runs the pipeline as a one-off service first
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.port=8530", "--server.address=0.0.0.0", "--server.headless=true"]
