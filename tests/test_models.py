## tests/test_models.py
import pytest
from pydantic import ValidationError
from src.models import BuildingElement


def test_building_element_valid_creation():
    """
    Test tạo BuildingElement hợp lệ với đầy đủ field bắt buộc
    """
    element = BuildingElement(
        id="bld_001",
        type="Building",
        name="Main Office Tower",
        parent_id="site_001",
        properties={
            "year_built": 2020,
            "total_floors": 4
        }
    )

    assert element.id == "bld_001"
    assert element.type == "Building"
    assert element.name == "Main Office Tower"
    assert element.parent_id == "site_001"
    assert element.properties["year_built"] == 2020


def test_building_element_optional_fields_none():
    """
    Test các field optional có thể để None
    """
    element = BuildingElement(
        id="prj_001",
        type="Project",
        name="VBIS Office Complex"
    )

    assert element.parent_id is None
    assert element.connects is None
    assert isinstance(element.properties, dict)


def test_building_element_missing_required_field():
    """
    Test thiếu field bắt buộc (name) phải raise ValidationError
    """
    with pytest.raises(ValidationError):
        BuildingElement(
            id="rm_001",
            type="Room"
        )


def test_building_element_connects_field_for_door():
    """
    Test field connects cho Door (kết nối giữa các room)
    """
    door = BuildingElement(
        id="dr_001",
        type="Door",
        name="Main Entrance",
        parent_id="rm_001",
        connects=["rm_001", "outside"],
        properties={
            "door_type": "Revolving",
            "width_mm": 2400
        }
    )

    assert door.type == "Door"
    assert door.connects == ["rm_001", "outside"]


def test_building_element_properties_default_is_dict():
    """
    Test properties mặc định là dict rỗng
    """
    element = BuildingElement(
        id="flr_001",
        type="Floor",
        name="Ground Floor"
    )

    assert element.properties == {}
    assert isinstance(element.properties, dict)
