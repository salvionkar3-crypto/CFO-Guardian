"""Database Base and Schema Initializer

Imports Base and all 13 model declarations so SQLAlchemy can initialize tables.
"""

from app.db.session import Base, engine
import app.models  # noqa: F401


def init_db():
    """Creates database tables if they do not exist."""
    Base.metadata.create_all(bind=engine)
