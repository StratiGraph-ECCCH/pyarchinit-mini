"""
Database Creator Utility
Creates empty PyArchInit-Mini databases with full schema
Supports SQLite and PostgreSQL
"""

import os
import logging
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def _import_all_models():
    """
    Import all models to ensure they are registered with Base.metadata
    This must be called before create_all() to ensure all tables are created
    """
    from ..models.base import Base
    from ..models.site import Site
    from ..models.us import US
    from ..models.user import User
    from ..models.inventario_materiali import InventarioMateriali
    from ..models.harris_matrix import USRelationships, Periodizzazione, Period
    from ..models.datazione import Datazione
    from ..models.thesaurus import ThesaurusSigle, ThesaurusField, ThesaurusCategory
    from ..models.media import Media
    from ..models.tomba import Tomba  # noqa: F401
    from ..models.struttura import Struttura  # noqa: F401
    from ..models.fauna import Fauna  # noqa: F401

    return Base


def create_sqlite_database(db_path: str, overwrite: bool = False) -> Dict[str, Any]:
    """
    Create an empty SQLite database with full PyArchInit-Mini schema
    
    Args:
        db_path: Path where to create the SQLite database file
        overwrite: If True, overwrite existing database. If False, raise error if exists.
    
    Returns:
        Dictionary with creation statistics
        
    Raises:
        FileExistsError: If database already exists and overwrite=False
        SQLAlchemyError: If database creation fails
    """
    stats = {
        'success': False,
        'db_type': 'sqlite',
        'db_path': db_path,
        'tables_created': 0,
        'message': ''
    }
    
    try:
        # Expand user home directory and convert to absolute path
        db_path = os.path.abspath(os.path.expanduser(db_path))
        stats['db_path'] = db_path
        
        # Check if database already exists
        if os.path.exists(db_path):
            if not overwrite:
                raise FileExistsError(f"Database already exists: {db_path}")
            else:
                logger.warning(f"Overwriting existing database: {db_path}")
                os.remove(db_path)
        
        # Ensure parent directory exists
        parent_dir = os.path.dirname(db_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            logger.info(f"Created directory: {parent_dir}")
        
        # Create connection string
        connection_string = f"sqlite:///{db_path}"
        
        # Create engine
        engine = create_engine(connection_string, echo=False)
        
        # Import all models to register them with Base.metadata
        Base = _import_all_models()
        
        # Create all tables
        logger.info(f"Creating PyArchInit-Mini schema in SQLite database: {db_path}")
        Base.metadata.create_all(engine)
        
        # Count created tables
        stats['tables_created'] = len(Base.metadata.tables)
        
        # Verify database was created
        if not os.path.exists(db_path):
            raise RuntimeError(f"Database file was not created: {db_path}")
        
        file_size = os.path.getsize(db_path)
        stats['success'] = True
        stats['message'] = f"Successfully created SQLite database with {stats['tables_created']} tables ({file_size} bytes)"
        logger.info(stats['message'])
        
        # Close engine
        engine.dispose()
        
        return stats
        
    except FileExistsError as e:
        stats['message'] = str(e)
        logger.error(stats['message'])
        raise
    except Exception as e:
        stats['message'] = f"Failed to create SQLite database: {str(e)}"
        logger.error(stats['message'])
        raise SQLAlchemyError(stats['message']) from e


def create_postgresql_database(
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    overwrite: bool = False
) -> Dict[str, Any]:
    """
    Create an empty PostgreSQL database with full PyArchInit-Mini schema
    
    Args:
        host: PostgreSQL server hostname
        port: PostgreSQL server port (usually 5432)
        database: Name of database to create
        username: PostgreSQL username
        password: PostgreSQL password
        overwrite: If True, drop and recreate database. If False, raise error if exists.
    
    Returns:
        Dictionary with creation statistics
        
    Raises:
        ValueError: If database already exists and overwrite=False
        SQLAlchemyError: If database creation fails
    """
    stats = {
        'success': False,
        'db_type': 'postgresql',
        'host': host,
        'port': port,
        'database': database,
        'tables_created': 0,
        'message': ''
    }
    
    try:
        # First connect to 'postgres' database to create new database
        admin_connection_string = f"postgresql://{username}:{password}@{host}:{port}/postgres"
        admin_engine = create_engine(admin_connection_string, isolation_level="AUTOCOMMIT")
        
        # Check if database exists. Connecting to the admin 'postgres' DB
        # may fail on managed providers (e.g. Railway) where only the project
        # DB is accessible — fall back to assuming the target exists.
        db_exists = False
        admin_available = True
        try:
            with admin_engine.connect() as conn:
                result = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                    {"dbname": database}
                )
                db_exists = result.fetchone() is not None

                if db_exists and overwrite:
                    logger.warning(f"Dropping existing database: {database}")
                    conn.execute(text(f"""
                        SELECT pg_terminate_backend(pg_stat_activity.pid)
                        FROM pg_stat_activity
                        WHERE pg_stat_activity.datname = '{database}'
                        AND pid <> pg_backend_pid()
                    """))
                    conn.execute(text(f"DROP DATABASE {database}"))
                    logger.info(f"Dropped database: {database}")
                    db_exists = False

                if not db_exists:
                    logger.info(f"Creating PostgreSQL database: {database}")
                    conn.execute(text(f"CREATE DATABASE {database}"))
                    logger.info(f"Database created: {database}")
        except Exception as admin_err:
            admin_available = False
            logger.warning(
                f"Cannot connect to admin 'postgres' DB ({admin_err}); "
                f"assuming target '{database}' already exists and reusing it."
            )

        admin_engine.dispose()
        
        # Now connect to the new database and create schema
        db_connection_string = f"postgresql://{username}:{password}@{host}:{port}/{database}"
        db_engine = create_engine(db_connection_string)
        
        # Import all models to register them with Base.metadata
        Base = _import_all_models()
        
        # Create all tables
        logger.info(f"Creating PyArchInit-Mini schema in PostgreSQL database: {database}")
        Base.metadata.create_all(db_engine)
        
        # Count created tables
        stats['tables_created'] = len(Base.metadata.tables)
        stats['success'] = True
        stats['message'] = f"Successfully created PostgreSQL database '{database}' with {stats['tables_created']} tables"
        logger.info(stats['message'])
        
        # Close engine
        db_engine.dispose()
        
        return stats
        
    except ValueError as e:
        stats['message'] = str(e)
        logger.error(stats['message'])
        raise
    except Exception as e:
        stats['message'] = f"Failed to create PostgreSQL database: {str(e)}"
        logger.error(stats['message'])
        raise SQLAlchemyError(stats['message']) from e


def create_empty_database(
    db_type: str,
    db_path_or_config: Any = None,
    overwrite: bool = False,
    use_default_path: bool = False
) -> Dict[str, Any]:
    """
    Unified interface to create empty database (SQLite or PostgreSQL)

    Args:
        db_type: 'sqlite' or 'postgresql'
        db_path_or_config:
            - For SQLite: string path to database file (or None to use default)
            - For PostgreSQL: dict with keys {host, port, database, username, password}
        overwrite: If True, overwrite/drop existing database
        use_default_path: If True, use default path ~/.pyarchinit_mini/data/ for SQLite

    Returns:
        Dictionary with creation statistics

    Raises:
        ValueError: If db_type is invalid or config is incomplete
        FileExistsError/ValueError: If database exists and overwrite=False
        SQLAlchemyError: If database creation fails
    """
    from pathlib import Path

    db_type = db_type.lower()

    if db_type == 'sqlite':
        # Use default path if requested or if no path specified
        if use_default_path or db_path_or_config is None:
            default_dir = Path.home() / '.pyarchinit_mini' / 'data'
            default_dir.mkdir(parents=True, exist_ok=True)

            # Generate default filename
            if db_path_or_config and isinstance(db_path_or_config, str):
                # Use provided filename in default directory
                filename = os.path.basename(db_path_or_config)
            else:
                # Use default filename
                filename = 'pyarchinit_empty.db'

            db_path_or_config = str(default_dir / filename)
            logger.info(f"Using default database path: {db_path_or_config}")

        if not isinstance(db_path_or_config, str):
            raise ValueError("For SQLite, db_path_or_config must be a string path")
        return create_sqlite_database(db_path_or_config, overwrite=overwrite)
    
    elif db_type == 'postgresql':
        if not isinstance(db_path_or_config, dict):
            raise ValueError("For PostgreSQL, db_path_or_config must be a dict with connection parameters")
        
        required_keys = ['host', 'port', 'database', 'username', 'password']
        missing_keys = [key for key in required_keys if key not in db_path_or_config]
        if missing_keys:
            raise ValueError(f"Missing required PostgreSQL parameters: {missing_keys}")
        
        return create_postgresql_database(
            host=db_path_or_config['host'],
            port=db_path_or_config['port'],
            database=db_path_or_config['database'],
            username=db_path_or_config['username'],
            password=db_path_or_config['password'],
            overwrite=overwrite
        )
    
    else:
        raise ValueError(f"Unsupported database type: {db_type}. Must be 'sqlite' or 'postgresql'")
