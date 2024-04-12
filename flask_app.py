import collections
import json
import os
import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import cartolafc.models

root_dir = os.path.dirname(os.path.abspath(__file__))

# api = cartolafc.Api(
#     glb_id='1804eaefa2b2592ad3b903c0d2304a289553238525168785a66324c694844376d434f67565a7763754e376f7368386a32337a48735a36364f364d4c794a644b53674f486b544349546765654f7274375950345f5f58624c575463445661566b7263525a6958513d3d3a303a646965676f2e323031312e382e35')

# ------------- Isso não funciona ---------------

bearer_token = "Bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJXLUppTjhfZXdyWE9uVnJFN2lfOGpIY28yU1R4dEtHZF94aW01R2N4WS1ZIn0.eyJleHAiOjE3MTU1MTg4MzUsImlhdCI6MTcxMjkyNjgzNSwiYXV0aF90aW1lIjoxNzEyOTI2ODM0LCJqdGkiOiI1MTE2ODQ4ZS1jNDU3LTQ3YmEtOTI1MC05OGY4MmQ3YmM3ZDIiLCJpc3MiOiJodHRwczovL2lkLmdsb2JvLmNvbS9hdXRoL3JlYWxtcy9nbG9iby5jb20iLCJzdWIiOiJmOjNjZGVhMWZiLTAwMmYtNDg5ZS1iOWMyLWQ1N2FiYTBhZTQ5NDpkMmJiNGVhMC1lOGQzLTQyOTItODQzZS03ZWYzYzBjMDEwOWQiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJjYXJ0b2xhQGFwcHMuZ2xvYm9pZCIsInNlc3Npb25fc3RhdGUiOiJiMmQ4YWJiNC1hZWQyLTRmZmEtYWM0ZS00ZGMxZTEzY2NlNDciLCJhY3IiOiIxIiwic2NvcGUiOiJvcGVuaWQgZW1haWwgcHJvZmlsZSBnbG9ib2lkIiwic2lkIjoiYjJkOGFiYjQtYWVkMi00ZmZhLWFjNGUtNGRjMWUxM2NjZTQ3IiwiZW1haWxfdmVyaWZpZWQiOnRydWUsIm5hbWUiOiJEaWVnbyBCYXJyb3NvIFBlcmVpcmEiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJkaWVnby4yMDExLjguNSIsImVtYWlsIjoiZGllZ29iYXJwZXJlaXJhQGdtYWlsLmNvbSIsImdsb2JvX2lkIjoiZDJiYjRlYTAtZThkMy00MjkyLTg0M2UtN2VmM2MwYzAxMDlkIn0.F1kqGsjrcwMYAAsLxaJF33eZuOredXQ-vqipo5PXIS9Mgis8NHLJNEzf67OQ6lPDvJN4KqNtXu_hoZ6GsVKXY17_XF0hdGRzTRgxteX4y5KadeyUxWNlkQigDMCSlhPVVGCr1ufeUKn8d_JcCWp8nSNZpaIjLIR6Mlh_BXyKj4xxK-0vH-MT-CH1XmysZMR3GDs-iLq4M8d-7J1QnaO-J7MN1L2Tt3mmwaBXxn35qC_XUF1bTV5sTwpf6hC0QgPOshRuDjz3HOZn8aUky4ox7adTHfvFe4ZHdcUrdncFiclqiobcPhFCWYcokFGSHyoYJMlLlzO_e1Y6HdzEoPhopQ"
api = cartolafc.Api(bearer_token=bearer_token)

times_ids = []
ligas = api.pontoscorridos('co1nbb2k58mq18etloj0')

for lig in ligas.times:
    times_ids.append(lig.ids)

print(times_ids)

# ------------- Isso não funciona ---------------


# ----------- Essa parte funciona!!! ------------------------

# bearer_token = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJXLUppTjhfZXdyWE9uVnJFN2lfOGpIY28yU1R4dEtHZF94aW01R2N4WS1ZIn0.eyJleHAiOjE3MTU1MTg4MzUsImlhdCI6MTcxMjkyNjgzNSwiYXV0aF90aW1lIjoxNzEyOTI2ODM0LCJqdGkiOiI1MTE2ODQ4ZS1jNDU3LTQ3YmEtOTI1MC05OGY4MmQ3YmM3ZDIiLCJpc3MiOiJodHRwczovL2lkLmdsb2JvLmNvbS9hdXRoL3JlYWxtcy9nbG9iby5jb20iLCJzdWIiOiJmOjNjZGVhMWZiLTAwMmYtNDg5ZS1iOWMyLWQ1N2FiYTBhZTQ5NDpkMmJiNGVhMC1lOGQzLTQyOTItODQzZS03ZWYzYzBjMDEwOWQiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJjYXJ0b2xhQGFwcHMuZ2xvYm9pZCIsInNlc3Npb25fc3RhdGUiOiJiMmQ4YWJiNC1hZWQyLTRmZmEtYWM0ZS00ZGMxZTEzY2NlNDciLCJhY3IiOiIxIiwic2NvcGUiOiJvcGVuaWQgZW1haWwgcHJvZmlsZSBnbG9ib2lkIiwic2lkIjoiYjJkOGFiYjQtYWVkMi00ZmZhLWFjNGUtNGRjMWUxM2NjZTQ3IiwiZW1haWxfdmVyaWZpZWQiOnRydWUsIm5hbWUiOiJEaWVnbyBCYXJyb3NvIFBlcmVpcmEiLCJwcmVmZXJyZWRfdXNlcm5hbWUiOiJkaWVnby4yMDExLjguNSIsImVtYWlsIjoiZGllZ29iYXJwZXJlaXJhQGdtYWlsLmNvbSIsImdsb2JvX2lkIjoiZDJiYjRlYTAtZThkMy00MjkyLTg0M2UtN2VmM2MwYzAxMDlkIn0.F1kqGsjrcwMYAAsLxaJF33eZuOredXQ-vqipo5PXIS9Mgis8NHLJNEzf67OQ6lPDvJN4KqNtXu_hoZ6GsVKXY17_XF0hdGRzTRgxteX4y5KadeyUxWNlkQigDMCSlhPVVGCr1ufeUKn8d_JcCWp8nSNZpaIjLIR6Mlh_BXyKj4xxK-0vH-MT-CH1XmysZMR3GDs-iLq4M8d-7J1QnaO-J7MN1L2Tt3mmwaBXxn35qC_XUF1bTV5sTwpf6hC0QgPOshRuDjz3HOZn8aUky4ox7adTHfvFe4ZHdcUrdncFiclqiobcPhFCWYcokFGSHyoYJMlLlzO_e1Y6HdzEoPhopQ"
#
# headers = {'Content-Type': 'application/json',
#            "Authorization": f"Bearer {bearer_token}"}
#
# response = requests.get("https://api.cartola.globo.com/auth/competicoes/pontoscorridos/slug/co1nbb2k58mq18etloj0", headers=headers)
#
# print(response.json())

# '----------- Essa parte funciona!!! ------------------------