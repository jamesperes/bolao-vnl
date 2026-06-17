import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Configura o banco na primeira execução: cria superuser e importa CSVs'

    def handle(self, *args, **options):
        Usuario = get_user_model()

        # Superuser via variáveis de ambiente
        admin_user = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_pass = os.environ.get('ADMIN_PASSWORD', '')
        admin_email = os.environ.get('ADMIN_EMAIL', '')

        if admin_pass and not Usuario.objects.filter(username=admin_user).exists():
            Usuario.objects.create_superuser(admin_user, admin_email, admin_pass)
            self.stdout.write(self.style.SUCCESS(f'Superuser "{admin_user}" criado.'))
        else:
            self.stdout.write(f'Superuser "{admin_user}" já existe ou ADMIN_PASSWORD não definido.')

        # Importar jogos apenas se o banco estiver vazio
        from core.models import Jogo
        if Jogo.objects.exists():
            self.stdout.write('Jogos já importados, pulando.')
            return

        from django.core.management import call_command
        csv_jogos = 'vnl_2026.csv'
        csv_jogadores = 'vnl_2026_jogadores.csv'

        if os.path.exists(csv_jogos):
            self.stdout.write(f'Importando {csv_jogos}...')
            call_command('importar_csv', csv_jogos)
        else:
            self.stdout.write(self.style.WARNING(f'{csv_jogos} não encontrado.'))

        if os.path.exists(csv_jogadores):
            self.stdout.write(f'Importando {csv_jogadores}...')
            call_command('importar_jogadores', csv_jogadores)
        else:
            self.stdout.write(self.style.WARNING(f'{csv_jogadores} não encontrado.'))
