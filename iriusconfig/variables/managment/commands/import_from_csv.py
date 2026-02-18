from csv import DictReader

from django.core.management import BaseCommand
from variables.models import cnfVariable, cnfVariableValue

from iriusconfig.settings import STATICFILES_DIRS

ORDER_FOR_IMPORT = {
    "variable": cnfVariable,
    "variable_values": cnfVariableValue,
}


class Command(BaseCommand):
    """Импорт данных из csv-файла в БД."""

    def handle(self, *args, **options):
        for item_name, item_model in ORDER_FOR_IMPORT.items():
            for row in DictReader(
                open(f"{STATICFILES_DIRS[0]}/data/{item_name}.csv", encoding="utf8")
            ):

                if not isinstance(item_model, dict):
                    row_db = item_model(**row)
                    self.save_to_db(row, row_db, item_model)
                elif isinstance(item_model, dict):
                    self.save_to_db_with_assign_fields(row, item_model)

    def save_to_db(self, row, row_db, model):
        pass

    def save_to_db_with_assign_fields(self, row, item_model):
        pass
