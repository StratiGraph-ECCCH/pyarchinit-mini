<p align="center">
  <img src="https://raw.githubusercontent.com/enzococca/pyarchinit-mini/main/logo/logo_pyarchinit-mini.png" alt="PyArchInit-Mini Logo" width="300">
</p>

<h1 align="center">PyArchInit-Mini</h1>

<p align="center">
  <a href="https://badge.fury.io/py/pyarchinit-mini"><img src="https://badge.fury.io/py/pyarchinit-mini.svg" alt="PyPI version"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.8--3.14-blue.svg" alt="Python 3.8-3.14"></a>
  <a href="https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html"><img src="https://img.shields.io/badge/License-GPL%20v2-blue.svg" alt="License: GPL v2"></a>
  <a href="https://pyarchinit-mini.readthedocs.io/en/latest/?badge=latest"><img src="https://readthedocs.org/projects/pyarchinit-mini/badge/?version=latest" alt="Documentation Status"></a>
  <a href="https://pypi.org/project/pyarchinit-mini/"><img src="https://img.shields.io/badge/status-stable-green.svg" alt="Status"></a>
</p>

**Lightweight Archaeological Data Management System - 100% Desktop GUI Parity**

PyArchInit-Mini is a standalone, modular version of PyArchInit focused on core archaeological data management functionality without GIS dependencies. It provides multiple interfaces (Web, Desktop GUI, CLI, REST API) with a clean, scalable architecture for managing archaeological sites, stratigraphic units, and material inventories.

---

## ✨ Features

### 🏛️ Core Data Management
- **Site Management**: Complete CRUD operations for archaeological sites with i18n support
- **Stratigraphic Units (US)**: 49 fields organized in 6 tabs, matching desktop GUI
- **Material Inventory**: 37 fields in 8 tabs with ICCD thesaurus support
- **Tomba Records** (NEW): Burial/grave records matching the classic PyArchInit `tomba_table` — ritual, structure, grave goods, and dating fields with thesaurus-backed dropdowns and media attachments
- **Struttura Records** (NEW): Architectural structure records matching the classic PyArchInit `struttura_table` — identification, description, room articolazione, and dating fields with thesaurus-backed dropdowns and media attachments
- **Fauna Records** (NEW): Faunal remains records matching the classic PyArchInit `fauna_table` — US-linked identification, recovery context, species/skeletal data, and combustion/taphonomy fields with thesaurus-backed dropdowns
- **UT (Topographic Unit) Records** (NEW): Survey unit records matching the classic PyArchInit `ut_table` — project-scoped identification, location, field-survey observations, and potential/risk scoring with thesaurus-backed dropdowns and media attachments
- **Multi-Database**: SQLite and PostgreSQL with upload/connect capabilities
- **Internationalization**: Full support for Italian and English languages

### 🔬 Advanced Archaeological Tools
- **Harris Matrix**: Graphviz visualizer with 4 grouping modes and GraphML export
- **3D Visualization**: s3Dgraphy integration for stratigraphic unit visualization
- **Stratigraphic Validation**: Paradox detection, cycle detection, auto-fix reciprocal relationships
- **PDF Export**: Desktop-style reports (Sites, US, Inventario, Harris Matrix embedded)
- **Media Management** (NEW in v1.8.0):
  - **Drag-and-Drop Upload**: Intuitive file upload with visual feedback
  - **6 Specialized Viewers**: Images (GLightbox), PDF, Video, Excel/CSV, DOCX, 3D models (Three.js)
  - **10 Video Formats**: MP4, AVI, MOV, WMV, FLV, WebM, MKV, M4V, MPEG, MPG
  - **6 3D Model Formats**: OBJ, STL, PLY, GLTF, GLB, DAE
  - **Delete Functionality**: Remove media from all entity forms with confirmation
  - **Smart Organization**: Automatic file organization by entity type and ID
  - **Gallery Support**: Separate galleries per entity to prevent cross-contamination
- **Thesaurus ICCD**: 4 controlled vocabularies for standardized data entry
- **Chronological Datazioni System**: Standardized archaeological dating periods table
  - 36 pre-configured Italian archaeological periods (Paleolitico → Età Contemporanea)
  - Format: "Nome Datazione (Fascia Cronologica)" (e.g., "Età del Bronzo Antico (2.200-1.700 a.C.)")
  - Multi-database support (SQLite + PostgreSQL)
  - GUI combobox integration coming in v1.6.0
- **Periodization & Thesaurus Management (v1.5.8+)**: Complete web GUI for configuration management
  - **Periodization Interface**: CRUD operations for managing archaeological dating periods
  - **Thesaurus ICCD Interface**: Manage controlled vocabularies with read-only ICCD standards protection
  - **US Form Integration**: Dynamic dropdowns for definizione_stratigrafica, formazione, colore, consistenza
  - **Visual Distinction**: Predefined ICCD values marked with badges, custom values fully editable
  - **Two-Step Selection**: Intuitive table → field selection for thesaurus management
  - **Full i18n Support**: English and Italian translations for all interfaces

### 🤖 AI Integration & MCP (Model Context Protocol)
- **Claude Desktop Integration**: Natural language queries and AI-powered archaeological workflows
- **Auto-Configuration** (NEW in v1.9.14): One-command setup with `pyarchinit-mini-configure-claude`
- **ChatGPT Integration**: Web-based AI access to archaeological data via HTTP/SSE
- **23 MCP Tools** (v1.9.23+):
  - **Data Management (8)**: search, fetch, filter, manage_data, material, position, import_excel, import_data
  - **Validation (3)**: validate_stratigraphic_relationships, validate_relationship_format, validate_relationship_integrity
  - **Harris Matrix & 3D (4)**: create_harris_matrix, export_harris_matrix_graphml, configure_em_nodes, build_3d
  - **Reports & Export (2)**: generate_report (5 types), export
  - **Media & Thesaurus (2)**: manage_media (7 operations), manage_thesaurus (8 operations)
  - **System (4)**: manage_database_connections, manage_services, pyarchinit_sync, create_database
- **5 MCP Resources**: graphml, us, periods, relationships, sites
- **3 MCP Prompts**: Stratigraphic Model, Period Visualization, US Description
- **Zero-Config Setup**: Works with `uvx` for instant Claude Desktop access
- 📖 **Complete Guide**: [MCP Integration Guide](docs/MCP_INTEGRATION.md)

### 🎨 3D Visualization & Blender Integration
- **Web 3D Viewer**: Interactive Three.js-based stratigraphic visualization in browser
  - Natural language commands via chat interface
  - Automatic positioning from Harris Matrix
  - Color-coding by period or unit type
  - Real-time updates from Blender
- **Blender Integration**: Professional 3D model creation
  - Real geometry based on US type (layers, structures, cuts, fills)
  - Realistic materials from archaeological data
  - Real-time streaming to web viewer
  - Export to .blend, .glb, .fbx, .obj formats
- **AI-Powered Reconstruction**: Use Claude/ChatGPT to automate 3D reconstruction
  - Specialized AI agents (Architect, Validator, Texturizer, Reconstructor)
  - Complete site reconstruction from archaeological data
  - Automatic prompt generation for any site
- 📖 **Complete Guides**:
  - [3D Viewer Guide](docs/3D_VIEWER_GUIDE.md)
  - [Blender Integration Guide](docs/BLENDER_INTEGRATION.md)

### 🖥️ Multiple User Interfaces
- **Web Interface (Flask)**: Modern Bootstrap 5 UI, responsive design
- **Desktop GUI (Tkinter)**: Complete native application
- **CLI Interface**: Rich-based interactive command-line
- **REST API (FastAPI)**: Scalable API with automatic OpenAPI docs

### 📊 Data Export/Import
- **Excel Export**: Export Sites, US, Inventario to .xlsx format
- **Excel Import (NEW in v1.6.0)**: Import stratigraphic data from Excel with dual format support
  - **Harris Matrix Template**: Sheet-based format (NODES + RELATIONSHIPS)
  - **Extended Matrix Parser**: Inline format with relationship columns
  - **Multi-Interface**: Available in Web GUI, Desktop GUI, and CLI
  - **GraphML Generation**: Optional automatic GraphML export for visualization
  - **Database Consistency**: Unified database path across all interfaces
  - 📖 **Complete Guide**: [Excel Import Guide](https://pyarchinit-mini.readthedocs.io/en/latest/features/harris_matrix_import.html)
- **CSV Export**: Export to CSV with optional site filtering
- **Batch Import**: Import data from CSV with validation and statistics
- **Multi-Interface**: Available in Web UI, Desktop GUI, and CLI
- **Duplicate Handling**: Skip duplicates option to preserve existing data

### 🔐 Multi-User Authentication
- **Role-Based Access Control**: 3 user roles (Admin, Operator, Viewer)
- **JWT Authentication**: Secure API access with JSON Web Tokens
- **Session Management**: Flask-Login for Web interface
- **Password Security**: Bcrypt hashing for secure password storage
- **User Management**: Admin interface for creating/editing/deleting users
- **Permissions**: Granular permissions (create, read, update, delete, manage_users)
- **Protected Routes**: All web routes require authentication

### 🌐 Real-Time Collaboration (NEW in v1.0.9)
- **WebSocket Support**: Flask-SocketIO for bidirectional real-time communication
- **Live Notifications**: Toast notifications for all CRUD operations (Sites, US, Inventario)
- **Online User Presence**: See who's currently connected to the system
- **Activity Tracking**: Real-time updates when users create, edit, or delete data
- **User Join/Leave Events**: Notifications when team members connect or disconnect
- **Instant Data Sync**: All team members see changes immediately without refreshing
- **Multi-Tab Support**: Works across multiple browser tabs and windows

### 📊 Analytics Dashboard (NEW in v1.1.0)
- **Interactive Charts**: 8 different chart types for comprehensive data visualization
- **Overview Statistics**: Total counts for sites, US, inventory items, regions, and provinces
- **Geographic Analysis**: Sites distribution by region and province (pie and bar charts)
- **Chronological Analysis**: US distribution by chronological period
- **Typological Analysis**: US and inventory items grouped by type (doughnut and bar charts)
- **Conservation Analysis**: Inventory items by conservation state with color-coded pie chart
- **Site-Level Aggregations**: Top 10 sites by US count and inventory count
- **Multi-Interface Support**: Available in both Web UI (Chart.js) and Desktop GUI (matplotlib)
- **Real-Time Data**: Charts update automatically with current database state

---

## 🆕 What's New in v1.8.0 (2025-10-30)

### Enhanced Media Management System
Complete overhaul of media file handling with professional viewing capabilities:

**Specialized Media Viewers**:
- **Image Viewer**: GLightbox integration with gallery support, separate galleries per entity type (sites, US, inventario)
- **PDF Viewer**: In-browser PDF viewing with GLightbox iframe support
- **Video Viewer**: Native HTML5 video playback with GLightbox support for 10 formats (MP4, AVI, MOV, WMV, FLV, WebM, MKV, M4V, MPEG, MPG)
- **Excel/CSV Viewer**: pandas-powered spreadsheet viewer with Bootstrap-styled tables, supports up to 1000 rows
- **DOCX Viewer**: python-docx HTML converter with table support and heading detection
- **3D Model Viewer**: Interactive Three.js viewer with OrbitControls for OBJ, STL, PLY, GLTF, GLB, DAE formats

**Media Management Features**:
- **Enhanced Video Detection**: Improved file type recognition by extension for 10 video formats
- **Delete Functionality**: Delete media from list view and all entity forms with JavaScript confirmation
- **Smart Redirects**: Context-aware redirects after deletion (returns to form if deleted from edit page)
- **Drag-and-Drop Upload**: Intuitive file upload with visual feedback (completed in v1.7.13)
- **File Organization**: Automatic organization by entity type and ID

**Technical Improvements**:
- Added `python-docx>=1.0.0` dependency for DOCX viewing
- GLightbox 3.2.0 for image/PDF/video lightbox viewing
- Three.js r147 for stable 3D model rendering
- pandas for Excel/CSV data parsing
- Separate galleries prevent cross-entity media mixing

**User Experience**:
- Complex viewers (DOCX, Excel, 3D) open in new window for better screen space
- Simple viewers (images, PDF, video) use lightbox for quick preview
- Consistent viewer interface across all entity forms
- CSRF protection on all delete operations

## What's New in v1.7.13 (2025-10-29)

### Unified Version Management
All interfaces now display the same version number dynamically from a single source:
- **Web Interface**: Dashboard and login pages show v1.7.13
- **Desktop GUI**: Main window displays v1.7.13
- **CLI**: `--version` flag shows v1.7.13
- **REST API**: Version endpoint returns v1.7.13

### Complete Web GUI Documentation
- **📹 Video Tutorial**: Complete [Video Walkthrough](docs/VIDEO_TUTORIAL.md) showing full workflow (~12 min, watch at 2x speed recommended)
- **New Tutorial**: Comprehensive [Web GUI Tutorial](docs/WEB_GUI_TUTORIAL.md) with 63 screenshots
- **Visual Guide**: Step-by-step walkthrough of all features and forms
- **Complete Coverage**: Login, Dashboard, Sites, US (6 tabs), Inventario (8 tabs), Harris Matrix, Analytics, Validation, and Administration
- **Best Practices**: Workflow recommendations and troubleshooting guide

### Version Consistency
Fixed hardcoded version strings across all interfaces to use centralized `__version__` from main package, ensuring consistent versioning across Web, Desktop GUI, CLI, and API.

---

### 🔄 Extended Matrix Framework & GraphML Export (v1.3.0+)
Complete implementation of Extended Matrix Framework with GraphML export for yEd Graph Editor, including PyArchInit-compatible edge styling and DOT-based workflow.

> 📖 **Full Documentation**: [Extended Matrix Export Technical Guide](https://pyarchinit-mini.readthedocs.io/en/latest/features/graphml-export-technical.html)

**Extended Matrix Framework**:
PyArchInit-Mini supports the full Extended Matrix specification with **14 unit types** and **dual relationship symbols**.

#### Unit Types Supported:

**Stratigraphic Units** (use `>` / `<` symbols):
- **US** - Stratigraphic Unit (traditional)
- **USM** - Masonry Stratigraphic Unit
- **VSF** - Virtual Stratigraphic Face
- **SF** - Stratigraphic Face
- **CON** - Connector
- **USD** - Destructive Stratigraphic Unit
- **USVA, USVB, USVC** - Virtual Stratigraphic Units (grouping)
- **TU** - Typological Unit

**Non-Stratigraphic Units** (use `>>` / `<<` symbols):
- **DOC** - Document (with `tipo_documento` field: Image, PDF, DOCX, CSV, Excel, TXT)
- **property** - Property/Attribute
- **Extractor** - Data extractor node
- **Combiner** - Data combiner node

#### Relationship Symbols:

**Standard Stratigraphic** (`>` and `<`):
- Used by: US, USM, VSF, SF, CON, USD, USVA, USVB, USVC, TU
- `>` indicates "above" or "more recent than"
- `<` indicates "below" or "older than"
- Example: `US 1001 > US 1002` (US 1001 covers US 1002)

**Special Non-Stratigraphic** (`>>` and `<<`):
- Used by: DOC, property, Extractor, Combiner
- `>>` indicates "is connected to" or "derives from"
- `<<` indicates "receives from" or "is source for"
- Example: `DOC 8001 >> US 1001` (Document 8001 documents US 1001)

#### DOC Units - Document Management with File Upload:

DOC units have special functionality with **tipo_documento** field and **file upload**:

```python
# Creating a DOC unit with file upload
us_data = {
    'sito': 'Pompei',
    'us': 'DOC-8001',
    'unita_tipo': 'DOC',
    'tipo_documento': 'Image',  # or: PDF, DOCX, CSV, Excel, TXT
    'file_path': 'DoSC/Pompei_DOC-8001_20251023_142530_photo.jpg',
    'd_interpretativa': 'General excavation photo, Area A'
}
```

**File Upload Features**:
- **DoSC Folder**: All files automatically saved in centralized `DoSC/` directory
- **Automatic Naming**: Files renamed as `{SITE}_{US}_{TIMESTAMP}_{ORIGINALNAME}`
- **Database Tracking**: File paths stored in `file_path` field for retrieval
- **Multiple Formats**: Support for Images, PDF, DOCX, CSV, Excel, TXT, and more
- **Both Interfaces**: Available in Web Interface and Desktop GUI

**Automatic Field Display**:
- Web Interface: tipo_documento and file upload fields appear when unita_tipo="DOC" is selected
- Desktop GUI: tipo_documento combobox and "Browse..." button shown/hidden based on unit type selection

**Usage**:
1. Select "DOC" as Unit Type
2. Choose Document Type (Image, PDF, DOCX, CSV, Excel, TXT)
3. Click "Browse..." / "Choose File" to select file
4. Save → File uploaded to `DoSC/SITE_US_TIMESTAMP_filename.ext`

> 📖 **Full Guide**: [DOC File Upload Documentation](https://pyarchinit-mini.readthedocs.io/en/latest/features/media_management.html)

#### GraphML Export Features:

**Core Capabilities**:
- **yEd Compatibility**: Full GraphML format support
- **Extended Matrix Palette**: All 14 unit types with specific colors and shapes
- **Relationship Symbols**: Automatic `>` or `>>` labeling based on unit type
- **Archaeological Metadata**: Node descriptions with stratigraphic/interpretative data
- **Period Grouping**: Automatic grouping by chronological periods
- **Transitive Reduction**: Removes redundant stratigraphic relationships
- **Multi-Interface Support**: Available in Web UI, Desktop GUI, CLI, and REST API

**EM_palette Node Styles**:
- **US/USM**: White fill, red border (#9B3333), rectangle
- **VSF/SF**: White fill, yellow border (#D8BD30), rounded rectangle
- **USVA**: Black fill, blue border (#248FE7), rectangle
- **USVB**: Black fill, green border (#31792D), rectangle
- **USVC**: Black fill, green border (#31792D), rectangle
- **USD**: White fill, orange border (#D86400), rounded rectangle
- **CON**: Black fill/border, small circle
- **DOC**: Special document shape (BPMN Artifact)
- **TU**: Standard stratigraphic style
- **property**: BPMN Artifact shape
- **Extractor**: SVG icon, 25x25px
- **Combiner**: SVG icon, 25x25px

**Edge Styles** (PyArchInit EM Palette):
All edges are **black** with differentiated styles and arrowheads:
- **Dotted** (taglia, tagliato da, property, EM symbols >, >>, <, <<): Dotted line with normal arrow
- **Bold double arrows** (uguale a, si lega a): Bold solid line, arrows on both ends (dir=both)
- **Dot arrowhead** (si appoggia, si appoggia a, gli si appoggia): Solid line with filled circle arrowhead
- **Box arrowhead** (riempie, riempito da): Solid line with square arrowhead
- **No arrowhead** (continuità/CON): Solid line without arrowhead
- **Normal arrows** (copre, coperto da, sopra): Standard solid line with normal arrowhead

**Usage Examples**:
```python
# Python API - Create Extended Matrix graph
import networkx as nx

graph = nx.DiGraph()

# Add stratigraphic units
graph.add_node(1001,
    unita_tipo='US',
    d_stratigrafica='Fill layer',
    d_interpretativa='Medieval deposit')

graph.add_node(2001,
    unita_tipo='USM',
    d_stratigrafica='Wall',
    d_interpretativa='Roman wall in opus reticulatum')

# Add DOC unit with document type
graph.add_node(8001,
    unita_tipo='DOC',
    tipo_documento='Image',
    d_interpretativa='General photo of Area A')

# Add stratigraphic relationship (uses >)
graph.add_edge(1001, 1002, relationship='copre')

# Add document relationship (uses >>)
graph.add_edge(8001, 1001, relationship='documenta')

# Export to GraphML
from pyarchinit_mini.graphml_converter import convert_dot_to_graphml
# ... (see full documentation)

# Web Interface
# Navigate to: US List → Export Harris Matrix to GraphML (yEd)
# Select site, area, and options → Download .graphml

# Desktop GUI
# Tools → Export Harris Matrix (GraphML)
```

**Database Migration**:
New installations have Extended Matrix support by default. Existing databases need migrations:

```bash
# Step 1: Add tipo_documento field (document type)
python run_tipo_documento_migration.py upgrade

# Step 2: Add file_path field (file upload support)
python run_file_path_migration.py upgrade

# Rollback if needed
python run_file_path_migration.py downgrade
python run_tipo_documento_migration.py downgrade
```

**Available Interfaces**:
- **Python Library**: `from pyarchinit_mini.graphml_converter import convert_dot_to_graphml`
- **CLI Tool**: `pyarchinit-graphml convert|template|batch`
- **REST API**: `/api/graphml/*` endpoints
- **Web Interface**: Form-based export with site selection
- **Desktop GUI**: Tools menu with file save dialog

**Output**:
- GraphML file compatible with yEd Graph Editor (v3.23+)
- All 14 Extended Matrix unit types with correct styling
- Relationship symbols (`>`, `>>`) on edge labels
- Node descriptions visible in yEd
- Period-based hierarchical structure
- EM_palette colors and shapes applied automatically

### 📊 Pure NetworkX GraphML Export (NEW in v1.5.8)

**Graphviz-Free Export with Full Extended Matrix Support**

PyArchInit-Mini now includes a pure Python GraphML exporter powered by NetworkX, eliminating the need for Graphviz software installation. This provides a streamlined, dependency-free way to generate yEd-compatible Harris Matrix exports.

#### Key Features

- **No Graphviz Required**: Pure Python implementation using NetworkX
- **Full EM Palette Support**: All 14 Extended Matrix unit types with SVG symbols
- **Period Clustering**: Automatic TableNode generation with chronological rows
- **Transitive Reduction**: Built-in NetworkX algorithm for edge optimization
- **Language-Aware Labels**: Smart label extraction based on node type
- **Document Integration**: DOC nodes with file paths in URL fields
- **Multi-Interface Support**: Available in CLI, Web, Desktop GUI, and REST API

#### Extended Matrix Node Styles

The pure NetworkX exporter includes authentic SVG symbols from the EM palette:

**BPMN Nodes with SVG Resources**:
- **Extractor** (refid=1): Complex SVG with pipes and circular elements
- **Combinar** (refid=2): Aggregation symbol with geometric shapes
- **CON** (refid=3): Black diamond for continuity relationships
- **DOC**: BPMN Artifact shape with file path in URL field
- **Property**: BPMN Artifact with language-aware labels ("Material" / "Materiale")

**Standard Shapes**:
- **US/USM**: White fill, red border (#9B3333), rectangle
- **USVA/USVB/USVC**: Black fill, colored borders (blue/green), special shapes
- **VSF/SF**: White fill, yellow border (#D8BD30), rounded rectangle
- **USD**: White fill, orange border (#D86400), rounded rectangle

#### Smart Label Formatting

The exporter applies intelligent label formatting based on node type:

```python
# Property nodes - Extract first word from description
"Materiale pietra dura" → Visual label: "Materiale"
"Material hard stone" → Visual label: "Material"

# DOC nodes - File path in URL field
DOC4001:
  URL: "DosCo\test1_1.graphml"
  Description: "" (empty)
  Visual Label: "D.4001"

# Extractor/Combinar - Prefixed labels
Extractor400 → Visual label: "D.400"
Combinar500 → Visual label: "C.500"

# Standard nodes - US prefix
US1001 → Visual label: "US1001"
```

#### Period-Based TableNode Structure

Automatic hierarchical organization by archaeological periods:

```xml
<y:TableNode>
  <y:NodeLabel>Site Name</y:NodeLabel>
  <y:Rows>
    <y:Row id="Et_contemporanea">Età contemporanea</y:Row>
    <y:Row id="Et_moderna">Età moderna</y:Row>
    <y:Row id="XV_secolo">XV secolo</y:Row>
    <!-- Nodes nested in period rows -->
  </y:Rows>
</y:TableNode>
```

- Chronological sorting using periodo_iniziale/fase_iniziale
- Reversible order (newest→oldest or oldest→newest)
- Color-coded period rows
- Nested graph structure for proper yEd rendering

#### Usage Examples

**Python API**:
```python
from pyarchinit_mini.harris_matrix.matrix_generator import HarrisMatrixGenerator
from pyarchinit_mini.database.manager import DatabaseManager

# Generate Harris Matrix
generator = HarrisMatrixGenerator(db_manager, us_service)
graph = generator.generate_matrix("Site Name")

# Export to GraphML (Pure NetworkX)
result = generator.export_to_graphml(
    graph=graph,
    output_path="harris_matrix.graphml",
    site_name="Site Name",
    title="Site Name Harris Matrix",
    use_extended_labels=True,    # Extended Matrix labels
    include_periods=True,         # Period clustering
    apply_transitive_reduction=True,  # Remove redundant edges
    reverse_epochs=False          # Chronological order (oldest→newest)
)
```

**CLI Interface**:
```bash
# Start interactive CLI
pyarchinit-mini

# Navigate to: Harris Matrix → Export Matrix
# Select site and options
# GraphML file generated with all features
```

**Web Interface**:
```bash
# Start web server
pyarchinit-mini-web

# Navigate to: Harris Matrix → Export GraphML
# Select site, configure options
# Download .graphml file
```

**Desktop GUI**:
```bash
# Start desktop application
pyarchinit-mini-gui

# Menu → Tools → Export Harris Matrix (GraphML)
# Configure export options
# Save dialog appears
```

#### Technical Details

**Architecture**:
- `pure_networkx_exporter.py`: Main export logic with period grouping
- `graphml_builder.py`: XML generation with yEd structures
- `svg_resources.py`: EM palette SVG definitions (Extractor, Combinar, CON)
- NetworkX transitive reduction for edge optimization
- ElementTree for efficient XML generation

**Advantages over Graphviz-based Export**:
- No external software installation required
- Faster export for large graphs
- More consistent cross-platform behavior
- Direct control over yEd-specific structures
- Easier to maintain and extend

**Compatibility**:
- yEd Graph Editor v3.23+
- All operating systems (Windows, Linux, macOS)
- Python 3.8-3.14
- Works with both SQLite and PostgreSQL databases

**Performance**:
- Handles 500+ nodes efficiently
- Sub-second export for typical sites (50-100 nodes)
- Memory-efficient streaming XML generation
- Optimized period grouping algorithms

#### Migration from Graphviz Export

The pure NetworkX exporter is fully compatible with existing workflows:

```python
# Old way (requires Graphviz software)
from pyarchinit_mini.graphml_converter import convert_dot_to_graphml
convert_dot_to_graphml(dot_file, graphml_file)

# New way (pure Python, no Graphviz needed)
from pyarchinit_mini.harris_matrix.matrix_generator import HarrisMatrixGenerator
generator.export_to_graphml(graph, output_path, site_name)

# Same result: yEd-compatible GraphML with full EM palette support
```

All interfaces (CLI, Web, Desktop GUI) automatically use the pure NetworkX exporter when calling `export_to_graphml()`.

### 🎨 Extensible EM Node Type System (NEW in v1.6.0)

**User-Friendly Configuration Management for Extended Matrix Node Types**

PyArchInit-Mini now features a flexible, extensible system for managing Extended Matrix node types. Add custom node types without modifying code, using either YAML configuration files or a user-friendly web interface.

#### Key Features

✅ **14 Built-in Node Types** - US, USM, VSF, SF, USD, USVA, USVB, USVC, TU, CON, DOC, property, Extractor, Combinar
✅ **Add Custom Types** - Create your own node types with custom styling
✅ **Web Interface** - Intuitive GUI for managing types (CRUD operations)
✅ **YAML Configuration** - Direct file editing for power users
✅ **Validation** - Automatic validation of colors, sizes, shapes
✅ **Hot Reload** - Changes take effect immediately

#### Managing Node Types

**Via Web Interface** (Recommended):
```bash
# Start web interface
cd web_interface
python app.py

# Navigate to: http://localhost:5000/em-node-config
```

The web interface provides:
- Visual cards for all node types (grouped by category)
- Add/Edit/Delete operations for custom types
- Color pickers for fill, border, and text colors
- Shape, font, and style selectors
- Real-time validation
- Built-in/Custom badges

**Via YAML Configuration** (Power Users):
```yaml
# File: pyarchinit_mini/config/em_node_types.yaml

node_types:
  SAMPLE:  # Custom type ID
    name: "Sample Unit"
    description: "Custom sample unit type"
    category: "stratigraphic"  # or "non_stratigraphic"
    symbol_type: "single_arrow"  # > / < (or "double_arrow" for >> / <<)
    visual:
      shape: "diamond"
      fill_color: "#FFE6E6"  # Hex color
      border_color: "#CC0000"
      border_width: 2.5
      width: 100.0
      height: 40.0
      font_family: "DialogInput"
      font_size: 14
      font_style: "bold"
      text_color: "#000000"
    label_format: "SAMPLE-{number}"  # {number} or {first_word}
    custom: true
```

#### Python API

```python
from pyarchinit_mini.config.em_node_config_manager import get_config_manager

# Get configuration manager
config = get_config_manager()

# Get all node types
all_types = config.get_all_node_types()

# Get visual style for a type
visual = config.get_visual_style('US')

# Format a label
label = config.format_label('US', '123', '')  # → "US123"

# Add custom type programmatically
visual = {
    'shape': 'hexagon',
    'fill_color': '#CCFFCC',
    'border_color': '#00AA00',
    'border_width': 2.0,
    'text_color': '#000000',
    'font_family': 'DialogInput',
    'font_size': 16,
    'font_style': 'bold'
}

success = config.add_custom_node_type(
    tipo_id='FIND',
    name='Find Unit',
    description='Archaeological find',
    category='stratigraphic',
    symbol_type='single_arrow',
    visual=visual,
    label_format='FIND{number}'
)

if success:
    config.save_config()
```

#### Label Format Placeholders

- `{number}` - Replaced with US number (e.g., "US{number}" → "US1", "US2")
- `{first_word}` - First word from description (e.g., "Materiale", "Material")

#### Configuration

All node types are defined in `pyarchinit_mini/config/em_node_types.yaml`:

**Node Categories**:
- **Stratigraphic** - Use single arrows (`>` / `<`) for relationships
- **Non-Stratigraphic** - Use double arrows (`>>` / `<<`) for relationships

**Visual Properties**:
- **Shapes**: rectangle, roundrectangle, hexagon, diamond, parallelogram, octagon, triangle, ellipse, trapezoid, bpmn_artifact, svg
- **Colors**: Hex format `#RRGGBB` (e.g., `#FFFFFF`, `#9B3333`)
- **Sizes**: Width/Height (10-500), Border Width (0.1-10)
- **Fonts**: DialogInput, Dialog, Arial, Helvetica
- **Styles**: plain, bold, italic, bolditalic

**Validation**: Automatic validation ensures:
- Valid hex colors
- Size ranges
- Required fields
- Valid categories and symbol types

For complete documentation, see: [Extended Matrix Framework Documentation](https://pyarchinit-mini.readthedocs.io/en/latest/features/extended-matrix-framework.html)

### 🎨 s3Dgraphy - 3D Stratigraphic Visualization (NEW in v1.6.0)

**Interactive 3D Harris Matrix with Extended Matrix (EM) Palette Integration**

s3Dgraphy provides a complete 3D visualization system for Harris Matrix diagrams, combining stratigraphic relationships with 3D models of archaeological contexts. The system uses GraphViz DOT layout for accurate positioning and supports OBJ, GLTF, and GLB 3D formats.

#### Core Features

- **Integrated 3D+2D Viewer**: Side-by-side Harris Matrix and 3D model visualization
- **GraphViz DOT Layout**: Professional stratigraphic positioning following archaeological standards
- **Extended Matrix Palette**: Automatic node coloring based on US type (10 archaeological categories)
- **3D Model Support**: OBJ, GLTF (with vertex colors), and GLB formats
- **Interactive Navigation**: Click nodes to focus 3D model, navigate between related US
- **Real-Time Sync**: Bi-directional synchronization between matrix and 3D view
- **Model Upload**: REST API for uploading 3D models per stratigraphic unit
- **Persistent Storage**: Site-based organization of 3D models

#### Extended Matrix Color Palette

Automatic node coloring based on `unita_tipo`:

| Type | Color | RGB | Hex |
|------|-------|-----|-----|
| Taglio | Brown | (139, 69, 19) | #8B4513 |
| Deposito | Chocolate | (210, 105, 30) | #D2691E |
| Riempimento | Peru | (205, 133, 63) | #CD853F |
| Humus | Dark Olive Green | (85, 107, 47) | #556B2F |
| Muro | Gray | (128, 128, 128) | #808080 |
| Pavimento | Dark Gray | (169, 169, 169) | #A9A9A9 |
| Crollo | Maroon | (128, 0, 0) | #800000 |
| Costruzione | Light Gray | (211, 211, 211) | #D3D3D3 |
| Distruzione | Dark Red | (139, 0, 0) | #8B0000 |
| Altro | Light Steel Blue | (176, 196, 222) | #B0C4DE |

#### API Endpoints

**Model Management**:
```python
# Upload 3D model for a specific US
POST /api/s3d/upload
Content-Type: multipart/form-data
Fields:
  - site_name: str          # Archaeological site name
  - us_id: str              # Stratigraphic unit ID
  - file: File              # 3D model file (OBJ/GLTF/GLB)

Response: {"message": str, "path": str}
```

**Viewer Access**:
```python
# Get integrated 3D Harris Matrix viewer
GET /s3d/viewer/<site_name>

# Get models for a site
GET /api/s3d/models/<site_name>

Response: [
    {
        "name": str,           # Display name
        "path": str,          # Relative path
        "us_id": str,         # US number or null for site-level
        "format": str         # "obj", "gltf", or "glb"
    }
]
```

#### Data Format for External Use

**Harris Matrix Graph Structure**:
```python
# Input format for Harris Matrix visualization
{
    "nodes": [
        {
            "id": str,                    # Unique node ID
            "us_number": str,             # US number for display
            "type": str,                  # EM palette type (see table above)
            "area": str,                  # Archaeological area/sector
            "period": str,                # Chronological period
            "definition": str,            # US description
            "d_stratigrafica": str,       # Stratigraphic description
            "d_interpretativa": str       # Archaeological interpretation
        }
    ],
    "edges": [
        {
            "source": str,                # Source node ID
            "target": str,                # Target node ID
            "stratigraphic_relation": str # COVERS, CUTS, FILLS, etc.
        }
    ]
}
```

**3D Model Requirements**:
- **OBJ Format**: Wavefront OBJ with optional MTL file
- **GLTF/GLB Format**: GLTF 2.0 with vertex colors support
- **File Size**: Max 100MB per model (configurable)
- **Coordinate System**: Y-up, meters
- **Model Organization**:
  - Site-level: `uploads/3d_models/<site_name>/site/model.obj`
  - US-level: `uploads/3d_models/<site_name>/US_<us_id>/model.obj`

#### Usage Examples

**Python API - Upload and Visualize**:
```python
from pyarchinit_mini.s3d_integration import Model3DManager
import requests

# Upload 3D model via API
files = {'file': open('model.obj', 'rb')}
data = {
    'site_name': 'Pompei',
    'us_id': '1001'
}
response = requests.post(
    'http://localhost:5001/api/s3d/upload',
    files=files,
    data=data
)

# Access viewer
viewer_url = f'http://localhost:5001/s3d/viewer/Pompei'
```

**Python API - Direct Model Management**:
```python
from pyarchinit_mini.s3d_integration import Model3DManager
from pathlib import Path

manager = Model3DManager(base_dir='uploads/3d_models')

# Get models for a site
models = manager.get_models_for_site('Pompei')
for model in models:
    print(f"US {model['us_id']}: {model['name']} ({model['format']})")

# Get model path for specific US
path = manager.get_model_path('Pompei', '1001')
```

**cURL - Upload Model**:
```bash
# Upload OBJ model
curl -X POST http://localhost:5001/api/s3d/upload \
  -F "site_name=Pompei" \
  -F "us_id=1001" \
  -F "file=@US1001.obj"

# Upload GLTF model with vertex colors
curl -X POST http://localhost:5001/api/s3d/upload \
  -F "site_name=Pompei" \
  -F "us_id=1002" \
  -F "file=@US1002.gltf"

# Upload site-level model (no US)
curl -X POST http://localhost:5001/api/s3d/upload \
  -F "site_name=Pompei" \
  -F "file=@site_overview.glb"
```

**Web Interface - Upload and View**:
1. Navigate to **Harris Matrix** → **3D Viewer** → Select site
2. Click **Upload Model** button
3. Select US (optional, leave blank for site-level model)
4. Choose 3D file (OBJ/GLTF/GLB)
5. Upload and view immediately

**Viewer Features**:
- **Dual Panel**: Harris Matrix (left) + 3D Model (right)
- **Node Click**: Click any US node to focus 3D camera on that model
- **Info Panel**: Right sidebar with US properties and stratigraphic relations
- **Navigation**: Click parent/child relations to navigate through stratigraphy
- **Scrollable Matrix**: Vertical scroll for deep stratigraphic sequences
- **Model Selection**: Dropdown to switch between different 3D models
- **Camera Controls**: OrbitControls for 3D navigation (rotate, pan, zoom)

#### Generating Test Models

For testing or creating proxy geometries:
```python
from pyarchinit_mini.s3d_integration.test_model_generator import (
    generate_test_models, EM_COLORS
)

# Generate colored box for each US type
us_data = {
    'us': 1001,
    'type': 'Deposito',      # Will use chocolate color
    'area': 'A',
    'period': 'Medievale',
    'position': (0, 0, 0),   # X, Y, Z coordinates
    'size': (2, 1, 2)        # Width, Height, Depth in meters
}

generate_test_models(
    us_list=[us_data],
    output_dir='output/3d_models',
    formats=['obj', 'gltf']  # Generate both formats
)
```

#### Integration with Existing Harris Matrix

The 3D viewer automatically integrates with PyArchInit's Harris Matrix data:

1. **Automatic Graph Generation**: Reads US and relationships from database
2. **GraphViz Layout**: Uses DOT algorithm for hierarchical positioning
3. **Extended Matrix Colors**: Applies EM palette based on `unita_tipo`
4. **Model Association**: Links 3D models by US number
5. **Bidirectional Sync**: Matrix clicks update 3D view, and vice versa

#### External Integration Example

Complete workflow for external applications:

```python
import requests
import json

# 1. Define stratigraphic data
harris_data = {
    "nodes": [
        {
            "id": "site_pompei_1001",
            "us_number": "1001",
            "type": "Deposito",
            "area": "Regio VI",
            "period": "Periodo Romano Imperiale",
            "definition": "Strato di abbandono"
        },
        {
            "id": "site_pompei_1002",
            "us_number": "1002",
            "type": "Pavimento",
            "area": "Regio VI",
            "period": "Periodo Romano Imperiale",
            "definition": "Pavimento a mosaico"
        }
    ],
    "edges": [
        {
            "source": "site_pompei_1001",
            "target": "site_pompei_1002",
            "stratigraphic_relation": "COVERS"
        }
    ]
}

# 2. Create site in PyArchInit (if not exists)
site_data = {
    "site_name": "Pompei",
    "location_region": "Campania",
    "location_comune": "Pompei"
}
requests.post('http://localhost:5001/api/sites', json=site_data)

# 3. Upload 3D models
for us in ["1001", "1002"]:
    with open(f'models/US{us}.gltf', 'rb') as f:
        files = {'file': f}
        data = {'site_name': 'Pompei', 'us_id': us}
        requests.post('http://localhost:5001/api/s3d/upload',
                     files=files, data=data)

# 4. Access integrated viewer
print("Viewer: http://localhost:5001/s3d/viewer/Pompei")
```

#### Configuration

Edit `~/.pyarchinit_mini/config/config.yaml`:

```yaml
s3dgraphy:
  enabled: true
  upload_dir: "web_interface/static/uploads/3d_models"
  max_file_size: 104857600  # 100MB
  allowed_formats: ["obj", "mtl", "gltf", "glb"]
  default_camera:
    position: [5, 5, 5]
    target: [0, 0, 0]
```

### 🌐 Heriverse/ATON Export Integration (NEW in v1.3.2)

**Full CouchDB/Scene Wrapper for Heriverse and ATON Platforms**

PyArchInit-Mini now supports complete Heriverse/ATON JSON export format with CouchDB wrapper, semantic shapes, and extended metadata for advanced 3D stratigraphic visualization on Heriverse and ATON platforms.

#### Key Features

- **CouchDB/Scene Wrapper**: Auto-generated scene metadata with UUIDs for CouchDB compatibility
- **Environment Configuration**: Panoramas, lighting, and scene settings
- **Scenegraph Support**: 3D scene hierarchy for rendering engines
- **USVn Category**: Virtual negative units (separate from USVs)
- **Semantic Shapes**: Auto-generated 3D proxy models (GLB) for each stratigraphic unit
- **Representation Models**: Full-detail 3D models (GLTF) support
- **Panorama Models**: 360° panoramic image integration
- **Extended Edge Types**: generic_connection, changed_from, contrasts_with for paradata
- **13 Node Categories**: Complete Extended Matrix compliance + Heriverse extensions
- **13 Edge Types**: Comprehensive relationship modeling

#### Export Formats Comparison

| Feature | s3Dgraphy JSON v1.5 | Heriverse JSON |
|---------|---------------------|----------------|
| **Format** | JSON v1.5 | Heriverse/CouchDB |
| **Wrapper** | No | CouchDB scene wrapper |
| **UUIDs** | No | Auto-generated |
| **Environment** | No | Panoramas, lighting |
| **Scenegraph** | No | 3D scene hierarchy |
| **USVn Category** | No | Yes (virtual negative units) |
| **Semantic Shapes** | No | Auto-generated GLB placeholders |
| **Use Case** | General web platforms | Heriverse/ATON platforms |

#### Web Interface Usage

1. Navigate to: **Menu → Harris Matrix → Export GraphML**
2. Scroll to **"Export s3Dgraphy (Extended Matrix)"** section
3. Select your archaeological site
4. Click **"Export Heriverse"** button (orange)
5. Download `{site_name}_heriverse.json`

#### API Endpoints

**Export Heriverse JSON**:
```bash
# Get Heriverse-formatted JSON with CouchDB wrapper
GET /3d/export/heriverse/<site_name>

# Example
curl http://localhost:5000/3d/export/heriverse/Pompeii \
  -o pompeii_heriverse.json
```

**Compare with standard s3Dgraphy export**:
```bash
# Standard s3Dgraphy JSON v1.5
GET /3d/export/json/<site_name>

# Heriverse JSON (with wrapper)
GET /3d/export/heriverse/<site_name>
```

#### Python API

```python
from pyarchinit_mini.s3d_integration import S3DConverter

converter = S3DConverter()
graph = converter.create_graph_from_us(us_list, "Pompeii")

# Export to Heriverse format
converter.export_to_heriverse_json(
    graph,
    "pompeii_heriverse.json",
    site_name="Pompeii",
    creator_id="user:abc123",           # Optional: defaults to auto-generated UUID
    resource_path="https://server.org/uploads"  # Optional: defaults to placeholder
)
```

#### JSON Structure

```json
{
  "_id": "scene:auto-generated-uuid",
  "_rev": "1-auto-generated-revision",
  "type": "scene",
  "creator": "user:auto-generated-uuid",
  "resource_path": "https://server/uploads/...",
  "title": "Site Name Stratigraphy",
  "resource_json": {
    "environment": {
      "mainpano": {"url": "s"},
      "lightprobes": {"auto": "true"},
      "mainlight": {"direction": ["0.0", "0.0", "0.0"]}
    },
    "scenegraph": {
      "nodes": {},
      "edges": {".": []}
    },
    "multigraph": {
      "version": "1.5",
      "context": {"absolute_time_Epochs": {}},
      "graphs": {
        "graph_id": {
          "nodes": {
            "stratigraphic": {
              "US": {},
              "USVs": {},
              "USVn": {},  // Virtual negative units
              "SF": {}
            },
            "semantic_shapes": {},        // 3D proxy models (GLB)
            "representation_models": {},  // Full 3D models (GLTF)
            "panorama_models": {}         // 360° images
          },
          "edges": {
            "is_before": [],
            "generic_connection": [],  // Paradata
            "changed_from": [],        // Evolution
            "contrasts_with": []       // Interpretations
          }
        }
      }
    }
  },
  "wapp": "heriverse",
  "visibility": "public"
}
```

#### When to Use

**Use Heriverse Export for**:
- Uploading stratigraphic data to Heriverse platform
- Integration with ATON 3D viewer
- CouchDB-based archaeological data systems
- Advanced 3D visualization with semantic proxy models
- Full scene environment configuration

**Use Standard s3Dgraphy Export for**:
- General web platform integration
- Programmatic analysis and data processing
- Extended Matrix Framework compliance
- Simpler JSON structure without CouchDB wrapper

#### Semantic Shapes Auto-Generation

The Heriverse export automatically creates semantic_shape placeholders for each stratigraphic unit:

```python
# For each US, a semantic shape is auto-generated:
{
  "shape_us_001": {
    "name": "3D Model for US 001",
    "description": "Proxy 3D model",
    "url": "https://server/uploads/models/us_001.glb",
    "format": "glb",
    "us_reference": "site_us_001"
  }
}
```

These placeholders are ready for integration with actual 3D models uploaded through the model management system.

#### Resources

- **Heriverse Platform**: https://heriverse.org
- **ATON Framework**: https://github.com/phoenixbf/aton
- **s3Dgraphy Docs**: https://docs.extendedmatrix.org/projects/s3dgraphy/
- **Import/Export Spec**: https://docs.extendedmatrix.org/projects/s3dgraphy/en/latest/s3dgraphy_import_export.html

### 🚀 Technical Features
- **Production Ready**: v1.1.5 with EM_palette GraphML Export + Archaeological Metadata + Clean Edges
- **Python 3.8-3.14**: Full support for latest Python versions including 3.12, 3.13, 3.14
- **Data Validation**: Comprehensive Pydantic schemas
- **Session Management**: Proper database connection pooling
- **Auto Documentation**: Interactive Swagger/OpenAPI docs
- **Cross-Platform**: Windows, Linux, macOS support
- **Tests Included**: Full test suite included in distribution

---

## 📊 Project Status

### 🚀 Version 1.5.7 - Web GUI Combobox Integration (NEW)

PyArchInit-Mini v1.5.7 implements web interface integration with the chronological datazioni system:

✅ **Web GUI Combobox**: Datazione field now uses SelectField with database-driven choices
✅ **Dynamic Choices**: Dropdown populated from datazioni_table on both create and edit forms
✅ **Italian Translation**: Complete Italian language support for chronology fields
✅ **Text Input Fields**: Periodo/Fase fields changed to simple text input (no dropdowns)
✅ **Form Consistency**: Same behavior on both US create and edit routes
✅ **Bootstrap 5 Integration**: Proper form-select and form-control CSS classes

### 🔧 What's New in v1.5.7 (2025-10-27)

**Web Interface Updates**
- `datazione` field: Changed from StringField to SelectField with database choices
- `periodo_iniziale`, `periodo_finale`: Changed from SelectField to StringField (removed 40+ hardcoded choices)
- `fase_iniziale`, `fase_finale`: Remain as StringField for flexible chronological data entry
- Choices populated dynamically in both `/us/create` and `/us/<us_id>/edit` routes
- Italian translations: "Periodo Iniziale", "Fase Iniziale", "Periodo Finale", "Fase Finale"

**Service Integration**
- `DatazioneService` initialized at app startup
- `get_datazioni_choices()` provides formatted dropdown data: `[{'value': 'nome', 'label': 'Nome (Fascia)'}]`
- Session management ensures no detached instance errors

**User Experience**
- Standardized dating selection via dropdown (36 Italian archaeological periods)
- Free-text entry for periodo/fase fields for flexibility
- Form displays: "-- Seleziona Datazione --" as default option
- Full Italian language support in web interface

**Next Steps (v1.6.0)**
- Desktop GUI combobox integration
- Parser synchronization with datazioni table
- Import/export updates for datazioni support

### 🚀 Version 1.5.6 - Chronological Datazioni System

PyArchInit-Mini v1.5.6 introduces a comprehensive chronological dating system for standardized archaeological periodization:

✅ **Datazioni Table**: New `datazioni_table` with 36 pre-configured Italian archaeological periods
✅ **Multi-Database Support**: Compatible with both SQLite and PostgreSQL
✅ **Service Layer**: Complete CRUD operations via DatazioneService
✅ **Default Initialization**: Auto-populate with standard Italian periods from Paleolitico to Età Contemporanea
✅ **API Ready**: Choices endpoint for dropdown/combobox integration

### 🔧 What's New in v1.5.6 (2025-10-27)

**Chronological Datazioni System**
- New `datazioni_table` model with fields: `nome_datazione`, `fascia_cronologica`, `descrizione`
- 36 default Italian archaeological periods covering full chronological span
- `DatazioneService` with complete CRUD operations and validation
- Method `get_datazioni_choices()` returns formatted data for form comboboxes
- Method `initialize_default_datazioni()` populates table with standard periods
- Multi-database compatibility: SQLite and PostgreSQL via SQLAlchemy ORM
- Session management with context managers to avoid detached instance errors

**Testing and Quality**
- Comprehensive test script (`test_datazioni_table.py`) with 7 test cases
- 90%+ test coverage for core functionality
- Validates table creation, CRUD operations, choices generation, and search

### 🚀 Version 1.5.0 - GraphML Periodization Fix

Critical fixes and improvements for GraphML export:

✅ **All Interfaces Working**: Web, Desktop GUI, CLI, and REST API fully operational
✅ **GraphML Periodization Fixed**: All archaeological periods now properly visible in yEd export (was showing only 3-4 instead of all 8 periods)
✅ **Chronological Ordering**: Periods arranged in correct archaeological sequence based on periodo/fase
✅ **Large Site Support**: Tested with Dom zu Lund (758 US nodes, 8 periods) - complete period display verified
✅ **3D Visualization**: s3Dgraphy integration for stratigraphic unit visualization
✅ **PyPI Package**: All console commands work correctly after `pip install`

### 🔧 What's New in v1.5.0 (2025-10-26)

**GraphML Export - Periodization Display Fixed**
- Fixed `parse_clusters()` to handle both quoted and unquoted label formats from Graphviz
- Fixed period ordering to use chronological sequence (oldest → newest) instead of alphabetical
- Fixed reverse epochs to properly invert chronological order (newest → oldest)
- All 8 archaeological periods now visible in GraphML export for large sites
- Maintains consistency with database periodization (periodo_iniziale, fase_iniziale)

See the [CHANGELOG](https://pyarchinit-mini.readthedocs.io/en/latest/development/changelog.html) for complete version history.

### 🔧 Previous Fixes (v1.2.5-1.2.9)
- Fixed missing email-validator dependency
- Fixed desktop GUI language switching
- Fixed web server Flask template/static path resolution  
- Added automatic i18n database column migrations
- All module imports now use absolute paths for installed packages

### 📈 Active Development
The project is actively maintained with regular updates. Check the [CHANGELOG](https://pyarchinit-mini.readthedocs.io/en/latest/development/changelog.html) for detailed version history.

---

## 🔧 System Requirements

### Python
- **Python 3.8-3.14** (Python 3.10+ recommended)

### Graphviz (Optional - Only for DOT File Generation)

**By default, PyArchInit-Mini uses Pure NetworkX for GraphML export (no Graphviz required).**

Graphviz software is **optional** and only needed if you want to:
- Generate DOT files for custom workflows
- Use the legacy Graphviz-based export pipeline
- Apply transitive reduction via the `tred` command

The Python module `graphviz` is installed automatically via pip, but the native Graphviz software requires manual installation if you need it.

**Installation by Operating System:**

#### Linux (Debian/Ubuntu)
```bash
sudo apt-get update
sudo apt-get install graphviz
```

#### Linux (Fedora/RHEL)
```bash
sudo dnf install graphviz
```

#### macOS (Homebrew)
```bash
brew install graphviz
```

#### macOS (MacPorts)
```bash
sudo port install graphviz
```

#### Windows
1. **Option 1 - Chocolatey** (Recommended, automatically adds to PATH):
   ```powershell
   choco install graphviz
   ```

2. **Option 2 - Direct Download** (Requires manual PATH configuration):

   **Step 1: Download and Installation**
   - Download installer from: https://graphviz.org/download/
   - Run the downloaded `.msi` 
   - During installation, **select "Add Graphviz to the system PATH for all users"**
   - If you don't select this option, you'll need to add it manually to PATH

   **Step 2: Manually Add to PATH (if needed)**

   If Graphviz was not automatically added to PATH:

   1. Find the installation path (default: `C:\Program Files\Graphviz\bin`)
   2. Open System Settings:
      - Windows 10/11: `Settings → System → About → Advanced system settings`
      - Or: search for "Environment Variables" in the Start menu
   3. Click on "Environment Variables..."
   4. In the "System variables" section, find and select "Path"
   5. Click on "Edit..."
   6. Click on "New"
   7. Paste the path: `C:\Program Files\Graphviz\bin`
   8. Click OK on all windows
   9. **IMPORTANT**: Restart any Command Prompt or PowerShell windows that were already open

   **Step 3: Verification (IMPORTANT)**

   Open a **new** Command Prompt or PowerShell and verify:
   ```powershell
   dot -V
   tred -V
   ```

   If you see "command not found" or "not recognized":
   - Did you close and reopen the terminal after modifying PATH?
   - Does the path `C:\Program Files\Graphviz\bin` contain `dot.exe` and `tred.exe`?
   - Check that PATH was added correctly in environment variables

**Installation Verification:**
```bash
# Check if dot command is available
dot -V

# Check if tred command is available (for transitive reduction)
tred -V
```

Expected output:
```
dot - graphviz version X.X.X (XXXXXXXX.XXXX)
```

> **Note**: If Harris Matrix / GraphML export is not needed, you can skip Graphviz installation and use only other features.

---

## 📦 Installation

### Basic Installation (API Only)
```bash
pip install pyarchinit-mini
```

### With CLI Interface
```bash
pip install 'pyarchinit-mini[cli]'
```

### With Web Interface
```bash
pip install 'pyarchinit-mini[web]'
```

### With Desktop GUI
```bash
pip install 'pyarchinit-mini[gui]'
```

### With Harris Matrix Visualization
```bash
pip install 'pyarchinit-mini[harris]'
```

### With Advanced PDF Export
```bash
pip install 'pyarchinit-mini[pdf]'
```

### With Excel/CSV Export and Import
```bash
pip install 'pyarchinit-mini[export]'
```

### With Authentication (Multi-User)
```bash
pip install 'pyarchinit-mini[auth]'
```

### Complete Installation (Recommended)
```bash
pip install 'pyarchinit-mini[all]'
```

### Development Installation
```bash
pip install 'pyarchinit-mini[dev]'
```

> **Note for zsh users**: Quote the package name to avoid globbing issues: `'pyarchinit-mini[all]'`

---

## 🚀 Quick Start

### 1. Initial Setup
After installation, run the initialization command to set up the database and create an admin user:

```bash
pyarchinit-mini-init
```

This command will:
1. Create the configuration directory and database in `~/.pyarchinit_mini/`
2. Prompt you to create an admin user (username, email, password)
3. Set up all necessary directories for media, exports, and backups

For non-interactive setup with default credentials:
```bash
pyarchinit-mini-init --non-interactive
# Creates admin user with username: admin, password: admin
```

**Note**: If using the non-interactive mode, change the default password immediately after first login!

The setup creates the following structure in your home directory:

```
~/.pyarchinit_mini/
├── data/              # Database SQLite files
├── media/             # Images, videos, documents
│   ├── images/
│   ├── videos/
│   ├── documents/
│   └── thumbnails/
├── export/            # Generated PDF exports
├── backup/            # Automatic database backups
├── config/            # Configuration files
│   └── config.yaml
└── logs/              # Application logs
```

### 2. Usage

#### Start the Web Interface
```bash
pyarchinit-mini-web
# Open http://localhost:5001 in your browser
# Login with the admin credentials created during initialization
```

#### Start the Desktop GUI
```bash
pyarchinit-mini-gui
```

#### Start the REST API Server
```bash
pyarchinit-mini-api
# API docs available at http://localhost:8000/docs
```

#### Start the CLI Interface
```bash
pyarchinit-mini
```

### 3. Accessing the Analytics Dashboard

The Analytics Dashboard provides comprehensive data visualization with 8 different chart types.

#### Web Interface
1. Start the web interface: `pyarchinit-mini-web`
2. Login with your admin credentials
3. Navigate to **Analytics** in the top menu
4. View interactive Chart.js charts with:
   - Sites by region (pie chart)
   - Sites by province (bar chart - top 10)
   - US by chronological period (horizontal bar chart)
   - US by type (doughnut chart)
   - Inventory by type (bar chart - top 10)
   - Inventory by conservation state (pie chart)
   - US by site (bar chart - top 10)
   - Inventory by site (bar chart - top 10)

#### Desktop GUI
1. Start the desktop application: `pyarchinit-gui`
2. Go to **Tools → Analytics Dashboard**
3. View matplotlib charts with the same 8 visualizations
4. Use the zoom/pan toolbar for detailed analysis
5. Scroll through all charts in a single window

**Charts Update Automatically**: All charts reflect the current state of your database in real-time.

---

## 🖥️ Complete Command Reference

PyArchInit-Mini provides 17 specialized commands for different tasks. Use `pyarchinit-mini --list-commands` to see this reference anytime.

### Interfaces

#### `pyarchinit-mini`
Interactive CLI with menu-driven interface
```bash
pyarchinit-mini [-d DATABASE_URL] [--version] [--list-commands]

# Examples
pyarchinit-mini  # Start with default database
pyarchinit-mini -d "postgresql://user:pass@localhost/db"
```

#### `pyarchinit-mini-api`
REST API server (default port: 8000)
```bash
# Configuration via environment variables
PYARCHINIT_API_HOST=0.0.0.0  # Default: 0.0.0.0
PYARCHINIT_API_PORT=8000      # Default: 8000
PYARCHINIT_API_RELOAD=false   # Default: false

# Example
PYARCHINIT_API_PORT=5000 pyarchinit-mini-api
```

#### `pyarchinit-mini-web`
Web interface (default port: 5001)
```bash
# Configuration via environment variables
PYARCHINIT_WEB_HOST=0.0.0.0   # Default: 0.0.0.0
PYARCHINIT_WEB_PORT=5001      # Default: 5001
PYARCHINIT_WEB_DEBUG=true     # Default: true

# Example
PYARCHINIT_WEB_PORT=8080 PYARCHINIT_WEB_DEBUG=false pyarchinit-mini-web
```

#### `pyarchinit-mini-gui`
Desktop GUI application (requires PyQt5)
```bash
pyarchinit-mini-gui
```

### Setup & Configuration

#### `pyarchinit-mini-setup`
Setup user environment in ~/.pyarchinit_mini
```bash
pyarchinit-mini-setup

# Creates: data/, media/, export/, backup/, config/, logs/
# Copies sample database and default configuration
```

#### `pyarchinit-mini-init`
Initialize database and create admin user
```bash
pyarchinit-mini-init                    # Interactive setup
pyarchinit-mini-init --non-interactive  # Use defaults (admin/admin)
```

#### `pyarchinit-mini-configure-claude`
Configure Claude Desktop MCP integration (requires uvx)
```bash
pyarchinit-mini-configure-claude
pyarchinit-mini-configure-claude --force   # Force reconfigure
pyarchinit-mini-configure-claude --silent  # No output
```

#### `pyarchinit-mini-migrate`
Run database migrations
```bash
pyarchinit-mini-migrate --database-url "sqlite:///my_db.db"
```

### MCP Servers

#### `pyarchinit-mini-mcp` / `pyarchinit-mcp-server`
MCP server (stdio transport) for Claude Desktop
```bash
# Configured automatically via pyarchinit-mini-configure-claude
pyarchinit-mini-mcp
```

#### `pyarchinit-mini-mcp-http` / `pyarchinit-mcp-http`
MCP server (HTTP transport) for ChatGPT and web clients
```bash
# Configuration via environment variables
MCP_HOST=localhost    # Default: localhost
MCP_PORT=8080         # Default: 8080
MCP_TRANSPORT=sse     # Default: sse

# Example
MCP_PORT=9000 pyarchinit-mini-mcp-http
```

### Data Import/Export

#### `pyarchinit-export-import`
Export/import data to/from Excel and CSV
```bash
# Subcommands: export-sites, export-us, export-inventario

# Export sites to Excel
pyarchinit-export-import export-sites -f excel -o sites.xlsx

# Export US to CSV for specific site
pyarchinit-export-import export-us -f csv -o us.csv -s "Pompei"

# Export inventory
pyarchinit-export-import export-inventario -f excel -o inventory.xlsx

# Options:
#   -f, --format [excel|csv]   Output format (default: csv)
#   -o, --output PATH          Output file path (required)
#   -s, --site TEXT            Filter by site name
#   -d, --database-url TEXT    Database connection
```

#### `pyarchinit-graphml`
Convert Graphviz DOT files to yEd GraphML format
```bash
# Subcommands: convert, template

# Convert DOT to GraphML
pyarchinit-graphml convert harris.dot output.graphml -t "Pompei"

# Download yEd template
pyarchinit-graphml template my_palette.graphml

# Options (convert):
#   -t, --title TEXT      Diagram title
#   --reverse-epochs      Reverse epoch ordering
#   -v, --verbose         Verbose output
```

#### `pyarchinit-mini-import`
Import from PyArchInit (full version) database
```bash
# Import all data from PyArchInit SQLite
pyarchinit-mini-import import-from-pyarchinit \
  -s sqlite:////path/to/pyarchinit.db

# Import specific tables with filters
pyarchinit-mini-import import-from-pyarchinit \
  -s postgresql://user:pass@host/db \
  -T sites -T us --sites "Pompei" --dry-run

# Options:
#   -s, --source-db TEXT       Source database URL (required)
#   -t, --target-db TEXT       Target database URL
#   -T, --tables [sites|us|inventario|periodizzazione|thesaurus|all]
#                              Tables to import (multiple allowed)
#   --sites TEXT               Filter by site names (multiple allowed)
#   --import-relationships     Import US relationships (default: yes)
#   --dry-run                  Preview without changes
```

#### `pyarchinit-harris-import`
Import Harris Matrix from Excel/CSV files
```bash
# Import Harris Matrix
pyarchinit-harris-import matrix.xlsx -s "Pompei"

# Import with GraphML and DOT export
pyarchinit-harris-import matrix.csv -s "Rome" -g -d -o ./exports

# Arguments:
#   FILE_PATH                  Excel or CSV file

# Options:
#   -s, --site TEXT            Site name (required)
#   -g, --export-graphml       Export to GraphML format
#   -d, --export-dot           Export to DOT format
#   -o, --output-dir TEXT      Output directory (default: current)
#   --db TEXT                  Database URL

# File Structure Required:
#   Sheet 1 (NODES):         us_number, unit_type, description, area, period, phase
#   Sheet 2 (RELATIONSHIPS): from_us, to_us, relationship
```

#### `pyarchinit-harris-template`
Generate Harris Matrix Excel/CSV template
```bash
# Generate template (creates harris_matrix_template.xlsx)
pyarchinit-harris-template

# Custom filename and format
pyarchinit-harris-template -f xlsx -o metro_c_template

# Options:
#   -f, --format [xlsx|csv]    Template format (default: xlsx)
#   -o, --output TEXT          Filename WITHOUT extension (default: harris_matrix_template)
#   -e, --with-examples        Include example data (default: yes)

# Complete Workflow:
#   1. Generate template:      pyarchinit-harris-template -o my_template
#   2. Fill in your data:      Edit my_template.xlsx with your US data
#   3. Import to database:     pyarchinit-harris-import my_template.xlsx -s "Site Name"
```

### Getting Help

View complete command reference anytime:
```bash
pyarchinit-mini --list-commands
```

View help for specific commands:
```bash
pyarchinit-export-import --help
pyarchinit-harris-import --help
pyarchinit-graphml --help
```

---

## 📚 Dependencies Structure

### Core (Always Installed)
- **FastAPI + Uvicorn**: REST API framework
- **SQLAlchemy**: ORM and database abstraction
- **psycopg2-binary**: PostgreSQL driver
- **Pydantic**: Data validation
- **NetworkX**: Harris Matrix generation
- **ReportLab**: PDF generation
- **Pillow**: Image processing

### Optional Extras

| Extra | Components | Installation |
|-------|-----------|--------------|
| `cli` | Click, Rich, Inquirer | `pip install 'pyarchinit-mini[cli]'` |
| `web` | Flask, WTForms, Jinja2, Flask-SocketIO | `pip install 'pyarchinit-mini[web]'` |
| `gui` | (Tkinter is in stdlib) | `pip install 'pyarchinit-mini[gui]'` |
| `harris` | Matplotlib, Graphviz | `pip install 'pyarchinit-mini[harris]'` |
| `pdf` | WeasyPrint | `pip install 'pyarchinit-mini[pdf]'` |
| `media` | python-magic, moviepy | `pip install 'pyarchinit-mini[media]'` |
| `export` | pandas, openpyxl | `pip install 'pyarchinit-mini[export]'` |
| `auth` | passlib, bcrypt, python-jose, flask-login | `pip install 'pyarchinit-mini[auth]'` |
| `all` | All of the above | `pip install 'pyarchinit-mini[all]'` |
| `dev` | pytest, black, mypy, flake8 | `pip install 'pyarchinit-mini[dev]'` |

---

## ⚙️ Configuration

### Database Configuration

Edit `~/.pyarchinit_mini/config/config.yaml`:

```yaml
database:
  # SQLite (default)
  url: "sqlite:///~/.pyarchinit_mini/data/pyarchinit_mini.db"

  # Or PostgreSQL
  # url: "postgresql://user:password@localhost:5432/pyarchinit"

api:
  host: "0.0.0.0"
  port: 8000
  reload: true

web:
  host: "0.0.0.0"
  port: 5001
  debug: true

media:
  base_dir: "~/.pyarchinit_mini/media"
  max_upload_size: 104857600  # 100MB

export:
  base_dir: "~/.pyarchinit_mini/export"
  pdf_dpi: 300

backup:
  enabled: true
  frequency: "daily"
  keep_count: 7
```

### Environment Variables

Alternatively, use environment variables:

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/pyarchinit"
export PYARCHINIT_WEB_PORT=5001
export PYARCHINIT_API_PORT=8000
```

---

## 🎯 Key Features in Detail

### Web Interface
- **Complete Forms**: US (49 fields/6 tabs), Inventario (37 fields/8 tabs)
- **Thesaurus Integration**: ICCD-compliant controlled vocabularies
- **Harris Matrix Viewer**: Interactive Graphviz visualization with 4 grouping modes
- **Validation Tools**: Stratigraphic paradox/cycle detection with auto-fix
- **Database Management**: Upload SQLite files, connect to PostgreSQL
- **PDF Export**: One-click export for Sites, US, Inventario with Harris Matrix

### Desktop GUI
- **Native Tkinter Application**: Full-featured desktop interface
- **Identical to Web**: Same 49-field US and 37-field Inventario forms
- **Offline Capable**: Works without internet connection
- **Cross-Platform**: Windows, Linux, macOS

### REST API
- **FastAPI Framework**: Modern, fast, async-capable
- **Auto Documentation**: Swagger UI at `/docs`, ReDoc at `/redoc`
- **Validation**: Automatic request/response validation
- **Scalable**: Production-ready with Uvicorn

### Harris Matrix
- **Graphviz Engine**: Professional orthogonal layout
- **4 Grouping Modes**:
  - `period_area`: Group by period and area
  - `period`: Group by period only
  - `area`: Group by area only
  - `none`: No grouping
- **High Resolution**: 300 DPI export for publications
- **PDF Integration**: Embedded in site reports

### Stratigraphic Validation
- **Paradox Detection**: Find logical impossibilities in stratigraphic relationships
- **Cycle Detection**: Identify circular dependencies
- **Reciprocal Check**: Verify bidirectional relationships
- **Auto-Fix**: One-click correction for missing reciprocals

### Export/Import
- **Web Interface**: Navigate to Export/Import page for visual interface
- **Desktop GUI**: Menu → Strumenti → Export/Import Dati
- **CLI Commands**:
  ```bash
  # Export to Excel/CSV
  pyarchinit-export-import export-sites -f excel -o sites.xlsx
  pyarchinit-export-import export-us -f csv -s "SiteName" -o us.csv
  pyarchinit-export-import export-inventario -f excel -o inventario.xlsx

  # Import from CSV
  pyarchinit-export-import import-sites sites.csv
  pyarchinit-export-import import-us --skip-duplicates us.csv
  pyarchinit-export-import import-inventario --no-skip-duplicates inv.csv
  ```
- **Features**:
  - Optional site filtering for US and Inventario exports
  - Skip duplicates option (default: enabled)
  - Import statistics (imported, skipped, errors)
  - Comprehensive error reporting

### Multi-User Authentication (v1.0.8)

Complete authentication system with role-based access control for Web and API interfaces.

#### User Roles

| Role | Permissions | Description |
|------|-------------|-------------|
| **Admin** | Full access + user management | Can create/edit/delete data and manage users |
| **Operator** | Create, Read, Update, Delete data | Can modify archaeological data but not users |
| **Viewer** | Read-only access | Can view data but cannot modify |

#### Setup Authentication

1. **Install with authentication support**:
   ```bash
   pip install 'pyarchinit-mini[auth]'
   # or
   pip install 'pyarchinit-mini[all]'
   ```

2. **Create users table and default admin**:
   ```bash
   python -m pyarchinit_mini.scripts.setup_auth
   ```

   This creates:
   - Users table in database
   - Default admin user (username: `admin`, password: `admin`)

3. **Change default password** (IMPORTANT):
   ```bash
   # Login to web interface at http://localhost:5001/auth/login
   # Navigate to Users → Edit admin user → Change password
   ```

#### Web Interface Authentication

- **Login page**: `http://localhost:5001/auth/login`
- **Default credentials**: username=`admin`, password=`admin`
- **User management**: Admin users can create/edit/delete users via the Users menu
- **Protected routes**: All web pages require authentication
- **Session management**: Uses Flask-Login with secure session cookies

#### API Authentication

- **JWT tokens**: Use `POST /api/auth/login` to get access token
- **Token usage**: Include in `Authorization: Bearer <token>` header
- **Token expiration**: 30 minutes (configurable)

Example:
```bash
# Get token
curl -X POST http://localhost:8000/api/auth/login \
  -d "username=admin&password=admin"

# Use token
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/sites
```

#### User Management

Admins can manage users via:
- **Web Interface**: Users menu (admin only)
- **API Endpoints**:
  - `POST /api/auth/register` - Create user (admin only)
  - `GET /api/auth/users` - List all users (admin only)
  - `PUT /api/auth/users/{id}` - Update user (admin only)
  - `DELETE /api/auth/users/{id}` - Delete user (admin only)

#### Permissions

| Permission | Admin | Operator | Viewer |
|------------|-------|----------|--------|
| View data | ✓ | ✓ | ✓ |
| Create data | ✓ | ✓ | ✗ |
| Edit data | ✓ | ✓ | ✗ |
| Delete data | ✓ | ✓ | ✗ |
| Manage users | ✓ | ✗ | ✗ |
| Export data | ✓ | ✓ | ✓ |
| Import data | ✓ | ✓ | ✗ |

---

## 💾 Database Management

### Why `~/.pyarchinit_mini`?
- **Persistence**: Data survives virtualenv removal
- **Easy Backup**: Single directory to backup
- **Multi-Project**: Same database accessible from different virtualenvs
- **Standard Convention**: Follows Unix/Linux conventions

### Database Options

#### SQLite (Default)
```bash
# Automatic setup
pyarchinit-mini-setup
```

Database created at: `~/.pyarchinit_mini/data/pyarchinit_mini.db`

#### PostgreSQL
```yaml
# config.yaml
database:
  url: "postgresql://user:password@localhost:5432/pyarchinit"
```

#### Upload Existing Database
Use the web interface:
1. Navigate to **Database** → **Upload Database**
2. Select your `.db` file from PyArchInit Desktop
3. Database is validated and copied to `~/.pyarchinit_mini/databases/`

---

## 🧪 Development

### Run from Source
```bash
git clone https://github.com/enzococca/pyarchinit-mini.git
cd pyarchinit-mini
pip install -e '.[dev]'
```

### Run Tests
```bash
pytest
pytest --cov=pyarchinit_mini
```

### Code Quality
```bash
black pyarchinit_mini/
isort pyarchinit_mini/
flake8 pyarchinit_mini/
mypy pyarchinit_mini/
```

---

## 📖 Documentation

- **API Docs**: http://localhost:8000/docs (after starting API server)
- **User Guide**: https://pyarchinit-mini.readthedocs.io
- **CHANGELOG**: https://pyarchinit-mini.readthedocs.io/en/latest/development/changelog.html
- **Quick Start**: https://pyarchinit-mini.readthedocs.io/en/latest/installation/quickstart.html

---

## 🐛 Troubleshooting

### Command Not Found After Installation
```bash
# Verify installation
pip show pyarchinit-mini

# On Linux/Mac, ensure pip bin directory is in PATH
export PATH="$HOME/.local/bin:$PATH"

# On Windows, commands are in:
# C:\Users\<username>\AppData\Local\Programs\Python\PythonXX\Scripts\
```

### Database Not Found
```bash
# Re-run setup
pyarchinit-mini-setup

# Or manually specify database URL
export DATABASE_URL="sqlite:///path/to/your/database.db"
```

### Tkinter Not Available (Linux)
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# Fedora/RHEL
sudo dnf install python3-tkinter

# Arch Linux
sudo pacman -S tk
```

### Graphviz Not Found
```bash
# macOS
brew install graphviz

# Ubuntu/Debian
sudo apt-get install graphviz

# Windows
# Download from https://graphviz.org/download/
```

### Port Already in Use
```bash
# Change web interface port
export PYARCHINIT_WEB_PORT=5002
pyarchinit-web

# Change API port
export PYARCHINIT_API_PORT=8001
pyarchinit-api
```

---

## 🗺️ Roadmap

### Recently Completed (v1.1.5)
- [x] **EM_palette Node Styling** - Automatic colors and shapes based on `unita_tipo` (US, USM, USD, USV, USV/s)
- [x] **Archaeological Metadata** - Node descriptions with `d_stratigrafica` + `d_interpretativa` visible in yEd
- [x] **Clean Edge Display** - Edges without text labels, relationship types in tooltips
- [x] **PyArchInit Edge Convention** - Contemporary (no arrow), stratigraphic (arrow), negative (dashed)
- [x] **GraphML Description Field** - Proper injection into yEd `<data key="d5">` element
- [x] **Transitive Reduction** - Automatic removal of redundant stratigraphic relationships

### Completed in v1.1.3
- [x] **GraphML Converter** - Export Harris Matrix to yEd Graph Editor compatible format
- [x] **Multi-Interface Export** - Python API, CLI, REST API, Web UI, Desktop GUI support
- [x] **Period Preservation** - Automatic archaeological periods with color coding
- [x] **Flexible Grouping** - Period+area, period, area, or no grouping modes
- [x] **yEd Template** - Custom template (EM_palette.graphml) for consistent styling
- [x] **Standalone Library** - Reusable in other projects via pip install

### Completed in v1.1.2
- [x] **Mobile & Tablet Optimization** - Complete responsive design for phones and tablets
- [x] **Touch-Friendly Interface** - 44px minimum button height (iOS/Android guidelines)
- [x] **Mobile Card View** - Tables converted to cards on mobile (< 768px)
- [x] **Responsive Breakpoints** - Mobile (<768px), Tablet (768-991px), Desktop (≥992px)
- [x] **iOS/Android Optimized** - 16px font prevents auto-zoom, optimized touch targets
- [x] **Print Styles** - Clean print layout for reports

### Completed in v1.1.1
- [x] **Full Edit Functionality** - Complete edit support for Sites, US, and Inventario in Web interface
- [x] **37 Inventario Fields Editable** - All 37 fields across 8 tabs fully editable
- [x] **49 US Fields Editable** - All 49 fields across 6 tabs fully editable
- [x] **Form Pre-population** - Forms automatically filled with existing data for editing
- [x] **Session Management Fix** - Resolved SQLAlchemy detached instance errors

### Completed in v1.1.0
- [x] **Analytics Dashboard** - Interactive charts and data visualization
- [x] **8 Chart Types** - Pie, bar, horizontal bar, and doughnut charts
- [x] **Geographic Analysis** - Sites distribution by region and province
- [x] **Chronological Analysis** - US distribution by period
- [x] **Typological Analysis** - US and inventory items by type
- [x] **Conservation Analysis** - Inventory items by conservation state
- [x] **Multi-Interface Charts** - Web UI (Chart.js) and Desktop GUI (matplotlib)

### Completed in v1.0.9
- [x] **Real-time collaboration** - WebSocket support with Flask-SocketIO
- [x] **Live notifications** - Toast notifications for all CRUD operations
- [x] **Online user presence** - See who's currently connected
- [x] **Activity tracking** - Real-time updates when users create/edit/delete data
- [x] **User join/leave events** - Team collaboration awareness

### Completed in v1.0.8
- [x] **Multi-user authentication** - Role-based access control (Admin, Operator, Viewer)
- [x] **JWT authentication** - Secure API access with JSON Web Tokens
- [x] **User management** - Admin interface for creating/editing/deleting users
- [x] **Protected routes** - All web routes require authentication
- [x] **Password security** - Bcrypt hashing for secure password storage

### Completed in v1.0.7
- [x] **Export to Excel/CSV** - Sites, US, Inventario export
- [x] **Batch import from CSV** - With validation and duplicate handling
- [x] **Multi-interface export/import** - Web UI, Desktop GUI, and CLI

### Completed in v1.5.4 (2025-10-26)
- [x] **Advanced Search System** - Multi-field filtering (site, area, unit type, year, US number)
- [x] **Record Navigation** - Prev/Next buttons directly in edit forms with position counter
- [x] **Filtered PDF Export** - Export only filtered results based on active search criteria
- [x] **Filtered Harris Matrix Export** - GraphML export with subgraph containing only filtered nodes
- [x] **Session-Based Filters** - Filter persistence across navigation for consistent workflow
- [x] **Smart Export Buttons** - Context-aware buttons with filter badges showing filtered record count

### Completed in v1.9.10+ (November 2025)
- [x] **Model Context Protocol (MCP) Server** - AI integration for Claude Desktop and ChatGPT
- [x] **3D Web Viewer** - Interactive Three.js visualization with chat interface
- [x] **Blender Integration** - Real-time streaming and professional 3D model creation
- [x] **AI-Powered Reconstruction** - Automated site reconstruction with specialized agents
- [x] **Natural Language Commands** - Chat-based 3D model generation and filtering
- [x] **MCP Tools & Resources** - 5 tools, 5 resources, 3 prompts for AI assistants
- [x] **Comprehensive Documentation** - Step-by-step guides for MCP, 3D Viewer, and Blender

### Upcoming Features
- [ ] **3D Viewer Enhancements**:
  - [ ] Advanced camera controls (fly mode, walk mode)
  - [ ] Section cutting/clipping planes
  - [ ] Measurement tools
  - [ ] VR/AR support for immersive viewing
  - [ ] Collaborative 3D viewing (multi-user)
- [ ] **Blender Interoperability**:
  - [ ] Bidirectional sync (edit in Blender, update PyArchInit)
  - [ ] Texture baking from archaeological photos
  - [ ] Animation export for presentations
  - [ ] USD format support for universal interchange
- [ ] **MCP Tools Expansion**:
  - [ ] Relationship analysis tool
  - [ ] Chronology validation tool
  - [ ] Bulk operations tool
  - [ ] Search and query tool
  - [ ] Statistics and reporting tool
- [ ] **General Improvements**:
  - [ ] Docker containerization
  - [ ] Cloud deployment guides (AWS, Azure, GCP)
  - [ ] Offline mode support
  - [ ] Advanced search for Inventory module (following US implementation pattern)
  - [ ] Mobile app (iOS/Android) for field data entry

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup
```bash
git clone https://github.com/enzococca/pyarchinit-mini.git
cd pyarchinit-mini
pip install -e '.[dev]'
pre-commit install  # Optional: install pre-commit hooks
```

### Documentation Verification System

PyArchInit-Mini includes an automated system to ensure documentation quality and consistency:

**Features:**
- ✅ **Version Alignment**: Automatically checks that versions match across `pyproject.toml`, `docs/conf.py`, and `CHANGELOG.md`
- ✅ **Language Consistency**: Verifies documentation is in English
- ✅ **ReadTheDocs Readiness**: Validates configuration and buildability
- ✅ **Changelog Updates**: Ensures each version has proper changelog entry

**Quick Usage:**

```bash
# Run verification
python scripts/verify_docs.py

# Auto-fix version misalignments
python scripts/verify_docs.py --fix

# Install pre-commit hooks (runs verification before each commit)
bash scripts/setup_pre_commit.sh
```

**Before Publishing a New Version:**

```bash
# 1. Update version in pyproject.toml
# 2. Run auto-fix to sync all version numbers
python scripts/verify_docs.py --fix

# 3. Update CHANGELOG.md with new version entry
# 4. Verify everything is aligned
python scripts/verify_docs.py

# 5. Commit and push (pre-commit hook will run automatically)
git add pyproject.toml docs/conf.py CHANGELOG.md
git commit -m "chore: Bump version to X.Y.Z"
git push

# 6. Build and publish to PyPI
python -m build
twine upload dist/*
```

**Documentation:** See [Contributing Guide](https://pyarchinit-mini.readthedocs.io/en/latest/development/contributing.html) for complete guide.

**CI/CD:** GitHub Actions automatically runs verification on every push and pull request.

---

## 📄 License

This project is licensed under the GNU General Public License v2.0 - see the [LICENSE](LICENSE) file for details.

---

## 💬 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/enzococca/pyarchinit-mini/issues)
- **Email**: enzo.ccc@gmail.com
- **PyPI**: [pypi.org/project/pyarchinit-mini](https://pypi.org/project/pyarchinit-mini/)

---

## 🙏 Acknowledgments

- **PyArchInit Team**: Original desktop application developers
- **Archaeological Community**: Feedback and feature requests
- **Open Source Contributors**: Libraries and tools that make this possible

---


**Made with ❤️ for the Archaeological Community**

## s3dgraphy integration

Since 2.2.0-alpha, pyarchinit-mini-web reads the canonical Extended Matrix
vocabulary (unit types, edge types, visual styles) from the
[s3dgraphy](https://github.com/zalmoxes-laran/s3dgraphy) package's JSON
catalogues. Unit types like `US`, `USVs`, `USVn`, `RSF`, `USM` come from
`s3Dgraphy_node_datamodel.json` (v1.5.4 at time of writing).

Bumping s3dgraphy (`pip install --upgrade s3dgraphy`) makes new EM types
immediately available in form selects without any pyarchinit-mini code change.

After upgrading, run the data alignment to update legacy records:

```bash
pyarchinit-mini-migrate-vocab --dry-run    # preview changes
pyarchinit-mini-migrate-vocab --apply      # backup + migrate
```

See `docs/CLI_MIGRATE_VOCAB.md` for the full CLI reference.

The vocab is exposed to the browser via:

- `GET /api/v1/vocab/unit-types?lang=it`
- `GET /api/v1/vocab/unit-types/<abbr>`
- `GET /api/v1/vocab/edge-types?lang=it`
- `GET /api/v1/vocab/visual-style/<unit_type>`
- `GET /api/v1/vocab/diagnostics` (admin-only)

## Graph projection & paradata

Since 2.3.0-alpha, pyarchinit-mini-web auto-generates the stratigraphic graph
as a GraphML file every time you save a US/USM record. Output lives at
`data/paradata/<site_slug>/stratigraphy.graphml`.

Paradata (authors, licenses, embargoes, documents, epochs) are stored in a
JSON sidecar:
```
data/paradata/<site_slug>/paradata.json
```
because s3dgraphy 0.1.42's GraphML exporter does not round-trip standalone
paradata nodes. The JSON sidecar IS committed to git.

### Paradata editing

Visit `/paradata/<site>/{authors,licenses,embargoes,documents,epochs}` to
manage paradata. REST endpoints under `/api/v1/paradata/<site>/...` mirror
the UI. See `docs/PARADATA_GUIDE.md`.

### Graph import

`/sites/<site>/graph/import-preview` accepts a GraphML upload; you see a
preview of planned INSERT/UPDATE/SKIP and must confirm via
`/sites/<site>/graph/import-apply` before any DB write.

### Auto-regen control

- Disable globally: `export PYARCHINIT_DISABLE_AUTO_REGEN=1`
- Disable during bulk ops: `with graphproj.auto_regen.disable_regen():`

See `docs/GRAPH_AUTO_REGEN.md`.

## Harris Swimlane Editor

Since 2.4.0, the Harris Matrix Creator at `/harris-creator/editor`
displays stratigraphic graphs with **yEd-like swimlanes** — horizontal
rows representing periods+phases. Existing US records are auto-placed
in their row based on `periodo_iniziale + fase_iniziale`. Users can
drag US records between rows, create new rows interactively, and save
back to the DB.

Row source priority:
1. `period_table` (formal definitions)
2. Fallback: distinct `(periodo_iniziale, fase_iniziale)` from
   `periodizzazione_table` + `us_table`

### Two GraphML outputs

- `data/paradata/<site>/stratigraphy.graphml` (Spec 2, auto-regen):
  s3dgraphy clean, EM-canonical, for the EM Datacenter
- `data/exports/harris_yed/<site>-harris-yed.graphml` (Spec 3-bis,
  on-demand): yEd-flavored with `y:TableNode`, for users editing in
  yEd Desktop

### Auto-regen integration

Save endpoint also triggers Spec 2's auto_regen for
`stratigraphy.graphml`, keeping the canonical output consistent with
DB state.

See `docs/HARRIS_SWIMLANE.md` and `docs/YED_INTEGRATION.md`.