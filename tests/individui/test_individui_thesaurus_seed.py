from pyarchinit_mini.models.thesaurus import THESAURUS_MAPPINGS

def test_individui_seed_present():
    i = THESAURUS_MAPPINGS.get("individui_table", {})
    for field in ["posizione_cranio", "posizione_scheletro", "orientamento_asse", "posizione_arti_superiori", "posizione_arti_inferiori", "area", "completo_si_no", "disturbato_si_no", "in_connessione_si_no"]:
        assert field in i and isinstance(i[field], list) and i[field]
