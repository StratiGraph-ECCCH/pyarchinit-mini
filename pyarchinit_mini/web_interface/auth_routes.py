"""
Authentication routes for Flask web interface
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps

from pyarchinit_mini.services.user_service import UserService
from pyarchinit_mini.models.user import UserRole


# Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# User class for Flask-Login
class User(UserMixin):
    """User class for Flask-Login with PyArchInit granular permissions support"""

    def __init__(self, user_dict):
        self.id = user_dict["id"]
        self.username = user_dict["username"]
        self.email = user_dict["email"]
        self.full_name = user_dict["full_name"]
        self.role = user_dict["role"]
        self.is_active_user = user_dict["is_active"]
        self.is_superuser = user_dict["is_superuser"]
        # ORCID iD, when this person has one — the identity the StratiGraph
        # ecosystem indexes people by. `.get`, not `[...]`, because every other
        # caller of this constructor predates the column.
        self.orcid = user_dict.get("orcid")
        # PyArchInit granular permissions (loaded at login from pyarchinit_roles/permissions)
        self._pa_role_perms = None   # {'can_insert': bool, 'can_update': bool, ...}
        self._pa_table_perms = None  # {table_name: {'can_insert': bool, ...}}

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return self.is_active_user

    def has_role(self, role):
        """Check if user has specific role"""
        return self.role == role

    def _check_pa_permission(self, pa_key, table_name=None):
        """Check PyArchInit permission. Returns None if not available (fallback to role).
        Table-level permissions override role-level permissions."""
        # If table_name specified → check that table
        if table_name and self._pa_table_perms and table_name in self._pa_table_perms:
            return bool(self._pa_table_perms[table_name].get(pa_key, False))
        # If table_name NOT specified but table perms exist → user has granular perms,
        # so check if ANY table allows this action (conservative: if all deny, deny)
        if self._pa_table_perms and not table_name:
            # If there are table-level perms, they override the role
            return any(bool(tp.get(pa_key, False)) for tp in self._pa_table_perms.values())
        # Role-level
        if self._pa_role_perms:
            return bool(self._pa_role_perms.get(pa_key, False))
        return None  # No PA permissions → fallback to Mini role

    def can_create(self, table_name=None):
        """Check if user can create records (optionally for a specific table)"""
        pa = self._check_pa_permission('can_insert', table_name)
        if pa is not None:
            return pa
        return self.role in [UserRole.ADMIN.value, UserRole.OPERATOR.value]

    def can_edit(self, table_name=None):
        """Check if user can edit records"""
        pa = self._check_pa_permission('can_update', table_name)
        if pa is not None:
            return pa
        return self.role in [UserRole.ADMIN.value, UserRole.OPERATOR.value]

    def can_delete(self, table_name=None):
        """Check if user can delete records"""
        pa = self._check_pa_permission('can_delete', table_name)
        if pa is not None:
            return pa
        return self.role in [UserRole.ADMIN.value, UserRole.OPERATOR.value]

    def can_manage_users(self):
        """Check if user can manage other users"""
        return self.role == UserRole.ADMIN.value or self.is_superuser


# Permission decorators
def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.can_manage_users():
            flash('Accesso negato. Permessi amministratore richiesti.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def write_permission_required(f):
    """Decorator to require write permission (operator or admin)"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.can_create():
            flash('Accesso negato. Permessi di scrittura richiesti.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def init_login_manager(app, user_service):
    """
    Initialize Flask-Login

    Args:
        app: Flask app
        user_service: UserService instance
    """
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Devi effettuare il login per accedere a questa pagina."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID, with PyArchInit granular permissions if available"""
        user_dict = user_service.get_user_by_id(int(user_id))
        if user_dict:
            user = User(user_dict)
            # Load PyArchInit permissions if PostgreSQL DB
            try:
                db_manager = getattr(app, 'db_manager', None)
                if db_manager and 'postgresql' in str(db_manager.connection.engine.url):
                    from sqlalchemy import text
                    with db_manager.connection.get_session() as session:
                        # Check if pyarchinit tables exist
                        has_pa = session.execute(text(
                            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                            "WHERE table_name = 'pyarchinit_users')"
                        )).scalar()
                        if has_pa:
                            # Get PA role for this user
                            pa_user = session.execute(text(
                                "SELECT pu.role FROM pyarchinit_users pu WHERE pu.username = :u"
                            ), {'u': user.username}).fetchone()
                            if pa_user:
                                role_perms = session.execute(text(
                                    "SELECT can_insert, can_update, can_delete, can_view "
                                    "FROM pyarchinit_roles WHERE role_name = :r"
                                ), {'r': pa_user[0]}).fetchone()
                                if role_perms:
                                    user._pa_role_perms = {
                                        'can_insert': role_perms[0], 'can_update': role_perms[1],
                                        'can_delete': role_perms[2], 'can_view': role_perms[3]
                                    }
                                # Table-level overrides
                                pa_id = session.execute(text(
                                    "SELECT id FROM pyarchinit_users WHERE username = :u"
                                ), {'u': user.username}).fetchone()
                                if pa_id:
                                    table_rows = session.execute(text(
                                        "SELECT table_name, can_insert, can_update, can_delete, can_view "
                                        "FROM pyarchinit_permissions WHERE user_id = :uid"
                                    ), {'uid': pa_id[0]}).fetchall()
                                    if table_rows:
                                        user._pa_table_perms = {}
                                        for r in table_rows:
                                            user._pa_table_perms[r[0]] = {
                                                'can_insert': r[1], 'can_update': r[2],
                                                'can_delete': r[3], 'can_view': r[4]
                                            }
            except Exception:
                pass  # PyArchInit tables may not exist (SQLite)
            return user
        return None

    return login_manager


# Routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', 'off') == 'on'

        # Debug logging
        print(f"[LOGIN] Username: {username}, Remember: {remember}")

        # Get user service from app context
        from flask import current_app
        user_service = current_app.user_service

        # Debug: Check if user exists first
        print(f"[DEBUG] Looking up user: {username}")
        user_check = user_service.get_user_by_username(username)
        print(f"[DEBUG] User found: {user_check is not None}")
        if user_check:
            print(f"[DEBUG] User data: username={user_check.get('username')}, role={user_check.get('role')}, active={user_check.get('is_active')}")
            print(f"[DEBUG] Has hashed_password: {'hashed_password' in user_check}")

        # Authenticate
        user_dict = user_service.authenticate_user(username, password)
        print(f"[LOGIN] Authentication result: {user_dict is not None}")

        if user_dict:
            user = User(user_dict)
            login_user(user, remember=remember)
            print(f"[LOGIN] User logged in: {user.username}")
            flash(f'Benvenuto, {user.username}!', 'success')

            # Redirect to next page or index
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            print(f"[LOGIN] Authentication failed for username: {username}")
            flash('Username o password non corretti.', 'error')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout"""
    logout_user()
    flash('Logout effettuato con successo.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/users')
@admin_required
def users_list():
    """User management page (admin only)"""
    from flask import current_app
    user_service = current_app.user_service

    users = user_service.get_all_users()
    return render_template('auth/users.html', users=users, current_user=current_user)


@auth_bp.route('/users/create', methods=['POST'])
@admin_required
def create_user():
    """Create new user (admin only)"""
    from flask import current_app
    user_service = current_app.user_service

    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        role = request.form.get('role', 'VIEWER').upper()

        user = user_service.create_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            role=UserRole(role)
        )

        flash(f'Utente {username} creato con successo!', 'success')
    except ValueError as e:
        flash(f'Errore: {str(e)}', 'error')
    except Exception as e:
        flash(f'Errore durante la creazione utente: {str(e)}', 'error')

    return redirect(url_for('auth.users_list'))


@auth_bp.route('/users/<int:user_id>/edit', methods=['POST'])
@admin_required
def edit_user(user_id):
    """Edit user (admin only)"""
    from flask import current_app
    user_service = current_app.user_service

    try:
        updates = {}

        if request.form.get('email'):
            updates['email'] = request.form.get('email')
        if request.form.get('full_name'):
            updates['full_name'] = request.form.get('full_name')
        if request.form.get('role'):
            updates['role'] = UserRole(request.form.get('role').upper())
        if request.form.get('password'):
            updates['password'] = request.form.get('password')

        updates['is_active'] = request.form.get('is_active') == '1'

        user = user_service.update_user(user_id, **updates)

        if user:
            flash('Utente aggiornato con successo!', 'success')
        else:
            flash('Utente non trovato.', 'error')

    except Exception as e:
        flash(f'Errore durante l\'aggiornamento: {str(e)}', 'error')

    return redirect(url_for('auth.users_list'))


@auth_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete user (admin only)"""
    from flask import current_app
    user_service = current_app.user_service

    # Prevent deleting yourself
    if user_id == current_user.id:
        flash('Non puoi eliminare il tuo account!', 'error')
        return redirect(url_for('auth.users_list'))

    try:
        deleted = user_service.delete_user(user_id)

        if deleted:
            flash('Utente eliminato con successo!', 'success')
        else:
            flash('Utente non trovato.', 'error')

    except Exception as e:
        flash(f'Errore durante l\'eliminazione: {str(e)}', 'error')

    return redirect(url_for('auth.users_list'))


# ── the ORCID door, if this server has one ───────────────────────────────────
# ONE import, at the bottom, and the position is the point: by here `auth_bp`
# and `User` exist, so `oidc_routes` can attach `/auth/oidc/login` and
# `/auth/oidc/callback` to this blueprint without a second blueprint and
# without a line of the flow living in this file. A fork keeps its merge
# surface small by adding files, not by editing them.
#
# The routes exist but the door does not open unless the OIDC_* variables are
# set: see `oidc_routes.configuration_error()`. No variables, no door.
from . import oidc_routes  # noqa: E402,F401  (imported for its side effect)
