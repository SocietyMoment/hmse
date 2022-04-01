# pylint: skip-file
from models import *
from playhouse.migrate import *

migrator = MySQLMigrator(db)

# This is the part you change

# nullabling a field
#migrate(migrator.drop_not_null('match', 'seller_order_id'))


# # adding a field
# created_time = pw.BigIntegerField(null=False, default=get_time())
# notification_subscription = pw.CharField(null=True)
# migrate(
#     migrator.add_column("loginsession", "created_time", created_time),
#     migrator.add_column("loginsession", "notification_subscription", notification_subscription),
# )
# 
# created_time = pw.BigIntegerField(null=False)
# migrate(
#     migrator.alter_column_type("loginsession", "created_time", created_time)
# )
# 
# # Altering field type
# notification_subscription = pw.TextField(null=True)
# 
# text = pw.TextField(null=False)
# link = pw.TextField(null=True)
# 
# migrate(
#     migrator.alter_column_type("loginsession", "notification_subscription", notification_subscription),
#     migrator.alter_column_type("notification", "text", text),
#     migrator.alter_column_type("notification", "link", link),
# )
# 
# show_push_notifications = pw.BooleanField(null=False, default=True)
# migrate(
#     migrator.add_column("user", "show_push_notifications", show_push_notifications),
# )
# 
# show_push_notifications = pw.BooleanField(null=False)
# migrate(
#     migrator.alter_column_type("user", "show_push_notifications", show_push_notifications)
# )

search_term = pw.CharField(null=True)
migrate(
    migrator.add_column("stonk", "search_term", search_term)
)

Stonk.update(search_term="black").where(Stonk.id==5905955).execute() # Black
Stonk.update(search_term="biden").where(Stonk.id==7541750).execute() # Biden
Stonk.update(search_term="women").where(Stonk.id==7548494).execute() # Women
Stonk.update(search_term="trump").where(Stonk.id==8774750).execute() # Trump
Stonk.update(search_term="transgender").where(Stonk.id==10374176).execute() # Trans
Stonk.update(search_term="antifa+blm").where(Stonk.id==17729659).execute() # Antifa
Stonk.update(search_term="russia").where(Stonk.id==19520289).execute() # Russia
Stonk.update(search_term="racism").where(Stonk.id==196812549).execute() # Racism
Stonk.update(search_term="autism").where(Stonk.id==196825465).execute() # Autism
Stonk.update(search_term="reddit").where(Stonk.id==291842910).execute() # Reddit

migrate(migrator.add_not_null('stonk', 'search_term'))
