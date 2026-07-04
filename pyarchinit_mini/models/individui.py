"""Individui (human skeletal remains) record — matches the classic pyarchinit individui_table."""
from sqlalchemy import Column, Integer, String, Text, Numeric, UniqueConstraint
from .base import BaseModel


class Individui(BaseModel):
    __tablename__ = 'individui_table'
    id_scheda_ind = Column(Integer, primary_key=True, autoincrement=True)
    sito = Column(Text)
    area = Column(Text)
    us = Column(Text)
    nr_individuo = Column(Integer)
    data_schedatura = Column(String(100))
    schedatore = Column(String(100))
    sesso = Column(String(100))
    eta_min = Column(Text)
    eta_max = Column(Text)
    classi_eta = Column(String(100))
    osservazioni = Column(Text)
    sigla_struttura = Column(Text)
    nr_struttura = Column(Integer)
    completo_si_no = Column(String(5))
    disturbato_si_no = Column(String(5))
    in_connessione_si_no = Column(String(5))
    lunghezza_scheletro = Column(Numeric(6, 2, asdecimal=False))
    posizione_scheletro = Column(String(50))
    posizione_cranio = Column(String(50))
    posizione_arti_superiori = Column(String(50))
    posizione_arti_inferiori = Column(String(50))
    orientamento_asse = Column(Text)
    orientamento_azimut = Column(Text)

    __table_args__ = (UniqueConstraint('sito', 'nr_individuo', name='ID_individuo_unico'),)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
