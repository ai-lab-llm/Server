# management/commands/import_users.py
import sqlite3
from django.core.management.base import BaseCommand
from django.conf import settings
from report.models import User 
import os

class Command(BaseCommand):
    help = "Import names from proctee.db users table"

    def handle(self, *args, **options):
        db_path = r"C:/Users/user/Server/db/protectee.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM users")
        rows = cursor.fetchall()
        count = 0

        for row in rows:
            name = row[0].strip()
            if name:
                obj, created = User.objects.get_or_create(name=name)
                if created:
                    count += 1

        conn.close()
        self.stdout.write(self.style.SUCCESS(f"Imported {count} names"))
