==================
CLI Usage Examples
==================

PyArchInit-Mini provides several command-line interfaces for batch operations and automation.

.. contents:: Table of Contents
   :local:
   :depth: 2

Available Commands
==================

After installation, the following commands are available:

- ``pyarchinit-mini-web`` - Start web interface
- ``pyarchinit-mini-gui`` - Launch desktop GUI
- ``pyarchinit-export-import`` - Export/import data
- ``pyarchinit-graphml`` - GraphML export utilities


Web Interface
=============

Start the web server:

.. code-block:: bash

    # Default (port 5001)
    pyarchinit-mini-web

    # Custom port
    pyarchinit-mini-web --port 8080

    # Production mode
    pyarchinit-mini-web --host 0.0.0.0 --port 80

    # Custom database
    DATABASE_URL="postgresql://user:pass@localhost/db" pyarchinit-mini-web


Desktop GUI
===========

Launch the graphical interface:

.. code-block:: bash

    pyarchinit-mini-gui

    # With custom database
    DATABASE_URL="sqlite:///./my_project.db" pyarchinit-mini-gui


Export/Import
=============

Export Sites
------------

.. code-block:: bash

    # Export all sites to JSON
    pyarchinit-export-import export sites --output sites.json

    # Export specific site
    pyarchinit-export-import export sites --site "Pompei" --output pompei.json

    # Export with related data (US + Inventory)
    pyarchinit-export-import export sites --site "Pompei" --include-related --output pompei_full.json


Export US
---------

.. code-block:: bash

    # Export all US for a site
    pyarchinit-export-import export us --site "Pompei" --output pompei_us.json

    # Export specific US range
    pyarchinit-export-import export us --site "Pompei" --from-us 1000 --to-us 2000 --output us_range.json

    # Export with media files
    pyarchinit-export-import export us --site "Pompei" --include-media --output pompei_us_media.zip


Export Inventory
----------------

.. code-block:: bash

    # Export all inventory
    pyarchinit-export-import export inventory --site "Pompei" --output inventory.json

    # Filter by type
    pyarchinit-export-import export inventory --site "Pompei" --type "Ceramica" --output ceramics.json


Import Data
-----------

.. code-block:: bash

    # Import sites
    pyarchinit-export-import import sites --input sites.json

    # Import with update on conflict
    pyarchinit-export-import import sites --input sites.json --update-existing

    # Import US
    pyarchinit-export-import import us --input us_data.json

    # Import inventory
    pyarchinit-export-import import inventory --input inventory.json


GraphML Export
==============

Generate Harris Matrix
----------------------

.. code-block:: bash

    # Generate GraphML for site
    pyarchinit-graphml generate --site "Pompei" --output pompei_matrix.graphml

    # With Extended Matrix palette
    pyarchinit-graphml generate --site "Pompei" --palette extended_matrix --output pompei_em.graphml

    # Include metadata
    pyarchinit-graphml generate --site "Pompei" --include-metadata --output pompei_full.graphml


Batch Operations
----------------

.. code-block:: bash

    # Generate matrices for all sites
    pyarchinit-graphml batch --output-dir matrices/

    # With custom layout
    pyarchinit-graphml batch --layout vertical --output-dir matrices_vertical/


Database Management
===================

Migrations
----------

.. code-block:: bash

    # Run pending migrations
    pyarchinit-mini-web migrate

    # Show migration status
    pyarchinit-mini-web migrate --status

    # Rollback last migration
    pyarchinit-mini-web migrate --rollback


Backup
------

.. code-block:: bash

    # Create SQLite backup
    cp pyarchinit_mini.db pyarchinit_mini_backup_$(date +%Y%m%d).db

    # PostgreSQL backup
    pg_dump -U postgres archaeology_db > backup_$(date +%Y%m%d).sql


Automation Scripts
==================

Bash Script Example
-------------------

.. code-block:: bash

    #!/bin/bash
    # Daily backup and export script

    DATE=$(date +%Y%m%d)
    BACKUP_DIR="/backups/$DATE"
    mkdir -p "$BACKUP_DIR"

    # Backup database
    cp pyarchinit_mini.db "$BACKUP_DIR/database.db"

    # Export all sites
    pyarchinit-export-import export sites --output "$BACKUP_DIR/sites.json"

    # Export each site individually with full data
    for site in $(pyarchinit-export-import list-sites); do
        echo "Exporting $site..."
        pyarchinit-export-import export sites \
            --site "$site" \
            --include-related \
            --output "$BACKUP_DIR/${site}_full.json"

        # Generate Harris Matrix
        pyarchinit-graphml generate \
            --site "$site" \
            --output "$BACKUP_DIR/${site}_matrix.graphml"
    done

    # Create archive
    tar -czf "/backups/backup_$DATE.tar.gz" "$BACKUP_DIR"

    # Cleanup old backups (keep last 30 days)
    find /backups -name "backup_*.tar.gz" -mtime +30 -delete

    echo "Backup complete: backup_$DATE.tar.gz"


Python Automation
-----------------

.. code-block:: python

    #!/usr/bin/env python3
    """
    Automated weekly report generation
    """
    import subprocess
    import datetime
    from pathlib import Path

    def generate_weekly_report():
        """Generate reports for all sites"""
        today = datetime.date.today()
        week = today.strftime("%Y-W%W")

        output_dir = Path(f"reports/{week}")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get list of sites
        result = subprocess.run(
            ["pyarchinit-export-import", "list-sites"],
            capture_output=True,
            text=True
        )
        sites = result.stdout.strip().split('\n')

        for site in sites:
            print(f"Processing {site}...")

            # Export data
            subprocess.run([
                "pyarchinit-export-import", "export", "sites",
                "--site", site,
                "--include-related",
                "--output", str(output_dir / f"{site}_data.json")
            ])

            # Generate matrix
            subprocess.run([
                "pyarchinit-graphml", "generate",
                "--site", site,
                "--output", str(output_dir / f"{site}_matrix.graphml")
            ])

            # Generate PDF report (custom script)
            subprocess.run([
                "python", "generate_pdf_report.py",
                "--site", site,
                "--output", str(output_dir / f"{site}_report.pdf")
            ])

        print(f"Weekly report generated in {output_dir}")

    if __name__ == "__main__":
        generate_weekly_report()


Cron Jobs
---------

Add to crontab (``crontab -e``):

.. code-block:: bash

    # Daily backup at 2 AM
    0 2 * * * /path/to/daily_backup.sh

    # Weekly report every Monday at 9 AM
    0 9 * * 1 python3 /path/to/weekly_report.py

    # Monthly full export on 1st of month
    0 0 1 * * pyarchinit-export-import export sites --include-related --output /archives/monthly_$(date +\%Y\%m).json


Environment Variables
=====================

Configure via environment variables:

.. code-block:: bash

    # Database
    export DATABASE_URL="postgresql://user:pass@localhost/archaeology"

    # Upload directory
    export UPLOAD_FOLDER="/data/uploads"

    # Secret key
    # generate one: python -c 'import secrets; print(secrets.token_urlsafe(48))'
    export PYARCHINIT_SESSION_KEY="<48 random bytes, url-safe>"

    # Debug mode
    export DEBUG=1

    # Language
    export BABEL_DEFAULT_LOCALE=it

    # Use in scripts
    DATABASE_URL="sqlite:///./test.db" pyarchinit-mini-web


Docker Usage
============

Using Docker Compose:

.. code-block:: bash

    # Start all services
    docker-compose up -d

    # View logs
    docker-compose logs -f web

    # Run migrations
    docker-compose exec web python -m pyarchinit_mini.database.migrations

    # Export data
    docker-compose exec web pyarchinit-export-import export sites --output /data/sites.json

    # Stop services
    docker-compose down


Advanced CLI Usage
==================

Combining Commands
------------------

.. code-block:: bash

    # Export and immediately convert to GraphML
    pyarchinit-export-import export us --site "Pompei" --output - | \
        pyarchinit-graphml convert --input - --output pompei.graphml

    # Filter and export
    pyarchinit-export-import export us --site "Pompei" --output - | \
        jq '.[] | select(.unita_tipo == "USM")' > walls.json


Parallel Processing
-------------------

.. code-block:: bash

    # Export multiple sites in parallel
    for site in Pompei Ercolano Ostia; do
        pyarchinit-export-import export sites --site "$site" --output "${site}.json" &
    done
    wait

    echo "All exports complete"


Monitoring
----------

.. code-block:: bash

    # Watch export progress
    watch -n 1 'du -sh exports/*.json'

    # Monitor database size
    watch -n 5 'ls -lh pyarchinit_mini.db'


Integration with Other Tools
============================

QGIS Integration
----------------

Export for QGIS:

.. code-block:: bash

    # Export as GeoJSON (if coordinates available)
    pyarchinit-export-import export sites --format geojson --output sites.geojson


yEd Integration
---------------

.. code-block:: bash

    # Export GraphML for yEd Graph Editor
    pyarchinit-graphml generate --site "Pompei" --palette extended_matrix --output pompei.graphml

    # Open in yEd
    yed pompei.graphml


Excel/LibreOffice
-----------------

.. code-block:: bash

    # Export as CSV
    pyarchinit-export-import export inventory --site "Pompei" --format csv --output inventory.csv

    # Import CSV
    pyarchinit-export-import import inventory --format csv --input data.csv


Troubleshooting
===============

Enable Verbose Output
---------------------

.. code-block:: bash

    pyarchinit-export-import export sites --verbose --output sites.json

Check Database Connection
-------------------------

.. code-block:: bash

    DATABASE_URL="your-url" python -c "from pyarchinit_mini.database.connection import DatabaseConnection; db = DatabaseConnection.from_url('$DATABASE_URL'); print('Connection OK')"

View Help
---------

.. code-block:: bash

    pyarchinit-export-import --help
    pyarchinit-graphml --help
    pyarchinit-mini-web --help
