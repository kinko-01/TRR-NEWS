from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except ImportError:
    Limiter = None
    get_remote_address = None


db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to access the newsroom."
login_manager.login_message_category = "info"
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=[]) if Limiter else None
