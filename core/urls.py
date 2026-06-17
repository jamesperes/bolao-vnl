from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('entrar/<uuid:codigo>/', views.entrar_convite, name='entrar_convite'),
    path('cadastro/', views.registro_publico, name='registro_publico'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('jogos/', views.jogos, name='jogos'),
    path('jogos/<int:jogo_id>/', views.detalhe_jogo, name='detalhe_jogo'),
    path('jogos/<int:jogo_id>/palpitar/', views.palpitar, name='palpitar'),
    path('ranking/', views.ranking, name='ranking'),
    path('meus-palpites/', views.meus_palpites, name='meus_palpites'),
    path('palpite-campeao/', views.palpite_campeao, name='palpite_campeao'),
    path('brasil/', views.brasil_stats, name='brasil_stats'),
]
