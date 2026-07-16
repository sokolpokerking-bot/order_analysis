"""Класс для пакетной обработки CSV-файлов с заказами."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

import pandas as pd
from pandas.errors import EmptyDataError, ParserError


PathLike = Union[str, Path]


class OrderAnalyzer:
    """Читает файлы с заказами, рассчитывает метрики и сохраняет общий отчёт."""

    def __init__(
        self,
        data_dir: PathLike,
        reports_dir: PathLike,
        logs_dir: PathLike,
        output_filename: str,
        log_filename: str,
        status_column: str,
        target_status: str,
        amount_column: str,
        required_columns: Sequence[str],
        report_columns: Sequence[str],
    ) -> None:
        self.data_dir = Path(data_dir)
        self.reports_dir = Path(reports_dir)
        self.logs_dir = Path(logs_dir)
        self.output_filename = output_filename
        self.log_filename = log_filename
        self.status_column = status_column
        self.target_status = target_status
        self.amount_column = amount_column
        self.required_columns = tuple(required_columns)
        self.report_columns = tuple(report_columns)

        self.results: List[Dict[str, object]] = []
        self.processed_files = 0
        self.error_files = 0

        self._create_directories()
        self.logger = self._create_logger()

    def _create_directories(self) -> None:
        """Создаёт рабочие папки, если они ещё не существуют."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _create_logger(self) -> logging.Logger:
        """Настраивает запись ошибок текущего запуска в файл."""
        logger = logging.getLogger("order_analysis")
        logger.setLevel(logging.ERROR)
        logger.propagate = False

        # Удаляем старые обработчики, чтобы сообщения не дублировались при повторном запуске.
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

        log_path = self.logs_dir / self.log_filename
        file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(file_handler)
        return logger

    def _register_error(self, file_path: Path, stage: str, error: Exception) -> None:
        """Учитывает ошибочный файл и записывает причину в лог."""
        self.error_files += 1
        self.logger.error(
            "Файл '%s'. Этап: %s. %s: %s",
            file_path.name,
            stage,
            type(error).__name__,
            str(error),
        )

    def _validate_columns(self, data: pd.DataFrame) -> None:
        """Проверяет наличие всех колонок из структуры входных данных."""
        missing_columns = [
            column for column in self.required_columns if column not in data.columns
        ]
        if missing_columns:
            missing_text = ", ".join(missing_columns)
            raise ValueError(f"отсутствуют обязательные колонки: {missing_text}")

    def _prepare_amount_column(self, data: pd.DataFrame) -> pd.DataFrame:
        """Проверяет сумму заказа и приводит колонку к числовому типу."""
        if data[self.amount_column].isna().any():
            raise ValueError(
                f"в колонке '{self.amount_column}' есть пустые значения"
            )

        prepared_data = data.copy()
        try:
            prepared_data[self.amount_column] = pd.to_numeric(
                prepared_data[self.amount_column], errors="raise"
            )
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"колонка '{self.amount_column}' содержит нечисловые значения"
            ) from error

        return prepared_data

    def load_file(self, file_path: PathLike) -> Optional[pd.DataFrame]:
        """Загружает и проверяет один CSV-файл; при ошибке возвращает None."""
        path = Path(file_path)

        try:
            data = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)

            if data.empty:
                raise ValueError("файл не содержит записей")

            self._validate_columns(data)
            return self._prepare_amount_column(data)

        except (EmptyDataError, ParserError, UnicodeDecodeError, OSError, ValueError) as error:
            self._register_error(path, "загрузка и проверка данных", error)
            return None

    def filter_delivered_orders(self, data: pd.DataFrame) -> pd.DataFrame:
        """Оставляет только заказы с заданным статусом доставки."""
        return data.loc[
            data[self.status_column] == self.target_status
        ].copy()

    def calculate_metrics(self, delivered_orders: pd.DataFrame) -> Dict[str, object]:
        """Рассчитывает выручку, средний чек и количество доставленных заказов."""
        order_count = int(len(delivered_orders))

        if order_count == 0:
            return {
                "total_revenue": 0.0,
                "average_order_value": 0.0,
                "order_count": 0,
            }

        total_revenue = float(delivered_orders[self.amount_column].sum())
        average_order_value = float(delivered_orders[self.amount_column].mean())

        return {
            "total_revenue": round(total_revenue, 2),
            "average_order_value": round(average_order_value, 2),
            "order_count": order_count,
        }

    def process_file(self, file_path: PathLike) -> Optional[Dict[str, object]]:
        """Последовательно загружает, фильтрует и анализирует один файл."""
        path = Path(file_path)
        data = self.load_file(path)

        if data is None:
            return None

        try:
            delivered_orders = self.filter_delivered_orders(data)
            metrics = self.calculate_metrics(delivered_orders)
        except (KeyError, TypeError, ValueError) as error:
            self._register_error(path, "фильтрация и расчёт метрик", error)
            return None

        self.processed_files += 1
        return {"file_name": path.name, **metrics}

    def _save_report(self) -> Path:
        """Сохраняет результаты всех успешно обработанных файлов в один CSV."""
        report_path = self.reports_dir / self.output_filename
        report = pd.DataFrame(self.results, columns=self.report_columns)

        try:
            report.to_csv(report_path, index=False, encoding="utf-8-sig")
        except OSError as error:
            self.logger.error(
                "Не удалось сохранить отчёт '%s'. %s: %s",
                report_path,
                type(error).__name__,
                str(error),
            )
            raise RuntimeError(f"не удалось сохранить отчёт: {report_path}") from error

        return report_path

    def process_all_files(self) -> Tuple[int, int, Path]:
        """Обрабатывает все CSV-файлы из data и формирует итоговый отчёт."""
        self.results.clear()
        self.processed_files = 0
        self.error_files = 0

        csv_files = sorted(
            path for path in self.data_dir.glob("*.csv") if path.is_file()
        )

        for file_path in csv_files:
            result = self.process_file(file_path)
            if result is not None:
                self.results.append(result)

        report_path = self._save_report()
        return self.processed_files, self.error_files, report_path
