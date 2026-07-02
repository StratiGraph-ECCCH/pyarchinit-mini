"""Flask blueprint for the AI Matrix Import flow."""
from __future__ import annotations

import base64
import json
import os

from flask import (
    Blueprint, request, render_template, redirect, url_for,
    flash, current_app,
)
from sqlalchemy import text

from pyarchinit_mini.ai_matrix.vision_extractor import extract
from pyarchinit_mini.ai_matrix.plan import AIPlan
from pyarchinit_mini.ai_matrix.apply import apply_ai_plan


matrix_import_bp = Blueprint(
    "matrix_import",
    __name__,
    url_prefix="/matrix-import",
)


def _get_session():
    """Mirror of yed_import_routes._get_session: app db_manager else env DATABASE_URL."""
    if hasattr(current_app, "db_manager"):
        return current_app.db_manager.connection.get_session()
    from pyarchinit_mini.database.connection import DatabaseConnection
    db_url = os.getenv("DATABASE_URL", "sqlite:///pyarchinit_mini.db")
    return DatabaseConnection.from_url(db_url).get_session()


def _bootstrap_ai_credentials_from_settings() -> None:
    """Copy AI keys from app_settings (UI Admin) into os.environ.

    Mirror of the same bootstrap done inside the /api/ai_ask endpoint so the
    matrix_import flow doesn't require shell-level env vars when the user has
    configured the keys via the admin UI.
    """
    if not hasattr(current_app, "db_manager"):
        return
    try:
        from pyarchinit_mini.services.app_setting_service import AppSettingService
        settings = AppSettingService(current_app.db_manager)
        provider = (settings.get("ai_provider") or "").strip().lower()
        if provider:
            os.environ["AI_PROVIDER"] = provider
        openai_key = (settings.get("openai_api_key") or "").strip()
        anthropic_key = (settings.get("anthropic_api_key") or "").strip()
        if openai_key:
            os.environ["OPENAI_API_KEY"] = openai_key
        if anthropic_key:
            os.environ["ANTHROPIC_API_KEY"] = anthropic_key
    except Exception as exc:
        current_app.logger.warning("matrix_import: AI settings bootstrap failed: %s", exc)


@matrix_import_bp.route("/")
def upload_form():
    with _get_session() as db:
        sites = db.execute(
            text("SELECT sito FROM site_table ORDER BY sito")
        ).fetchall()
    return render_template(
        "matrix_import/upload.html",
        sites=[r[0] for r in sites],
        default_provider=os.environ.get("AI_PROVIDER", "anthropic"),
    )


@matrix_import_bp.post("/upload")
def upload():
    image_file = request.files.get("image")
    text_hint = request.form.get("descrizione", "").strip()
    sito_form = request.form.get("sito", "").strip()
    sito_new = request.form.get("sito_new", "").strip()
    area_form = request.form.get("area", "").strip()
    provider = request.form.get("provider", "anthropic")

    if not image_file or not image_file.filename:
        flash("Carica un'immagine", "error")
        return redirect(url_for("matrix_import.upload_form"))
    image_bytes = image_file.read()

    _bootstrap_ai_credentials_from_settings()

    try:
        result = extract(image_bytes, text_hint, provider)
    except Exception as e:
        current_app.logger.exception("matrix_import: extract() raised")
        flash(f"Errore AI: {e}", "error")
        return redirect(url_for("matrix_import.upload_form"))

    if result.rejected:
        return render_template(
            "matrix_import/rejected.html",
            reason=result.reason,
            confidence=result.confidence,
        )

    if sito_form == "__NEW__":
        sito_form = ""
    sito_finale = sito_new or sito_form or (result.plan.detected_site or "")

    return render_template(
        "matrix_import/preview.html",
        plan=result.plan,
        sito=sito_finale,
        area_default=area_form or (result.plan.detected_area or ""),
        sito_needs_input=(sito_finale == ""),
        image_b64=base64.b64encode(image_bytes).decode(),
        plan_json=json.dumps(result.plan.as_dict()),
    )


def _apply_form_edits(
    plan: AIPlan,
    form,
    selected_us_idx: set,
    selected_edges_idx: set,
) -> AIPlan:
    """Build a filtered plan with user-edited values for selected rows only."""
    from pyarchinit_mini.ai_matrix.plan import USRow, EdgeRow
    new_us = []
    for idx, _u in enumerate(plan.us):
        if str(idx) not in selected_us_idx:
            continue
        new_us.append(USRow(
            us_num=form.get(f"us_num_{idx}", "").strip(),
            area=form.get(f"area_{idx}", "").strip() or None,
            unit_type=form.get(f"unit_type_{idx}", "US").strip(),
            descrizione=form.get(f"desc_{idx}", "").strip(),
            fase_recente=int(form.get(f"fr_{idx}", "1") or "1"),
            fase_iniziale=int(form.get(f"fi_{idx}", "1") or "1"),
        ))
    new_edges = []
    for idx, _e in enumerate(plan.edges):
        if str(idx) not in selected_edges_idx:
            continue
        new_edges.append(EdgeRow(
            us_from=form.get(f"ef_{idx}", "").strip(),
            us_to=form.get(f"et_{idx}", "").strip(),
            tipo=form.get(f"etipo_{idx}", "copre").strip(),
        ))
    return AIPlan(
        detected_site=plan.detected_site,
        detected_area=plan.detected_area,
        us=new_us, edges=new_edges,
    )


@matrix_import_bp.post("/apply")
def apply():
    plan_json_str = request.form.get("plan_json", "")
    sito = request.form.get("sito", "").strip()
    image_b64 = request.form.get("image_b64", "")

    if not sito:
        flash("Nome sito obbligatorio", "error")
        return redirect(url_for("matrix_import.upload_form"))
    if not plan_json_str:
        flash("Plan mancante", "error")
        return redirect(url_for("matrix_import.upload_form"))

    selected_us = set(request.form.getlist("selected_us"))
    selected_edges = set(request.form.getlist("selected_edges"))

    try:
        plan = AIPlan.from_dict(json.loads(plan_json_str))
    except (json.JSONDecodeError, TypeError) as e:
        current_app.logger.warning("matrix_import: malformed plan_json: %s", e)
        flash("Plan malformato — riprova l'analisi", "error")
        return redirect(url_for("matrix_import.upload_form"))
    try:
        plan = _apply_form_edits(plan, request.form, selected_us, selected_edges)
    except (ValueError, TypeError) as e:
        current_app.logger.warning("matrix_import: malformed form edits: %s", e)
        flash("Valori non validi nel form — controlla i campi numerici", "error")
        return redirect(url_for("matrix_import.upload_form"))

    if not plan.us and not plan.edges:
        flash("Nessuna riga selezionata — controlla almeno una US o relazione", "error")
        return redirect(url_for("matrix_import.upload_form"))

    with _get_session() as db:
        result = apply_ai_plan(plan, sito, db)

        # Save source image as media for the site (best-effort, non-blocking)
        if image_b64:
            try:
                _save_image_for_site(db, sito, image_b64)
            except Exception as exc:
                current_app.logger.warning("matrix_import media save failed: %s", exc)

    flash(
        f"Importate {result.us_imported} US, {result.edges_imported} relazioni "
        f"({result.us_skipped} US e {result.edges_skipped} relazioni saltate)",
        "success",
    )
    return redirect(url_for("us_list", sito=sito))


def _save_image_for_site(db, sito: str, image_b64: str) -> None:
    """Best-effort: persist the source image as a Media row linked to the site.

    Uses MediaService.add_media via a temporary file. Looks up id_sito by
    sito name; if MediaService isn't wired into this app context, silently
    no-ops (the import already committed).
    """
    import tempfile
    from sqlalchemy import text as _text

    row = db.execute(
        _text("SELECT id_sito FROM site_table WHERE sito = :s"), {"s": sito}
    ).fetchone()
    if not row:
        return
    id_sito = int(row[0])

    image_bytes = base64.b64decode(image_b64)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    try:
        media_svc = current_app.extensions.get("media_service")
        if media_svc is None:
            return
        media_svc.add_media(
            tmp_path,
            "site",
            id_sito,
            descrizione="AI Matrix Import source",
            tags="matrix_source,ai_import",
        )
    finally:
        import os as _os
        try:
            _os.unlink(tmp_path)
        except OSError:
            pass
