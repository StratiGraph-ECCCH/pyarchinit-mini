"""
PyArchInit-Mini: Standalone Archaeological Data Management System

A lightweight, modular version of PyArchInit focused on core archaeological
data management functionality without GIS dependencies.

Features:
- Site management with complete CRUD operations
- Stratigraphic Unit (US) management (49 fields, 6 tabs)
- Material inventory management (37 fields, 8 tabs, ICCD thesaurus)
- Harris Matrix generation (Matplotlib + Graphviz with 4 grouping modes)
- Stratigraphic validation (paradoxes, cycles, auto-fix)
- Multi-database support (PostgreSQL/SQLite upload/connect)
- PDF export (Sites, US, Inventario, Harris Matrix)
- Excel/CSV export and batch import
- Multi-user authentication with role-based permissions (Admin, Operator, Viewer)
- Real-time collaboration with WebSocket notifications (Flask-SocketIO)
- Analytics dashboard with 8 chart types (Chart.js for web, matplotlib for desktop)
- REST API interface (FastAPI with JWT authentication)
- Web UI interface (Flask with session-based auth) - 100% Desktop GUI parity
- Desktop GUI interface (Tkinter)
- CLI interface
- Scalable and modular architecture
"""

__version__ = "3.4.0"
__author__ = "PyArchInit Team"
__email__ = "enzo.ccc@gmail.com"

from .database.manager import DatabaseManager
from .services.site_service import SiteService
from .services.us_service import USService
from .services.inventario_service import InventarioService

__all__ = [
    "DatabaseManager",
    "SiteService", 
    "USService",
    "InventarioService"
]