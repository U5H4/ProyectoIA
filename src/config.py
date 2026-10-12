"""Configuracion central del proyecto.

Sistema Inteligente de Analisis, Prediccion y Trazabilidad de Incidentes
de Ciberseguridad (Tema 3).

Define rutas, fuentes de datos, semilla y todos los parametros del ETL para
que el pipeline sea reproducible.
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------
# Rutas
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent

DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
REPORTS = DATA / "reports"
FIGURES = DATA / "figures"
BLOCKCHAIN = DATA / "blockchain"
MODELS = ROOT / "models"
LOGS = ROOT / "logs"

CICIDS_DIR = RAW / "cicids2017"
CTI_DIR = RAW / "cti_reports"

ALL_DIRS = [
    RAW,
    PROCESSED,
    REPORTS,
    FIGURES,
    BLOCKCHAIN,
    MODELS,
    LOGS,
    CICIDS_DIR,
    CTI_DIR,
]

# --------------------------------------------------------------------------
# Reproducibilidad
# --------------------------------------------------------------------------
SEED = 20261007

# --------------------------------------------------------------------------
# Fuente 1: CICIDS2017 (flujos de red etiquetados) para Machine Learning.
# Mirror publico en HuggingFace (los CSV originales del CIC-UNB).
# --------------------------------------------------------------------------
CICIDS_HF_REPO = "bvsam/cic-ids-2017"
CICIDS_HF_BASE = (
    f"https://huggingface.co/datasets/{CICIDS_HF_REPO}/resolve/main/machine_learning"
)
CICIDS_LICENSE_URL = "https://www.unb.ca/cic/datasets/ids-2017.html"
CICIDS_CITATION = (
    "Sharafaldin, I., Habibi Lashkari, A., & Ghorbani, A. A. (2018). "
    "Toward Generating a New Intrusion Detection Dataset and Intrusion "
    "Traffic Characterization. ICISSP 2018."
)

# Los 8 dias de captura, cada uno en su parquet (MachineLearningCVE convertido).
CICIDS_FILES = [
    "Monday-WorkingHours.pcap_ISCX.csv.parquet",
    "Tuesday-WorkingHours.pcap_ISCX.csv.parquet",
    "Wednesday-workingHours.pcap_ISCX.csv.parquet",
    "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv.parquet",
    "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv.parquet",
    "Friday-WorkingHours-Morning.pcap_ISCX.csv.parquet",
    "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv.parquet",
    "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv.parquet",
]

# --------------------------------------------------------------------------
# Fuente 2: reportes de ciber-threat-intelligence (textos) para PNL.
# --------------------------------------------------------------------------
CTI_REPORTS_URL = (
    "https://huggingface.co/datasets/guychuk/cyber-threat-intelligence-reports/"
    "resolve/main/data/train-00000-of-00001.parquet"
)
CTI_MIN_TEXT_LEN = 50
CTI_MAX_CHARS = 20_000

# --------------------------------------------------------------------------
# Variable objetivo y agrupacion de etiquetas de CICIDS2017.
# Reduce el numero de clases agrupando variantes del mismo tipo de ataque.
# --------------------------------------------------------------------------
RAW_LABEL_COLUMN = "Label"
TARGET_COLUMN = "label"

LABEL_GROUPS = {
    "BENIGN": "BENIGN",
    "DoS Hulk": "DoS",
    "DoS GoldenEye": "DoS",
    "DoS slowloris": "DoS",
    "DoS Slowhttptest": "DoS",
    "DDoS": "DDoS",
    "PortScan": "PortScan",
    "FTP-Patator": "BruteForce",
    "SSH-Patator": "BruteForce",
    "Bot": "Bot",
    "Web Attack - Brute Force": "WebAttack",
    "Web Attack - XSS": "WebAttack",
    "Web Attack - Sql Injection": "WebAttack",
    "Infiltration": "Infiltration",
    "Heartbleed": "Heartbleed",
}

# --------------------------------------------------------------------------
# Parametros del ETL
# --------------------------------------------------------------------------
CHUNK_SIZE = 200_000
DEFAULT_SAMPLE_SIZE = 40_000
DEFAULT_MAX_PER_CLASS = 6_000
DEFAULT_PER_FILE_CLASS_CAP = 2_000
TEST_SIZE = 0.30

# Tratamiento de valores atipicos (winsorizacion por rango intercuartilico).
IQR_FACTOR = 3.0

# Minimos del enunciado (referencia: al menos 5,000 registros).
MIN_REGISTROS_FLUJOS = 5_000
MIN_REGISTROS_REPORTES = 300

# --------------------------------------------------------------------------
# Machine Learning (Entregable 3)
# --------------------------------------------------------------------------
# Columnas que NO son variables predictoras (etiqueta cruda, agrupada y original).
COLUMNAS_NO_FEATURE = [TARGET_COLUMN, "label_raw", RAW_LABEL_COLUMN]

# Validacion cruzada estratificada sobre el conjunto de entrenamiento.
CV_FOLDS = 5

# --------------------------------------------------------------------------
# PNL (Entregable 4)
# --------------------------------------------------------------------------
# Numero de terminos mas relevantes (TF-IDF) que se reportan.
PNL_TOP_TERMINOS = 25
# Oraciones del resumen extractivo por documento.
PNL_RESUMEN_ORACIONES = 2
# Longitud maxima de texto analizada (caracteres) para sentimiento.
PNL_MAX_CHARS_SENTIMIENTO = 4_000

# --------------------------------------------------------------------------
# Blockchain (Entregable 5)
# --------------------------------------------------------------------------
BLOCKCHAIN_JSON = BLOCKCHAIN / "cadena.json"
