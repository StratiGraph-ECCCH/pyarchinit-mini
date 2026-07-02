from pyarchinit_mini.models.thesaurus import THESAURUS_MAPPINGS
def test_tomba_seed_present():
    t = THESAURUS_MAPPINGS.get("tomba_table", {})
    for f in ["rito","tipo_sepoltura","tipo_deposizione","copertura_tipo",
              "tipo_contenitore_resti","stato_di_conservazione","corredo_presenza"]:
        assert f in t and isinstance(t[f], list) and t[f]
