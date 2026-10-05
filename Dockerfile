# Airflow image with the project's Python dependencies installed,
# so every Airflow task can import the pipeline code in src/.
FROM apache/airflow:3.3.2-python3.12

COPY requirements.txt /tmp/requirements.txt

# Pinning apache-airflow stops pip from upgrading/downgrading Airflow
# while it installs the project dependencies.
RUN pip install --no-cache-dir "apache-airflow==3.3.2" -r /tmp/requirements.txt
