"""
AI Archaeological Assistant Service

Provides AI-powered analysis of archaeological data using configurable
LLM providers (OpenAI GPT or Anthropic Claude).
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Default models per provider (latest as of May 2026)
# OpenAI: gpt-5.5-mini (fast+cheap), gpt-5.5 (best), o4-mini (reasoning)
# Anthropic: claude-haiku-4-5 (cheapest), claude-sonnet-4-7 (fast), claude-opus-4-7 (best)
DEFAULT_MODELS = {
    "openai": "gpt-5.5-mini",
    "anthropic": "claude-sonnet-4-7",
}
# All supported models for UI selection
AVAILABLE_MODELS = {
    "openai": [
        "gpt-5.5", "gpt-5.5-mini", "gpt-5.4", "gpt-5.4-mini",
        "gpt-4.1", "gpt-4.1-mini", "o4-mini",
    ],
    "anthropic": [
        "claude-opus-4-7", "claude-sonnet-4-7", "claude-haiku-4-5",
        "claude-opus-4-6", "claude-sonnet-4-6",
    ],
}
# Models that use max_completion_tokens instead of max_tokens
_NEW_TOKEN_PARAM_MODELS = {
    "gpt-5.5", "gpt-5.5-mini", "gpt-5.4", "gpt-5.4-mini",
    "o4-mini", "o3", "o3-mini", "o1", "o1-mini",
}

SYSTEM_PROMPT_IT = """Sei un assistente archeologico esperto per il sistema PyArchInit.
Aiuti ad analizzare dati stratigrafici, materiali, cronologia e informazioni sui siti.

REGOLE (OBBLIGATORIE):
1. Rispondi SEMPRE in HTML ben formattato (MAI markdown).
2. Usa <h4> per i titoli, <h5> per sottotitoli, <p> per paragrafi, <ul>/<li> per liste.
3. Per tabelle: <table class="table table-sm table-striped"><thead>...<tbody>...
4. Per dati importanti: <strong> o <span class="badge bg-info">.
5. Link alle US: <a href="/us?sito=NOME_SITO&us_number=NUMERO" class="text-primary">US NUMERO</a>
6. Link ai materiali: <a href="/inventario" class="text-primary">Inv. NUMERO</a>
   Link alle pottery: <a href="/pottery/ID_REP" class="text-primary">Pottery ID_REP</a>
   Per le pottery usa context['pottery_summary']: aggregazioni by_form, by_fabric, by_us e un sample fino a 200 record.
   Quando rispondi su frammenti ceramici cita conteggi totali e per US.
   Link alle tombe: <a href="/tomba/ID" class="text-primary">Tomba ID</a>
   Link alle strutture: <a href="/struttura/ID" class="text-primary">Struttura ID</a>
   Link alla fauna: <a href="/fauna/ID" class="text-primary">Fauna ID</a>
7. MAI tralasciare dati. Se ci sono 700 US, cita e analizza TUTTE le US — raggruppa per tipo, area, periodo, anno, ma includi TUTTI i numeri. Crea tabelle complete.
8. Includi statistiche dettagliate: conteggi per tipo, per area, per periodo, per operatore.
9. Sii ESAUSTIVO: ogni US, ogni materiale, ogni relazione deve essere menzionata o inclusa in una tabella.
10. GRAFICI: quando l'utente chiede esplicitamente un grafico, plot, istogramma o visualizzazione, emetti
    un blocco <div class="ai-chart" data-chart='{"type":"bar|line|pie|doughnut","title":"...","labels":[...],"data":[...]}'></div>
    al posto della tabella (o in aggiunta). Il frontend lo trasforma in grafico Chart.js con bottone Download PNG.
"""

SYSTEM_PROMPT_EN = """You are an expert archaeological assistant for the PyArchInit system.
You help analyze stratigraphic data, materials, chronology, and site information.

RULES (MANDATORY):
1. ALWAYS respond in well-formatted HTML (NEVER markdown).
2. Use <h4> for titles, <h5> for subtitles, <p> for paragraphs, <ul>/<li> for lists.
3. For tables: <table class="table table-sm table-striped"><thead>...<tbody>...
4. For important data: <strong> or <span class="badge bg-info">.
5. Link to US: <a href="/us?sito=SITE_NAME&us_number=NUMBER" class="text-primary">US NUMBER</a>
6. Link to materials: <a href="/inventario" class="text-primary">Inv. NUMBER</a>
   Pottery links: <a href="/pottery/ID_REP" class="text-primary">Pottery ID_REP</a>
   For pottery use context['pottery_summary']: by_form, by_fabric, by_us aggregations + sample up to 200 records.
   When asked about pottery sherds, include totals and per-US counts.
   Tomba links: <a href="/tomba/ID" class="text-primary">Tomba ID</a>
   Struttura links: <a href="/struttura/ID" class="text-primary">Struttura ID</a>
   Fauna links: <a href="/fauna/ID" class="text-primary">Fauna ID</a>
7. NEVER omit data. If there are 700 US, cite and analyze ALL of them — group by type, area, period, year, but include ALL numbers. Create complete tables.
8. Include detailed statistics: counts by type, area, period, operator.
9. Be EXHAUSTIVE: every US, every material, every relationship must be mentioned or included in a table.
10. CHARTS: when the user explicitly asks for a chart, plot, histogram, or visualisation, emit a
    <div class="ai-chart" data-chart='{"type":"bar|line|pie|doughnut","title":"...","labels":[...],"data":[...]}'></div>
    block instead of (or in addition to) the table. The frontend renders it via Chart.js with a Download PNG button.
"""

def _get_system_prompt(lang='it'):
    return SYSTEM_PROMPT_IT if lang == 'it' else SYSTEM_PROMPT_EN


class AIAssistantService:
    """Service for AI-powered archaeological analysis.

    Configuration via environment variables:
        AI_PROVIDER  - 'openai' or 'anthropic' (default: 'openai')
        AI_API_KEY   - API key for the chosen provider
        AI_MODEL     - Model name override (optional)
    """

    def __init__(self, db_manager=None):
        """Initialize with optional DatabaseManager for AppSetting-backed config.

        Priority order for each setting:
          1. AppSetting row in the DB (via AppSettingService)
          2. Environment variable
          3. Hardcoded default in DEFAULT_MODELS
        """
        provider_env = os.environ.get("AI_PROVIDER", "openai").lower()
        api_key_env = os.environ.get("AI_API_KEY", "")
        model_env = os.environ.get("AI_MODEL", "")

        provider = api_key = model = None
        if db_manager is not None:
            try:
                from .app_setting_service import AppSettingService
                svc = AppSettingService(db_manager)
                p_from_db = svc.get("ai_provider")
                if p_from_db:
                    provider = p_from_db.lower()
                    api_key = svc.get(f"{provider}_api_key") or None
                model = svc.get("ai_model") or None
            except Exception as exc:
                # AppSetting infra may be unavailable during boot/migrations
                logging.getLogger(__name__).debug(
                    f"AIAssistantService: AppSetting unavailable, fallback to env: {exc}"
                )

        self.provider = (provider or provider_env).lower()
        self.api_key = api_key or api_key_env
        self.model = model or model_env or DEFAULT_MODELS.get(self.provider, "gpt-5.4-mini")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ask(self, question: str, context: Optional[Dict[str, Any]] = None, lang: str = 'it') -> str:
        """Ask the AI assistant a free-form question.

        Args:
            question: The user's question.
            context: Optional dict with site/US/material data for grounding.
            lang: 'it' or 'en' for response language.

        Returns:
            HTML-formatted AI response, or an error message string.
        """
        system = _get_system_prompt(lang)
        if context:
            site_name = context.get('site', {}).get('sito', '') if isinstance(context.get('site'), dict) else ''
            if site_name:
                system += f"\n\nSite name for links: {site_name}"

            # Build comprehensive context: stats first, then data
            ctx_parts = []
            if context.get('site'):
                ctx_parts.append("SITE INFO:\n" + json.dumps(context['site'], indent=1, default=str))
            if context.get('us_statistics'):
                ctx_parts.append("US STATISTICS (COMPLETE):\n" + json.dumps(context['us_statistics'], indent=1, default=str))
            if context.get('inv_statistics'):
                ctx_parts.append("MATERIAL STATISTICS (COMPLETE):\n" + json.dumps(context['inv_statistics'], indent=1, default=str))
            if context.get('pottery_summary'):
                ctx_parts.append("POTTERY STATISTICS (COMPLETE):\n" + json.dumps(context['pottery_summary'], indent=1, default=str))
            # Include ALL US records (truncated per record to save tokens)
            if context.get('us_list'):
                us_summary = []
                for u in context['us_list']:
                    us_summary.append({k: u.get(k) for k in ['us', 'area', 'unita_tipo', 'd_stratigrafica', 'd_interpretativa', 'datazione', 'schedatore', 'anno_scavo', 'rapporti'] if u.get(k)})
                ctx_parts.append(f"ALL {len(us_summary)} US RECORDS (key fields):\n" + json.dumps(us_summary, default=str))
            if context.get('inv_list'):
                inv_summary = []
                for i in context['inv_list']:
                    inv_summary.append({k: i.get(k) for k in ['numero_inventario', 'tipo_reperto', 'definizione', 'us', 'area', 'stato_conservazione', 'datazione_reperto'] if i.get(k)})
                ctx_parts.append(f"ALL {len(inv_summary)} MATERIAL RECORDS (key fields):\n" + json.dumps(inv_summary, default=str))

            full_context = "\n\n".join(ctx_parts)
            # Limit to 30000 chars to fit in context window
            system += "\n\nCOMPLETE DATA:\n" + full_context[:30000]

        return self._call_llm(system_prompt=system, user_message=question)

    def generate_report_summary(
        self,
        site_data: Dict[str, Any],
        us_list: List[Any],
        inv_list: List[Any],
        lang: str = 'it',
    ) -> str:
        """Generate a professional archaeological summary report.

        Args:
            site_data: Dictionary with site metadata.
            us_list: List of stratigraphic-unit records (dicts or objects).
            inv_list: List of inventory/material records.

        Returns:
            A formatted summary string.
        """
        # Build comprehensive context with ALL data
        context_parts = [
            "SITE INFORMATION:",
            json.dumps(site_data, indent=1, default=str),
            f"\nTOTAL STRATIGRAPHIC UNITS: {len(us_list)}",
        ]
        if us_list:
            # Send ALL US with key fields
            us_summary = [{k: u.get(k) if isinstance(u, dict) else getattr(u, k, None)
                          for k in ['us', 'area', 'unita_tipo', 'd_stratigrafica', 'd_interpretativa',
                                   'datazione', 'schedatore', 'anno_scavo', 'rapporti', 'descrizione']
                          if (u.get(k) if isinstance(u, dict) else getattr(u, k, None))}
                         for u in us_list]
            context_parts.append(f"ALL {len(us_summary)} US RECORDS:")
            context_parts.append(json.dumps(us_summary, default=str))
        context_parts.append(f"\nTOTAL INVENTORY ITEMS: {len(inv_list)}")
        # pottery_summary: caller can attach it onto self for transient use
        _ps = getattr(self, '_pottery_summary', None)
        if _ps:
            context_parts.append("POTTERY STATISTICS (COMPLETE):")
            context_parts.append(json.dumps(_ps, indent=1, default=str))
        if inv_list:
            inv_summary = [{k: i.get(k) if isinstance(i, dict) else getattr(i, k, None)
                          for k in ['numero_inventario', 'tipo_reperto', 'definizione', 'descrizione',
                                   'us', 'area', 'stato_conservazione', 'datazione_reperto']
                          if (i.get(k) if isinstance(i, dict) else getattr(i, k, None))}
                         for i in inv_list]
            context_parts.append(f"ALL {len(inv_summary)} MATERIAL RECORDS:")
            context_parts.append(json.dumps(inv_summary, default=str))

        site_name = site_data.get('sito', '')
        if lang == 'it':
            user_message = (
                f"Basandoti sui seguenti dati archeologici del sito '{site_name}', "
                "scrivi un report archeologico professionale in HTML. Includi sezioni su: "
                "panoramica del sito, sequenza stratigrafica, cultura materiale, "
                "interpretazione preliminare. Crea link alle US menzionate. "
                "Usa tabelle HTML per i dati tabulari.\n\n"
                + "\n".join(context_parts)
            )
        else:
            user_message = (
                f"Based on the following archaeological data for site '{site_name}', "
                "write a professional archaeological summary report in HTML. Include sections on: "
                "site overview, stratigraphic sequence, material culture, and "
                "preliminary interpretation. Create links to mentioned US. "
                "Use HTML tables for tabular data.\n\n"
                + "\n".join(context_parts)
            )

        return self._call_llm(system_prompt=_get_system_prompt(lang), user_message=user_message)

    def analyze_stratigraphy(
        self, site_name: str, relationships: List[Any], lang: str = 'it'
    ) -> str:
        if lang == 'it':
            user_message = (
                f"Analizza la sequenza stratigrafica del sito '{site_name}'. "
                "Identifica le fasi principali, possibili disturbi, e suggerisci "
                "un'interpretazione della storia deposizionale. "
                "Crea link alle US menzionate nel formato HTML. Usa tabelle se utile.\n\n"
                "Relazioni stratigrafiche:\n"
                + json.dumps(relationships[:100], indent=2, default=str)
            )
        else:
            user_message = (
                f"Analyze the stratigraphic sequence for site '{site_name}'. "
                "Identify the main phases, possible disturbances, and suggest "
                "an interpretation of the depositional history. "
                "Create links to mentioned US in HTML format. Use tables if helpful.\n\n"
                "Stratigraphic relationships:\n"
                + json.dumps(relationships[:100], indent=2, default=str)
            )

        return self._call_llm(system_prompt=_get_system_prompt(lang), user_message=user_message)

    # ------------------------------------------------------------------
    # Provider helpers (lazy imports)
    # ------------------------------------------------------------------

    def _call_llm(self, system_prompt: str, user_message: str) -> str:
        """Route the request to the configured provider."""
        if not self.api_key:
            return (
                "Error: AI_API_KEY environment variable is not set. "
                "Please configure it with your API key."
            )

        try:
            if self.provider == "anthropic":
                return self._call_anthropic(system_prompt, user_message)
            else:
                return self._call_openai(system_prompt, user_message)
        except Exception as exc:  # noqa: BLE001
            logger.exception("AI assistant call failed")
            return f"Error communicating with AI provider: {exc}"

    def _call_openai(self, system_prompt: str, user_message: str) -> str:
        """Call the OpenAI chat completions API."""
        try:
            import openai  # lazy import
        except ImportError:
            return (
                "Error: the 'openai' package is not installed. "
                "Run: pip install pyarchinit-mini[ai]   (or: pip install openai)"
            )

        client = openai.OpenAI(api_key=self.api_key)
        params = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.1,
        }
        # GPT-5.4, o-series use max_completion_tokens; older models use max_tokens
        if self.model in _NEW_TOKEN_PARAM_MODELS:
            params["max_completion_tokens"] = 16384
        else:
            params["max_tokens"] = 16384
        response = client.chat.completions.create(**params)
        return response.choices[0].message.content

    def _call_anthropic(self, system_prompt: str, user_message: str) -> str:
        """Call the Anthropic messages API."""
        try:
            import anthropic  # lazy import
        except ImportError:
            return (
                "Error: the 'anthropic' package is not installed. "
                "Run: pip install pyarchinit-mini[ai]   (or: pip install anthropic)"
            )

        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=16384,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message},
            ],
        )
        return response.content[0].text
