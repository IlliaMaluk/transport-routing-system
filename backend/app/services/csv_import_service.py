from __future__ import annotations

import csv
from io import TextIOWrapper
from typing import List, Tuple, Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.db_models import EdgeMetadata
from app.services.graph_manager import GraphManager


class CsvImportSummary:
    """
    Результат імпорту CSV у граф.
    """

    def __init__(
        self,
        edges_imported: int,
        skipped_rows: int,
        errors: List[str],
        sample_rows: int,
    ) -> None:
        self.edges_imported = edges_imported
        self.skipped_rows = skipped_rows
        self.errors = errors
        self.sample_rows = sample_rows


def _parse_float(value: str) -> Optional[float]:
    value = value.strip()
    if not value:
        return None
    return float(value)


def _parse_bool(value: str, default: bool = True) -> bool:
    if value is None:
        return default
    v = value.strip().lower()
    if v in ("0", "false", "no", "n"):
        return False
    if v in ("1", "true", "yes", "y"):
        return True
    return default


def import_edges_from_csv(
    manager: GraphManager,
    file: UploadFile,
    db: Session,
) -> CsvImportSummary:
    """
    Читає CSV-файл з ребрами та додає їх у GraphManager + EdgeMetadata.

    Формат CSV (заголовок + дані):

      обов'язкові стовпці:
        - from_node / from
        - to_node / to
        - weight

      опціональні стовпці:
        - edge_type / type
        - distance / dist
        - time / travel_time
        - cost
        - capacity
        - is_one_way / one_way
    """
    file.file.seek(0)

    text_stream = TextIOWrapper(file.file, encoding="utf-8")
    reader = csv.DictReader(text_stream)

    if not reader.fieldnames:
        return CsvImportSummary(
            edges_imported=0,
            skipped_rows=0,
            errors=["CSV-файл не містить заголовка (fieldnames)."],
            sample_rows=0,
        )

    fieldnames = [name.strip() for name in reader.fieldnames]

    from_col = None
    to_col = None
    weight_col = None

    if "from_node" in fieldnames:
        from_col = "from_node"
    elif "from" in fieldnames:
        from_col = "from"

    if "to_node" in fieldnames:
        to_col = "to_node"
    elif "to" in fieldnames:
        to_col = "to"

    if "weight" in fieldnames:
        weight_col = "weight"

    errors: List[str] = []
    if from_col is None or to_col is None or weight_col is None:
        missing = []
        if from_col is None:
            missing.append("from_node або from")
        if to_col is None:
            missing.append("to_node або to")
        if weight_col is None:
            missing.append("weight")
        errors.append(
            "В CSV-файлі відсутні необхідні стовпці: " + ", ".join(missing)
        )
        return CsvImportSummary(
            edges_imported=0,
            skipped_rows=0,
            errors=errors,
            sample_rows=0,
        )

    def col(*names: str) -> Optional[str]:
        for n in names:
            if n in fieldnames:
                return n
        return None

    edge_type_col = col("edge_type", "type")
    distance_col = col("distance", "dist")
    time_col = col("time", "travel_time")
    cost_col = col("cost",)
    capacity_col = col("capacity",)
    is_one_way_col = col("is_one_way", "one_way")

    edges: List[Tuple[int, int, float]] = []
    edges_imported = 0
    skipped_rows = 0
    sample_rows = 0
    metadata_records: List[EdgeMetadata] = []

    for row_index, row in enumerate(reader, start=2):
        sample_rows += 1
        try:
            raw_from = row.get(from_col, "").strip()
            raw_to = row.get(to_col, "").strip()
            raw_weight = row.get(weight_col, "").strip()

            if raw_from == "" or raw_to == "" or raw_weight == "":
                raise ValueError("порожнє значення одного з обов'язкових полів")

            from_node = int(raw_from)
            to_node = int(raw_to)
            weight = float(raw_weight)

            edges.append((from_node, to_node, weight))
            edges_imported += 1

            edge_type = (
                row.get(edge_type_col).strip()
                if edge_type_col and row.get(edge_type_col) is not None
                else None
            )

            distance = (
                _parse_float(row.get(distance_col, ""))
                if distance_col
                else None
            )
            travel_time = (
                _parse_float(row.get(time_col, ""))
                if time_col
                else None
            )
            cost_val = (
                _parse_float(row.get(cost_col, ""))
                if cost_col
                else None
            )
            capacity = (
                _parse_float(row.get(capacity_col, ""))
                if capacity_col
                else None
            )

            is_one_way = True
            if is_one_way_col:
                is_one_way = _parse_bool(row.get(is_one_way_col, ""), True)

            metadata = EdgeMetadata(
                from_node=from_node,
                to_node=to_node,
                edge_type=edge_type,
                distance=distance,
                travel_time=travel_time,
                cost=cost_val,
                capacity=capacity,
                is_one_way=is_one_way,
            )
            metadata_records.append(metadata)

        except Exception as exc:  # noqa: BLE001
            skipped_rows += 1
            errors.append(f"Рядок {row_index}: {exc}")

    if edges:
        manager.add_edges(edges)

    if metadata_records:
        db.add_all(metadata_records)
        db.commit()

    return CsvImportSummary(
        edges_imported=edges_imported,
        skipped_rows=skipped_rows,
        errors=errors,
        sample_rows=sample_rows,
    )
