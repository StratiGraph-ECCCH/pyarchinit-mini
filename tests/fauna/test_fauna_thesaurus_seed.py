from pyarchinit_mini.models.thesaurus import THESAURUS_MAPPINGS

def test_fauna_seed_present():
    f = THESAURUS_MAPPINGS.get("fauna_table", {})
    for field in ["specie", "parti_scheletriche", "contesto", "stato_conservazione", "metodologia_recupero", "deposizione"]:
        assert field in f and isinstance(f[field], list) and f[field]
