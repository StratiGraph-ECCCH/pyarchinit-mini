import pytest
from pyarchinit_mini.media_manager.entity_map import ENTITY_MAP, resolve_entity

def test_us_maps_to_plugin_values():
    assert resolve_entity("us") == ("US", "us_table", "id_us")

def test_inventario_uses_id_invmat():
    assert resolve_entity("inventario") == ("REPERTO", "inventario_materiali_table", "id_invmat")

def test_pottery_uses_ceramica_and_id_rep():
    assert resolve_entity("pottery") == ("CERAMICA", "pottery_table", "id_rep")

def test_site_is_mini_only_but_mapped():
    assert resolve_entity("site") == ("SITE", "site_table", "id_sito")

def test_unknown_key_raises():
    with pytest.raises(KeyError):
        resolve_entity("nope")

def test_map_has_all_expected_keys():
    assert set(ENTITY_MAP) == {"us", "inventario", "pottery", "struttura", "tomba", "tma", "ut", "site"}
