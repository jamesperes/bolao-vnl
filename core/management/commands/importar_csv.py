import csv
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Time, Jogo


FASE_MAP = {
    'Fase Preliminar': 'preliminar',
    'Final (QF/SF/3º/Final)': 'final',
}

GENERO_MAP = {'Feminino': 'F', 'Masculino': 'M'}


def parse_set(valor):
    v = valor.strip() if valor else ''
    if v and v != '-' and v != '':
        try:
            return int(v)
        except ValueError:
            pass
    return None


def parse_placar(placar_str):
    """'3-1' → (3, 1); '-' ou vazio → (None, None)"""
    s = placar_str.strip() if placar_str else ''
    if not s or s == '-':
        return None, None
    partes = s.split('-')
    if len(partes) == 2:
        try:
            return int(partes[0]), int(partes[1])
        except ValueError:
            pass
    return None, None


class Command(BaseCommand):
    help = 'Importa jogos da VNL 2026 a partir do CSV'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', nargs='?', default='vnl_2026.csv')

    def handle(self, *args, **options):
        path = options['csv_path']
        criados = 0
        atualizados = 0
        ignorados = 0

        with open(path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                genero_str = row['genero'].strip()
                genero = GENERO_MAP.get(genero_str, 'F')
                semana = row['semana'].strip()
                fase_str = row['fase'].strip()
                fase = FASE_MAP.get(fase_str, 'preliminar')
                pool = row['pool'].strip()
                arena = row['local'].strip()
                data_str = row['data'].strip()
                nome_a = row['time_mandante'].strip()
                nome_b = row['time_visitante'].strip()
                placar_str = row['placar_sets'].strip()
                status = row['status'].strip()

                # Jogos de fase final sem times definidos (TBD)
                if 'TBD' in nome_b or 'TBD' in nome_a:
                    ignorados += 1
                    continue

                try:
                    data = datetime.strptime(data_str, '%d/%m/%Y')
                except ValueError:
                    self.stderr.write(f'Data inválida: {data_str}')
                    continue

                # Horário não consta no CSV — usar meio-dia como placeholder
                data_hora = timezone.make_aware(data.replace(hour=12, minute=0))

                # Determinar fase para quartas/semi/bronze/final pelos nomes
                nome_a_lower = nome_a.lower()
                if 'qf' in nome_a_lower:
                    fase = 'quartas'
                elif 'sf' in nome_a_lower:
                    fase = 'semi'
                elif 'bronze' in nome_a_lower or '3º' in nome_a_lower:
                    fase = '3lugar'
                elif 'final' in nome_a_lower and 'ouro' in nome_a_lower:
                    fase = 'final'

                time_a, _ = Time.objects.get_or_create(
                    nome=nome_a, genero=genero,
                    defaults={'pais': nome_a}
                )
                time_b, _ = Time.objects.get_or_create(
                    nome=nome_b, genero=genero,
                    defaults={'pais': nome_b}
                )

                sets_a, sets_b = parse_placar(placar_str)
                encerrado = status == 'Realizado' and sets_a is not None

                defaults = {
                    'genero': genero,
                    'semana': semana,
                    'fase': fase,
                    'pool': pool,
                    'arena': arena,
                    'sets_a': sets_a,
                    'sets_b': sets_b,
                    'encerrado': encerrado,
                    'set1_a': parse_set(row.get('set1', '')),
                    'set1_b': None,
                    'set2_a': parse_set(row.get('set2', '')),
                    'set2_b': None,
                    'set3_a': parse_set(row.get('set3', '')),
                    'set3_b': None,
                    'set4_a': parse_set(row.get('set4', '')),
                    'set4_b': None,
                    'set5_a': parse_set(row.get('set5', '')),
                    'set5_b': None,
                }

                # Parsear scores de cada set "25-22" → set1_a=25, set1_b=22
                for i, campo in enumerate(['set1', 'set2', 'set3', 'set4', 'set5'], 1):
                    val = row.get(campo, '').strip()
                    if val and val != '-' and '-' in val:
                        partes = val.split('-')
                        try:
                            defaults[f'set{i}_a'] = int(partes[0])
                            defaults[f'set{i}_b'] = int(partes[1])
                        except (ValueError, IndexError):
                            pass

                jogo, created = Jogo.objects.update_or_create(
                    time_a=time_a,
                    time_b=time_b,
                    data_hora=data_hora,
                    defaults=defaults,
                )

                if created:
                    criados += 1
                else:
                    atualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'Importação concluída: {criados} criados, {atualizados} atualizados, {ignorados} ignorados (TBD).'
        ))
