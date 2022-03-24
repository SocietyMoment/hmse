# pylint: skip-file
from models import *
from playhouse.migrate import *

migrator = MySQLMigrator(db)

# This is the part you change

# adding a field
#created_time = pw.BigIntegerField()
#migrate(migrator.add_column("notification", "created_time", created_time))

# nullabling a field
migrate(migrator.drop_not_null('match', 'seller_order_id'))
