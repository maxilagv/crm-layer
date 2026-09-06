from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("business_settings", "0003_prospectingpolicy"),
    ]

    operations = [
        migrations.AddField(
            model_name="businessprofile",
            name="closer_name",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="businessprofile",
            name="closer_role",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="businessprofile",
            name="closer_whatsapp",
            field=models.CharField(blank=True, max_length=32),
        ),
    ]
