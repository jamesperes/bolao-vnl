from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from .models import Convite, Usuario, Jogo, Palpite, Time, Destaque, PalpiteCampeao
from .forms import RegistroForm, PalpiteForm


def entrar_convite(request, codigo):
    convite = get_object_or_404(Convite, codigo=codigo, ativo=True)
    if request.method == 'POST':
        form = RegistroForm(convite, request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Bem-vindo ao bolão, {user.username}!')
            return redirect('home')
    else:
        form = RegistroForm(convite)
    return render(request, 'core/registro.html', {'form': form, 'convite': convite})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    erro = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'home'))
        erro = 'Usuário ou senha inválidos.'
    return render(request, 'core/login.html', {'erro': erro})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def home(request):
    proximos_f = Jogo.objects.filter(encerrado=False, genero='F').select_related('time_a', 'time_b')[:4]
    proximos_m = Jogo.objects.filter(encerrado=False, genero='M').select_related('time_a', 'time_b')[:4]
    recentes = Jogo.objects.filter(encerrado=True).select_related('time_a', 'time_b').order_by('-data_hora')[:6]
    ranking = (
        Usuario.objects
        .filter(is_staff=False)
        .annotate(pontos=Sum('palpites__pontos'))
        .order_by('-pontos')[:10]
    )
    stats = {
        'total_jogos': Jogo.objects.count(),
        'realizados': Jogo.objects.filter(encerrado=True).count(),
        'proximos': Jogo.objects.filter(encerrado=False).count(),
        'participantes': Usuario.objects.filter(is_staff=False).count(),
    }
    return render(request, 'core/home.html', {
        'proximos_f': proximos_f,
        'proximos_m': proximos_m,
        'recentes': recentes,
        'ranking': ranking,
        'stats': stats,
    })


@login_required
def jogos(request):
    genero = request.GET.get('genero', 'F')
    semana = request.GET.get('semana', '')
    time_id = request.GET.get('time', '')

    qs = Jogo.objects.filter(genero=genero).select_related('time_a', 'time_b')
    if semana:
        qs = qs.filter(semana=semana)
    if time_id:
        qs = qs.filter(Q(time_a_id=time_id) | Q(time_b_id=time_id))

    semanas = Jogo.objects.filter(genero=genero).values_list('semana', flat=True).distinct().order_by('semana')
    times = Time.objects.filter(genero=genero).order_by('nome')
    palpites_usuario = {p.jogo_id: p for p in request.user.palpites.all()}

    return render(request, 'core/jogos.html', {
        'jogos': qs,
        'palpites_usuario': palpites_usuario,
        'genero': genero,
        'semana_sel': semana,
        'semanas': semanas,
        'times': times,
        'time_sel': time_id,
    })


@login_required
def palpitar(request, jogo_id):
    jogo = get_object_or_404(Jogo, pk=jogo_id)
    if not jogo.palpite_aberto():
        messages.error(request, 'Prazo para palpitar encerrado.')
        return redirect('jogos')

    palpite_existente = Palpite.objects.filter(usuario=request.user, jogo=jogo).first()

    if request.method == 'POST':
        form = PalpiteForm(request.POST, instance=palpite_existente)
        if form.is_valid():
            p = form.save(commit=False)
            p.usuario = request.user
            p.jogo = jogo
            p.save()
            messages.success(request, 'Palpite salvo!')
            return redirect('jogos')
    else:
        form = PalpiteForm(instance=palpite_existente)

    return render(request, 'core/palpitar.html', {'jogo': jogo, 'form': form, 'palpite_existente': palpite_existente})


@login_required
def ranking(request):
    genero = request.GET.get('genero', '')
    participantes = (
        Usuario.objects
        .filter(is_staff=False)
        .annotate(
            pontos=Sum('palpites__pontos'),
            total_palpites=Count('palpites'),
            acertos_exatos=Count('palpites', filter=Q(palpites__pontos=5)),
        )
        .order_by('-pontos')
    )
    return render(request, 'core/ranking.html', {'participantes': participantes})


@login_required
def meus_palpites(request):
    palpites = (
        request.user.palpites
        .select_related('jogo__time_a', 'jogo__time_b')
        .order_by('-jogo__data_hora')
    )
    total_pts = sum(p.pontos for p in palpites if p.jogo.encerrado)
    acertos_exatos = sum(1 for p in palpites if p.pontos == 5)
    return render(request, 'core/meus_palpites.html', {
        'palpites': palpites,
        'total_pts': total_pts,
        'acertos_exatos': acertos_exatos,
    })


@login_required
def palpite_campeao(request):
    genero = request.GET.get('genero', 'F')
    times = Time.objects.filter(genero=genero).order_by('nome')
    meu_palpite = PalpiteCampeao.objects.filter(usuario=request.user, genero=genero).first()
    todos_palpites = (
        PalpiteCampeao.objects
        .filter(genero=genero)
        .select_related('usuario', 'time')
        .order_by('-pontos', 'criado_em')
    )
    campeao_definido = Time.objects.filter(genero=genero, campeao=True).first()

    if request.method == 'POST':
        time_id = request.POST.get('time_id')
        if time_id:
            time_obj = get_object_or_404(Time, pk=time_id, genero=genero)
            PalpiteCampeao.objects.update_or_create(
                usuario=request.user, genero=genero,
                defaults={'time': time_obj},
            )
            messages.success(request, f'Palpite de campeão salvo: {time_obj.bandeira} {time_obj.nome}!')
            return redirect(f'{request.path}?genero={genero}')

    return render(request, 'core/palpite_campeao.html', {
        'genero': genero,
        'times': times,
        'meu_palpite': meu_palpite,
        'todos_palpites': todos_palpites,
        'campeao_definido': campeao_definido,
    })


@login_required
def brasil_stats(request):
    genero = request.GET.get('genero', 'F')

    jogos_brasil = (
        Jogo.objects
        .filter(genero=genero, encerrado=True)
        .filter(Q(time_a__nome='Brasil') | Q(time_b__nome='Brasil'))
        .select_related('time_a', 'time_b')
        .order_by('data_hora')
    )

    vitorias = derrotas = sets_pro = sets_contra = 0
    for j in jogos_brasil:
        brasil_e_a = j.time_a.nome == 'Brasil'
        s_pro = j.sets_a if brasil_e_a else j.sets_b
        s_con = j.sets_b if brasil_e_a else j.sets_a
        sets_pro += s_pro
        sets_contra += s_con
        if s_pro > s_con:
            vitorias += 1
        else:
            derrotas += 1

    destaques_brasil = (
        Destaque.objects
        .filter(genero=genero, time='Brasil', tipo='jogo')
        .select_related('jogo__time_a', 'jogo__time_b')
        .order_by('-pontos')
    )

    return render(request, 'core/brasil_stats.html', {
        'genero': genero,
        'jogos': jogos_brasil,
        'vitorias': vitorias,
        'derrotas': derrotas,
        'sets_pro': sets_pro,
        'sets_contra': sets_contra,
        'destaques': destaques_brasil,
    })


@login_required
def detalhe_jogo(request, jogo_id):
    jogo = get_object_or_404(Jogo.objects.select_related('time_a', 'time_b'), pk=jogo_id)
    destaques = jogo.destaques.all().order_by('-pontos')
    palpites = (
        jogo.palpites
        .select_related('usuario')
        .order_by('-pontos', 'usuario__username')
    )
    meu_palpite = jogo.palpites.filter(usuario=request.user).first()
    return render(request, 'core/jogo_detalhe.html', {
        'jogo': jogo,
        'destaques': destaques,
        'palpites': palpites,
        'meu_palpite': meu_palpite,
    })
