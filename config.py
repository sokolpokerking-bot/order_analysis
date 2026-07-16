"""Настройки проекта пакетного анализа заказов."""

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"

OUTPUT_FILENAME = "summary_report.csv"
LOG_FILENAME = "errors.log"

STATUS_COLUMN = "status"
TARGET_STATUS = "Delivered"
AMOUNT_COLUMN = "total_amount"

REQUIRED_COLUMNS = (
    "order_id",
    "person_id",
    "order_date",
    "status",
    "total_amount",
    "currency",
    "payment_method",
    "shipping_method",
    "notes",
)

REPORT_COLUMNS = (
    "file_name",
    "total_revenue",
    "average_order_value",
    "order_count",
)
