# pylint: skip-file
from models import *
from playhouse.migrate import *

migrator = MySQLMigrator(db)


# This is the part you change
created_time = pw.BigIntegerField()
migrate(migrator.add_column("notification", "created_time", created_time))
