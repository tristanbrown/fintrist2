import os
import importlib

def upgrade():
    dynamic_import('upgrade')

def downgrade():
    dynamic_import('downgrade')

def dynamic_import(func):
    """Dynamically import and run a given function from all modules here."""
    base_path = os.path.dirname(os.path.realpath(__file__))
    python_executable = 'python3'

    module_list = [
        file_name.rstrip('.py') for file_name in os.listdir(base_path)
        if file_name.endswith('.py') and file_name.startswith('migrate')
    ]

    print(f'Running {func} migrations:')
    for i, module in enumerate(sorted(module_list)):
        print(f"   {i}: {module}")
        ## Import each migration
        mod = importlib.import_module(f'.{module}', 'fintrist.migrations')
        try:
            getattr(mod, func)()
            print(f"    -> {func} successful.")
        except AttributeError:
            print(f"    -> No {func} method.")
    print("Migrations complete")
