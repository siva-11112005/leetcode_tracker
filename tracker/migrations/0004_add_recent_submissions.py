# Generated migration: add recent_submissions JSONField
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0003_add_streaks'),
    ]

    operations = [
        migrations.AddField(
            model_name='trackeduser',
            name='recent_submissions',
            field=models.JSONField(default=list, blank=True),
        ),
    ]
