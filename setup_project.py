import os
import sys

base_dir = "/Users/techstore/Desktop/yangi_loyiha_noyabr"

# 1. Update apps/<name>/apps.py
apps = ['accounts', 'academic', 'assessment', 'analytics', 'gamification']
for app in apps:
    app_py_path = os.path.join(base_dir, f"apps/{app}/apps.py")
    with open(app_py_path, "w") as f:
        f.write(f"""from django.apps import AppConfig

class {app.capitalize()}Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.{app}'
""")

print("Apps config updated.")
