"""Struttura (structure) record — matches the classic pyarchinit struttura_table."""
from sqlalchemy import Column, Integer, String, Text, Float
from .base import BaseModel

class Struttura(BaseModel):
    __tablename__ = 'struttura_table'
    id_struttura = Column(Integer, primary_key=True, autoincrement=True)
    sito = Column(Text)
    sigla_struttura = Column(Text)
    numero_struttura = Column(Integer)
    categoria_struttura = Column(Text)
    tipologia_struttura = Column(Text)
    definizione_struttura = Column(Text)
    descrizione = Column(Text)
    interpretazione = Column(Text)
    periodo_iniziale = Column(Integer)
    fase_iniziale = Column(Integer)
    periodo_finale = Column(Integer)
    fase_finale = Column(Integer)
    datazione_estesa = Column(String(300))
    materiali_impiegati = Column(Text)
    elementi_strutturali = Column(Text)
    rapporti_struttura = Column(Text)
    misure_struttura = Column(Text)
    data_compilazione = Column(Text)
    nome_compilatore = Column(Text)
    stato_conservazione = Column(Text)
    quota = Column(Float)
    relazione_topografica = Column(Text)
    prospetto_ingresso = Column(Text)
    orientamento_ingresso = Column(Text)
    articolazione = Column(Text)
    n_ambienti = Column(Integer)
    orientamento_ambienti = Column(Text)
    sviluppo_planimetrico = Column(Text)
    elementi_costitutivi = Column(Text)
    motivo_decorativo = Column(Text)
    potenzialita_archeologica = Column(Text)
    manufatti = Column(Text)
    elementi_datanti = Column(Text)
    fasi_funzionali = Column(Text)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
