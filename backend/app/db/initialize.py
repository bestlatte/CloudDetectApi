from alembic.config import Config

from alembic import command
from app.core.config import get_settings
from app.db.seed import seed_monitors


def main() -> None:
    settings = get_settings()
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
    command.upgrade(config, "head")
    print({"seeded": seed_monitors()})


if __name__ == "__main__":
    main()

