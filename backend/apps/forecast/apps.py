from django.apps import AppConfig


class ForecastConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.forecast"

    def ready(self):
        import sys

        if any(cmd in sys.argv for cmd in ("migrate", "makemigrations")):
            return
        from apps.forecast.runtime import load_runtime

        load_runtime()
