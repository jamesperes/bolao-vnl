import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


BANDEIRAS = {
    'Brasil': '🇧🇷', 'EUA': '🇺🇸', 'Japão': '🇯🇵', 'Itália': '🇮🇹', 'Polônia': '🇵🇱',
    'França': '🇫🇷', 'Sérvia': '🇷🇸', 'Turquia': '🇹🇷', 'Alemanha': '🇩🇪', 'China': '🇨🇳',
    'Canadá': '🇨🇦', 'Holanda': '🇳🇱', 'Argentina': '🇦🇷', 'Bélgica': '🇧🇪', 'Irã': '🇮🇷',
    'Eslováquia': '🇸🇰', 'Bulgária': '🇧🇬', 'Rep. Tcheca': '🇨🇿', 'Ucrânia': '🇺🇦',
    'Rep. Dominicana': '🇩🇴', 'Tailândia': '🇹🇭', 'Coreia do Sul': '🇰🇷', 'Austrália': '🇦🇺',
    'Eslovênia': '🇸🇮', 'Cuba': '🇨🇺', 'Rússia': '🇷🇺', 'México': '🇲🇽', 'Croácia': '🇭🇷',
    'Egito': '🇪🇬', 'Finlândia': '🇫🇮', 'Índia': '🇮🇳', 'Porto Rico': '🇵🇷',
}


class Convite(models.Model):
    codigo = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"Convite {str(self.codigo)[:8]}... ({'ativo' if self.ativo else 'inativo'})"


class Usuario(AbstractUser):
    convite_usado = models.ForeignKey(
        Convite, null=True, blank=True, on_delete=models.SET_NULL, related_name='usuarios'
    )

    def total_pontos(self):
        return sum(p.pontos for p in self.palpites.all())


class Time(models.Model):
    GENERO_CHOICES = [('M', 'Masculino'), ('F', 'Feminino')]
    nome = models.CharField(max_length=100)
    pais = models.CharField(max_length=100)
    genero = models.CharField(max_length=1, choices=GENERO_CHOICES)
    bandeira = models.CharField(max_length=10, blank=True)
    campeao = models.BooleanField(default=False)

    class Meta:
        ordering = ['nome']
        unique_together = ('nome', 'genero')

    def save(self, *args, **kwargs):
        if not self.bandeira:
            self.bandeira = BANDEIRAS.get(self.nome, '🏐')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.bandeira} {self.nome} ({self.get_genero_display()})"

    def nome_curto(self):
        return f"{self.bandeira} {self.nome}"


class Jogo(models.Model):
    FASE_CHOICES = [
        ('preliminar', 'Fase Preliminar'),
        ('quartas', 'Quartas de Final'),
        ('semi', 'Semifinal'),
        ('final', 'Final'),
        ('3lugar', 'Disputa de 3º Lugar'),
    ]
    GENERO_CHOICES = [('M', 'Masculino'), ('F', 'Feminino')]

    genero = models.CharField(max_length=1, choices=GENERO_CHOICES, default='F')
    semana = models.CharField(max_length=30, blank=True)
    fase = models.CharField(max_length=20, choices=FASE_CHOICES, default='preliminar')
    pool = models.CharField(max_length=100, blank=True)
    arena = models.CharField(max_length=150, blank=True)
    time_a = models.ForeignKey(Time, on_delete=models.PROTECT, related_name='jogos_como_a')
    time_b = models.ForeignKey(Time, on_delete=models.PROTECT, related_name='jogos_como_b')
    data_hora = models.DateTimeField()
    sets_a = models.PositiveSmallIntegerField(null=True, blank=True)
    sets_b = models.PositiveSmallIntegerField(null=True, blank=True)
    # Pontuação por set individual
    set1_a = models.PositiveSmallIntegerField(null=True, blank=True)
    set1_b = models.PositiveSmallIntegerField(null=True, blank=True)
    set2_a = models.PositiveSmallIntegerField(null=True, blank=True)
    set2_b = models.PositiveSmallIntegerField(null=True, blank=True)
    set3_a = models.PositiveSmallIntegerField(null=True, blank=True)
    set3_b = models.PositiveSmallIntegerField(null=True, blank=True)
    set4_a = models.PositiveSmallIntegerField(null=True, blank=True)
    set4_b = models.PositiveSmallIntegerField(null=True, blank=True)
    set5_a = models.PositiveSmallIntegerField(null=True, blank=True)
    set5_b = models.PositiveSmallIntegerField(null=True, blank=True)
    encerrado = models.BooleanField(default=False)

    class Meta:
        ordering = ['data_hora']

    def __str__(self):
        return f"{self.time_a.nome} x {self.time_b.nome} — {self.data_hora.strftime('%d/%m %H:%M')}"

    def palpite_aberto(self):
        limite = self.data_hora - timezone.timedelta(minutes=5)
        return not self.encerrado and timezone.now() < limite

    def salvar_resultado(self, sets_a, sets_b):
        self.sets_a = sets_a
        self.sets_b = sets_b
        self.encerrado = True
        self.save()
        for palpite in self.palpites.all():
            palpite.calcular_pontos()
            palpite.save()

    def sets_detalhados(self):
        sets = []
        for i in range(1, 6):
            a = getattr(self, f'set{i}_a')
            b = getattr(self, f'set{i}_b')
            if a is not None and b is not None:
                sets.append((a, b))
        return sets


class Destaque(models.Model):
    TIPO_CHOICES = [('jogo', 'Destaque de jogo'), ('semana', 'Destaque semanal')]
    jogo = models.ForeignKey(Jogo, null=True, blank=True, on_delete=models.SET_NULL, related_name='destaques')
    semana = models.CharField(max_length=30, blank=True)
    genero = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Feminino')], default='F')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='jogo')
    jogador = models.CharField(max_length=100)
    time = models.CharField(max_length=100, blank=True)
    posicao = models.CharField(max_length=50, blank=True)
    pontos = models.PositiveSmallIntegerField(null=True, blank=True)
    aces = models.PositiveSmallIntegerField(null=True, blank=True)
    bloqueios = models.PositiveSmallIntegerField(null=True, blank=True)
    ataque_pct = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    recepcao_pct = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    observacao = models.TextField(blank=True)

    class Meta:
        ordering = ['-pontos']

    def __str__(self):
        return f"{self.jogador} ({self.time}) — {self.jogo or self.semana}"

    def bandeira_time(self):
        return BANDEIRAS.get(self.time, '🏐')


class PalpiteCampeao(models.Model):
    GENERO_CHOICES = [('M', 'Masculino'), ('F', 'Feminino')]
    PONTOS_ACERTO = 10

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='palpites_campeao')
    time = models.ForeignKey(Time, on_delete=models.PROTECT, related_name='palpites_campeao')
    genero = models.CharField(max_length=1, choices=GENERO_CHOICES)
    pontos = models.PositiveSmallIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'genero')

    def __str__(self):
        return f"{self.usuario.username} → {self.time.nome} ({self.get_genero_display()})"

    def calcular_pontos(self):
        self.pontos = self.PONTOS_ACERTO if self.time.campeao else 0
        self.save()


class Palpite(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='palpites')
    jogo = models.ForeignKey(Jogo, on_delete=models.CASCADE, related_name='palpites')
    sets_a = models.PositiveSmallIntegerField()
    sets_b = models.PositiveSmallIntegerField()
    pontos = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ('usuario', 'jogo')

    def __str__(self):
        return f"{self.usuario.username}: {self.sets_a}x{self.sets_b} — {self.jogo}"

    def calcular_pontos(self):
        j = self.jogo
        if not j.encerrado or j.sets_a is None or j.sets_b is None:
            self.pontos = 0
            return

        pts = 0
        vencedor_real = 'a' if j.sets_a > j.sets_b else 'b'
        vencedor_palpite = 'a' if self.sets_a > self.sets_b else 'b'

        if vencedor_real == vencedor_palpite:
            pts += 1
            sets_perdedor_real = min(j.sets_a, j.sets_b)
            sets_perdedor_palpite = min(self.sets_a, self.sets_b)
            if sets_perdedor_real == sets_perdedor_palpite:
                pts += 1

        if self.sets_a == j.sets_a and self.sets_b == j.sets_b:
            pts += 2

        self.pontos = pts
