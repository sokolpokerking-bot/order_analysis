"""Точка запуска пакетного анализа заказов."""

import config
from src.analyzer import OrderAnalyzer


def main() -> None:
    """Запускает обработку файлов и выводит итоговую статистику."""
    analyzer = OrderAnalyzer(
        data_dir=config.DATA_DIR,
        reports_dir=config.REPORTS_DIR,
        logs_dir=config.LOGS_DIR,
        output_filename=config.OUTPUT_FILENAME,
        log_filename=config.LOG_FILENAME,
        status_column=config.STATUS_COLUMN,
        target_status=config.TARGET_STATUS,
        amount_column=config.AMOUNT_COLUMN,
        required_columns=config.REQUIRED_COLUMNS,
        report_columns=config.REPORT_COLUMNS,
    )

    processed_files, error_files, report_path = analyzer.process_all_files()

    print(f"Обработано файлов: {processed_files}")
    print(f"Файлов с ошибками: {error_files}")
    print(f"Итоговый отчёт: {report_path}")


if __name__ == "__main__":
    main()
