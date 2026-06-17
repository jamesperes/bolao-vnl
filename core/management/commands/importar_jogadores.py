import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from core.models import Jogo, Destaque

GENERO_MAP = {'Feminino': 'F', 'Masculino': 'M'}


def parse_num(val):
    v = str(val).strip() if val else ''
    try:
        return int(v) if v else None
    except ValueError:
        return None


def parse_dec(val):
    v = str(val).strip() if val else ''
    try:
        return float(v) if v else None
    except ValueError:
        return None


def find_jogo(genero, data_str, mandante, visitante):
    try:
        data = datetime.strptime(data_str.strip(), '%d/%m/%Y').date()
    except ValueError:
        return None
    m, v = mandante.strip().lower(), visitante.strip().lower()
    for jogo in Jogo.objects.filter(genero=genero, data_hora__date=data).select_related('time_a', 'time_b'):
        a, b = jogo.time_a.nome.lower(), jogo.time_b.nome.lower()
        if (a == m and b == v) or (a == v and b == m):
            return jogo
    return None


class Command(BaseCommand):
    help = 'Importa destaques de jogadores do vnl_2026_jogadores.csv'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', nargs='?', default='vnl_2026_jogadores.csv')
        parser.add_argument('--limpar', action='store_true', help='Apaga todos os destaques antes de importar')

    def handle(self, *args, **options):
        if options['limpar']:
            Destaque.objects.all().delete()
            self.stdout.write('Destaques apagados.')

        criados = atualizados = sem_jogo = 0

        with open(options['csv_path'], encoding='utf-8') as f:
            for row in csv.DictReader(f):
                genero = GENERO_MAP.get(row['genero'].strip(), 'F')
                semana = row['semana'].strip()
                data = row['data'].strip()
                mandante = row['time_mandante'].strip()
                visitante = row['time_visitante'].strip()
                jogador = row['jogador'].strip()
                time_nome = row['time'].strip()

                if not jogador:
                    continue

                # Determina tipo e tenta linkar ao jogo
                tipo = 'semana'
                jogo = None
                if data and mandante not in ('TOP SEMANA', ''):
                    jogo = find_jogo(genero, data, mandante, visitante)
                    tipo = 'jogo' if jogo else 'semana'
                    if not jogo:
                        sem_jogo += 1

                defaults = dict(
                    semana=semana, genero=genero, tipo=tipo,
                    time=time_nome,
                    posicao=row.get('posicao', '').strip(),
                    pontos=parse_num(row.get('pontos')),
                    aces=parse_num(row.get('aces')),
                    bloqueios=parse_num(row.get('bloqueios')),
                    ataque_pct=parse_dec(row.get('ataque_pct')),
                    recepcao_pct=parse_dec(row.get('recepcao_pct')),
                    observacao=row.get('observacao', '').strip(),
                )

                obj, created = Destaque.objects.update_or_create(
                    jogo=jogo, semana=semana, genero=genero,
                    jogador=jogador, tipo=tipo,
                    defaults=defaults,
                )
                if created:
                    criados += 1
                else:
                    atualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'Jogadores: {criados} criados, {atualizados} atualizados, {sem_jogo} sem jogo vinculado.'
        ))
