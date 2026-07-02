from pyarchinit_mini.models.thesaurus import THESAURUS_MAPPINGS

def test_struttura_seed_present():
    s = THESAURUS_MAPPINGS.get("struttura_table", {})
    for f in ["categoria_struttura", "tipologia_struttura", "orientamento_ingresso", "articolazione"]:
        assert f in s and isinstance(s[f], list) and s[f]
