from pyarchinit_mini.models.thesaurus import THESAURUS_MAPPINGS

def test_ut_seed_present():
    ut = THESAURUS_MAPPINGS.get("ut_table", {})
    for field in ["def_ut", "survey_type", "gps_method", "surface_condition", "accessibility"]:
        assert field in ut and isinstance(ut[field], list) and ut[field]
