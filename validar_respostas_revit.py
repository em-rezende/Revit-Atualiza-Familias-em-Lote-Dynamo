# -*- coding: utf-8 -*-
# =============================================================================
#  VALIDADOR (SEM ABRIR O REVIT) DAS RESPOSTAS AUTOMATICAS DO SCRIPT
# -----------------------------------------------------------------------------
#  Testa a logica que faz o lote responder "OK" sozinho nas janelas de aviso do
#  Revit (ex.: "Remover restricoes" / "OK" sobre as restricoes da geometria):
#    - evento UIApplication.DialogBoxShowing -> _ao_mostrar_dialogo():
#      OverrideResult(1), IDS_DIALOGOS_IGNORADOS, registro no log e tolerancia
#      a falhas ao responder (o lote nao pode parar por causa disso);
#    - IFailuresPreprocessor de silenciar_avisos():
#      avisos (warnings) descartados = efeito de clicar "OK"; falha de erro ->
#      rollback + registro nos avisos da familia.
#
#  Como funciona: as APIs do Revit (clr, Autodesk.Revit.DB, RevitServices) sao
#  substituidas por stubs simples e o proprio batch_format_families.py e lido e
#  executado no fim do arquivo. Nada e gravado em disco.
#
#  Uso (o Python do proprio Dynamo serve):
#      python .\validar_respostas_revit.py
#
#  Saida esperada: uma linha "OK | ..." por verificacao e, no fim,
#  "VERIFICACOES FALHAS: 0" (codigo de saida 0; cada falha aparece listada).
# =============================================================================
"""Valida, fora do Revit, as respostas automaticas de batch_format_families.py."""

import io
import os
import re
import sys
import builtins
import types

RAIZ = os.path.dirname(os.path.abspath(__file__))
CAMINHO_SCRIPT = os.path.join(RAIZ, "batch_format_families.py")
FONTE = io.open(CAMINHO_SCRIPT, encoding="utf-8").read()

FALHAS = []


def verificar(condicao, descricao):
    print(("{0} | {1}").format("OK   " if condicao else "FALHA", descricao))
    if not condicao:
        FALHAS.append(descricao)


class Fake(object):
    """Objeto generico: aceita chamada, indexacao e qualquer atributo."""

    def __init__(self, nome):
        object.__setattr__(self, "_nome", nome)
        object.__setattr__(self, "_filhos", {})

    def __getattr__(self, item):
        filhos = object.__getattribute__(self, "_filhos")
        if item not in filhos:
            filhos[item] = Fake(object.__getattribute__(self, "_nome") + "." + item)
        return filhos[item]

    def __getitem__(self, item):
        return self

    def __call__(self, *args, **kwargs):
        return Fake(object.__getattribute__(self, "_nome") + "()")

    def __repr__(self):
        return "<Fake {0}>".format(object.__getattribute__(self, "_nome"))


class IFailuresPreprocessor(object):
    """Precisa ser classe de verdade (usada como classe base)."""
    pass


class HashSet(object):
    def __init__(self, *args):
        self.itens = []

    def __getitem__(self, item):
        return self


class List(object):
    def __init__(self, *args):
        self.itens = []

    def __getitem__(self, item):
        return List

    def Add(self, item):
        self.itens.append(item)


# --- stub de Autodesk.Revit.DB (nomes extraidos do proprio script) -----------
nomes = sorted(n for n in set(re.findall(r"\b([A-Z][A-Za-z0-9_]*)\b", FONTE))
               if not hasattr(builtins, n))
banco = types.ModuleType("Autodesk.Revit.DB")
for nome in nomes:
    setattr(banco, nome, Fake(nome))
banco.IFailuresPreprocessor = IFailuresPreprocessor
banco.__all__ = nomes

clr = types.ModuleType("clr")
clr.AddReference = lambda *args, **kwargs: None

genericos = types.ModuleType("System.Collections.Generic")
genericos.HashSet = HashSet
genericos.List = List


class Evento(object):
    def __init__(self, dono):
        self.dono = dono

    def __iadd__(self, manipulador):
        self.dono.manipuladores.append(manipulador)
        return self

    def __isub__(self, manipulador):
        if manipulador in self.dono.manipuladores:
            self.dono.manipuladores.remove(manipulador)
        return self


class UIApplicationFalso(object):
    def __init__(self):
        self.manipuladores = []
        # No pythonnet "evento += handler" equivale a add_<Evento>(handler); para
        # o teste, um objeto com __iadd__/__isub__ simula esse comportamento.
        self.DialogBoxShowing = Evento(self)
        self.Application = Fake("Application")
        self.Application.VersionNumber = "2026"
        self.Application.Documents = []


ui = UIApplicationFalso()
instancia = Fake("Instance")
instancia.CurrentUIApplication = ui

persistencia = types.ModuleType("RevitServices.Persistence")


class DocumentManager(object):
    Instance = instancia


persistencia.DocumentManager = DocumentManager

for nome, modulo in (
        ("clr", clr),
        ("System", types.ModuleType("System")),
        ("System.Collections", types.ModuleType("System.Collections")),
        ("System.Collections.Generic", genericos),
        ("Autodesk", types.ModuleType("Autodesk")),
        ("Autodesk.Revit", types.ModuleType("Autodesk.Revit")),
        ("Autodesk.Revit.DB", banco),
        ("RevitServices", types.ModuleType("RevitServices")),
        ("RevitServices.Persistence", persistencia),
):
    sys.modules[nome] = modulo

globais = {"__name__": "batch_format_families_teste", "IN": [""]}

exec(compile(FONTE, CAMINHO_SCRIPT, "exec"), globais)

print("--- importacao do script (sem Revit) ---")
verificar(globais["OUT"][0].startswith("RESUMO | familias encontradas: 0"),
          "bloco em lote executado: " + globais["OUT"][0])
verificar(ui.manipuladores == [],
          "handler removido no fim do lote (desativar_respostas_automaticas)")

print("--- configuracao ---")
verificar(globais["RESULTADO_OK"] == 1, "RESULTADO_OK = 1 (TaskDialogResult.Ok / IDOK)")
verificar(globais["RESPONDER_DIALOGOS_COM_OK"] is True, "respostas automaticas ligadas")
verificar(globais["IDS_DIALOGOS_IGNORADOS"] == (), "IDS_DIALOGOS_IGNORADOS vazio por padrao")

ativar = globais["ativar_respostas_automaticas"]
desativar = globais["desativar_respostas_automaticas"]
ao_mostrar = globais["_ao_mostrar_dialogo"]
respondidos = globais["_dialogos_respondidos"]


class JanelaFalsa(object):
    def __init__(self, identificador="", mensagem=None):
        self.DialogId = identificador
        if mensagem is not None:
            self.Message = mensagem
        self.resultado = None

    def OverrideResult(self, valor):
        self.resultado = valor


print("--- evento DialogBoxShowing ---")
verificar(ativar() is True, "ativar_respostas_automaticas() assina o evento")
verificar(len(ui.manipuladores) == 1, "um handler assinado no DialogBoxShowing")

janela = JanelaFalsa("TaskDialog_Constraints",
                     "As restricoes entre a geometria da familia podem se comportar "
                     "de forma imprevisivel ao modificar parametros...")
ao_mostrar(None, janela)
verificar(janela.resultado == 1, "TaskDialog das restricoes respondido com OK (1)")
verificar(respondidos[-1].startswith("JANELA | OK: TaskDialog_Constraints"), "registro: " + respondidos[-1])
verificar("restricoes" in respondidos[-1], "mensagem da janela registrada no log")

simples = JanelaFalsa("DialogBox_Simple")
ao_mostrar(None, simples)
verificar(simples.resultado == 1, "DialogBox sem a propriedade Message respondido com OK (1)")
verificar(respondidos[-1] == "JANELA | OK: DialogBox_Simple", "registro: " + respondidos[-1])

vazia = JanelaFalsa("")
ao_mostrar(None, vazia)
verificar(vazia.resultado == 1, "janela sem id respondida com OK (1)")
verificar(respondidos[-1] == "JANELA | OK: (sem id)", "registro: " + respondidos[-1])

anterior = globais["IDS_DIALOGOS_IGNORADOS"]
globais["IDS_DIALOGOS_IGNORADOS"] = ("TaskDialog_Save",)
quantidade = len(respondidos)
ignorada = JanelaFalsa("TaskDialog_Save", "Deseja salvar?")
ao_mostrar(None, ignorada)
verificar(ignorada.resultado is None and len(respondidos) == quantidade,
          "janela em IDS_DIALOGOS_IGNORADOS fica para o usuario")
globais["IDS_DIALOGOS_IGNORADOS"] = anterior


class JanelaQueFalha(JanelaFalsa):
    def OverrideResult(self, valor):
        raise RuntimeError("nao da para responder")


ao_mostrar(None, JanelaQueFalha("TaskDialog_X"))
verificar(respondidos[-1].startswith("AVISO  | janela do Revit 'TaskDialog_X' nao pode ser respondida"),
          "falha ao responder nao interrompe o script: " + respondidos[-1])

desativar()
verificar(ui.manipuladores == [], "desativar_respostas_automaticas() remove o handler")

print("--- IFailuresPreprocessor (silenciar_avisos) ---")


class OpcoesFalsas(object):
    def __init__(self):
        self.preprocessador = None
        self.clear_after_rollback = None

    def SetFailuresPreprocessor(self, preprocessador):
        self.preprocessador = preprocessador

    def SetClearAfterRollback(self, valor):
        self.clear_after_rollback = valor


class TransacaoFalsa(object):
    def __init__(self):
        self.opcoes = OpcoesFalsas()

    def GetFailureHandlingOptions(self):
        return self.opcoes

    def SetFailureHandlingOptions(self, opcoes):
        self.opcoes = opcoes


class FalhaFalsa(object):
    def __init__(self, severidade, texto):
        self.severidade = severidade
        self.texto = texto

    def GetSeverity(self):
        return self.severidade

    def GetDescriptionText(self):
        return self.texto


class AcessorFalso(object):
    def __init__(self, falhas):
        self.falhas = falhas
        self.avisos_apagados = 0

    def DeleteAllWarnings(self):
        self.avisos_apagados += 1

    def GetFailureMessages(self):
        return self.falhas


transacao = TransacaoFalsa()
avisos = []
globais["silenciar_avisos"](transacao, avisos)
preprocessador = transacao.opcoes.preprocessador
verificar(preprocessador is not None, "preprocessador instalado na transacao")
verificar(transacao.opcoes.clear_after_rollback is True, "SetClearAfterRollback(True) aplicado")

acessor = AcessorFalso([FalhaFalsa(globais["FailureSeverity"].Warning, "aviso qualquer")])
resultado = preprocessador.PreprocessFailures(acessor)
verificar(acessor.avisos_apagados == 1, "avisos (warnings) descartados - equivale a clicar OK")
verificar(resultado is globais["FailureProcessingResult"].Continue, "com avisos: transacao continua")
verificar(avisos == [], "nenhum aviso registrado quando so ha warnings")

texto_erro = "As restricoes entre a geometria da familia sao invalidas"
acessor = AcessorFalso([FalhaFalsa(globais["FailureSeverity"].Error, texto_erro)])
resultado = preprocessador.PreprocessFailures(acessor)
verificar(resultado is globais["FailureProcessingResult"].ProceedWithRollBack,
          "com ERRO: pede rollback (nunca escolhe uma resolucao)")
verificar(avisos == ["Revit: " + texto_erro + " (transacao desfeita)"],
          "erro registrado nos avisos da familia: " + repr(avisos))

transacao_sem_avisos = TransacaoFalsa()
globais["silenciar_avisos"](transacao_sem_avisos)
verificar(transacao_sem_avisos.opcoes.preprocessador is not None,
          "silenciar_avisos() sem a lista de avisos continua funcionando")

print("--- resumo ---")
print("VERIFICACOES FALHAS: {0}".format(len(FALHAS)))
for falha in FALHAS:
    print("  - " + falha)
sys.exit(1 if FALHAS else 0)

