## src/models.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class BuildingElement(BaseModel):
    id: str
    type: str  # "Project", "Site", "Building", "Floor", "Room", "Door", "Window"
    name: str
    parent_id: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    connects: Optional[List[str]] = None  # For doors connecting rooms