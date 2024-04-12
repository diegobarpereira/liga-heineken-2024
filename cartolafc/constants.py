import json
import os

global local
global prod

local = False
prod = False

# if "C:\\" in os.getcwd():
#     local = True
# else:
#     prod = True
#
MERCADO_ABERTO = 1
MERCADO_FECHADO = 2

CAMPEONATO = 'campeonato'
TURNO = 'turno'
MES = 'mes'
RODADA = 'rodada'
PATRIMONIO = 'patrimonio'
#
# dict_prem = {}
#
# if not local:
#     with open('./tmp/dict_prem.json', encoding='utf-8', mode='r') as currentFile:
#         data = currentFile.read().replace('\n', '')
#         for k, v in json.loads(data).items():
#             dict_prem[k] = v
# else:
#     with open('static/dict_prem.json', encoding='utf-8', mode='r') as currentFile:
#         data = currentFile.read().replace('\n', '')
#         for k, v in json.loads(data).items():
#             dict_prem[k] = v
#
# with open('static/dict_prem.json', encoding='utf-8', mode='r') as currentFile:
#     data = currentFile.read().replace('\n', '')
#     for k, v in json.loads(data).items():
#         dict_prem[k] = v
#
# rodadas_campeonato = range(1, 39)
# rodadas_primeiro_turno = range(1, 20)
# rodadas_segundo_turno = range(20, 39)
# rodadas_liberta_prim_turno = range(2, 12)
# rodadas_oitavas_prim_turno = range(12, 14)
# rodadas_quartas_prim_turno = range(14, 16)
# rodadas_semis_prim_turno = range(16, 18)
# rodadas_finais_prim_turno = range(18, 20)
# rodadas_liberta_seg_turno = range(21, 31)
# rodadas_oitavas_seg_turno = range(31, 33)
# rodadas_quartas_seg_turno = range(33, 35)
# rodadas_semis_seg_turno = range(35, 37)
# rodadas_finais_seg_turno = range(37, 39)
#
# grupo_liberta_prim_turno = [44558779, 1241021, 1893918, 1889674,
#                             19190102, 47620752, 219929, 279314,
#                             1245808, 44509672, 18796615, 13957925,
#                             47803719, 25582672, 48733, 3646412, 8912058,
#                             315637, 71375, 1235701, 977136, 28919430]
#
# grupo_liberta_seg_turno = [
#                             13957925, 315637, 18796615, 8912058,
#                             279314, 28919430, 1889674, 3646412,
#                             48733, 19190102, 977136, 44509672,
#                             47620752, 1235701, 1245808, 1241021, 25582672,
#                             71375, 44558779, 219929, 47803719, 1893918
#                             ]
#
#
# list_oitavas_prim_turno = ['47620752', '13957925', '279314', '3646412', '1889674', '8912058', '977136', '315637', '1893918', '18796615', '71375', '25582672', '44558779', '28919430', '48733', '1245808']
#
# list_quartas_prim_turno = ['47620752', '18796615', '279314', '1889674', '13957925', '1893918', '44558779', '71375']
#
# list_semis_prim_turno = ['219929', '3646412', '25588958', '28919430']
#
# list_finais_prim_turno = ['3646412', '28919430']
#
# premios = {
#     'prem_camp_geral': 945.00,
#     'prem_vice_geral': 420.00,
#     'prem_terc_geral': 210.00,
#     'prem_quarto_geral': 105.00,
#     'prem_camp_turno': 210.00,
#     'prem_camp_mm': 393.75,
#     'prem_vice_mm': 131.25
# }
#
# list_quartas_seg_turno = []
#
# list_semis_seg_turno = []
#
# list_finais_seg_turno = []
#
# dict_matamata = {}
#
# list_oitavas_seg_turno = ["25582672", "48733", "28919430", "44558779", "13957925", "3646412", "18796615", "19190102", "1241021", "71375", "1893918", "47620752", "8912058", "219929", "1235701", "1889674"]
