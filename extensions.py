from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# Shared extensions to avoid circular imports.
db = SQLAlchemy()
migrate = Migrate()
