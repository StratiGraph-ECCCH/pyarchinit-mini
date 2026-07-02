"""Tomba (burial) record — matches the classic pyarchinit tomba_table."""
from sqlalchemy import Column, Integer, String, Text
from .base import BaseModel

class Tomba(BaseModel):
    __tablename__ = 'tomba_table'
    id_tomba = Column(Integer, primary_key=True, autoincrement=True)
    sito = Column(Text)
    area = Column(Integer)
    nr_scheda_taf = Column(Integer)
    sigla_struttura = Column(Text)
    nr_struttura = Column(Integer)
    nr_individuo = Column(Text)
    rito = Column(Text)
    descrizione_taf = Column(Text)
    interpretazione_taf = Column(Text)
    segnacoli = Column(Text)
    canale_libatorio_si_no = Column(Text)
    oggetti_rinvenuti_esterno = Column(Text)
    stato_di_conservazione = Column(Text)
    copertura_tipo = Column(Text)
    tipo_contenitore_resti = Column(Text)
    tipo_deposizione = Column(Text)
    tipo_sepoltura = Column(Text)
    corredo_presenza = Column(Text)
    corredo_tipo = Column(Text)
    corredo_descrizione = Column(Text)
    periodo_iniziale = Column(Integer)
    fase_iniziale = Column(Integer)
    periodo_finale = Column(Integer)
    fase_finale = Column(Integer)
    datazione_estesa = Column(String(300))

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
