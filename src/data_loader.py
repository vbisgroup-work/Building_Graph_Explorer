## src/data_loader.py
import json
from typing import List, Any, Set
from .models import BuildingElement


# IDs được phép tham chiếu nhưng không cần tồn tại trong dữ liệu
ALLOWED_EXTERNAL_IDS: Set[str] = {"outside", "corridor"}


def load_and_parse_data(file_path: str) -> List[BuildingElement]:
    """
    Load BIM JSON data, parse into BuildingElement models,
    and validate basic data integrity.
    """
    # --------------------------------------------------
    # 1. Load JSON file
    # --------------------------------------------------
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    elements: List[BuildingElement] = []

    # --------------------------------------------------
    # 2. Helper: normalize single object or list
    # --------------------------------------------------
    def process_items(items: Any, default_type: str | None = None) -> None:
        """
        Convert raw JSON items into BuildingElement instances.
        Accepts a dict or a list of dicts.
        """
        if not items:
            return

        if isinstance(items, dict):
            items = [items]

        for item in items:
            # Ensure "type" field exists
            if "type" not in item and default_type:
                item["type"] = default_type

            elements.append(BuildingElement(**item))

    # --------------------------------------------------
    # 3. Parse all top-level BIM entities
    # --------------------------------------------------
    process_items(data.get("project"), "Project")
    process_items(data.get("site"), "Site")
    process_items(data.get("buildings"), "Building")
    process_items(data.get("floors"), "Floor")
    process_items(data.get("rooms"), "Room")
    process_items(data.get("doors"), "Door")
    process_items(data.get("windows"), "Window")


    # --------------------------------------------------
    # 4. Validate data integrity
    # --------------------------------------------------
    all_ids = {e.id for e in elements}

    # 4.1 Validate unique IDs
    if len(all_ids) != len(elements):
        raise ValueError("Duplicate element IDs detected in input data.")

    # 4.2 Validate parent references
    for element in elements:
        if element.parent_id:
            if (
                element.parent_id not in all_ids
                and element.parent_id not in ALLOWED_EXTERNAL_IDS
            ):
                raise ValueError(
                    f"Invalid parent_id '{element.parent_id}' "
                    f"for element '{element.id}'."
                )

    # 4.3 Validate door connections (if applicable)
    for element in elements:
        if element.type == "Door" and element.connects:
            for target_id in element.connects:
                if (
                    target_id not in all_ids
                    and target_id not in ALLOWED_EXTERNAL_IDS
                ):
                    raise ValueError(
                        f"Door '{element.id}' connects to "
                        f"non-existent element '{target_id}'."
                    )

    return elements
