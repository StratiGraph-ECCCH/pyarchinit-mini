"""Mapping between pyarchinit-mini entity keys and the classic plugin's
media_to_entity_table (entity_type, table_name) values, plus the entity PK column."""

# key -> (entity_type, table_name, id_column)
ENTITY_MAP: dict[str, tuple[str, str, str]] = {
    "us":         ("US",        "us_table",                   "id_us"),
    "inventario": ("REPERTO",   "inventario_materiali_table", "id_invmat"),
    "pottery":    ("CERAMICA",  "pottery_table",              "id_rep"),
    "struttura":  ("STRUTTURA", "struttura_table",            "id_struttura"),
    "tomba":      ("TOMBA",     "tomba_table",                "id_tomba"),
    "tma":        ("TMA",       "tma_table",                  "id_tma"),
    "ut":         ("UT",        "ut_table",                   "id_ut"),
    # mini-only: the plugin never links media to sites, so these rows are
    # invisible in QGIS but valid.
    "site":       ("SITE",      "site_table",                 "id_sito"),
}

def resolve_entity(key: str) -> tuple[str, str, str]:
    """Return (entity_type, table_name, id_column) for a mini entity key."""
    return ENTITY_MAP[key]
