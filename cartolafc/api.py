# -*- coding: utf-8 -*-
import concurrent.futures
import json
import logging
from fileinput import filename
from typing import Any, Dict, List, Optional, Union

import redis
import requests

from redis import ConnectionError, TimeoutError
from requests.status_codes import codes
from requests.exceptions import HTTPError
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, ALL_COMPLETED
import threading

from .constants import MERCADO_ABERTO, MERCADO_FECHADO, CAMPEONATO
from .decorators import RequiresAuthentication
from .errors import CartolaFCError, CartolaFCOverloadError
from .models import Atleta, Clube, DestaqueRodada, Liga, LigaPatrocinador, Mercado, Partida, PontuacaoInfo, \
    Clube_Atleta, Capitaes, Reservas
from .models import Time, TimeInfo, Destaques
from .util import convert_team_name_to_slug, parse_and_check_cartolafc

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


class Api(object):
    """ Uma API em Python para o Cartola FC
    Exemplo de uso:
        Para criar uma instância da classe cartolafc.Api, sem autenticação:
            >>> import cartolafc
            >>> api = cartolafc.Api()
        Para obter o status atual do mercado
            >>> mercado = api.mercado()
            >>> print(mercado.rodada_atual, mercado.status.nome)
        Para utilizar autenticação, é necessário instancias a classe cartolafc.Api com os argumentos email e senha.
            >>> api =  cartolafc.Api(email='usuario@email.com', password='s3nha')
        Para obter os dados de uma liga (após se autenticar), onde "nome" é o nome da liga que deseja buscar:
            >>> liga = api.liga('nome')
            >>> print(liga.nome)
        python-cartolafc é massa!!! E possui muitos outros métodos, como:
            >>> api.mercado()
            >>> api.time(123, 'slug')
            >>> api.times('termo')
    """

    def __init__(self, email: Optional[str] = None, password: Optional[str] = None, attempts: int = 1,
                 redis_url: Optional[str] = None, redis_timeout: int = 10, bearer_token=None, glb_id=None) -> None:
        """ Instancia um novo objeto de cartolafc.Api.
        Args:
            email (str): O e-mail da sua conta no CartolaFC. Requerido se o password for informado.
            password (str): A senha da sua conta no CartolaFC. Requerido se o email for informado.
            attempts (int): Quantidade de tentativas que serão efetuadas se os servidores estiverem sobrecarregados.
            redis_url (str): URL para conectar ao servidor Redis, exemplo: redis://user:password@localhost:6379/2.
            redis_timeout (int): O timeout padrão (em segundos).
        Raises:
            cartolafc.CartolaFCError: Se as credenciais forem inválidas ou se apenas um dos
            dois argumentos (email e password) for informado.
        """

        self._api_url = 'https://api.cartolafc.globo.com'
        self._auth_url = 'https://login.globo.com/api/authentication'
        self._email = None
        self._password = None
        self._bearer_token = bearer_token
        self._glb_id = glb_id
        self._attempts = attempts if isinstance(attempts, int) and attempts > 0 else 1
        self._redis_url = None
        self._redis_timeout = None
        self._redis = None

        self.set_credentials(email, password)
        self.set_redis(redis_url, redis_timeout)

    def set_credentials(self, email: str, password: str) -> None:
        """ Realiza a autenticação no sistema do CartolaFC utilizando o email e password informados.
        Args:
            email (str): O email do usuário
            password (str): A senha do usuário
        Raises:
            cartolafc.CartolaFCError: Se o conjunto (email, password) não conseguiu realizar a autenticação com sucesso.
        """

        if bool(email) != bool(password):
            raise CartolaFCError('E-mail ou senha ausente')
        elif not email:
            return

        self._email = email
        self._password = password

        data = {
            "payload": {
                "email": self._email,
                "password": self._password,
                "serviceId": 4728,
            }
        }

        try:
            response = requests.post(self._auth_url, json=data)
            body = response.json()

            if response.status_code != codes.ok:
                raise CartolaFCError(body['userMessage'])

            self._glb_id = body['glbId']
            self._bearer_token = body['bearer_Token']
        except HTTPError:
            raise CartolaFCError('Erro authenticando no Cartola.')

    def set_redis(self, redis_url: str, redis_timeout: int = 10) -> None:
        """ Realiza a autenticação no servidor Redis utilizando a URL informada.
        Args:
            redis_url (str): URL para conectar ao servidor Redis, exemplo: redis://user:password@localhost:6379/2.
            redis_timeout (int): O timeout padrão (em segundos).
        Raises:
            cartolafc.CartolaFCError: Se não for possível se conectar ao servidor Redis
        """
        if not redis_url:
            return

        self._redis_url = redis_url
        self._redis_timeout = redis_timeout if isinstance(redis_timeout, int) and redis_timeout > 0 else 10

        try:
            self._redis = redis.StrictRedis.from_url(url=redis_url)
            self._redis.ping()
        except (ConnectionError, TimeoutError, ValueError):
            self._redis = None
            raise CartolaFCError('Erro conectando ao servidor Redis.')

    @RequiresAuthentication
    def amigos(self) -> List[TimeInfo]:
        url = '{api_url}/auth/amigos'.format(api_url=self._api_url)
        data = self._request(url)
        return [TimeInfo.from_dict(time_info) for time_info in data['times']]

    @RequiresAuthentication
    def liga(self, nome: Optional[str] = None, slug: Optional[str] = None, page: int = 1,
             order_by: str = CAMPEONATO) -> Liga:
        """ Este serviço requer que a API esteja autenticada, e realiza uma busca pelo nome ou slug informados.
        Este serviço obtém apenas 20 times por página, portanto, caso sua liga possua mais que 20 membros, deve-se
        utilizar o argumento "page" para obter mais times.
        Args:
            nome (str): Nome da liga que se deseja obter. Requerido se o slug não for informado.
            slug (str): Slug do time que se deseja obter. *Este argumento tem prioridade sobre o nome*
            page (int): Página dos times que se deseja obter.
            order_by (str): É possível obter os times ordenados por "campeonato", "turno", "mes", "rodada" e
            "patrimonio". As constantes estão disponíveis em "cartolafc.CAMPEONATO", "cartolafc.TURNO" e assim
            sucessivamente.
        Returns:
            Um objeto representando a liga encontrada.
        Raises:
            CartolaFCError: Se a API não está autenticada ou se nenhuma liga foi encontrada com os dados recebidos.
        """

        if not any((nome, slug)):
            raise CartolaFCError('Você precisa informar o nome ou o slug da liga que deseja obter')

        slug = slug if slug else convert_team_name_to_slug(nome)
        url = '{api_url}/auth/liga/{slug}'.format(api_url=self._api_url, slug=slug)
        data = self._request(url, params=dict(page=page, orderBy=order_by))
        return Liga.from_dict(data, order_by)

    @RequiresAuthentication
    def pontoscorridos(self, nome: Optional[str] = None, slug: Optional[str] = None, page: int = 1,
                       order_by: str = CAMPEONATO) -> Liga:
        """ Este serviço requer que a API esteja autenticada, e realiza uma busca pelo nome ou slug informados.
        Este serviço obtém apenas 20 times por página, portanto, caso sua liga possua mais que 20 membros, deve-se
        utilizar o argumento "page" para obter mais times.
        Args:
            nome (str): Nome da liga que se deseja obter. Requerido se o slug não for informado.
            slug (str): Slug do time que se deseja obter. *Este argumento tem prioridade sobre o nome*
            page (int): Página dos times que se deseja obter.
            order_by (str): É possível obter os times ordenados por "campeonato", "turno", "mes", "rodada" e
            "patrimonio". As constantes estão disponíveis em "cartolafc.CAMPEONATO", "cartolafc.TURNO" e assim
            sucessivamente.
        Returns:
            Um objeto representando a liga encontrada.
        Raises:
            CartolaFCError: Se a API não está autenticada ou se nenhuma liga foi encontrada com os dados recebidos.
        """

        if not any((nome, slug)):
            raise CartolaFCError('Você precisa informar o nome ou o slug da liga que deseja obter')

        slug = slug if slug else convert_team_name_to_slug(nome)
        url = '{api_url}/auth/competicoes/pontoscorridos/slug/{slug}'.format(api_url=self._api_url, slug=slug)
        data = self._request(url, params=dict(page=page, orderBy=order_by))
        return Liga.from_dict(data, order_by)

    @RequiresAuthentication
    def pontuacao_atleta(self, atleta_id: int) -> List[PontuacaoInfo]:
        url = '{api_url}/auth/mercado/atleta/{id}/pontuacao'.format(api_url=self._api_url, id=atleta_id)
        data = self._request(url)
        return [PontuacaoInfo.from_dict(pontuacao_info) for pontuacao_info in data]

    @RequiresAuthentication
    def time_logado(self) -> Time:
        url = '{api_url}/auth/time'.format(api_url=self._api_url)
        data = self._request(url)
        clubes = {clube['id']: Clube.from_dict(clube) for clube in data['clubes'].values()}
        return Time.from_dict(data, clubes=clubes, capitao=data['capitao_id'])

    def clubes(self) -> Dict[int, Clube]:
        url = '{api_url}/clubes'.format(api_url=self._api_url)
        data = self._request(url)
        return {int(clube_id): Clube.from_dict(clube) for clube_id, clube in data.items()}

    def ligas(self, query: str) -> List[Liga]:
        """ Retorna o resultado da busca ao Cartola por um determinado termo de pesquisa.
        Args:
            query (str): Termo para utilizar na busca.
        Returns:
            Uma lista de instâncias de cartolafc.Liga, uma para cada liga contento o termo utilizado na busca.
        """

        url = '{api_url}/ligas'.format(api_url=self._api_url)
        data = self._request(url, params=dict(q=query))
        return [Liga.from_dict(liga_info) for liga_info in data]

    def ligas_patrocinadores(self) -> Dict[int, LigaPatrocinador]:
        url = '{api_url}/patrocinadores'.format(api_url=self._api_url)
        data = self._request(url)
        return {
            int(patrocinador_id): LigaPatrocinador.from_dict(patrocinador)
            for patrocinador_id, patrocinador in data.items()
        }

    def mercado(self) -> Mercado:
        """ Obtém o status do mercado na rodada atual.
        Returns:
            Uma instância de cartolafc.Mercado representando o status do mercado na rodada atual.
        """

        url = '{api_url}/mercado/status'.format(api_url=self._api_url)
        data = self._request(url)
        return Mercado.from_dict(data)

    def mercado_atletas(self) -> List[Atleta]:
        url = '{api_url}/atletas/mercado'.format(api_url=self._api_url)
        data = self._request(url)
        clubes = {clube['id']: Clube.from_dict(clube) for clube in data['clubes'].values()}
        return [Atleta.from_dict(atleta, clubes=clubes) for atleta in data['atletas']]

    def clubes_atletas(self) -> Dict[int, Clube_Atleta]:
        url = '{api_url}/atletas/mercado'.format(api_url=self._api_url)
        data = self._request(url)
        clubes = {clube['id']: Clube.from_dict(clube) for clube in data['clubes'].values()}
        return data['clubes']

    def parciais(self, rodada: Optional[int] = 0) -> Dict[int, Atleta]:

        """ Obtém um mapa com todos os atletas que já pontuaram na rodada atual (aberta).
        Returns:
            Uma mapa, onde a key é um inteiro representando o id do atleta e o valor é uma instância de cartolafc.Atleta
        Raises:
            CartolaFCError: Se o mercado atual estiver com o status fechado.
        """

        if self.mercado().status.id == MERCADO_FECHADO:
            url = '{api_url}/atletas/pontuados/'.format(api_url=self._api_url)
            if rodada:
                url += f'/{rodada}'

            data = self._request(url)

            clubes = {clube['id']: Clube.from_dict(clube) for clube in data['clubes'].values()}
            return {
                int(atleta_id): Atleta.from_dict(atleta, clubes=clubes, atleta_id=int(atleta_id))
                for atleta_id, atleta in data['atletas'].items()
                if atleta['clube_id'] > 0}

        elif self.mercado().status.id == MERCADO_ABERTO and rodada != self.mercado().rodada_atual:
            url = '{api_url}/atletas/pontuados/'.format(api_url=self._api_url)
            if rodada:
                url += f'/{rodada}'

            data = self._request(url)

            clubes = {clube['id']: Clube.from_dict(clube) for clube in data['clubes'].values()}
            return {
                int(atleta_id): Atleta.from_dict(atleta, clubes=clubes, atleta_id=int(atleta_id))
                for atleta_id, atleta in data['atletas'].items()
                if atleta['clube_id'] > 0}

        else:
            raise CartolaFCError('As pontuações parciais só ficam disponíveis com o mercado fechado.')

    def parciais_2(self, rodada: Optional[int] = 0) -> Dict[int, Atleta]:

        """ Obtém um mapa com todos os atletas que já pontuaram na rodada atual (aberta).
        Returns:
            Uma mapa, onde a key é um inteiro representando o id do atleta e o valor é uma instância de cartolafc.Atleta
        Raises:
            CartolaFCError: Se o mercado atual estiver com o status fechado.
        """

        if self.mercado().status.nome == 'Mercado fechado':
            url = '{api_url}/atletas/pontuados/'.format(api_url=self._api_url)
            if rodada:
                url += f'/{rodada}'

            data = self._request(url)

            with open(f'static/dict_parciais.json', 'w') as f:
                json.dump(data, f)

            clubes = {clube['id']: Clube.from_dict(clube) for clube in data['clubes'].values()}

            return {
                int(atleta_id): Atleta.from_dict(atleta, clubes=clubes, atleta_id=int(atleta_id))
                for atleta_id, atleta in data['atletas'].items()
                if atleta['clube_id'] > 0}

        else:
            raise CartolaFCError('As pontuações parciais só ficam disponíveis com o mercado fechado.')

    def partidas(self, rodada) -> List[Partida]:
        url = '{api_url}/partidas/{rodada}'.format(api_url=self._api_url, rodada=rodada)
        data = self._request(url)
        clubes = {clube['id']: Clube.from_dict(clube) for clube in data['clubes'].values()}
        return sorted([Partida.from_dict(partida, clubes=clubes) for partida in data['partidas']], key=lambda p: p.data)

    def pos_rodada_destaques(self) -> DestaqueRodada:
        if self.mercado().status.id == MERCADO_ABERTO:
            url = '{api_url}/pos-rodada/destaques'.format(api_url=self._api_url)
            data = self._request(url)
            return DestaqueRodada.from_dict(data)

        raise CartolaFCError('Os destaques de pós-rodada só ficam disponíveis com o mercado aberto.')

    def destaques(self) -> List[Destaques]:
        url = '{api_url}/mercado/destaques'.format(api_url=self._api_url)
        data = self._request(url)
        # return sorted([Destaques.from_dict(destaque) for destaque in data], key=lambda p: p.escalacoes, reverse=True)
        return [Destaques.from_dict(destaque) for destaque in data]

    def capitaes(self) -> List[Capitaes]:
        url = '{api_url}/mercado/selecao'.format(api_url=self._api_url)
        data = self._request(url)
        # return [Capitaes.from_dict(capitaes) for capitaes in data['capitaes']]
        return sorted([Capitaes.from_dict(capitaes) for capitaes in data['capitaes']], key=lambda p: p.escalacoes,
                      reverse=True)

    def reservas(self) -> List[Reservas]:
        url = '{api_url}/mercado/selecao'.format(api_url=self._api_url)
        data = self._request(url)
        # return [Reservas.from_dict(reservas) for reservas in data['reservas']]
        return sorted([Reservas.from_dict(reservas) for reservas in data['reservas']], key=lambda p: p.escalacoes,
                      reverse=True)

    # def time(self, time_id: Optional[int] = None, nome: Optional[str] = None, slug: Optional[str] = None,
    #          as_json: bool = False, rodada: Optional[int] = 0) -> Union[Time, dict]:
    def time(self, time_id: int, rodada: Optional[int] = 0) -> Union[Time, dict]:
        """ Obtém um time específico, baseando-se no nome ou no slug utilizado.
        Ao menos um dos dois devem ser informado.
        Args:
            time_id (int): Id to time que se deseja obter. *Este argumento sempre será utilizado primeiro*
            nome (str): Nome do time que se deseja obter. Requerido se o slug não for informado.
            slug (str): Slug do time que se deseja obter. *Este argumento tem prioridade sobre o nome*
            as_json (bool): Se desejar obter o retorno no formato json.
            rodada (int): Numero da rodada Opcional
        Returns:
            Uma instância de cartolafc.Time se o time foi encontrado.
        Raises:
            cartolafc.CartolaFCError: Se algum erro aconteceu, como por exemplo: Nenhum time foi encontrado.
        """
        # if not any((time_id, nome, slug)):
        # if not any((time_id)):
        #     raise CartolaFCError('Você precisa informar o nome ou o slug do time que deseja obter')

        # param = 'id' if time_id else 'slug'
        # value = time_id if time_id else (slug if slug else convert_team_name_to_slug(nome))
        # url = '{api_url}/time/{param}/{value}/'.format(api_url=self._api_url, param=param, value=value)
        url = '{api_url}/time/id/{time_id}/'.format(api_url=self._api_url, time_id=time_id)
        if rodada:
            url += f'{rodada}'

        data = self._request(url)

        # if bool(as_json):
        #     return data
        #############################################################################################################
        clubes = {clube['id']: Clube.from_dict(clube) for clube in data['clubes'].values()} if 'clubes' in data else \
            Api().clubes()
        return Time.from_dict(data, clubes=clubes, capitao=data['capitao_id'])
        # return Time.from_dict(data, capitao=data['capitao_id'])

    def time_parcial(self, time_id: Optional[int] = None, nome: Optional[str] = None, slug: Optional[str] = None,
                     parciais: Optional[Dict[int, Atleta]] = None) -> Time:
        # if parciais is None and self.mercado().status.id == MERCADO_FECHADO:
        if parciais is None and self.mercado().status.id != MERCADO_FECHADO:
            raise CartolaFCError('As pontuações parciais só ficam disponíveis com o mercado fechado.')

        parciais = parciais if isinstance(parciais, dict) else self.parciais()
        time = self.time(time_id)

        #####################
        # with ThreadPoolExecutor() as executor:
        #     # futures = [executor.submit(self.time, time_id, nome, slug)]
        #     futures = [executor.submit(time_id)]
        #     parciais = parciais if isinstance(parciais, dict) else self.parciais()
        #
        #     for future in concurrent.futures.as_completed(futures):
        #         return self._calculate_parcial(future.result(), parciais)

        ######################

        return self._calculate_parcial(time, parciais)

    def time_parcial_2(self, time_id: Optional[int] = None,
                       parciais_2: Optional[Dict[int, Atleta]] = None) -> Time:
        if parciais_2 is None and self.mercado().status.id != MERCADO_FECHADO:
            raise CartolaFCError('As pontuações parciais só ficam disponíveis com o mercado fechado.')

        dict_time = {}
        parciais_2 = {}

        with open('static/dict_parciais.json', encoding='utf-8', mode='r') as currentFile:
            data = currentFile.read().replace('\n', '')

            for k, v in json.loads(data).items():
                dict_time[k] = v

        for key, valor in dict_time['atletas'].items():
            # for id, scouts in valor.items():
            parciais_2[key] = valor

        # with ThreadPoolExecutor() as executor:
        #     futures = [executor.submit(self.time, time_id, nome, slug)]
        #     parciais_2 = parciais_2 if isinstance(parciais_2, dict) else self.parciais_2()
        #
        #     for future in concurrent.futures.as_completed(futures):
        #         return self._calculate_parcial_2(future.result(), parciais_2)

        parciais_2 = parciais_2 if isinstance(parciais_2, dict) else self.parciais_2()
        time = self.time(time_id)
        return self._calculate_parcial_2(time, parciais_2)

    def times(self, query: str) -> List[TimeInfo]:
        """ Retorna o resultado da busca ao Cartola por um determinado termo de pesquisa.
        Args:
            query (str): Termo para utilizar na busca.
        Returns:
            Uma lista de instâncias de cartolafc.TimeInfo, uma para cada time contento o termo utilizado na busca.
        """
        url = '{api_url}/times'.format(api_url=self._api_url)
        data = self._request(url, params=dict(q=query))
        return [TimeInfo.from_dict(time_info) for time_info in data]

    def _teste(parciais: Dict[int, Atleta], id_):
        atleta_parcial = parciais.get(id_)
        return atleta_parcial

    def _teste_2(parciais_2: Dict[int, Atleta], id_):
        atleta_parcial_2 = parciais_2.get(id_)
        return atleta_parcial_2

    @staticmethod
    def _calculate_parcial(time: Time, parciais: Dict[int, Atleta], teste=_teste) -> Time:
        if any(not isinstance(key, int) or not isinstance(parciais[key], Atleta) for key in parciais.keys()) \
                or not isinstance(time, Time):
            raise CartolaFCError('Time ou parciais não são válidos.')
        rodada_atual = Api().mercado().rodada_atual
        partidas = Api().partidas(rodada_atual)
        time.pontos = 0
        time.jogados = 0
        reserva_pontos = 0
        foundRes = False
        reserva_usado = []

        for atleta in time.atletas:

            # atleta_parcial = parciais.get(atleta.id)

            #####################################################
            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(teste, parciais, atleta.id)]

                for future in concurrent.futures.as_completed(futures):
                    atleta_parcial = future.result()

                    tem_parcial = isinstance(atleta_parcial, Atleta)

                    atleta.nome = atleta_parcial.apelido if tem_parcial else ''
                    atleta.pontos = atleta_parcial.pontos if tem_parcial else 0
                    atleta.scout = atleta_parcial.scout if tem_parcial else {}
                    # atleta.clube = atleta_parcial.clube.nome #if tem_parcial else ''
                    # atleta.pos = atleta_parcial.posicao.abreviacao if tem_parcial else atleta.posicao
                    atleta.entrou_em_campo = atleta_parcial.entrou_em_campo if tem_parcial else False
                    time.jogados += 1 if tem_parcial else 0

                    jogo_finalizou = False

                    for partida in partidas:
                        if atleta.clube != '' and (
                                atleta.clube.nome == partida.clube_casa.nome or atleta.clube.nome == partida.clube_visitante.nome):

                            # if partida.status_transmissao_tr == 'ENCERRADA' or not partida.valida:
                            if (
                                    partida.fim_de_jogo == 'veja como foi' or partida.status_transmissao_tr == 'ENCERRADA') or not partida.valida:
                                jogo_finalizou = True
                            else:
                                jogo_finalizou = False

                    if time.reservas:
                        for reserva in time.reservas:

                            reserva_parcial = parciais.get(reserva.id)
                            res_tem_parcial = isinstance(reserva_parcial, Atleta)
                            reserva.pontos = reserva_parcial.pontos if res_tem_parcial else 0
                            reserva.scout = reserva_parcial.scout if res_tem_parcial else {}
                            # reserva.club = reserva_parcial.clube.nome if res_tem_parcial else ''
                            # reserva.pos = reserva_parcial.posicao if res_tem_parcial else ''
                            reserva_cap = 0

                            if not atleta.entrou_em_campo:

                                foundRes = False
                                if atleta.posicao.nome in reserva_usado:
                                    break

                                if atleta.is_capitao and atleta.posicao.nome == reserva.posicao.nome and jogo_finalizou:
                                    time.pontos += reserva.pontos

                                if atleta.posicao.nome == reserva.posicao.nome and not foundRes and jogo_finalizou \
                                        and reserva.pontos >= 0.1:
                                    time.pontos += reserva.pontos
                                    foundRes = True
                                    reserva_usado.append(reserva.posicao.nome)
                                    break

                            else:
                                break

                    if atleta.is_capitao:
                        atleta.pontos *= 1.5

                    time.pontos += atleta.pontos

        return time

    @staticmethod
    def _calculate_parcial_2(time: Time, parciais_2: Dict[int, Atleta], teste=_teste_2) -> Time:

        if any(not isinstance(key, int) or not isinstance(parciais_2[key], Atleta) for key in parciais_2.keys()) \
                or not isinstance(time, Time):
            raise CartolaFCError('Time ou parciais não são válidos.')
        rodada_atual = Api().mercado().rodada_atual
        partidas = Api().partidas(rodada_atual)
        time.pontos = 0
        time.jogados = 0
        reserva_pontos = 0
        foundRes = False
        reserva_usado = []

        for atleta in time.atletas:

            # atleta_parcial_2 = parciais_2.get(atleta.id)

            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(teste, parciais_2, atleta.id)]

                for future in concurrent.futures.as_completed(futures):
                    atleta_parcial_2 = future.result()

                    # atleta_parcial_2 = parciais_2.get(atleta.id)
                    tem_parcial = isinstance(atleta_parcial_2, Atleta)

                    atleta.nome = atleta_parcial_2.apelido if tem_parcial else ''
                    atleta.pontos = atleta_parcial_2.pontos if tem_parcial else 0
                    atleta.scout = atleta_parcial_2.scout if tem_parcial else {}
                    # atleta.clube = atleta_parcial.clube.nome #if tem_parcial else ''
                    # atleta.pos = atleta_parcial.posicao.abreviacao if tem_parcial else atleta.posicao
                    atleta.entrou_em_campo = atleta_parcial_2.entrou_em_campo if tem_parcial else False
                    time.jogados += 1 if tem_parcial else 0

                    jogo_finalizou = False

                    for partida in partidas:
                        if atleta.clube != '' and (
                                atleta.clube.nome == partida.clube_casa.nome or atleta.clube.nome == partida.clube_visitante.nome):

                            # if partida.status_transmissao_tr == 'ENCERRADA' or not partida.valida:
                            if (
                                    partida.fim_de_jogo == 'veja como foi' or partida.status_transmissao_tr == 'ENCERRADA') or not partida.valida:
                                jogo_finalizou = True
                            else:
                                jogo_finalizou = False

                    if time.reservas:
                        for reserva in time.reservas:

                            reserva_parcial = parciais_2.get(reserva.id)
                            res_tem_parcial = isinstance(reserva_parcial, Atleta)
                            reserva.pontos = reserva_parcial.pontos if res_tem_parcial else 0
                            reserva.scout = reserva_parcial.scout if res_tem_parcial else {}
                            # reserva.club = reserva_parcial.clube.nome if res_tem_parcial else ''
                            # reserva.pos = reserva_parcial.posicao if res_tem_parcial else ''
                            reserva_cap = 0

                            if not atleta.entrou_em_campo:

                                foundRes = False
                                if atleta.posicao.nome in reserva_usado:
                                    break

                                if atleta.is_capitao and atleta.posicao.nome == reserva.posicao.nome and jogo_finalizou:
                                    time.pontos += reserva.pontos

                                if atleta.posicao.nome == reserva.posicao.nome and not foundRes and jogo_finalizou \
                                        and reserva.pontos >= 0.1:
                                    time.pontos += reserva.pontos
                                    foundRes = True
                                    reserva_usado.append(reserva.posicao.nome)
                                    break

                            else:
                                break

                    if atleta.is_capitao:
                        atleta.pontos *= 1.5

                    time.pontos += atleta.pontos

        return time

    def _request(self, url: str, params: Optional[Dict[str, Any]] = None) -> dict:

        cached = self._get(url)
        if cached:
            try:
                cached = cached.decode('utf-8')
            except AttributeError:
                pass
            return json.loads(cached)

        attempts = self._attempts
        while attempts:
            try:
                # headers = {'X-GLB-Token': self._glb_id} if self._glb_id else None
                headers = {"Content-Type": "application/json",
                           "Authorization": self._bearer_token} if self._bearer_token else None

                response = requests.get(url, headers=headers)
                # if self._bearer_token and response.status_code == codes.unauthorized:
                #     self.set_credentials(self._email, self._password)
                #     # response = requests.get(url, params=params, headers={'X-GLB-Token': self._glb_id})
                #     response = requests.get(url, params=params, headers={'Content-Type': 'application/json',
                #                                                          "Authorization": f"Bearer {self._bearer_token}"})
                parsed = parse_and_check_cartolafc(response.content.decode('utf-8'))

                return self._set(url, parsed)
            except CartolaFCOverloadError as error:
                attempts -= 1
                if not attempts:
                    raise error

    def _get(self, url: str) -> bytes:
        cached = None
        if self._redis:
            cached = self._redis.get(url)
        return cached

    def _set(self, url: str, data: dict) -> dict:
        if self._redis:
            self._redis.set(url, json.dumps(data), ex=self._redis_timeout)
        return data
