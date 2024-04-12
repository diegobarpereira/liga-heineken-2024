# -*- coding: utf-8 -*-

import json
from collections import namedtuple
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar
from .util import json_default

Posicao = namedtuple('Posicao', ['id', 'nome', 'abreviacao'])
Status = namedtuple('Status', ['id', 'nome'])

_posicoes = {
    1: Posicao(1, 'Goleiro', 'GOL'),
    2: Posicao(2, 'Lateral', 'LAT'),
    3: Posicao(3, 'Zagueiro', 'ZAG'),
    4: Posicao(4, 'Meia', 'MEI'),
    5: Posicao(5, 'Atacante', 'ATA'),
    6: Posicao(6, 'Técnico', 'TEC')
}

_atleta_status = {
    2: Status(2, 'Dúvida'),
    3: Status(3, 'Suspenso'),
    5: Status(5, 'Contundido'),
    6: Status(6, 'Nulo'),
    7: Status(7, 'Provável')
}

_mercado_status = {
    # 2: Status(2, 'Mercado aberto'),
    # 1: Status(1, 'Mercado fechado'),
    1: Status(1, 'Mercado aberto'),
    2: Status(2, 'Mercado fechado'),
    3: Status(3, 'Mercado em atualização'),
    4: Status(4, 'Mercado em manutenção'),
    6: Status(6, 'Final de temporada')
}

T = TypeVar('T', bound='BaseModel')


class BaseModel(object):
    def __repr__(self) -> str:
        return json.dumps(self, default=json_default)

    @classmethod
    def from_dict(cls: Type[T], *args: Tuple[Any], **kwargs: Dict[str, Any]) -> T:
        raise NotImplementedError


class TimeInfo(BaseModel):
    """ Time Info """

    def __init__(self, time_id: int, nome: str, nome_cartola: str, slug: str, assinante: bool,
                 pontos: float, ids: List[int], ids_: List[int], foto: str, pts_rodada: float) -> None:
        self.id = time_id
        self.nome = nome
        self.nome_cartola = nome_cartola
        self.slug = slug
        self.assinante = assinante
        self.pontos = pontos
        self.ids = ids
        self.ids_ = ids_
        self.foto = foto
        self.pts_rodada = pts_rodada

    @classmethod
    def from_dict(cls, data: dict, ranking: str = None) -> 'TimeInfo':
        pontos = data['pontos'][ranking] if ranking and ranking in data['pontos'] else None
        pts_rodada = data['pontos']['rodada'] if ranking and ranking in data['pontos'] else None
        lista_ids = data['time_id'] if 'time_id' in data else None
        lista2_ids = [data['time_id'] if 'time_id' in data else None]
        return cls(data['time_id'], data['nome'], data['nome_cartola'], data['slug'], data['assinante'], pontos,
                   lista_ids, lista2_ids, data['url_escudo_svg'], pts_rodada)


class Clube(BaseModel):
    """ Representa um dos 20 clubes presentes no campeonato, e possui informações como o nome e a abreviação """

    def __init__(self, clube_id: int, nome: str, abreviacao: str, escudos: Dict[str, str]) -> None:
        self.id = clube_id
        self.nome = nome
        self.abreviacao = abreviacao
        self.escudos = escudos if escudos else ''

    @classmethod
    def from_dict(cls, data: dict) -> 'Clube':
        return cls(data['id'], data['nome'], data['abreviacao'], data['escudos']['60x60'])


class Atleta(BaseModel):
    """ Representa um atleta (jogador ou técnico), e possui informações como o apelido, clube e pontuação obtida """

    def __init__(self, atleta_id: int, apelido: str, foto: str, pontos: float, scout: Dict[str, int], posicao_id: int,
                 jogos_num: int, media_num: int, entrou_em_campo: bool, clube: Clube,
                 minimo_para_valorizar: Optional[float] = 0, status_id: Optional[int] = None, is_capitao: Optional[bool] = None) -> None:

        self.id = atleta_id
        self.apelido = apelido
        self.foto = foto
        self.pontos = pontos
        self.scout = scout if scout else ''
        self.posicao = _posicoes[posicao_id]
        self.jogos_num = jogos_num
        self.media_num = media_num
        self.entrou_em_campo = entrou_em_campo
        self.clube = clube
        self.minimo_para_valorizar = minimo_para_valorizar if minimo_para_valorizar else 0.00
        self.status = _atleta_status[status_id] if status_id else None
        self.is_capitao = is_capitao

    def __lt__(self, other):
        return self.pontos < other.pontos

    @classmethod
    def from_dict(cls, data: dict, clubes: Dict[int, Clube], atleta_id: Optional[int] = None,
                  minimo_para_valorizar: Optional[float] = 0.00, is_capitao: Optional[bool] = None, default=None) -> 'Atleta':

        atleta_id = atleta_id if atleta_id else data['atleta_id']
        foto = data['foto'] if data['foto'] is not None else ''
        pontos = data['pontos_num'] if 'pontos_num' in data else data['pontuacao']
        clube = clubes.get(data['clube_id']) if data['clube_id'] != 1 else ''
        jogos_num = data['jogos_num'] if 'jogos_num' in data else None
        media_num = data['media_num'] if 'media_num' in data else None
        entrou_em_campo = data['entrou_em_campo'] if 'entrou_em_campo' in data else None
        minimo_para_valorizar = data['minimo_para_valorizar'] if 'minimo_para_valorizar' in data else 0.00

        return cls(
            atleta_id, data['apelido'],
            foto,
            pontos,
            data['scout'],
            data['posicao_id'],
            jogos_num,
            media_num,
            entrou_em_campo,
            clube,
            minimo_para_valorizar,
            data.get('status_id', None),
            is_capitao
        )


class Clube_Atleta(BaseModel):
    """ Representa um atleta (jogador ou técnico), e possui informações como o apelido, clube e pontuação obtida """

    def __init__(self, id: int, nome: str, abreviacao: str) -> None:
        self.id = id
        self.nome = nome
        self.abreviacao = abreviacao

    @classmethod
    def from_dict(cls, data: dict, clubes: Dict[int, Clube]) -> 'Clube_Atleta':
        clube = clubes.get(data['clube_id']) if data['clube_id'] != 1 else ''

        return cls(
            data['id'], data['nome'], data['abreviacao']
        )


class DestaqueRodada(BaseModel):
    """ Destaque Rodada"""

    def __init__(self, media_cartoletas: float, media_pontos: float, mito_rodada: TimeInfo) -> None:
        self.media_cartoletas = media_cartoletas
        self.media_pontos = media_pontos
        self.mito_rodada = mito_rodada

    @classmethod
    def from_dict(cls, data: dict) -> 'DestaqueRodada':
        mito_rodada = TimeInfo.from_dict(data['mito_rodada'])
        return cls(data['media_cartoletas'], data['media_pontos'], mito_rodada)


class Destaques(BaseModel):
    """ Destaques """

    def __init__(self, posicao: str, clube_nome: str, escudo_clube: str, escalacoes: int, atleta: Dict[str, str],
                 adv: str, minimo_para_valorizar: float, mand: bool) -> None:
        self.posicao = posicao
        self.clube_nome = clube_nome
        self.escudo_clube = escudo_clube
        self.escalacoes = escalacoes
        self.atleta = atleta
        self.adv = adv
        self.minimo_para_valorizar = minimo_para_valorizar
        self.mand = mand

    @classmethod
    def from_dict(cls, data: dict, adv=None, minimo_para_valorizar=0.00, mand=None) -> 'Destaques':
        return cls(data['posicao'], data['clube_nome'], data['escudo_clube'], data['escalacoes'], data['Atleta'], adv,
                   minimo_para_valorizar, mand)


class Capitaes(BaseModel):
    """ Capitaes """

    def __init__(self, posicao: str, clube_nome: str, clube_id: int, escudo_clube: str, escalacoes: int,
                 atleta: Dict[str, str], adv: str, minimo_para_valorizar: float, mand: bool) -> None:
        self.posicao = posicao
        self.clube_nome = clube_nome
        self.clube_id = clube_id
        self.escudo_clube = escudo_clube
        self.escalacoes = escalacoes
        self.atleta = atleta
        self.adv = adv
        self.minimo_para_valorizar = minimo_para_valorizar
        self.mand = mand

    @classmethod
    def from_dict(cls, data: dict, clube_nome=None, adv=None, minimo_para_valorizar=0.00, mand=None) -> 'Capitaes':
        return cls(data['posicao'], clube_nome, data['clube_id'], data['escudo_clube'], data['escalacoes'], data['Atleta'],
                   adv, minimo_para_valorizar, mand)


class Reservas(BaseModel):
    """ Reservas """

    def __init__(self, posicao: str, clube_nome: str, clube_id: int, escudo_clube: str, escalacoes: int,
                 atleta: Dict[str, str], adv: str, minimo_para_valorizar: float, mand: bool) -> None:
        self.posicao = posicao
        self.clube_nome = clube_nome
        self.clube_id = clube_id
        self.escudo_clube = escudo_clube
        self.escalacoes = escalacoes
        self.atleta = atleta
        self.adv = adv
        self.minimo_para_valorizar = minimo_para_valorizar
        self.mand = mand

    @classmethod
    def from_dict(cls, data: dict, clube_nome=None, adv=None, minimo_para_valorizar=0.00, mand=None) -> 'Reservas':
        return cls(data['posicao'], clube_nome, data['clube_id'], data['escudo_clube'], data['escalacoes'], data['Atleta'],
                   adv, minimo_para_valorizar, mand)


class Liga(BaseModel):
    """ Liga """

    def __init__(self, liga_id: int, nome: str, slug: str, descricao: str, times: List[TimeInfo], escudo: str) -> None:
        self.id = liga_id
        self.nome = nome
        self.slug = slug
        self.descricao = descricao
        self.times = times
        self.escudo = escudo

    @classmethod
    def from_dict(cls, data: dict, ranking: Optional[str] = None) -> 'Liga':
        data_liga = data.get('liga', data)
        times = [TimeInfo.from_dict(time, ranking=ranking) for time in data['times']] if 'times' in data else None
        return cls(data_liga['liga_id'], data_liga['nome'], data_liga['slug'], data_liga['descricao'], times,
                   data_liga['url_flamula_png'])


class LigaPatrocinador(BaseModel):
    """ Liga Patrocinador """

    def __init__(self, liga_id: int, nome: str, url_link: str) -> None:
        self.id = liga_id
        self.nome = nome
        self.url_link = url_link

    @classmethod
    def from_dict(cls, data: dict) -> 'LigaPatrocinador':
        return cls(data['liga_id'], data['nome'], data['url_link'])


class Mercado(BaseModel):
    """ Mercado """

    # def __init__(self, rodada_atual: int, status_mercado: int, times_escalados: int, aviso: str,
    #             fechamento: datetime) -> None:
    def __init__(self, rodada_atual: int, status_mercado: int, times_escalados: int, fechamento: datetime) -> None:
        self.rodada_atual = rodada_atual
        self.status = _mercado_status[status_mercado]
        self.times_escalados = times_escalados
        # self.aviso = aviso
        self.fechamento = fechamento

    @classmethod
    def from_dict(cls, data: dict) -> 'Mercado':
        fechamento = datetime(
            data['fechamento']['ano'],
            data['fechamento']['mes'],
            data['fechamento']['dia'],
            data['fechamento']['hora'],
            data['fechamento']['minuto'],
        )
        # return cls(data['rodada_atual'], data['status_mercado'], data['times_escalados'], data['aviso'], fechamento)
        return cls(data['rodada_atual'], data['status_mercado'], data['times_escalados'], fechamento)


class Partida(BaseModel):
    """ Partida """

    def __init__(self, data: datetime, local: str, valida: bool, clube_casa: Clube, placar_casa: int,
                 clube_visitante: Clube,
                 placar_visitante: int, fim_de_jogo: str, status_transmissao_tr: str,
                 clube_casa_escudo: Clube, clube_visitante_escudo: Clube, clube_casa_posicao: int, clube_visitante_posicao: int) -> None:
        self.data = data
        self.local = local
        self.valida = valida
        self.clube_casa = clube_casa
        self.placar_casa = placar_casa
        self.clube_visitante = clube_visitante
        self.placar_visitante = placar_visitante
        self.fim_de_jogo = fim_de_jogo
        self.status_transmissao_tr = status_transmissao_tr
        self.clube_casa_escudo = clube_casa_escudo
        self.clube_visitante_escudo = clube_visitante_escudo
        self.clube_casa_posicao = clube_casa_posicao
        self.clube_visitante_posicao = clube_visitante_posicao

    @classmethod
    def from_dict(cls, data: dict, clubes: Dict[int, Clube]) -> 'Partida':
        data_ = datetime.strptime(data['partida_data'], '%Y-%m-%d %H:%M:%S')
        local = data['local']
        valida = data['valida']
        clube_casa = clubes[data['clube_casa_id']]
        placar_casa = data['placar_oficial_mandante']
        clube_visitante = clubes[data['clube_visitante_id']]
        placar_visitante = data['placar_oficial_visitante']
        fim_de_jogo = data['transmissao']['label']
        status_transmissao_tr = data['status_transmissao_tr']
        clube_casa_escudo = clubes[data['clube_casa_id']]
        clube_visitante_escudo = clubes[data['clube_visitante_id']]
        clube_casa_posicao = data['clube_casa_posicao']
        clube_visitante_posicao = data['clube_visitante_posicao']

        return cls(data_, local, valida, clube_casa, placar_casa, clube_visitante, placar_visitante, fim_de_jogo,
                   status_transmissao_tr, clube_casa_escudo, clube_visitante_escudo, clube_casa_posicao, clube_visitante_posicao)


class PontuacaoInfo(BaseModel):
    """ Pontuação Info """

    def __init__(self, atleta_id: int, rodada_id: int, pontos: float, preco: float, variacao: float,
                 media: float) -> None:
        self.atleta_id = atleta_id
        self.rodada_id = rodada_id
        self.pontos = pontos
        self.preco = preco
        self.variacao = variacao
        self.media = media

    @classmethod
    def from_dict(cls, data: dict) -> 'PontuacaoInfo':
        return cls(data['atleta_id'], data['rodada_id'], data['pontos'], data['preco'], data['variacao'], data['media'])


class Time(BaseModel):
    """ Time """

    def __init__(self, patrimonio: float, valor_time: float, ultima_pontuacao: float, atletas: List[Atleta],
                 reservas: List[Atleta], info: TimeInfo, pontos: float, rodada_atual: int) -> None:
        self.patrimonio = patrimonio
        self.valor_time = valor_time
        self.ultima_pontuacao = ultima_pontuacao
        self.atletas = atletas
        self.reservas = reservas
        self.info = info
        # self.pontos = None
        self.pontos = pontos
        self.rodada_atual = rodada_atual

    @classmethod
    def from_dict(cls, data: dict, clubes: Dict[int, Clube], capitao: int) -> 'Time':
        data['atletas'].sort(key=lambda a: a['posicao_id'])

        atletas = [
            Atleta.from_dict(atleta, clubes, is_capitao=atleta['atleta_id'] == capitao)
            for atleta in data['atletas']
        ]

        data['reservas'].sort(key=lambda a: a['posicao_id']) if 'reservas' in data else None

        reservas = [
            Atleta.from_dict(reserva, clubes, is_capitao=reserva['atleta_id'] == capitao)
            for reserva in data['reservas']
        ] if 'reservas' in data else None

        info = TimeInfo.from_dict(data['time'])
        return cls(data['patrimonio'], data['valor_time'], data['pontos'], atletas, reservas, info,
                   data['pontos_campeonato'], data['rodada_atual'])
