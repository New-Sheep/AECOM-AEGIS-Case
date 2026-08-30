# Generated manually for operational_state + ScenarioClock

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0002_audit_shadow"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="baseline_load",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="asset",
            name="operational_state",
            field=models.CharField(
                choices=[
                    ("normal", "Normal"),
                    ("load_reduced", "Load reduced"),
                    ("deenergized", "Deenergized"),
                ],
                default="normal",
                max_length=32,
            ),
        ),
        migrations.CreateModel(
            name="ScenarioClock",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "sim_phase",
                    models.CharField(
                        choices=[
                            ("approach", "Approach"),
                            ("peak", "Peak"),
                            ("landfall", "Landfall"),
                            ("aftermath", "Aftermath"),
                        ],
                        default="peak",
                        max_length=32,
                    ),
                ),
                ("sim_tick", models.PositiveIntegerField(default=0)),
                ("paused", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "scenario clock",
                "verbose_name_plural": "scenario clocks",
            },
        ),
    ]
