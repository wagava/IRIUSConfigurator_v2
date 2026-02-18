from django.contrib.auth import get_user_model
from django.shortcuts import redirect

from .forms import EquipmentForm
from .models import cnfEquipment, cnfSequenceRole

User = get_user_model()


class EquipmentViewMixin:
    """Миксин-класс переменной."""

    ITEM_NAMES = {
        "equipments_cnfequipmentlinkedpidvariable": [
            "var_pid_role",
            "var_pid_par",
            "var_pid_timer",
            "var_pid_masked",
            "pid",
        ],
        "equipments_cnfequipmentlinkedvariable": [
            "var_role",
            "var_par",
            "var_timer",
            "var_masked",
            "var",
        ],
        "equipments_cnfequipmentlinkedequipment": [
            "eq_role",
            "eq_par",
            "eq_timer",
            "eq_masked",
            "eq",
        ],
        #   'equipments_cnfsequencelinkedvariable':['seq_start_role',
        #                                               'eq_par',
        #                                               'eq_timer',
        #                                               'eq'],
        #   'equipments_cnfsequencelinkedequipment':['eq_role',
        #                                               'eq_par',
        #                                               'eq_timer',
        #                                               'eq'],
    }
    ITEM_SEQ_GROUP = {
        "start": 1,
        "quick_start": 2,
        "stop": 3,
        "em_stop": 4,
    }
    model = cnfEquipment
    template_name = "equipments/create.html"
    form_class = EquipmentForm

    def get_roles(self, form, model_link, model_role, model_type, var_pid_data=None):

        table_name = model_link._meta.db_table
        linked_records = []
        linked_records_create = []

        # 'equipments_cnfequipmentlinkedpidvariable'
        for item in range(1, 255):
            item_role_value = form.data.get(f"{self.ITEM_NAMES[table_name][0]}{item}")
            item_par_value = form.data.get(f"{self.ITEM_NAMES[table_name][1]}{item}")
            item_timer_value = form.data.get(f"{self.ITEM_NAMES[table_name][2]}{item}")
            item_masked_value = form.data.get(f"{self.ITEM_NAMES[table_name][3]}{item}")
            item_index = item
            idx = None
            if var_pid_data:
                for item_var_role in var_pid_data:
                    if item_role_value and item_role_value != "select_item":
                        if int(item_role_value) == item_var_role["n_role_id"]:
                        # if int(item_role_value) == item_var_role["n_role"]:
                            idx = item_var_role["id"]
                            var_pid_data.remove(item_var_role)
                            break
                    else:
                        break
            if item_role_value is None or item_role_value == "select_item":
                pass
            else:
                if self.ITEM_NAMES[table_name][4] == "pid":
                    if idx:
                        linked_records.append(
                            model_link(
                                id=idx,
                                n_timer=(
                                    item_timer_value if item_timer_value != "" else 0
                                ),
                                n_equipment=form.instance,
                                n_role=model_role.objects.get(id=item_role_value),
                                n_variable_link=model_type.objects.get(
                                    id=item_par_value,
                                ),
                                b_masked=True if item_masked_value == "on" else False,
                                n_index=item_index
                            )
                        )
                    else:
                        linked_records_create.append(
                            model_link(
                                n_timer=(
                                    item_timer_value if item_timer_value != "" else 0
                                ),
                                n_equipment=form.instance,
                                n_role=model_role.objects.get(id=item_role_value),
                                n_variable_link=model_type.objects.get(
                                    id=item_par_value
                                ),
                                b_masked=True if item_masked_value == "on" else False,
                                n_index=item_index
                            )
                        )
                elif self.ITEM_NAMES[table_name][4] == "var":
                    if idx:
                        linked_records.append(
                            model_link(
                                id=idx,
                                n_timer=(
                                    item_timer_value if item_timer_value != "" else 0
                                ),
                                n_equipment=form.instance,
                                n_role=model_role.objects.get(id=item_role_value),
                                n_variable=model_type.objects.get(id=item_par_value),
                                b_masked=True if item_masked_value == "on" else False,
                                n_index=item_index
                            )
                        )
                    else:
                        linked_records_create.append(
                            model_link(
                                n_timer=(
                                    item_timer_value if item_timer_value != "" else 0
                                ),
                                n_equipment=form.instance,
                                n_role=model_role.objects.get(id=item_role_value),
                                n_variable=model_type.objects.get(id=item_par_value),
                                b_masked=True if item_masked_value == "on" else False,
                                n_index=item_index
                            )
                        )
                else:
                    if idx:
                        linked_records.append(
                            model_link(
                                id=idx,
                                n_timer=(
                                    item_timer_value if item_timer_value != "" else 0
                                ),
                                n_equipment=form.instance,
                                n_role=model_role.objects.get(id=item_role_value),
                                n_equipment_link=model_type.objects.get(
                                    id=item_par_value
                                ),
                                b_masked=True if item_masked_value == "on" else False,
                                n_index=item_index
                            )
                        )
                    else:
                        linked_records_create.append(
                            model_link(
                                n_timer=(
                                    item_timer_value if item_timer_value != "" else 0
                                ),
                                n_equipment=form.instance,
                                n_role=model_role.objects.get(id=item_role_value),
                                n_equipment_link=model_type.objects.get(
                                    id=item_par_value
                                ),
                                b_masked=True if item_masked_value == "on" else False,
                                n_index=item_index
                            )
                        )

        return {
            "creating": linked_records_create,
            "updating": linked_records,
        }

    def get_sequences_roles(
        self,
        form,
        model_var_link,
        model_eq_link,
        model_role,
        model_var,
        model_eq,
        existing_data=None,
    ):
        # выбираем роли по индексу и флагу отношения к оборудованию
        all_roles = {
            item.n_role_index: item.b_role_equipment
            for item in model_role.objects.all()
        }

        # table_var_name = model_var_link._meta.db_table
        # table_eq_name = model_var_link._meta.db_table
        linked_var_records = []
        linked_var_records_create = []
        linked_eq_records = []
        linked_eq_records_create = []

        # 'equipments_cnfequipmentlinkedpidvariable'
        for seq_group, seq_group_num in self.ITEM_SEQ_GROUP.items():
            for item in range(1, 100):
                item_role_value = form.data.get(
                    f"seq_{seq_group}_role{item}"
                )  # индекс роли
                item_par_value = form.data.get(
                    f"seq_{seq_group}_par{item}"
                )  # индекс объекта(переменная/оборудование)
                item_timer_value = form.data.get(f"seq_{seq_group}_timer{item}")  #
                item_masked = form.data.get(f"seq_{seq_group}_masked{item}")

                idx = None
                if existing_data:
                    if (
                        existing_data.get(seq_group_num)
                        and len(existing_data[seq_group_num]) > 0
                    ):

                        for item_step in existing_data[seq_group_num]:

                            if (
                                item == item_step[1]["n_step"]
                                and item_par_value is not None
                                and item_par_value != "select_item"
                            ):
                                # Если роль с формы совпадает с ролью записи из БД - удаляем,
                                # чтобы запись обновилась (все что остается - позже удаляется)
                                if (
                                    item_step[1]["n_role__b_role_equipment"]
                                    == all_roles[int(item_role_value)]
                                ):
                                    idx = item_step[1]["id"]
                                    existing_data[seq_group_num].remove(item_step)
                                    break

                if (
                    item_role_value is None
                    or item_role_value == "select_item"
                    or item_par_value == "select_item"
                ):
                    break
                else:
                    # выясняем - оборудование или переменная
                    role_object = cnfSequenceRole.objects.get(id=item_role_value)

                    if role_object.b_role_equipment:
                        #  equipment
                        if idx:
                            linked_eq_records.append(
                                model_eq_link(
                                    id=idx,
                                    n_timer=item_timer_value,
                                    n_equipment=form.instance,
                                    n_role=role_object,
                                    n_equipment_link=model_eq.objects.get(
                                        id=item_par_value
                                    ),
                                    n_seq_type=seq_group_num,
                                    n_step=item,
                                    b_masked=True if item_masked == "on" else False,
                                )
                            )
                        else:
                            linked_eq_records_create.append(
                                model_eq_link(
                                    n_timer=item_timer_value,
                                    n_equipment=form.instance,
                                    n_role=role_object,
                                    n_equipment_link=model_eq.objects.get(
                                        id=item_par_value
                                    ),
                                    n_seq_type=seq_group_num,
                                    n_step=item,
                                    b_masked=True if item_masked == "on" else False,
                                )
                            )
                    else:
                        # variable
                        if idx:
                            linked_var_records.append(
                                model_var_link(
                                    id=idx,
                                    n_timer=item_timer_value,
                                    n_equipment=form.instance,
                                    n_role=role_object,
                                    n_variable_link=model_var.objects.get(
                                        id=item_par_value
                                    ),
                                    n_seq_type=seq_group_num,
                                    n_step=item,
                                    b_masked=True if item_masked == "on" else False,
                                )
                            )
                        else:
                            linked_var_records_create.append(
                                model_var_link(
                                    n_timer=item_timer_value,
                                    n_equipment=form.instance,
                                    n_role=role_object,
                                    n_variable_link=model_var.objects.get(
                                        id=item_par_value
                                    ),
                                    n_seq_type=seq_group_num,
                                    n_step=item,
                                    b_masked=True if item_masked == "on" else False,
                                )
                            )

        return {
            "variable": linked_var_records,
            "variable_create": linked_var_records_create,
            "equipment": linked_eq_records,
            "equipment_create": linked_eq_records_create,
        }


class EquipmentAuthMixin:
    """Миксин-класс оборудования для проверки пользователя."""

    def dispatch(self, request, *args, **kwargs):
        user = User.objects.get(username=self.request.user.username)
        if not user.is_staff:
            return redirect('equipments:equipment_home')
        return super().dispatch(request, *args, **kwargs)