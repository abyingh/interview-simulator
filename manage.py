import os, sys
from dotenv import load_dotenv
from django.core.management import execute_from_command_line

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

def main():
    try:
        load_dotenv()
    except ImportError:
        pass
    execute_from_command_line(sys.argv) # Run CLI commands (e.g. runserver, migrate)

if __name__ == '__main__':
    main()
