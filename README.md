# BIM Graph Explorer - Quick Setup

## 1. Requirements
- Python 3.12.7
- Docker 28.2.2
### 1.1 Tạo virtual environment
``` bash
python -m venv venv
```
### 1.2 Kích hoạt venv

- Windows
```bash
venv\Scripts\activate
```

- Linux/macOS
```bash
source venv/bin/activate
```
### 1.3 Cài đặt dependencies
```bash
pip install -r requirements.txt
```
## 2. Start ArangoDB
Chạy ArangoDB bằng Docker:
```bash
docker-compose up -d
```
- Web UI: [http://localhost:8529](http://localhost:8529)  
- Username: `root`  
- Password: `password`  

Database `bim_graph_db` sẽ được tạo tự động khi chạy demo.

## 3. Chuẩn bị Data
Dữ liệu JSON có sẵn tại:

```
data/building_data.json
```

## 4. Chạy Demo

Chạy script demo:

```bash
python -m examples.demo
```

Demo sẽ thực hiện:
- Query 1: Lấy tất cả các phòng họp (Meeting Rooms) trong tòa nhà.
- Query 2: Thống kê số lượng các loại phần tử (tầng, phòng, cửa, cửa sổ) và tổng diện tích của một tòa nhà.
- Query 3: Tìm đường đi từ sảnh chính (Main Lobby) đến phòng họp (Board Room).
- Query 4: Lấy danh sách các phòng kết nối với sảnh chính thông qua các cửa.
- Query 5: Lấy tổng số phòng trong tòa nhà.
- Query 6: Lấy chi tiết thông tin của một cửa cụ thể (dr_001).
- Query 7: Lấy các phần tử con trực tiếp của một tòa nhà.
- Query 8: Lấy tất cả các phần tử con (descendants) của một tầng và thống kê theo loại phần tử.
- Query 9: Lấy tất cả các phần tử cha (ancestors) của một phòng cụ thể.
- Query 10: Lấy các phòng kết nối với một phòng cụ thể thông qua các cửa.
- Query 11: Lấy tất cả các cửa và cửa sổ của một phòng.
- Query 12: Tìm đường đi giữa hai phòng cụ thể.
- Query 13: Thống kê số lượng phần tử và tổng diện tích của một tòa nhà khác.
- Query 14: Báo cáo sức chứa phòng theo loại phòng trong một tòa nhà.
- Query 15: Thống kê metadata của toàn bộ graph, bao gồm tổng số phần tử, số lượng theo loại, và số lượng quan hệ.

## 5. Cấu trúc thư mục
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