.. image:: _static/images/pyarchinit-mini-logo.png
   :align: center
   :width: 300px
   :alt: PyArchInit-Mini Logo

PyArchInit-Mini Documentation
=============================

.. image:: https://badge.fury.io/py/pyarchinit-mini.svg
   :target: https://badge.fury.io/py/pyarchinit-mini
   :alt: PyPI version

.. image:: https://img.shields.io/badge/python-3.8--3.14-blue.svg
   :target: https://www.python.org/downloads/
   :alt: Python versions

.. image:: https://img.shields.io/badge/License-GPL%20v2-blue.svg
   :target: https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html
   :alt: License

.. image:: https://readthedocs.org/projects/pyarchinit-mini/badge/?version=latest
   :target: https://pyarchinit-mini.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

**Lightweight Archaeological Data Management System**

PyArchInit-Mini is a standalone, modular version of PyArchInit focused on core archaeological data management functionality without GIS dependencies. It provides multiple interfaces (Web, Desktop GUI, CLI, REST API) with a clean, scalable architecture for managing archaeological sites, stratigraphic units, and material inventories.

Key Features
------------

- **Multi-Interface Support**: Web, Desktop GUI, CLI, and REST API
- **Multi-Database**: SQLite and PostgreSQL support
- **Internationalization**: Full Italian and English language support
- **Harris Matrix**: Graphviz visualization with GraphML export
- **Extended Matrix Framework**: 14 specialized unit types with custom workflows
- **3D Visualization**: s3Dgraphy integration for stratigraphic units
- **Multi-User Authentication**: Role-based access control
- **Real-Time Collaboration**: WebSocket support for team updates
- **Analytics Dashboard**: Interactive charts and data visualization
- **Python API**: Complete programmatic access for custom integrations

Quick Links
-----------

- :doc:`installation/quickstart` - Get started in 5 minutes
- :doc:`MCP_INTEGRATION` - AI Integration with Claude Desktop & ChatGPT (NEW!)
- :doc:`3D_VIEWER_GUIDE` - Interactive 3D visualization in browser (NEW!)
- :doc:`BLENDER_INTEGRATION` - Professional 3D modeling with Blender (NEW!)
- :doc:`python-api/overview` - Python API with integration examples
- :doc:`features/pyarchinit-import-export` - Import/Export from PyArchInit
- :doc:`features/extended-matrix-framework` - Extended Matrix 14 unit types
- :doc:`examples/python_api` - Complete code examples

What's New
----------

Version 1.9.23 - MCP Tools Expansion & AI Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 1.9.23

   **MCP (Model Context Protocol) Integration**:

   - ✨ **23 MCP Tools** for Claude Desktop & ChatGPT integration (expanded from 5)
   - ✨ **6 Tool Categories**: Data Management (8), Validation (3), Harris Matrix & 3D (4), Reports & Export (2), Media & Thesaurus (2), System (4)
   - ✨ **Advanced Validation**: Stratigraphic relationship validation with cycle detection
   - ✨ **Media Management**: 7 operations (list, upload, download, delete, get_info, search, update_metadata)
   - ✨ **Thesaurus Management**: 8 operations (list, get_values, add/update/delete, search, import/export)
   - ✨ **5 Resources**: GraphML, US, Periods, Relationships, Sites
   - ✨ **3 Prompts**: Stratigraphic Model, Period Visualization, US Description

   See :doc:`MCP_INTEGRATION` for complete AI integration guide.

Version 1.8.5 - Database Creation & Chronological Management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 1.7.0

   **Database Creation Features**:

   - ✨ Empty database creation (SQLite/PostgreSQL) with complete schema
   - ✨ Multi-interface support (CLI, Python API, Web GUI)
   - ✨ Automatic dating synchronization from US values
   - ✨ Periodization records viewer with advanced search

   See :doc:`features/database_creation` for complete documentation.

Version 1.8.5 - Extended Matrix & GraphML Export
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 1.6.0

   - ✨ Extensible EM node type system (YAML configuration)
   - ✨ Pure NetworkX GraphML export (no Graphviz dependency)
   - ✨ 14 built-in node types with custom extension support

   See :doc:`features/extended-matrix-framework` and :doc:`features/graphml-export-technical`.

.. toctree::
   :maxdepth: 1
   :caption: Release Notes
   :hidden:

   development/changelog

Getting Started
===============

New to PyArchInit-Mini? Start here for installation and basic setup.

.. toctree::
   :maxdepth: 2
   :caption: Installation & Setup

   installation/quickstart
   installation/requirements
   installation/configuration
   installation/first_steps

Tutorials
=========

Step-by-step tutorials with screenshots to get you started quickly.

.. toctree::
   :maxdepth: 2
   :caption: Interactive Tutorials

   tutorials/video_tutorial
   tutorials/installation_tutorial
   tutorials/web_interface_tutorial
   tutorials/desktop_gui_tutorial

User Guides
===========

Complete guides for using PyArchInit-Mini interfaces and features.

.. toctree::
   :maxdepth: 2
   :caption: Interface Guides

   web/index
   gui/index
   cli/index
   api/index

Core Features
=============

In-depth documentation for PyArchInit-Mini's main features.

Database Management
-------------------

.. toctree::
   :maxdepth: 2

   features/database_creation
   data/database_management
   data/migrations
   features/pyarchinit-import-export

Data Management
---------------

.. toctree::
   :maxdepth: 2

   data/sites
   data/stratigraphic_units
   data/inventory
   tomba
   tomba_service
   struttura
   struttura_service
   features/stratigraphic_relationships

Harris Matrix & Visualization
------------------------------

.. toctree::
   :maxdepth: 2

   features/harris_matrix
   features/harris_matrix_import
   features/extended-matrix-framework
   features/graphml_export
   features/graphml-export-technical
   features/s3dgraphy

AI Integration & 3D Visualization
----------------------------------

.. toctree::
   :maxdepth: 2

   MCP_INTEGRATION
   3D_VIEWER_GUIDE
   BLENDER_INTEGRATION

Import/Export & Integration
----------------------------

.. toctree::
   :maxdepth: 2

   features/pyarchinit_import_export
   features/export_import
   features/media_management

User Management & Analytics
----------------------------

.. toctree::
   :maxdepth: 2

   features/authentication
   features/analytics

Python API & Integration
=========================

Complete Python API documentation with integration examples for external projects.

.. toctree::
   :maxdepth: 2
   :caption: Python API

   python-api/overview

Examples & Tutorials
====================

Practical examples and step-by-step tutorials.

.. toctree::
   :maxdepth: 2
   :caption: Code Examples

   examples/python_api
   examples/rest_api
   examples/cli_usage
   examples/integration

Reference
=========

Technical reference and API documentation.

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   development/api_reference
   development/architecture

Development
===========

Contributing, testing, and development documentation.

.. toctree::
   :maxdepth: 2
   :caption: Developer Guides

   development/contributing
   development/testing
   development/changelog

Indices and Search
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
