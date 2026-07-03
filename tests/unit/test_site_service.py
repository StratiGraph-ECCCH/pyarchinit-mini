"""
Unit tests for SiteService
"""

import pytest
from pyarchinit_mini.utils.exceptions import ValidationError, DuplicateRecordError

def test_create_site_success(site_service, sample_site_data):
    """Test successful site creation"""
    site = site_service.create_site(sample_site_data)
    
    assert site.sito == sample_site_data["sito"]
    assert site.nazione == sample_site_data["nazione"]
    assert site.comune == sample_site_data["comune"]
    assert site.id_sito is not None

def test_create_site_duplicate_name(site_service, sample_site_data):
    """Test that duplicate site names are rejected"""
    # Create first site
    site_service.create_site(sample_site_data)
    
    # Try to create duplicate
    with pytest.raises(DuplicateRecordError):
        site_service.create_site(sample_site_data)

def test_create_site_invalid_data(site_service):
    """Test validation of site data"""
    invalid_data = {
        "sito": "",  # Empty name should fail
        "nazione": "Italia"
    }
    
    with pytest.raises(ValidationError):
        site_service.create_site(invalid_data)

def test_get_site_by_id(site_service, sample_site_data):
    """Test retrieving site by ID"""
    created_site = site_service.create_site(sample_site_data)
    
    retrieved_site = site_service.get_site_by_id(created_site.id_sito)
    
    assert retrieved_site is not None
    assert retrieved_site.id_sito == created_site.id_sito
    assert retrieved_site.sito == created_site.sito

def test_get_site_by_name(site_service, sample_site_data):
    """Test retrieving site by name"""
    created_site = site_service.create_site(sample_site_data)
    
    retrieved_site = site_service.get_site_by_name(sample_site_data["sito"])
    
    assert retrieved_site is not None
    assert retrieved_site.sito == sample_site_data["sito"]

def test_update_site(site_service, sample_site_data):
    """Test updating site data"""
    created_site = site_service.create_site(sample_site_data)
    
    update_data = {"descrizione": "Updated description"}
    updated_site = site_service.update_site(created_site.id_sito, update_data)
    
    assert updated_site.descrizione == "Updated description"
    assert updated_site.sito == sample_site_data["sito"]  # Other fields unchanged

def test_delete_site(site_service, sample_site_data):
    """Test deleting a site"""
    created_site = site_service.create_site(sample_site_data)
    
    result = site_service.delete_site(created_site.id_sito)
    # delete_site does a cascade delete and returns per-table deletion counts
    assert result['site'] == 1

    # Verify site is deleted
    deleted_site = site_service.get_site_by_id(created_site.id_sito)
    assert deleted_site is None

def test_get_all_sites(site_service):
    """Test getting all sites with pagination"""
    # Create multiple sites
    for i in range(5):
        site_data = {
            "sito": f"Test Site {i}",
            "nazione": "Italia",
            "comune": "Roma"
        }
        site_service.create_site(site_data)
    
    # Get all sites
    sites = site_service.get_all_sites(page=1, size=10)
    assert len(sites) == 5
    
    # Test pagination
    sites_page1 = site_service.get_all_sites(page=1, size=2)
    sites_page2 = site_service.get_all_sites(page=2, size=2)
    
    assert len(sites_page1) == 2
    assert len(sites_page2) == 2
    assert sites_page1[0].id_sito != sites_page2[0].id_sito

def test_count_sites(site_service, sample_site_data):
    """Test counting sites"""
    initial_count = site_service.count_sites()
    
    site_service.create_site(sample_site_data)
    
    new_count = site_service.count_sites()
    assert new_count == initial_count + 1