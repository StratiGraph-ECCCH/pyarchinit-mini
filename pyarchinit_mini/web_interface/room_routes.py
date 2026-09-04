"""The two routes that make the room client reachable — and nothing more.

One page that says what is configured and what this session can do, and one POST
that delivers a site. The work is in `room_client`; the reading of rows is here,
because that is the one thing that must know about this database's tables.

**THE BLUEPRINT IS REGISTERED ONLY WHEN A ROOM IS CONFIGURED.** Not «registered
and disabled»: `create_app` skips it entirely, so with no variables these URLs
are a 404 and the menu entry does not render. That is the difference between «an
application that has a feature turned off» and «the application Enzo's users
have always run», and only the second is what «absent means unchanged» promises.

## WHY A SITE IS THE UNIT OF WORK

Because it is the unit of work of an excavation, and because the room's own cap
was measured against it: `OPS_BATCH_MAX = 1000`, chosen to sit «above the real
unit of work», and pyarchinit-mini's tutorial database holds 51 units and 187
relationships for one site. One site is one request. Anything bigger is paging,
and the room says so with a 413.
"""

from __future__ import annotations

import logging

from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, session, url_for)
from flask_login import current_user, login_required

from . import oidc_routes, oidc_tokens, room_client

log = logging.getLogger(__name__)

room_bp = Blueprint("stratigraph_room", __name__, url_prefix="/stratigraph")


def _orcid_of_current_user() -> str:
    """The verified iD on the signed-in account, normalised.

    `users.orcid` and not a token claim: the column is where step 02 put the
    identity after verifying it, and `load_user` rebuilds `current_user` from
    that row on every request. Reading it from a token here would be a second
    answer to «who is this».
    """
    return oidc_routes.normalize_orcid(getattr(current_user, "orcid", None)) or ""


def _sites_with_units():
    """Which sites have stratigraphy, and how much of it.

    Read straight through the connection the services share — the same handle
    `oidc_routes._local_user_for` borrows, and for the same reason: it sees the
    database the application is actually using, including after a
    `switch_database()`.
    """
    from sqlalchemy import func

    from pyarchinit_mini.models.harris_matrix import USRelationships
    from pyarchinit_mini.models.us import US

    connection = current_app.us_service.db_manager.connection
    with connection.get_session() as db:
        units = dict(db.query(US.sito, func.count(US.id_us))
                     .group_by(US.sito).all())
        edges = dict(db.query(USRelationships.sito,
                              func.count(USRelationships.id_relationship))
                     .group_by(USRelationships.sito).all())
    return [{"sito": name, "units": count, "relationships": edges.get(name, 0)}
            for name, count in sorted(units.items())]


def _rows_for(site: str):
    """A site's units and relationships, as plain dictionaries.

    PLAIN DICTIONARIES and not model instances, because that is what the adapter
    takes — it is a pure function of rows, and handing it a SQLAlchemy object
    would attach it to a session it must not know about. The dictionaries are
    built while the session is open; nothing lazy escapes it.
    """
    from pyarchinit_mini.models.harris_matrix import USRelationships
    from pyarchinit_mini.models.us import US

    connection = current_app.us_service.db_manager.connection
    with connection.get_session() as db:
        units = [{column.name: getattr(row, column.name)
                  for column in US.__table__.columns}
                 for row in db.query(US).filter(US.sito == site).all()]
        edges = [{column.name: getattr(row, column.name)
                  for column in USRelationships.__table__.columns}
                 for row in db.query(USRelationships)
                 .filter(USRelationships.sito == site).all()]
    return units, edges


@room_bp.route("/")
@login_required
def index():
    """What is configured, who you are here, and what can be delivered."""
    it = room_client.settings()
    return render_template(
        "stratigraph/room.html",
        room=it,
        orcid=_orcid_of_current_user(),
        no_author=room_client.NO_AUTHOR,
        bearer=oidc_tokens.status(session.get(oidc_tokens.HANDLE_KEY)),
        sites=_sites_with_units(),
        batch_max=room_client.BATCH_MAX,
    )


@room_bp.route("/deliver", methods=["POST"])
@login_required
def deliver():
    """One site, one POST, one outcome — and the refusals in the right order."""
    site = (request.form.get("sito") or "").strip()
    if not site:
        flash("Nessun sito scelto.", "error")
        return redirect(url_for("stratigraph_room.index"))

    orcid = _orcid_of_current_user()
    handle = session.get(oidc_tokens.HANDLE_KEY)
    oidc = oidc_routes.settings()

    # The token is fetched ONLY IF the delivery gets that far. Passing a
    # callable rather than a token is what keeps the identity refusal ahead of
    # every network call — including the refresh, which is itself a call to the
    # realm.
    def token_source() -> str:
        return oidc_tokens.bearer(handle, orcid, oidc)

    units, relationships = _rows_for(site)
    try:
        outcome = room_client.deliver(units, relationships,
                                      orcid=orcid, token_source=token_source)
    except room_client.RoomRefusal as refusal:
        flash(str(refusal), "error")
        return redirect(url_for("stratigraph_room.index"))
    except oidc_tokens.SignInAgain as expired:
        flash(str(expired), "error")
        return redirect(url_for("stratigraph_room.index"))

    if outcome.sent == 0:
        flash(f"«{site}» non ha prodotto nessuna operazione: "
              f"{'; '.join(outcome.skipped) or 'nessuna US da consegnare'}.",
              "warning")
    elif outcome.a_repeat:
        # The normal shape of a SECOND delivery, said as such rather than as a
        # failure. Note what it does NOT claim: not «nothing happened». The
        # nodes were re-applied as merges, and a merge restamps `modified_at` —
        # measured, and reported in this chapter's end-of, because a timestamp
        # that moves when nobody edited anything is a claim nobody made.
        flash(f"«{site}»: la stanza «{outcome.room_id}» aveva già questa "
              f"stratigrafia. {outcome.sent} operazioni consegnate, "
              f"{outcome.idempotent} rifiutate perché già presenti e "
              f"{outcome.applied} riapplicate senza aggiungere nulla. La "
              f"struttura del grafo non cambia.", "info")
    else:
        # `applied` conflates «created» and «merged» — the server does not
        # separate them — so the wording says «applicate» and never «aggiunte».
        flash(f"«{site}» → stanza «{outcome.room_id}»: {outcome.summary()}.",
              "success")
    for refusal in outcome.other_refusals[:5]:
        # A refusal that is NOT idempotency is a bug at this end, and it must
        # not be filed away with the ordinary ones.
        flash(f"Operazione rifiutata dalla stanza: {refusal}", "error")
    for line in outcome.skipped[:10]:
        flash(line, "warning")
    return redirect(url_for("stratigraph_room.index"))
