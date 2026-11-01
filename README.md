# Emergency Evacuation Route Analyzer

An educational and interactive planning tool for floor plan graph conversion, evacuation route analysis, and corridor hazard modeling using graph algorithms (**BFS**, **DFS**, and **Dijkstra / A\***).

> ⚠️ **Educational & Planning Disclaimer**  
> This system is designed strictly for educational, research, and scenario-planning demonstrations. It is **not** a certified life-safety system and does not replace official architectural fire-code analysis, certified building evacuation plans, or local emergency authority directives.

---

## Architecture Overview

- **Backend:** Python 3.11, FastAPI, OpenCV, NumPy, SciPy, scikit-image, Pillow, PyMuPDF.
  - Hand-written graph algorithms: Breadth-First Search (BFS), Depth-First Search (DFS, single-path and capped all-paths enumeration), Dijkstra's shortest path, and A* with admissible Euclidean heuristic.
  - Dual graph builders: Grid Occupancy Graph (Strategy A) & Topological Skeleton Centerline Graph (Strategy B).
  - Hazard modeling: blocked corridors and hazard polygon zones with automatic rerouting.
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Zustand state management, interactive HTML5 Canvas / SVG rendering overlay.

---

## Directory Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI application & CORS
│   │   ├── config.py                 # Application settings
│   │   ├── api/                      # REST endpoints (plans, graphs, routes, hazards)
│   │   ├── schemas/                  # Pydantic models for graphs, routes, hazards
│   │   ├── services/                 # Image processing, graph builders, storage
│   │   ├── algorithms/               # Hand-written graph algorithms (BFS, DFS, Dijkstra, A*)
│   │   └── utils/                    # Geometry & coordinate mapping
│   ├── tests/                        # Pytest suite & synthetic floor plan fixtures
│   └── pyproject.toml / requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/                      # Typed API client
│   │   ├── components/               # Canvas, toolbar, route results, modals
│   │   ├── hooks/                    # Canvas interaction & pan/zoom hooks
│   │   ├── store/                    # Zustand application store
│   │   ├── types/                    # TypeScript interfaces mirroring Pydantic schemas
│   │   └── utils/                    # Coordinate transforms & math
│   ├── package.json, vite.config.ts, tailwind.config.js
└── README.md
```

---

## Getting Started

### Quick Start (Windows)
Double-click [`run.bat`](file:///d:/Daa%20project/run.bat) in the project root. It will:
1. Start the FastAPI backend on `http://localhost:8000`
2. Start the Vite dev server on `http://localhost:5173`
3. Automatically launch your browser at `http://localhost:5173`

---

### Manual Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI server
uvicorn app.main:app --reload --port 8000
```

Backend API will be available at `http://localhost:8000`. Interactive OpenAPI documentation is at `http://localhost:8000/docs`.

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run Vite dev server
npm run dev
```

Frontend will be running at `http://localhost:5173`.

