# pylint: skip-file
from models import *
from playhouse.migrate import *

migrator = MySQLMigrator(db)

# This is the part you change

# nullabling a field
#migrate(migrator.drop_not_null('match', 'seller_order_id'))


# adding a field
created_time = pw.BigIntegerField(null=False, default=get_time())
notification_subscription = pw.CharField(null=True)
migrate(
    migrator.add_column("loginsession", "created_time", created_time),
    migrator.add_column("loginsession", "notification_subscription", notification_subscription),
)

created_time = pw.BigIntegerField(null=False)
migrate(
    migrator.alter_column_type("loginsession", "created_time", created_time)
)

# Altering field type
notification_subscription = pw.TextField(null=True)

text = pw.TextField(null=False)
link = pw.TextField(null=True)

migrate(
    migrator.alter_column_type("loginsession", "notification_subscription", notification_subscription),
    migrator.alter_column_type("notification", "text", text),
    migrator.alter_column_type("notification", "link", link),
)

show_push_notifications = pw.BooleanField(null=False, default=True)
migrate(
    migrator.add_column("user", "show_push_notifications", show_push_notifications),
)

show_push_notifications = pw.BooleanField(null=False)
migrate(
    migrator.alter_column_type("user", "show_push_notifications", show_push_notifications)
)
