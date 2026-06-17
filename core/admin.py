from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Convite, Usuario, Time, Jogo, Palpite, PalpiteCampeao


@admin.register(Convite)
class ConviteAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'ativo', 'criado_em')
    list_editable = ('ativo',)
    readonly_fields = ('codigo', 'criado_em')


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'convite_usado', 'total_pontos', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Bolão', {'fields': ('convite_usado',)}),
    )

    def total_pontos(self, obj):
        return obj.total_pontos()
    total_pontos.short_description = 'Pontos'


@admin.register(Time)
class TimeAdmin(admin.ModelAdmin):
    list_display = ('nome', 'pais', 'genero', 'campeao')
    list_filter = ('genero', 'campeao')
    list_editable = ('campeao',)

    def save_model(self, request, obj, form, change):
        campeao_anterior = Time.objects.get(pk=obj.pk).campeao if obj.pk else False
        super().save_model(request, obj, form, change)
        if obj.campeao and not campeao_anterior:
            for pc in PalpiteCampeao.objects.filter(genero=obj.genero):
                pc.calcular_pontos()


class PalpiteInline(admin.TabularInline):
    model = Palpite
    extra = 0
    readonly_fields = ('usuario', 'sets_a', 'sets_b', 'pontos')
    can_delete = False


@admin.register(Jogo)
class JogoAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'fase', 'data_hora', 'resultado', 'encerrado')
    list_filter = ('fase', 'encerrado')
    inlines = [PalpiteInline]

    def resultado(self, obj):
        if obj.sets_a is not None:
            return f"{obj.sets_a}x{obj.sets_b}"
        return "—"
    resultado.short_description = 'Resultado'

    def save_model(self, request, obj, form, change):
        sets_a_anterior = None
        sets_b_anterior = None
        if obj.pk:
            original = Jogo.objects.get(pk=obj.pk)
            sets_a_anterior = original.sets_a
            sets_b_anterior = original.sets_b

        super().save_model(request, obj, form, change)

        resultado_novo = obj.sets_a is not None and obj.sets_b is not None
        resultado_mudou = (obj.sets_a != sets_a_anterior or obj.sets_b != sets_b_anterior)

        if resultado_novo and resultado_mudou and obj.encerrado:
            for palpite in obj.palpites.all():
                palpite.calcular_pontos()
                palpite.save()


@admin.register(Palpite)
class PalpiteAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'jogo', 'sets_a', 'sets_b', 'pontos')
    list_filter = ('jogo__fase',)
    readonly_fields = ('pontos',)


@admin.register(PalpiteCampeao)
class PalpiteCampeaoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'genero', 'time', 'pontos')
    list_filter = ('genero',)
    readonly_fields = ('pontos',)
