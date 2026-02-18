superuser: irius irius
test
***eee

## REST API

- Авторизация и получение токена
```
curl -X POST http://127.0.0.1:8000/api/auth/token/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "irius", "password": "irius"}'
```
- Обновление токена
```
curl -X POST http://127.0.0.1:8000/api/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc2MDY3MzQ4NiwiaWF0IjoxNzYwNTg3MDg2LCJqdGkiOiIzNzBiYjE4OWFhNjE0NjM3OTJhODY0YmVlZWM0ZWYxNSIsInVzZXJfaWQiOjF9.Z-cxMW34mQUfzqq84SYpGHa0v-MdJt8dwdHmVPL2Ag8"}'
```
- Получение данных по ПИД
```
curl -X GET \
  "http://127.0.0.1:8000/api/equipment/pid?index=2&plc=1" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzYwNTg4MDgxLCJpYXQiOjE3NjA1ODU1NjgsImp0aSI6ImZmZjMxNDNiNjVjOTRjNGRhMWRhZTkxMTc3ZTM5ZmQxIiwidXNlcl9pZCI6MX0.35Ft6YFKFE7AZsQY8VpVVLz5zHjCTd5EjBHowcFSpNE"
```
- Запись данных по ПИД
curl -X PATCH "http://127.0.0.1:8000/api/equipment/pid" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzYwNTg4OTYwLCJpYXQiOjE3NjA1ODU1NjgsImp0aSI6ImE4OWQwMDE1OWEwODRkMzRiMzJjZDhlOTY0YjIzYjVkIiwidXNlcl9pZCI6MX0.8oR62rifB_LYm6WMSUQt53BCGpZSQhT9TAVwvnskceQ" \
  -H "Content-Type: application/json" \
  -d '{
    "equipment_data": [
        {
            "plc": 1,
            "equipment_index": 2,
            "attributes": {
                "PID_Kp": 0.51,
                "PID_Ti": 5.0,
                "PID_Td": 0.0
            }
        }
    ]
}'