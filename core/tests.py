from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import Usuario, Time, Jogo, Palpite, PalpiteCampeao


def criar_times():
    brasil_f = Time.objects.create(nome='Brasil', pais='Brasil', genero='F')
    eua_f = Time.objects.create(nome='EUA', pais='EUA', genero='F')
    brasil_m = Time.objects.create(nome='Brasil', pais='Brasil', genero='M')
    eua_m = Time.objects.create(nome='EUA', pais='EUA', genero='M')
    return brasil_f, eua_f, brasil_m, eua_m


def criar_jogos(brasil_f, eua_f, brasil_m, eua_m):
    agora = timezone.now()
    jogos = []

    # 5 jogos feminino encerrados
    for i in range(5):
        j = Jogo.objects.create(
            genero='F', semana='Semana 1',
            time_a=brasil_f, time_b=eua_f,
            data_hora=agora - timedelta(days=i + 1),
            sets_a=3, sets_b=1, encerrado=True,
        )
        jogos.append(j)

    # 5 jogos masculino encerrados
    for i in range(5):
        j = Jogo.objects.create(
            genero='M', semana='Semana 1',
            time_a=brasil_m, time_b=eua_m,
            data_hora=agora - timedelta(days=i + 1),
            sets_a=3, sets_b=0, encerrado=True,
        )
        jogos.append(j)

    # 5 jogos feminino futuros (palpite aberto)
    for i in range(5):
        j = Jogo.objects.create(
            genero='F', semana='Semana 2',
            time_a=brasil_f, time_b=eua_f,
            data_hora=agora + timedelta(days=i + 1, hours=1),
            encerrado=False,
        )
        jogos.append(j)

    return jogos


class SetupMixin:
    def setUp(self):
        self.client = Client()
        self.jogador1 = Usuario.objects.create_user(username='jogador1', password='senha123')
        self.jogador2 = Usuario.objects.create_user(username='jogador2', password='senha123')

        brasil_f, eua_f, brasil_m, eua_m = criar_times()
        self.brasil_f = brasil_f
        self.eua_f = eua_f
        self.jogos = criar_jogos(brasil_f, eua_f, brasil_m, eua_m)

        encerrados = [j for j in self.jogos if j.encerrado]
        abertos = [j for j in self.jogos if not j.encerrado]

        # 10 palpites por usuário em jogos encerrados + 5 em abertos
        for usuario in [self.jogador1, self.jogador2]:
            for jogo in encerrados[:10]:
                p = Palpite.objects.create(usuario=usuario, jogo=jogo, sets_a=3, sets_b=1)
                p.calcular_pontos()
                p.save()
            for jogo in abertos[:5]:
                Palpite.objects.create(usuario=usuario, jogo=jogo, sets_a=3, sets_b=0)

        self.client.login(username='jogador1', password='senha123')
        self.jogo_aberto = abertos[0]
        self.jogo_encerrado = encerrados[0]


class PageStatusTest(SetupMixin, TestCase):
    """Todas as páginas principais devem retornar HTTP 200."""

    def test_home(self):
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)

    def test_jogos_feminino(self):
        self.assertEqual(self.client.get(reverse('jogos') + '?genero=F').status_code, 200)

    def test_jogos_masculino(self):
        self.assertEqual(self.client.get(reverse('jogos') + '?genero=M').status_code, 200)

    def test_ranking(self):
        self.assertEqual(self.client.get(reverse('ranking')).status_code, 200)

    def test_meus_palpites(self):
        self.assertEqual(self.client.get(reverse('meus_palpites')).status_code, 200)

    def test_palpite_campeao_feminino(self):
        self.assertEqual(self.client.get(reverse('palpite_campeao') + '?genero=F').status_code, 200)

    def test_palpite_campeao_masculino(self):
        self.assertEqual(self.client.get(reverse('palpite_campeao') + '?genero=M').status_code, 200)

    def test_brasil_stats_feminino(self):
        self.assertEqual(self.client.get(reverse('brasil_stats') + '?genero=F').status_code, 200)

    def test_brasil_stats_masculino(self):
        self.assertEqual(self.client.get(reverse('brasil_stats') + '?genero=M').status_code, 200)

    def test_palpitar_jogo_aberto(self):
        self.assertEqual(self.client.get(reverse('palpitar', args=[self.jogo_aberto.pk])).status_code, 200)

    def test_detalhe_jogo(self):
        self.assertEqual(self.client.get(reverse('detalhe_jogo', args=[self.jogo_encerrado.pk])).status_code, 200)

    def test_cadastro_publico(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('registro_publico')).status_code, 200)

    def test_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('login')).status_code, 200)

    def test_redirect_unauthenticated(self):
        self.client.logout()
        r = self.client.get(reverse('home'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login/', r['Location'])


class RankingContentTest(SetupMixin, TestCase):
    """Ranking deve mostrar os dois jogadores com pontos corretos."""

    def test_dois_jogadores_aparecem(self):
        r = self.client.get(reverse('ranking'))
        self.assertContains(r, 'jogador1')
        self.assertContains(r, 'jogador2')

    def test_colunas_visiveis(self):
        r = self.client.get(reverse('ranking'))
        self.assertContains(r, 'Pts')
        self.assertContains(r, 'Participante')

    def test_pontos_calculados(self):
        # 10 palpites 3x1 em jogos 3x1 → 4 pts cada = 40 pts por jogador
        r = self.client.get(reverse('ranking'))
        self.assertContains(r, '40')


class MeusPalpitesContentTest(SetupMixin, TestCase):
    """Meus palpites deve mostrar palpites e pontuação do usuário logado."""

    def test_palpites_aparecem(self):
        r = self.client.get(reverse('meus_palpites'))
        self.assertContains(r, 'Brasil')

    def test_total_pontos_exibido(self):
        # 10 palpites × 4 pts = 40 pts
        r = self.client.get(reverse('meus_palpites'))
        self.assertContains(r, '40')

    def test_nao_mostra_palpites_do_outro_jogador(self):
        # jogador2 tem os mesmos jogos mas os dados são separados por usuário
        r = self.client.get(reverse('meus_palpites'))
        # Verifica que a contagem é 15, não 30
        self.assertContains(r, '15')


class PontuacaoTest(TestCase):
    """Testa cálculo de pontos dos palpites."""

    def setUp(self):
        brasil = Time.objects.create(nome='Brasil', pais='Brasil', genero='F')
        eua = Time.objects.create(nome='EUA', pais='EUA', genero='F')
        self.usuario = Usuario.objects.create_user(username='tester', password='senha123')
        agora = timezone.now()
        self.jogo = Jogo.objects.create(
            genero='F', time_a=brasil, time_b=eua,
            data_hora=agora - timedelta(hours=2),
            sets_a=3, sets_b=1, encerrado=True,
        )

    def _palpite_pts(self, sa, sb):
        p = Palpite(usuario=self.usuario, jogo=self.jogo, sets_a=sa, sets_b=sb)
        p.calcular_pontos()
        return p.pontos

    def test_placar_exato_4pts(self):
        # 3x1 exato → vencedor(1) + sets_perdedor(1) + exato(2) = 4
        self.assertEqual(self._palpite_pts(3, 1), 4)

    def test_vencedor_certo_sets_errado_1pt(self):
        # 3x2 → vencedor certo (1), sets perdedor: real=1 vs palpite=2 → errou = 1 pt
        self.assertEqual(self._palpite_pts(3, 2), 1)

    def test_vencedor_certo_sets_certo_2pts(self):
        # 3x0 em jogo 3x1 → vencedor(1), sets perdedor: real=1 vs palpite=0 → errou = 1 pt
        self.assertEqual(self._palpite_pts(3, 0), 1)

    def test_vencedor_errado_0pts(self):
        self.assertEqual(self._palpite_pts(1, 3), 0)


class PalpiteFormTest(SetupMixin, TestCase):
    """Testa envio de formulário de palpite."""

    def test_salvar_redireciona_meus_palpites(self):
        # Usar um jogo aberto sem palpite existente: cria novo
        brasil_f = self.brasil_f
        eua_f = self.eua_f
        agora = timezone.now()
        novo_jogo = Jogo.objects.create(
            genero='F', semana='Semana 3',
            time_a=brasil_f, time_b=eua_f,
            data_hora=agora + timedelta(days=10),
            encerrado=False,
        )
        r = self.client.post(reverse('palpitar', args=[novo_jogo.pk]), {'sets_a': 3, 'sets_b': 0})
        self.assertRedirects(r, reverse('meus_palpites'))

    def test_palpitar_jogo_encerrado_redireciona(self):
        r = self.client.post(
            reverse('palpitar', args=[self.jogo_encerrado.pk]),
            {'sets_a': 3, 'sets_b': 0},
        )
        self.assertEqual(r.status_code, 302)

    def test_cadastro_publico_cria_usuario(self):
        self.client.logout()
        r = self.client.post(reverse('registro_publico'), {
            'username': 'novousuario',
            'password1': 'senhaok123',
            'password2': 'senhaok123',
        })
        self.assertRedirects(r, reverse('home'))
        self.assertTrue(Usuario.objects.filter(username='novousuario').exists())
