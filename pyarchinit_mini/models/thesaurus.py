"""
Thesaurus model for controlled vocabularies
Based on PyArchInit thesaurus system
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import BaseModel

class ThesaurusSigle(BaseModel):
    """
    Thesaurus for controlled vocabularies and abbreviations
    Based on pyarchinit_thesaurus_sigle table
    """
    __tablename__ = 'pyarchinit_thesaurus_sigle'
    
    # Primary key
    id_thesaurus_sigle = Column(Integer, primary_key=True, autoincrement=True)
    
    # Table reference
    nome_tabella = Column(Text, nullable=False)  # Which table this vocabulary applies to
    
    # Vocabulary entries
    sigla = Column(Text, nullable=False)  # Short code/abbreviation
    sigla_estesa = Column(Text)  # Extended form
    descrizione = Column(Text)  # Description
    
    # Classification
    tipologia_sigla = Column(Text)  # Type of abbreviation
    lingua = Column(String(2), default='it')  # Language code
    
    # Metadata
    fonte = Column(Text)  # Source reference
    note = Column(Text)  # Additional notes
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('nome_tabella', 'sigla', 'lingua', name='thesaurus_unique'),
    )
    
    def __repr__(self):
        return f"<ThesaurusSigle(id={self.id_thesaurus_sigle}, " \
               f"tabella='{self.nome_tabella}', sigla='{self.sigla}')>"
    
    @property
    def display_value(self):
        """Display value for UI"""
        if self.sigla_estesa:
            return f"{self.sigla} - {self.sigla_estesa}"
        return self.sigla

class ThesaurusField(BaseModel):
    """
    Field-specific thesaurus entries
    For detailed field vocabularies
    """
    __tablename__ = 'thesaurus_field'
    
    # Primary key
    id_field = Column(Integer, primary_key=True, autoincrement=True)
    
    # Field reference
    table_name = Column(Text, nullable=False)
    field_name = Column(Text, nullable=False)
    
    # Vocabulary entry
    value = Column(Text, nullable=False)
    label = Column(Text)  # Human-readable label
    description = Column(Text)
    
    # Hierarchy support
    parent_id = Column(Integer, ForeignKey('thesaurus_field.id_field'))
    sort_order = Column(Integer, default=0)
    
    # Status
    active = Column(String(1), default='1')  # 1=active, 0=inactive
    
    # Language support
    language = Column(String(2), default='it')
    
    # Relationships
    children = relationship("ThesaurusField", backref="parent", remote_side=[id_field])
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('table_name', 'field_name', 'value', 'language', name='field_value_unique'),
    )
    
    def __repr__(self):
        return f"<ThesaurusField(table='{self.table_name}', " \
               f"field='{self.field_name}', value='{self.value}')>"
    
    @property
    def display_name(self):
        """Display name for UI"""
        return self.label if self.label else self.value

class ThesaurusCategory(BaseModel):
    """
    Categories for organizing thesaurus entries
    """
    __tablename__ = 'thesaurus_category'
    
    # Primary key
    id_category = Column(Integer, primary_key=True, autoincrement=True)
    
    # Category information
    category_name = Column(Text, nullable=False)
    category_code = Column(String(20))
    description = Column(Text)
    
    # Hierarchy
    parent_id = Column(Integer, ForeignKey('thesaurus_category.id_category'))
    level = Column(Integer, default=0)
    sort_order = Column(Integer, default=0)
    
    # Status
    active = Column(String(1), default='1')
    
    # Relationships
    children = relationship("ThesaurusCategory", backref="parent", remote_side=[id_category])
    
    def __repr__(self):
        return f"<ThesaurusCategory(id={self.id_category}, name='{self.category_name}')>"

# Predefined thesaurus mappings for common archaeological fields
THESAURUS_MAPPINGS = {
    'site_table': {
        'tipologia_sito': [
            'Abitato', 'Necropoli', 'Santuario', 'Insediamento', 'Villa', 
            'Castelliere', 'Fortezza', 'Ponte', 'Acquedotto', 'Teatro',
            'Anfiteatro', 'Foro', 'Basilica', 'Terme', 'Domus'
        ],
        'definizione_sito': [
            'Scavo stratigrafico', 'Ricognizione', 'Controllo archeologico',
            'Scavo d\'emergenza', 'Sondaggio', 'Prospezione geofisica'
        ],
        'periodo_iniziale': [
            'Paleolitico', 'Mesolitico', 'Neolitico', 'Eneolitico',
            'Età del Bronzo', 'Età del Ferro', 'Età Romana',
            'Tardoantico', 'Altomedioevo', 'Medioevo', 'Postmedioevo'
        ]
    },
    'us_table': {
        'tipo_us': [
            'Strato', 'Struttura', 'Interface', 'Riempimento', 'Deposito',
            'Taglio', 'Crollo', 'Livellamento', 'Preparazione', 'Pavimento'
        ],
        'formazione': [
            'Naturale', 'Antropica', 'Mista'
        ],
        'consistenza': [
            'Compatta', 'Semicompatta', 'Sciolsa', 'Molto sciolsa'
        ],
        'colore': [
            'Marrone', 'Marrone scuro', 'Marrone chiaro', 'Grigio',
            'Grigio scuro', 'Grigio chiaro', 'Nero', 'Giallo',
            'Rossastro', 'Biancastro'
        ]
    },
    'inventario_materiali_table': {
        'tipo_reperto': [
            'Ceramica', 'Metallo', 'Vetro', 'Osso', 'Pietra',
            'Legno', 'Tessuto', 'Plastica', 'Moneta', 'Laterizio'
        ],
        'stato_conservazione': [
            'Ottimo', 'Buono', 'Discreto', 'Cattivo', 'Pessimo',
            'Frammentario', 'Lacunoso', 'Integro'
        ],
        'corpo_ceramico': [
            'Depurato', 'Semi-depurato', 'Grezzo', 'Fine',
            'Medio-fine', 'Grossolano'
        ],
        'rivestimento': [
            'Verniciato', 'Ingobbato', 'Dipinto', 'Graffito',
            'Inciso', 'Impresso', 'Nudo'
        ]
    },
    # PyArchInit splits TMA thesaurus into TWO separate categories:
    # - 'TMA materiali archeologici' (master TMA card fields)
    # - 'TMA Materiali Ripetibili'   (detail repetitive material fields, NOTE capital R)
    'TMA materiali archeologici': {
        'area': [  # 10.7
            'A', 'B', 'C', 'D', '1', '2', '3'
        ],
        'localita': [  # 10.3
            'Rimini', 'Cesena', 'Forli', 'Ravenna', 'Bellaria',
            'Apecchio', 'San Costanzo', 'Pesaro', 'Faenza'
        ],
        'settore': [  # 10.15
            'A', 'B', 'C', 'D', 'Nord', 'Sud', 'Est', 'Ovest'
        ],
        'ldct': [  # 10.2 - Tipologia collocazione
            'Magazzino', 'Museo', 'Caveau', 'Laboratorio',
            'Restauro', 'Deposito', 'Archivio'
        ],
        'ldcn': [  # 10.1 - Denominazione collocazione
            'Soprintendenza ABAP Ravenna',
            'Soprintendenza ABAP Bologna',
            'Museo Archeologico Cesena',
            'Museo Archeologico Rimini',
            'Museo Fellini Rimini',
        ],
        'scan': [  # 10.5 - Denominazione scavo
            'Scavo stratigrafico', 'Scavo di emergenza',
            'Saggio', 'Sondaggio', 'Trincea', 'Recupero'
        ],
        'dtzg': [  # 10.4 - Fascia cronologica
            'Eta preistorica', 'Eta protostorica',
            'Eta etrusca (VIII-V sec. a.C.)',
            'Eta romana repubblicana (II-I sec. a.C.)',
            'Eta romana imperiale (I-II sec. d.C.)',
            'Eta tardo-antica (IV-VI sec. d.C.)',
            'Eta alto-medievale (VI-X sec.)',
            'Eta medievale (XI-XIV sec.)',
            'Eta rinascimentale (XV-XVI sec.)',
            'Eta moderna (XVI-XVIII sec.)',
        ],
        'aint': [  # 10.6 - Tipologia acquisizione
            'Scavo stratigrafico', 'Scavo di emergenza',
            'Recupero', 'Donazione', 'Sequestro',
            'Acquisto', 'Ricognizione di superficie'
        ],
        'ftap': [  # 10.9 - Tipo fotografia
            'Digitale', 'Pellicola', 'Diapositiva',
            'Macro digitale', 'Digitale alta risoluzione',
        ],
        'drat': [  # 10.16 - Tipo disegno
            'Tecnico', 'Rilievo', 'Schizzo',
            'Sezione', 'Pianta', 'Prospetto'
        ],
    },
    'TMA Materiali Ripetibili': {
        # Detail fields used by tma_materiali_ripetibili
        'macc': [  # 10.10 - Categoria materiale
            'Ceramica', 'Vetro', 'Metallo', 'Osso', 'Pietra',
            'Legno', 'Bronzo', 'Ferro', 'Argilla', 'Mosaico',
            'Numismatica', 'Terra sigillata italica',
            'Terra sigillata africana', 'Bucchero', 'Anfora',
            'Maiolica graffita', 'Maiolica ingobbiata'
        ],
        'macl': [  # 10.11 - Classe
            'Vasellame', 'Strumento', 'Contenitore', 'Equipaggiamento',
            'Vestiario', 'Resti umani', 'Tessera', 'Lucerna',
            'Numismatica', 'Architettonico'
        ],
        'macp': [  # 10.12 - Precisazione tipologica (forma)
            'Coppa', 'Piatto', 'Bicchiere', 'Boccale', 'Olla',
            'Anfora', 'Lucerna', 'Chiodo', 'Fibbia', 'Macina',
            'Peso da telaio', 'Tessera', 'Cranio', 'Ossa lunghe',
            'Ferro di cavallo', 'Balsamario'
        ],
        'macd': [  # 10.13 - Definizione
            'Forma Conspectus 22', 'Hayes 27', 'Dragendorff 18',
            'Dressel 6A', 'Isings 12', 'Isings 8',
            'Manuale ovoidale', 'Tronco-piramidale',
            'Etrusco-padano', 'Profilo articolato',
            'Decoro a fasce', 'Frammentario'
        ],
        'cronologia_mac': [  # 10.4 (same code as dtzg, but different table)
            'I sec. d.C.', 'II sec. d.C.', 'III sec. d.C.',
            'IV sec. d.C.', 'V sec. d.C.', 'VI sec. d.C.',
            'VII-VIII sec.', 'XII sec.', 'XIII sec.',
            'XV sec.', 'XVI sec.', 'II-I sec. a.C.',
            'VI-V sec. a.C.'
        ],
    },
    'pottery_table': {
        'material': [
            'Ceramica', 'Vetro', 'Metallo', 'Osso', 'Pietra', 'Terracotta',
            'Stucco', 'Mosaico', 'Marmo', 'Bronzo',
        ],
        'form': [
            'Olla', 'Ciotola', 'Anfora', 'Coppa', 'Lucerna', 'Bicchiere',
            'Brocca', 'Piatto', 'Pentola', 'Vaso', 'Catino', 'Boccale',
            'Tegame', 'Mortaio', 'Unguentario',
        ],
        'fabric': [
            'Coarse ware', 'Fine ware', 'Common ware', 'Cooking ware',
            'Storage ware', 'Tableware', 'Painted ware', 'Glazed ware',
        ],
        'ware': [
            'African Red Slip', 'Eastern Sigillata A', 'Eastern Sigillata B',
            'Terra Sigillata Italica', 'Terra Sigillata Sud-Gallica',
            'Phocaean Red Slip', 'Cypriot Red Slip', 'Late Roman C',
            'Italo-Megarian', 'Black Glazed',
        ],
        'surf_trat': [
            'Lisciatura', 'Lucidatura', 'Stralucidatura', 'Stralucidatura a stecca',
            'Ingobbio', 'Vernice', 'Smalto', 'Pittura', 'Nessuno',
        ],
        'wheel_made': ['Yes', 'No', 'Indeterminate'],
    },
    'tomba_table': {
        'rito': [
            'Inumazione', 'Cremazione', 'Incinerazione'
        ],
        'tipo_sepoltura': [
            'Fossa terragna', 'Cassa', 'Sarcofago', 'Enchytrismos', 'A cappuccina'
        ],
        'tipo_deposizione': [
            'Primaria', 'Secondaria', 'Supina', 'Prona', 'Rannicchiata'
        ],
        'copertura_tipo': [
            'Tegole', 'Lastre', 'Laterizi', 'Assente'
        ],
        'tipo_contenitore_resti': [
            'Anfora', 'Olla', 'Cassa lignea', 'Assente'
        ],
        'stato_di_conservazione': [
            'Ottimo', 'Buono', 'Discreto', 'Cattivo', 'Frammentario'
        ],
        'corredo_presenza': [
            'Sì', 'No', 'Parziale'
        ]
    },
    'struttura_table': {
        'categoria_struttura': [
            'Muro', 'Fondazione', 'Pavimentazione', 'Focolare', 'Pozzo',
            'Canaletta', 'Buca', 'Struttura muraria'
        ],
        'tipologia_struttura': [
            'In pietra', 'In laterizio', 'Mista', 'In terra', 'Lignea'
        ],
        'orientamento_ingresso': [
            'N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO'
        ],
        'articolazione': [
            'Semplice', 'Complessa', 'A vani multipli'
        ]
    },
    'fauna_table': {
        'specie': [
            'Bos taurus', 'Ovis aries', 'Capra hircus', 'Sus domesticus',
            'Equus caballus', 'Canis familiaris', 'Cervus elaphus', 'Gallus gallus'
        ],
        'parti_scheletriche': [
            'Cranio', 'Mandibola', 'Costola', 'Vertebra', 'Omero',
            'Femore', 'Tibia', 'Metapodio', 'Falange'
        ],
        'contesto': [
            'Strato', 'Fossa', 'Focolare', 'Butto', 'Sepoltura', 'Riempimento'
        ],
        'stato_conservazione': [
            'Ottimo', 'Buono', 'Discreto', 'Cattivo', 'Frammentario'
        ],
        'metodologia_recupero': [
            'Raccolta manuale', 'Setacciatura a secco', 'Flottazione', 'Vagliatura'
        ],
        'deposizione': [
            'Primaria', 'Secondaria', 'In connessione', 'Sparsa'
        ]
    },
    'ut_table': {
        'def_ut': [
            'Area', 'Struttura', 'Affioramento', 'Dispersione di materiale', 'Traccia'
        ],
        'survey_type': [
            'Sistematica', 'Non sistematica', 'Intensiva', 'Estensiva', 'Campionaria'
        ],
        'gps_method': [
            'RTK', 'DGPS', 'Navigazione', 'Punto singolo'
        ],
        'surface_condition': [
            'Arato', 'Incolto', 'Boscato', 'Urbanizzato', 'Prato'
        ],
        'accessibility': [
            'Alta', 'Media', 'Bassa', 'Non accessibile'
        ]
    },
    'individui_table': {
        'posizione_cranio': [
            'Nord', 'Nord-Est', 'Est', 'Sud-Est', 'Sud', 'Sud-Ovest', 'Ovest', 'Nord-Ovest',
            'Frontale', 'Laterale destro', 'Laterale sinistro'
        ],
        'posizione_scheletro': [
            'Supino', 'Prono', 'Fianco destro', 'Fianco sinistro', 'Rannicchiato', 'Seduto'
        ],
        'orientamento_asse': [
            'N-S', 'S-N', 'E-O', 'O-E', 'NE-SO', 'SO-NE', 'NO-SE', 'SE-NO'
        ],
        'posizione_arti_superiori': [
            'Distesi lungo i fianchi', 'Incrociati sul bacino', 'Incrociati sul petto',
            'Piegati sul bacino', 'Piegati sul petto'
        ],
        'posizione_arti_inferiori': [
            'Distesi', 'Flessi', 'Incrociati', 'Rannicchiati'
        ],
        'area': [
            '1', '2', '3'
        ],
        'completo_si_no': [
            'Sì', 'No', 'Parziale'
        ],
        'disturbato_si_no': [
            'Sì', 'No'
        ],
        'in_connessione_si_no': [
            'Sì', 'No', 'Parziale'
        ]
    },
}