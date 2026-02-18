import http

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect

from general.crypt import encrypt_password
from iriusconfig.settings import P_KEY

@csrf_exempt
def generate(request):
    if request.method == "POST":
        try:
            print("passw")
            # count = int(request.POST.get("count", 1))
            # discount = float(request.POST.get("discount", 0))
            # days_valid = int(request.POST.get("days_valid", 1))
            # cutoff = int(request.POST.get("cutoff", 1))
            password = request.POST.get("password", "")
            # length = int(request.POST.get("length", 4))
            epassword = encrypt_password(password,P_KEY)
            
            
            return JsonResponse(
                        {
                            "status": "success",
                            "message": "Пароль успешно сгенерирован!",
                            "password": epassword.decode()
                        }
            )
            

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=http.HTTPStatus.BAD_REQUEST)
    else:
        return JsonResponse(
            {"status": "error", "message": "Метод не поддерживается"},
            status=http.HTTPStatus.METHOD_NOT_ALLOWED,
        )
    
def index(request):
    return redirect('accounts:logout')