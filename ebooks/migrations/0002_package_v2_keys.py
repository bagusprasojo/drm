from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ebooks", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="ebook",
            name="package_format_version",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="ebook",
            name="encrypted_content_key_b64",
            field=models.TextField(blank=True),
        ),
    ]
