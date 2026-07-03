"""Fauna (faunal remains) record — matches the classic pyarchinit fauna_table."""
from sqlalchemy import Column, BigInteger, Integer, String, Text, Date, Boolean
from .base import BaseModel

class Fauna(BaseModel):
    __tablename__ = 'fauna_table'
    id_fauna = Column(BigInteger, primary_key=True, autoincrement=True)
    id_us = Column(BigInteger)
    sito = Column(Text)
    area = Column(Text)
    saggio = Column(Text)
    us = Column(Text)
    datazione_us = Column(Text)
    responsabile_scheda = Column(Text)
    data_compilazione = Column(Date)
    documentazione_fotografica = Column(Text)
    metodologia_recupero = Column(Text)
    contesto = Column(Text)
    descrizione_contesto = Column(Text)
    resti_connessione_anatomica = Column(Text)
    tipologia_accumulo = Column(Text)
    deposizione = Column(Text)
    numero_stimato_resti = Column(Text)
    numero_minimo_individui = Column(Integer)
    specie = Column(Text)
    parti_scheletriche = Column(Text)
    specie_psi = Column(Text)
    misure_ossa = Column(Text)
    stato_frammentazione = Column(Text)
    tracce_combustione = Column(Text)
    combustione_altri_materiali_us = Column(Boolean)
    tipo_combustione = Column(Text)
    segni_tafonomici_evidenti = Column(Text)
    caratterizzazione_segni_tafonomici = Column(Text)
    stato_conservazione = Column(Text)
    alterazioni_morfologiche = Column(Text)
    note_terreno_giacitura = Column(Text)
    campionature_effettuate = Column(Text)
    affidabilita_stratigrafica = Column(Text)
    classi_reperti_associazione = Column(Text)
    osservazioni = Column(Text)
    interpretazione = Column(Text)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
