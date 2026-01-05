# BIM Graph Explorer - Quick Setup

## 1. Requirements
- Python 3.12.7
- Docker 28.2.2
### 1.1 Create virtual environment
``` bash
python -m venv venv
```
### 1.2 Activate venv

- Windows
```bash
venv\Scripts\activate
```

- Linux/macOS
```bash
source venv/bin/activate
```
### 1.3 Install dependencies
```bash
pip install -r requirements.txt
```
## 2. Start ArangoDB
Run ArangoDB by Docker:
```bash
docker-compose up -d
```
- Web UI: [http://localhost:8529](http://localhost:8529)  

Database `bim_graph_db` will create when you run demo.

## 3. Prepare Data
```
data/building_data.json
```

## 4. Run Demo

Run script to demo:

```bash
python -m examples.demo
```

Demo will perform:
- Query 1: Get all meeting rooms (Meeting Rooms) in the building.
- Query 2: Statistics on the number of element types (floors, rooms, doors, windows) and total area of ​​a building.
- Query 3: Find the way from the main lobby (Main Lobby) to the meeting room (Board Room).
- Query 4: Get a list of rooms connected to the main lobby through doors.
- Query 5: Get the total number of rooms in the building.
- Query 6: Get detailed information of a specific door (dr_001).
- Query 7: Get direct child elements of a building.
- Query 8: Get all child elements (descendants) of a layer and statistics by element type.
- Query 9: Get all parent elements (ancestors) of a specific room.
- Query 10: Get rooms connected to a specific room through doors.
- Query 11: Get all doors and windows of a room.
- Query 12: Find the way between two specific rooms.
- Query 13: Statistics on the number of elements and total area of ​​another building.
- Query 14: Report room occupancy by room type in a building.
- Query 15: Metadata statistics of the entire graph, including total number of elements, number by type, and number of relationships.

## 5. Folder structure
```
building-graph-explorer/
├── README.md                   # Setup and usage instructions
├── requirements.txt            # Python dependencies
├── docker-compose.yaml         # ArangoDB container setup
├── brief_report.docx           # Design decisions
├── src/
│   ├── __init__.py
│   ├── models.py               # Pydantic models
│   ├── data_loader.py          # JSON loading and validation
│   ├── graph_service.py        # ArangoDB operations
│   └── queries.py              # Graph traversal functions
├── tests/
│   ├── __init__.py
│   ├── test_models.py          # Model validation tests
│   ├── test_graph_service.py   # Database operation tests
│   └── test_queries.py         # Query function tests
├── data/
│   └── building_data.json      # Mock data file
└── examples/
    └── demo.py                 # Usage demonstration
```