from django.db import transaction
from equipments.models import cnfEquipment, cnfEquipmentValue
from general.models import cnfAttribute
from equipments.views import download_equipments

def save_equipment_attributes_to_db(equipment_data):
    """
    Сохраняет или обновляет значения атрибутов для указанного оборудования.
    """
    try:
        with transaction.atomic():
            for item in equipment_data:
                equipment_index = item["equipment_index"]
                plc_id = item["plc"]
                attributes = item["attributes"]

                # Получение оборудования
                equipment = cnfEquipment.objects.get(n_controller=plc_id, n_equipment_index=equipment_index)

                # Обновление или создание значений атрибутов
                for attr_name, value in attributes.items():
                    attrname = attr_name.replace("_",".")
                    attribute = cnfAttribute.objects.get(c_name_attribute=attrname)
                    cnfEquipmentValue.objects.update_or_create(
                        n_equipment=equipment,
                        n_attribute=attribute,
                        defaults={"f_value": value}
                    )
    except Exception as error:
        print(error)
        
def save_equipment_to_plc(equipment_data):
    """
    Сохраняет или обновляет указанное оборудования в контроллер.
    """
    for item in equipment_data:
        equipment_index = item["equipment_index"]
        plc_id = item["plc"]
        equipment = cnfEquipment.objects.get(n_controller=plc_id, n_equipment_index=equipment_index)

        # download_equipments(
        #             request=False, plc_id=plc_id, min=equipment.pk, max=equipment.pk, ajax=False
        #         )
