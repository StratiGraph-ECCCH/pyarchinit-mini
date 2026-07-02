"""
Test that StorageManager works without optional backend dependencies installed.

This verifies that missing optional SDKs (boto3, dropbox, etc.) don't prevent
the core StorageManager from being imported or instantiated. Only the backends
that depend on those SDKs should be unavailable.
"""

import pytest
from pyarchinit_mini.storage.storage_manager import StorageManager
from pyarchinit_mini.storage.base_backend import StorageType


def test_storage_manager_imports_without_optional_deps():
    """Test that StorageManager can be imported without optional dependencies."""
    # If this test runs, the import succeeded (it would have failed otherwise)
    assert StorageManager is not None


def test_storage_manager_instantiates_without_optional_deps():
    """Test that StorageManager() can be instantiated without optional dependencies."""
    mgr = StorageManager()
    assert mgr is not None
    assert mgr.credentials_manager is not None


def test_get_available_backends_returns_local_unibo_without_optional_deps():
    """
    Test that get_available_backends() includes at least local and unibo,
    even if optional backend SDKs are not installed.

    Local and Unibo backends have no external dependencies beyond stdlib.
    """
    mgr = StorageManager()
    available = mgr.get_available_backends()

    # Convert to StorageType values for easier comparison
    available_types = set(available) if available else set()

    # Local backend should be available (no external deps)
    assert StorageType.LOCAL in available_types, \
        f"LOCAL backend not available. Available: {[t.value for t in available_types]}"

    # Unibo backend should be available (no external deps)
    assert StorageType.UNIBO in available_types, \
        f"UNIBO backend not available. Available: {[t.value for t in available_types]}"
