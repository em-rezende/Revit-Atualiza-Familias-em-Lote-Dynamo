# Atualiza Famílias em Lote — atualização e formatação em lote de famílias do Revit (.rfa) — Revit 2026

Script em Python para rodar dentro do **Dynamo do Revit 2026** (engine **CPython3**).
Processa uma **pasta inteira** (e subpastas) de famílias `.rfa`, atualizando cada
arquivo para o Revit 2026 e padronizando unidades/formato numérico.

O usuário escolhe, no próprio grafo, **o que vai virar preview** (tipo de vista), **de que
ângulo** (as 6 vistas do cubo) e **com qual estilo visual** — veja
[Escolhas no Dynamo](#️-escolhas-no-dynamo-custom-selection-in1in2in3).

## 🎯 O que o script faz (por família)

1. **Abre a família em segundo plano** — abrir + salvar no Revit 2026 já converte o
   arquivo para o formato/versão atual (upgrade).
2. **Unidades do projeto → Sistema Internacional (métrico)**
   - `SISTEMA_METRICO_COMPLETO = True` cria um objeto `Units(UnitSystem.Metric)`
     (todas as especificações em métrico, como o "Sistema Internacional" do Revit).
   - Comprimento: **mm** · Área: **m²** · Volume: **m³** (constantes configuráveis).
3. **Formato numérico `123.456.789,00`**
   - `Units.DecimalSymbol = Comma` (vírgula decimal)
   - `Units.DigitGroupingSymbol = Dot` (ponto de agrupamento de milhares)
   - `Units.DigitGroupingAmount = Three` e `FormatOptions.UseDigitGrouping = True`
4. **Eliminar não utilizados (Purge Unused) em loop**, até não sobrar nada —
   usando a API oficial `Document.GetUnusedElements()` (a mesma lista da janela
   "Eliminar não utilizados" do Revit), seguida de `Document.Delete()`.
5. **Vista de preview garantida e orientada** — o script usa (ou cria) uma vista do
   **tipo escolhido em `IN[1]`** (`Vista 3D`, `Planta`, `Corte`, `Detalhe` ou `Elevação`)
   para ser o preview/miniatura do arquivo:
   - **Vista 3D**: renomeia para `NOME_VISTA_3D` (`"Vista 1"`), aplica a isométrica
     escolhida em `IN[2]` (uma das **6 vistas do cubo** — veja
     [as 6 isométricas](#-as-6-isométricas-do-cubo-in2)) com `View3D.SetOrientation`
     e **grava a orientação dentro do arquivo** (`View3D.SaveOrientation`) — o `.rfa`
     reabre já naquela direção.
   - **Planta / Corte / Detalhe / Elevação**: procura uma vista existente desse tipo;
     se não houver, tenta criar (`ViewPlan.Create` / `ViewSection.CreateSection` /
     `ViewDrafting.Create`). Como essas vistas nem sempre são válidas como
     `PreviewViewId`, o script **valida** com `IsViewIdValidForPreview` e, se
     reprovar, **cai na Vista 3D** com aviso no `OUT`.
6. **Estilo visual escolhido em `IN[3]`, sem anotações/cotas** — na **mesma** vista
   usada como preview, o script aplica o estilo visual (`View.DisplayStyle`) escolhido
   pelo usuário (`Wireframe`, `Hidden Lines`, `Shading`, `Shading With Edges`,
   `Flat Colors`, `Realistic`, `Realistic With Edges`). Em seguida **oculta por
   categoria** as anotações/cotas (cotas, notas de texto, símbolos de anotação, níveis,
   eixos) e os elementos auxiliares (planos/linhas/pontos de referência, paredes, pisos,
   forros, telhados) com `View.SetCategoryHidden()` (`OCULTAR_CATEGORIAS_VISTA_3D` /
   `CATEGORIAS_OCULTAS_VISTA_3D`). A categoria da **própria família** nunca é ocultada —
   o preview nunca fica vazio. Veja
   [Estilo visual e categorias ocultas](#estilo-visual-e-categorias-ocultas).
7. **Preview/miniatura** — a vista escolhida é gravada como preview permanente do
   documento (`DocumentPreviewSettings.PreviewViewId`, validada antes por
   `IsViewIdValidForPreview`) e informada em `SaveOptions.PreviewViewId`.
8. **Nomes de vistas em português (Brasil)** — vistas que ainda usam os nomes padrão
   do Revit (`Ref. Level`, `Front`, `Back`, `Left`, `Right`, `Level 1`,
   `View 2`, `Section 1`...) passam a `Nível de Referência`, `Parte Frontal`,
   `Parte Posterior`, `Esquerda`, `Direita`, `Nível 1`, `Vista 2`, `Corte 1`
   (`View.Name`). Somente **nomes de vistas**: modelos de vista (*view templates*)
   e níveis não são alterados.
   - **Outros idiomas** — a tradução também cobre os nomes padrão do Revit em
   **francês** (`Vue 3D`, `Niveau de Référence`/`Niveau de réf.`, `Face avant`,
   `Face arrière`, `Gauche`, `Droite`, `Dessus`/`Dessous`,
   `Nord`/`Sud`/`Est`/`Ouest`, `Plan d'étage`, `Plafond`, `Légende`,
   `Promenade`, `Coupe`, `Élévation`, `Détail` e os numerados `Vue N`,
   `Niveau N`, `Coupe N`, `Élévation N`, `Détail N`) e em **espanhol**
   (`Vista 3D`, `Nivel de Referencia`, `Frontal`/`Frente`, `Posterior`,
   `Izquierda`, `Derecha`, `Superior`/`Inferior`, `Norte`/`Sur`/`Este`/`Oeste`,
   `Planta de piso`, `Planta de techo`, `Techo`, `Leyenda`, `Recorrido`,
   `Sección`, `Alzado`, `Detalle` e os numerados `Vista N`, `Nivel N`,
   `Sección N`, `Detalle N`, `Alzado N`).
   - **A comparação ignora maiúsculas/minúsculas, acentos, aspas tipográficas e o
     ponto final** (`chave_nome_vista()`), então `Niveau de Référence`,
     `niveau de reference` e `NIVEAU DE RÉF.` são tratados como o mesmo nome.
     Veja a seção [Nomes de vistas em português](#nomes-de-vistas-em-português-brasil).
9. **Salva** com `SaveOptions.Compact = True` (arquivo compactado) e **fecha** a
   família (garantido por `try/finally`, para nunca deixar arquivo travado).
10. **Backup opcional** dos originais em `_backup_upgrade\`, criado na **raiz da
    pasta pesquisada** (a pasta informada em `IN[0]`), preservando as subpastas.
11. **Log** `_log_atualiza_familias.txt` na mesma raiz da pesquisa + resultado em `OUT`.
12. **Responde "OK" sozinho nas janelas de aviso do Revit** que interromperiam o lote
    (ex.: *"As restrições entre a geometria da família podem se comportar de forma
    imprevisível ao modificar parâmetros..."*, com os botões **Remover restrições** e
    **OK**): o Dynamo deixa de ficar parado esperando um clique. Veja
    [Janelas de aviso do Revit respondidas com "OK"](#-janelas-de-aviso-do-revit-respondidas-com-ok).

> ⚠️ **O `.py` não é o que o Dynamo executa.** O grafo `.dyn` guarda o Python
> **embutido** (campo JSON `Code`). Depois de alterar `batch_format_families.py` é
> obrigatório rodar `sincronizar_dyn.ps1` (veja
> [O que compõe o projeto](#-o-que-compõe-o-projeto) e
> [Como usar no Dynamo](#️-como-usar-no-dynamo-revit-2026)); sem isso o Dynamo
> continua rodando a **versão antiga** do código.

---

## 📦 O que compõe o projeto

O projeto **não é só o `.dyn`**. Ele é formado por **6 arquivos que precisam ficar
juntos na mesma pasta**, porque os utilitários se procuram por caminho relativo
(`$PSScriptRoot` no PowerShell; `os.path.dirname(__file__)` nos validadores).

| Arquivo | O que é | Obrigatório? |
|---|---|---|
| `Atualiza Familias em Lote.dyn` | O grafo do Dynamo (nós, fios, Custom Selections). **Contém uma cópia embutida** do Python no campo `Code` do nó Python Script. | ✅ Sim — é o que o Dynamo abre |
| `batch_format_families.py` | O código-fonte "de verdade" do script Python. É **aqui** que se edita. | ✅ Sim — é a fonte que você edita |
| `sincronizar_dyn.ps1` | Copia o conteúdo do `.py` para dentro do `.dyn` (campo `Code`), sem tocar no resto do grafo. Lê o `.dyn` de volta como JSON e confere caractere a caractere. | ✅ Sim — é o que mantém os dois em sincronia |
| `validar_traducao.py` | Confere, **fora do Revit**, a tradução dos nomes de vista (inglês/francês/espanhol) e, de quebra, se o `.dyn` está sincronizado com o `.py`. | ✅ Sim — rede de segurança |
| `validar_respostas_revit.py` | Confere, **fora do Revit**, o handler de `DialogBoxShowing` e o `IFailuresPreprocessor` (respostas automáticas "OK"). | ✅ Sim — rede de segurança |
| `validar_vista_3d.py` | Confere, **fora do Revit**, o estilo visual e as categorias ocultas da vista de preview. | ✅ Sim — rede de segurança |
| `README.md` | Esta documentação. | ✅ Sim — referência |

### Ordem correta para salvar o projeto

Como o `.dyn` guarda uma **cópia** do `.py` (no campo `Code`), salvar os dois fora de
ordem faz o grafo voltar para a versão antiga. O fluxo é:

1. **Salve os arquivos de texto normalmente** (`.py`, `.ps1`, validadores, `README.md`)
   no editor/IDE que você usa.
2. **No Dynamo, salve o grafo** com **Ctrl+S** (ou `Arquivo → Salvar`). Isso grava o
   layout dos nós e as escolhas dos Custom Selections.
3. **Rode o `sincronizar_dyn.ps1`** para copiar o `.py` atualizado para dentro do `.dyn`:

   ```powershell
   powershell -ExecutionPolicy Bypass -File ".\sincronizar_dyn.ps1"
   ```

   Saída esperada:
   ```
   OK | .dyn sincronizado com batch_format_families.py | NNNN caracteres | Engine: CPython3
   ```

   > ⚠️ **A ordem importa:** sincronizar **antes** de salvar o grafo no Dynamo faz o
   > Dynamo sobrescrever o `.dyn` com a versão em memória (com o `Code` antigo) — você
   > perde a sincronização. **Primeiro salva o grafo no Dynamo, depois sincroniza.**
4. **Rode os validadores** (opcional, mas recomendado antes de rodar no Revit):

   ```powershell
   python .\validar_traducao.py
   python .\validar_respostas_revit.py
   python .\validar_vista_3d.py
   ```

   Cada um deve terminar com código de saída `0` (`VERIFICACOES FALHAS: 0` ou
   `OK: todas as traducoes esperadas foram confirmadas.`).

### Como saber que está tudo em sincronia

Feche e reabra o `.dyn` no Dynamo, clique no nó Python Script e role o código embutido
até achar a constante que você mudou (por exemplo `DIRECOES_VISTA_3D`). Ela deve estar
**igual ao `.py`**. Se estiver diferente, a sincronização não pegou.

O teste definitivo é o `validar_traducao.py`: ele lê o `.dyn`, extrai o `Code` e compara
**caractere por caractere** com o `.py`. Se estiver fora de sincronia, ele falha com:

```
- Python embutido no .dyn (rode sincronizar_dyn.ps1): obtido ..., esperado ...
```

### Levar o projeto para outro computador

Copie a **pasta inteira** (todos os 6 arquivos juntos), mantendo os nomes exatos. Não
adianta copiar só o `.dyn` porque ele não carrega o `.py` sozinho — ele carrega a cópia
que está dentro dele, que pode estar desatualizada em relação ao `.py` que ficou para
trás.

### Resumo de uma linha

**Salve o `.dyn` no Dynamo → rode `sincronizar_dyn.ps1` → confirme com
`validar_traducao.py`.** Os três passos, nessa ordem, garantem que o projeto está íntegro.

---

## 🎛️ Escolhas no Dynamo (Custom Selection → `IN[1]`/`IN[2]`/`IN[3]`)

O **editor do Dynamo** não permite criar botões/dropdowns a partir do Python — quem cria
os nós de UI é o próprio usuário, arrastando-os no canvas. O script expõe as escolhas
como **entradas opcionais** `IN[1]`, `IN[2]` e `IN[3]`; o usuário conecta um nó
**Custom Selection** (nativo a partir do Dynamo 2.16 / Revit 2023.1) a cada uma.

As três entradas são **opcionais**: se uma delas não vier (ou vier vazia/`None`), vale a
constante de configuração correspondente. Se vier um valor **desconhecido**, o script
cai no padrão e registra `AVISO | IN[x]: valor desconhecido '...'` no `OUT` — nunca
quebra o lote.

### Esquema de ligação no grafo

```
┌──────────────────┐
│ Directory Path   │──► IN[0]  (pasta das famílias)
└──────────────────┘

┌──────────────────────────┐
│ Custom Selection         │
│ (tipo de vista)          │──► IN[1]
└──────────────────────────┘

┌──────────────────────────┐
│ Custom Selection         │
│ (isométrica)             │──► IN[2]
└──────────────────────────┘

┌──────────────────────────┐
│ Custom Selection         │
│ (estilo visual)          │──► IN[3]
└──────────────────────────┘
                │
                ▼
        ┌───────────────┐
        │ Python Script │──► OUT
        │  (CPython3)   │
        └───────────────┘
```

### `IN[1]` — tipo de vista que será gravada como preview

| Display (visível ao usuário) | Value (passado ao Python) | Chave interna |
|---|---|---|
| Vista 3D | `VISTA_3D` | `VISTA_3D` |
| Planta | `PLANTA` | `PLANTA` |
| Corte | `CORTE` | `CORTE` |
| Detalhe | `DETALHE` | `DETALHE` |
| Elevação | `ELEVACAO` | `ELEVACAO` |

- Se a vista do tipo escolhido **não existir**, o script tenta criá-la
  (`ViewPlan.Create`, `ViewSection.CreateSection`, `ViewDrafting.Create`).
- Como Planta/Corte/Detalhe/Elevação **nem sempre são válidas como `PreviewViewId`**, o
  script valida com `IsViewIdValidForPreview` e, se reprovar, **cai na Vista 3D** com
  aviso no `OUT`.
- A **isométrica** (`IN[2]`) só é aplicada quando o tipo escolhido é `Vista 3D` —
  Planta/Corte/Detalhe/Elevação têm direção fixa pela própria natureza.

### `IN[2]` — as 6 isométricas do cubo

São as **6 vistas possíveis de um cubo** pelo ViewCube. As 4 primeiras equivalem às
antigas `SE/SO/NE/NO Isometric` (os nomes antigos continuam aceitos como apelido, para
não quebrar grafos que já os usavam).

| Display (visível ao usuário) | Value (passado ao Python) | O que é |
|---|---|---|
| Frente-Superior-Direita | `FSD` | Canto superior frontal direito (era `SE Isometric`) |
| Frente-Superior-Esquerda | `FSE` | Canto superior frontal esquerdo (era `SO Isometric`) |
| Tras-Superior-Direita | `TSD` | Canto superior traseiro direito (era `NE Isometric`) |
| Tras-Superior-Esquerda | `TSE` | Canto superior traseiro esquerdo (era `NO Isometric`) |
| Frente-Inferior-Direita | `FID` | Canto inferior frontal direito (câmera abaixo, olhando para cima) |
| Frente-Inferior-Esquerda | `FIE` | Canto inferior frontal esquerdo (câmera abaixo, olhando para cima) |

Todos os pares `forward`/`up` são **ortogonais** (produto escalar = 0), requisito da API
`ViewOrientation3D` — sem isso o Revit lança
*"up vector is not perpendicular to the view direction"*.

#### Os vetores por trás das 6 direções

| Chave | forward | up | Canto visto |
|---|---|---|---|
| `FSD` | `(-1, 1, -1)` | `(-1, 1, 2)` | Sudeste, acima |
| `FSE` | `(1, 1, -1)` | `(1, 1, 2)` | Sudoeste, acima |
| `TSD` | `(-1, -1, -1)` | `(-1, -1, 2)` | Nordeste, acima |
| `TSE` | `(1, -1, -1)` | `(1, -1, 2)` | Noroeste, acima |
| `FID` | `(-1, 1, 1)` | `(-1, 1, -2)` | Sudeste, abaixo |
| `FIE` | `(1, 1, 1)` | `(1, 1, -2)` | Sudoeste, abaixo |

Para as duas de baixo (`FID`/`FIE`), o `up` tem componente Z negativo de propósito: a
câmera está **abaixo** do modelo olhando para cima, então o "topo da tela" precisa
apontar para -Z, senão a imagem sai de cabeça para baixo no sentido errado.

### `IN[3]` — estilo visual (`View.DisplayStyle`)

| Display (visível ao usuário) | Value (passado ao Python) | `DisplayStyle` |
|---|---|---|
| Wireframe | `WIREFRAME` | `DisplayStyle.Wireframe` |
| Hidden Lines | `HIDDEN_LINES` | `DisplayStyle.HLR` |
| Shading | `SHADING` | `DisplayStyle.Shading` |
| Shading With Edges | `SHADING_WITH_EDGES` | `DisplayStyle.ShadingWithEdges` |
| Flat Colors | `FLAT_COLORS` | `DisplayStyle.FlatColors` |
| Realistic | `REALISTIC` | `DisplayStyle.Realistic` |
| Realistic With Edges | `REALISTIC_WITH_EDGES` | `DisplayStyle.RealisticWithEdges` |

> ⚠️ **Interação com `MOSTRAR_ARESTAS_VISTA_3D`:** se essa flag estiver `True` (padrão) e
> o estilo escolhido for `SHADING` ou `REALISTIC`, o script aplica automaticamente a
> variante **com arestas** (`SHADING_WITH_EDGES` / `REALISTIC_WITH_EDGES`). Para obter
> `Shading` "puro" (sem arestas), ou escolha `Shading With Edges` explicitamente e
> desligue a flag, ou desligue `MOSTRAR_ARESTAS_VISTA_3D = False` no topo do script.

### Como conferir no `OUT`

Após executar, a primeira linha do `OUT` mostra as escolhas que o script recebeu:

```
RESUMO | familias encontradas: N | OK: ... | IN[1] tipo de vista: VISTA_3D |
IN[2] isometrica: FSD | IN[3] estilo: SHADING | ...
```

Se você selecionou "Frente-Inferior-Direita" no dropdown e o `OUT` mostrar
`IN[2] isometrica: FID`, está tudo certo. Se aparecer `AVISO | IN[2]: valor
desconhecido 'One'`, o Custom Selection ainda está com o valor padrão (`One`) — volte
ao passo 2 e configure as opções.

---

## ⚠️ O erro "File already exists!" — causa e correção

O código anterior salvava assim:

```python
save_opts = SaveAsOptions()
save_opts.OverwriteExistingFiles = True   # <-- NOME ERRADO (plural)
...
doc.SaveAs(file_path, save_opts)          # file_path == caminho já aberto
```

Duas coisas davam errado:

1. **O nome correto da propriedade é `OverwriteExistingFile` (SINGULAR).**
   Ela não existe no plural — a documentação oficial da API
   (`RevitAPI.xml`, Revit 2026) lista apenas:
   `P:Autodesk.Revit.DB.SaveAsOptions.OverwriteExistingFile`.
   Como a opção continuou no valor padrão (**`false`**), o Revit recusou a
   gravação sobre o arquivo existente. A própria documentação de
   `Document.SaveAs(String, SaveAsOptions)` descreve exatamente essa exceção:

   > `InvalidOperationException`: **options.overwriteExistingFile is 'false' but
   > there is an existing file at filepath.**

   (é essa condição que gera a mensagem **"File already exists!"**)

2. **Para salvar no mesmo caminho, o método correto é `Save()`, não `SaveAs()`.**
   `Document.SaveAs` serve para gravar em **outro** caminho/nome.

### Correção aplicada

```python
opcoes = SaveOptions()          # SaveOptions também aceita Compact e PreviewViewId
opcoes.Compact = True
if vista_preview is not None:
    opcoes.PreviewViewId = vista_preview.Id
doc.Save(opcoes)                # grava no MESMO arquivo, sem "File already exists!"
```

E, no modo opcional "salvar em outra pasta", o nome correto é usado:

```python
opcoes_saveas = SaveAsOptions()
opcoes_saveas.OverwriteExistingFile = True   # SINGULAR
doc.SaveAs(destino, opcoes_saveas)
```

> **Requisito de leitura:** `Document.Save(SaveOptions)` exige que o documento já
> tenha um caminho (arquivo aberto do disco) — é o caso aqui. O upgrade de versão
> acontece porque o arquivo é regravado pelo Revit atual.

---

## ⚠️ Onde nascem o `_backup_upgrade\` e o log (correção)

O código antigo deduzia a "pasta raiz" do **primeiro `.rfa` encontrado**:

```python
pasta_raiz = os.path.dirname(lista_final[0]) if lista_final else ""
```

Quando a pasta pesquisada tinha famílias apenas em **subpastas**, `lista_final[0]`
vinha de dentro de uma delas — e o `_backup_upgrade\` (e o log) nasciam **dentro
dessa subpasta**, em vez da raiz da pasta pesquisada.

### Correção aplicada

A raiz passou a ser a **pasta informada em `IN[0]`**: `coletar_arquivos()` anota a raiz
de origem de cada família e o lote usa a raiz **da própria família**:

```python
raiz = os.path.abspath(alvo)                       # IN[0] (ou a pasta do .rfa)
...
raiz_do_arquivo[os.path.normcase(caminho)] = raiz  # cada familia leva a sua raiz
...
lista_final.append((caminho, raiz))                # (caminho, raiz da pesquisa)
...
pasta_raiz = raizes[0] if raizes else ""           # log: 1a pasta de IN[0]
```

Resultado: `_backup_upgrade\` e `_log_atualiza_familias.txt` nascem na **raiz da
pasta pesquisada**, e a árvore de subpastas continua sendo preservada dentro do
backup. Com uma **lista** de pastas em `IN[0]`, cada pasta recebe o seu.

---

## 🧭 Vista de preview: tipo, direção e gravação da orientação

### Ordem das ações no lote

1. `obter_vista_preview(doc, tipo_vista, direcao3d, avisos)` resolve a vista de
   preview de acordo com `IN[1]`:
   - **`VISTA_3D`**: `obter_vista_3d()` + `padronizar_nome_vista_3d()` +
     `orientar_vista_3d()` (aplica a isométrica de `IN[2]` e grava).
   - **`PLANTA` / `CORTE` / `DETALHE` / `ELEVACAO`**: `obter_ou_criar_vista_*()`
     (procura uma existente; se não houver, cria). A direção de `IN[2]` é ignorada
     (essas vistas têm direção fixa).
   - Se a vista obtida **não for válida** como `PreviewViewId`, o script cai na
     **Vista 3D** com aviso.
2. `definir_estilo_vista_3d(doc, vista, avisos)` aplica o estilo de `IN[3]`
   (`View.DisplayStyle`); se a vista já está no estilo pedido, devolve `True` sem
   criar transação.
3. `ocultar_categorias_vista_3d(doc, vista, avisos)` oculta **por categoria** o que
   está em `CATEGORIAS_OCULTAS_VISTA_3D` (uma única transação) e devolve a lista do
   que foi ocultado — a categoria da própria família é sempre preservada.
4. `definir_preview_permanente(doc, vista)` grava a vista como preview permanente.
5. `renomear_vistas_pt_br(doc)` traduz as vistas que continuam com nome padrão em inglês.

### Por que a vista 3D é renomeada ANTES de gravar a orientação

Não é capricho: é exigência da API. `View3D.SaveOrientation()` **não funciona** na vista
3D padrão do documento. Texto oficial da `RevitAPI.xml` (Revit 2026):

> `M:Autodesk.Revit.DB.View3D.SaveOrientation`
> *Converts the temporary orientation of the View3D into its saved orientation.*
> **Remarks:** *The View3D will be oriented to its saved orientation on file open.
> To save the orientation of the default View3D, first rename the default View3D.*
> `InvalidOperationException`: *The orientation of the View3D cannot be saved.*

Como a renomeação acontece antes, a vista deixa de ser a padrão e o método passa a
funcionar. O script ainda checa `View3D.CanSaveOrientation()` e, se não puder gravar,
registra o aviso no `OUT` em vez de falhar:

```python
vista.SetOrientation(ViewOrientation3D(olho, cima, frente))  # orientação TEMPORÁRIA
if GRAVAR_ORIENTACAO_VISTA_3D and vista.CanSaveOrientation():
    vista.SaveOrientation()                                  # vira orientação SALVA
```

> `View3D.Lock()` **não existe** na API do Revit (verificado na `RevitAPI.xml` 2026).
> O script usa apenas `View3D.IsLocked` e `View3D.Unlock()` (desbloqueio preventivo,
> caso a vista esteja travada por outro script/usuário). Travar já gravando seria
> `View3D.SaveOrientationAndLock()`, que o script **não** usa — assim a vista continua
> livre para o usuário.

### Estilo visual e categorias ocultas

Dois ajustes são feitos **na mesma vista** que vira preview, depois de resolver a vista
e **antes** de salvar:

| Constante / entrada | Padrão | Efeito |
|---|---|---|
| `IN[3]` (estilo visual) | `"SHADING"` | Estilo pedido: `View.DisplayStyle` |
| `MOSTRAR_ARESTAS_VISTA_3D` | `True` | `True` = troca `SHADING`/`REALISTIC` pela variante **com arestas** |
| `OCULTAR_CATEGORIAS_VISTA_3D` | `True` | liga/desliga o passo que oculta categorias |
| `CATEGORIAS_OCULTAS_VISTA_3D` | 12 `BuiltInCategory` | `View.SetCategoryHidden(cat.Id, True)` |

`View.DisplayStyle` é propriedade da **vista** (não do documento): fica gravada no `.rfa`
e é o estilo que aparece na miniatura. Valores aceitos:

| Chave interna | `DisplayStyle` | Rótulo no Revit |
|---|---|---|
| `ESTRUTURA_ARAME` | `DisplayStyle.Wireframe` | Estrutura de arame |
| `LINHAS_OCULTAS` | `DisplayStyle.HLR` | Linhas ocultas |
| `SOMBREADO` | `DisplayStyle.Shading` | Sombreado |
| `SOMBREADO_COM_ARESTAS` | `DisplayStyle.ShadingWithEdges` | **Sombreado com arestas** |
| `CORES_CONSISTENTES` | `DisplayStyle.FlatColors` | Cores consistentes |
| `REALISTA` | `DisplayStyle.Realistic` | Realista |
| `REALISTA_COM_ARESTAS` | `DisplayStyle.RealisticWithEdges` | Realista com arestas |

`estilo_visual_configurado()` aceita a **chave**, um **apelido** (`SHADING`, `Shaded`,
`Wireframe`, `HIDDEN_LINES`, `SHADING_WITH_EDGES`, `FLAT_COLORS`, `Realistic`...) ou o
**próprio valor do enum** (`ESTILO_VISUAL_VISTA_3D = DisplayStyle.Shading`). A comparação
normaliza caixa, espaços, hífens e underscores (`"Shading With Edges"`,
`"SHADING_WITH_EDGES"` e `"Shading-With-Edges"` caem na mesma chave). Com `""` (string
vazia) ou `None` o estilo **não é mexido** (`estilo: nao aplicado` no `OUT`).

#### Arestas visíveis no preview (`MOSTRAR_ARESTAS_VISTA_3D`)

**Não existe `View.ShowEdges` nem `View3D.ShowEdges` na API do Revit** — o checkbox
*Mostrar arestas* das opções de exibição gráfica não tem propriedade correspondente
(verificado na `RevitAPI.xml` do Revit 2026; o que existe é `ViewDisplayModel`, com
`SmoothEdges`, `ShowHiddenLines` e `Transparency`). O caminho que a API oferece é o
**próprio estilo visual**, que tem uma variante com arestas:

```
"SOMBREADO" + arestas  ->  DisplayStyle.ShadingWithEdges   ("Sombreado com arestas")
"REALISTA"  + arestas  ->  DisplayStyle.RealisticWithEdges ("Realista com arestas")
```

Com `MOSTRAR_ARESTAS_VISTA_3D = True` (padrão) o script troca o estilo pedido pela variante
com arestas — inclusive quando o estilo foi dado pelo próprio valor do enum:

| Escolha em `IN[3]` | Estilo aplicado de fato |
|---|---|
| `SHADING` | `SOMBREADO_COM_ARESTAS` (`DisplayStyle.ShadingWithEdges`) |
| `REALISTIC` | `REALISTA_COM_ARESTAS` (`DisplayStyle.RealisticWithEdges`) |
| `WIREFRAME` / `HIDDEN_LINES` | iguais (já mostram as arestas) |
| `FLAT_COLORS` | igual (não há variante com arestas na API) |
| `SHADING_WITH_EDGES` / `REALISTIC_WITH_EDGES` | iguais (já pedem as arestas) |
| `""` / `None` | nada é mexido |

Com `MOSTRAR_ARESTAS_VISTA_3D = False` vale exatamente o que o usuário escolheu. Em uma
versão do Revit sem `ShadingWithEdges` / `RealisticWithEdges` o ajuste é ignorado em
silêncio (o estilo simples continua sendo aplicado). `chave_estilo_visual()` e
`descricao_estilo_visual()` fazem esse cálculo, e é ele que aparece no `OUT`:
`estilo: SOMBREADO_COM_ARESTAS (de SOMBREADO + MOSTRAR_ARESTAS_VISTA_3D)`.

> 🔎 **Conferência depois de gravar:** `definir_estilo_vista_3d()` lê `View.DisplayStyle`
> de volta. Se o Revit aplicar outro estilo (a API recusa alguns estilos em algumas
> vistas), aparece `Vista (estilo visual): o arquivo ficou em 'X' (pedido: 'Y')` em
> `avisos:` — em vez de a miniatura sair diferente do esperado sem ninguém perceber.

> ⚠️ **"Sombreado" é `DisplayStyle.Shading`.** O valor `DisplayStyle.Shaded` **não existe**
> na API. Se a constante não for reconhecida, o script **não altera a vista** e registra
> `Vista (estilo visual): valor desconhecido '...' (use um de: ...)` em `avisos:`.

Para tirar as anotações do preview, o caminho é **por categoria**:

```python
View.SetCategoryHidden(Category.GetCategory(doc, BuiltInCategory).Id, True)
```

Em documento de **família** a API não oferece `View.HideElements` (ocultar elementos
isolados) — daí ocultar a categoria inteira, o equivalente a desmarcar a categoria em
*Visibilidade/Substituições da vista* (V/G). A lista padrão:

| `CATEGORIAS_OCULTAS_VISTA_3D` | O que esconde |
|---|---|
| `OST_Dimensions` | Cotas |
| `OST_TextNotes` | Notas de texto |
| `OST_GenericAnnotation` | Símbolos de anotação (anotação genérica) |
| `OST_Levels` | Níveis (inclusive o Nível de Referência) |
| `OST_Grids` | Eixos |
| `OST_CLines` | Planos de referência (nome interno do `BuiltInCategory`) |
| `OST_ReferenceLines` / `OST_ReferencePoints` | Linhas e pontos de referência |
| `OST_Walls` / `OST_Floors` / `OST_Ceilings` / `OST_Roofs` | Paredes, pisos, forros e telhados |

Regras de segurança do passo (tudo vira aviso no log/`OUT`, nunca interrupção do lote):

- **A categoria da própria família nunca é ocultada** — `categoria_da_propria_familia()`
  lê `doc.OwnerFamily.FamilyCategory`; se ela estiver na lista, o script mantém visível e
  registra `'X' e a categoria da propria familia - mantida visivel`. Assim uma família de
  parede continua mostrando a parede e uma de anotação continua mostrando o símbolo: o
  preview nunca fica vazio.
- Nome de `BuiltInCategory` que **não existe** na versão do Revit (erro de digitação) é
  ignorado e o `OUT` mostra
  `categoria(s) nao encontrada(s) (N): ...`.
- Categoria que a família **não possui** (ou sem `Id` válido) também é ignorada em silêncio.
- Se **uma** categoria falhar, as outras continuam (`Vista (ocultar X): ...`).
- Se a transação inteira falhar, ela é desfeita (`RollBack`) e o lote segue.
- `OCULTAR_CATEGORIAS_VISTA_3D = False` desliga tudo: nenhuma transação é criada.

### Nomes de vistas em português (Brasil)

`RENOMEAR_VISTAS_PT_BR = True` ativa a tradução. **Antes de qualquer
comparação**, o nome da vista passa por `chave_nome_vista()`, que produz uma
**chave normalizada**:

- minúsculas;
- **sem acentos** (`é`→`e`, `ñ`→`n`, `ç`→`c`, `á`→`a`...);
- aspas tipográficas normalizadas (`’` `´` `` ` `` → `'`);
- traços tipográficos normalizados (`–` `—` `−` → `-`);
- espaços repetidos / espaço inquebrável reduzidos a um espaço simples;
- espaços e pontos no início/fim descartados.

Assim `Niveau de Référence`, `niveau de référence`, `NIVEAU DE RÉF.` e
`niveau de ref` viram todos a **mesma** chave — por isso a tradução funciona
independentemente de caixa, acento ou ponto final. A tradução acontece em duas
etapas, ambas sobre essa chave:

1. **Nomes exatos** — `NOMES_VISTAS_PT_BR` (consultado pelo dicionário derivado
   `NOMES_VISTAS_PT_BR_NORMALIZADOS`, montado uma única vez na carga do script):
   - **inglês**: `{3D}` / `3D View` / `Default 3D View` → `Vista 3D`;
     `Ref. Level` / `Ref Level` / `Reference Level` / `Ref. Plane` →
     `Nível de Referência`; `Ground Floor` / `Ground Level` → `Piso Térreo`;
     `Front` → `Parte Frontal`; `Back` / `Rear` → `Parte Posterior`;
     `Left` → `Esquerda`; `Right` → `Direita`; `Top` → `Superior`;
     `Bottom` → `Inferior`; `North`/`South`/`East`/`West` →
     `Norte`/`Sul`/`Leste`/`Oeste`; `Floor Plan`/`Ceiling Plan`/`Site Plan`/
     `Area Plan`/`Structural Plan` → `Planta de Piso`/`Planta de Forro`/
     `Planta de Implantação`/`Planta de Área`/`Planta Estrutural`;
     `Ceiling` → `Forro`; `Legend` → `Legenda`; `Walkthrough` → `Passeio`;
     `Section` → `Corte`; `Elevation` → `Elevação`; `Detail` → `Detalhe`;
     `Exterior`/`Interior` → `Exterior`/`Interior`.
   - **francês**: `Vue 3D` / `Vue 1` → `Vista 3D` / `Vista 1`;
     `Niveau de Référence` / `Niveau de réf.` / `Niveau ref.` / `Réf. Niveau` →
     `Nível de Referência`; `Face avant` / `Élévation avant` / `Avant` →
     `Parte Frontal`; `Face arrière` / `Élévation arrière` / `Arrière` →
     `Parte Posterior`; `Face gauche` / `Gauche` → `Esquerda`;
     `Face droite` / `Droite` → `Direita`; `Vue de dessus` / `Dessus` →
     `Superior`; `Vue de dessous` / `Dessous` → `Inferior`;
     `Nord`/`Sud`/`Est`/`Ouest` → `Norte`/`Sul`/`Leste`/`Oeste`;
     `Plan d'étage` / `Vue en plan` → `Planta de Piso`; `Plan de plafond` / `Plafond` →
     `Planta de Forro` / `Forro`; `Plan de masse` / `Plan d'implantation` →
     `Planta de Implantação`; `Plan de surface` → `Planta de Área`;
     `Légende` → `Legenda`; `Promenade` → `Passeio`; `Coupe` → `Corte`;
     `Extérieur`/`Intérieur` → `Exterior`/`Interior`.
   - **espanhol**: `Vista 3D` / `Vista 3D {3D}` → `Vista 3D`; `Vista 1` →
     `Vista 1`; `Nivel de Referencia` / `Nivel de Ref.` / `Nivel Ref.` /
     `Ref. Nivel` → `Nível de Referência`; `Frontal` / `Frente` /
     `Alzado frontal` → `Parte Frontal`; `Posterior` / `Atrás` / `Detrás` /
     `Alzado posterior` → `Parte Posterior`; `Izquierda`/`Izquierdo` /
     `Alzado izquierdo` → `Esquerda`; `Derecha`/`Derecho` / `Alzado derecho` →
     `Direita`; `Superior`/`Inferior`; `Norte`/`Sur`/`Este`/`Oeste`;
     `Planta de piso` → `Planta de Piso`; `Planta baja` → `Piso Térreo`;
     `Planta de techo` / `Techo` → `Planta de Forro` / `Forro`;
     `Planta de emplazamiento` → `Planta de Implantação`; `Planta de área` →
     `Planta de Área`; `Planta de estructura` → `Planta Estrutural`;
     `Leyenda` → `Legenda`; `Recorrido` → `Passeio`; `Sección` → `Corte`;
     `Alzado` → `Elevação`; `Detalle` → `Detalhe`.
2. **Nomes numerados** — `REGRAS_NOMES_VISTAS_PT_BR` (expressões regulares
   aplicadas à chave, por isso escritas **sem acento**): `View N` → `Vista N`,
   `Level N` → `Nível N`, `Section N` → `Corte N`, `Detail N` → `Detalhe N`,
   `Elevation N` → `Elevação N`, `Plan N` → `Planta N`, `Vue N` → `Vista N`,
   `Niveau N` → `Nível N`, `Coupe N` → `Corte N`, `Vue en plan N` → `Planta N`,
   `Vista N` → `Vista N`, `Nivel N` → `Nível N`, `Sección N` → `Corte N`,
   `Alzado N` → `Elevação N`, `Vue 3D N` / `Vista 3D N` → `Vista 3D N`.

**Falta algum idioma?** Ligue `RELATAR_VISTAS_NAO_TRADUZIDAS = True` e rode o
script: todos os nomes de vista que não casaram com nenhum padrão aparecem no log
e em `OUT` (`vistas sem traducao: ...`). Basta então acrescentar cada nome — ou a
expressão regular, se for numerado — ao dicionário/às regras com a tradução
desejada e voltar a flag para `False`.

O que **não** muda — e por quê:

- **Nomes de níveis** (`Level 1` na lista de níveis) — o script altera apenas
  documentos de **vista** (`View.Name`); os níveis (`Level`) não são tocados.
- **Agrupamentos do Navegador de Projeto** (`Views`, `3D Views`, `Elevations`...) —
  são **textos da interface**, definidos pelo idioma instalado do Revit. Não existem na
  API como propriedades renomeáveis, portanto não há como alterá-los por script
  (instale o Revit em português para vê-los traduzidos).
- **Modelos de vista** (`View.IsTemplate = True`) — o nome é preservado.
- **Nomes já personalizados** continuam iguais: só há tradução quando o nome atual
  corresponde **exatamente** a um dos padrões do Revit.

---

## ✋ Janelas de aviso do Revit respondidas com "OK"

Algumas famílias fazem o Revit abrir uma janela **modal** durante o lote:

> **As restrições entre a geometria da família podem se comportar de forma imprevisível ao
> modificar parâmetros...** — botões **Remover restrições** e **OK**

Enquanto ninguém responde, o **Dynamo fica parado** (a janela aparece mesmo quando a família
é aberta/salva por API). O script responde **"OK" sozinho**, por dois caminhos que se completam:

| Origem do aviso | Como é tratado | Código |
|---|---|---|
| Avisos/falhas gerados pelas **transações do script** (excluir elementos, trocar unidades, renomear vistas, criar/orientar a vista 3D, gravar o preview) | `IFailuresPreprocessor` descarta os avisos e deixa a transação seguir — exatamente o efeito de clicar em **OK** | `silenciar_avisos(transacao, avisos)`, chamado em **todas** as transações |
| Janelas que o **próprio Revit** abre (ao abrir/salvar a família, por exemplo) | o evento `UIApplication.DialogBoxShowing` responde a janela **antes** de ela aparecer, com `DialogBoxShowingEventArgs.OverrideResult(1)` | `ativar_respostas_automaticas()` / `_ao_mostrar_dialogo()` |

O código do botão é `RESULTADO_OK = 1` = `TaskDialogResult.Ok` (o mesmo `IDOK` das caixas de
mensagem do Windows; em um Task Dialog com *command links*, o `CommandLink1` seria `1001`).

### O que o script nunca faz

- **Não escolhe "Remover restrições"** (nem qualquer outra *resolução*): a família **não é
  alterada** por causa do aviso — a resposta automática é sempre o botão **OK**.
- Se um passo depender de uma *resolução*, a transação é **desfeita**
  (`FailureProcessingResult.ProceedWithRollBack`) e o motivo entra nos `avisos:` da família:
  preferimos pular um passo (e registrar) a travar o lote ou mudar a geometria do cliente.
- Nada fica alterado no Revit: o handler do evento é **removido** no fim do lote
  (`desativar_respostas_automaticas()`, dentro de `try/finally`).

### Como saber qual janela foi respondida

Com `REGISTRAR_DIALOGOS = True`, cada resposta vira uma linha no `OUT`/log (e a quantidade
aparece no `RESUMO`):

```
JANELA | OK: TaskDialog_... | As restricoes entre a geometria da familia...
```

Se o evento não puder ser assinado (situação incomum), o lote continua normalmente e aparece
o aviso `AVISO  | nao foi possivel assinar o evento de janelas do Revit ...`.

### Ajustando o comportamento

| Situação | O que fazer |
|---|---|
| Responder **tudo** manualmente | `RESPONDER_DIALOGOS_COM_OK = False` |
| Deixar **uma** janela para o usuário (ex.: "Salvar?") | `IDS_DIALOGOS_IGNORADOS = ("TaskDialog_Save",)` — o `DialogId` exato aparece nas linhas `JANELA` do log/`OUT` |
| Não poluir o log | `REGISTRAR_DIALOGOS = False` |
| Botão diferente de "OK" (raro) | troque `RESULTADO_OK` (ex.: `1001` = primeiro *command link*) |

Uma **falha de erro** (não apenas um aviso) não pode ser "descartada": nesse caso a transação
é desfeita e a linha da família mostra `avisos: ... Revit: <texto da falha> (transacao desfeita)`.

### Por que o aviso aparece (e como eliminá-lo)

A causa está na própria família: há geometria **sem restrição** a níveis, planos de referência
ou linhas de referência. O aviso é informativo — **"OK"** significa *"continuar sem mexer nas
restrições"*, que é o que o script responde. Para o aviso deixar de aparecer também fora do
lote, a recomendação da Autodesk é editar a família e **restringir a geometria**
(alinhar + bloquear). Clicar em **"Remover restrições" NÃO é equivalente**: o Revit apaga
restrições existentes para "resolver" o aviso, o que pode **mudar o comportamento da família**.

> ℹ️ **Limite conhecido:** a API do Revit documenta que **nem todo** diálogo dispara o evento
> `DialogBoxShowing` — janelas mostradas no meio de algumas chamadas de API podem não ser
> interceptáveis. Por isso o `IFailuresPreprocessor` também está em todas as transações e as
> janelas respondidas **ficam registradas**: se o lote parar em uma janela, o `DialogId` (ou a
> ausência dele) no log mostra exatamente o que aconteceu.

---

## 🔄 Diferenças em relação à versão anterior

| Item | Antes | Agora |
|---|---|---|
| Salvamento | `doc.SaveAs(mesmo caminho)` → **File already exists!** | `doc.Save(SaveOptions)` no mesmo caminho |
| Opção de sobrescrever | `OverwriteExistingFiles` (não existe) | `OverwriteExistingFile = True` (usada só no modo "outra pasta") |
| Purge Unused | `PerformanceAdviser` + `rule.Guid` (propriedade que **não existe** em `PerformanceAdviserRuleId`) | `Document.GetUnusedElements()` — API oficial do Purge Unused |
| Preview/miniatura | `SaveAsOptions.PreviewViewId` apenas | `SaveOptions.PreviewViewId` + `DocumentPreviewSettings` (com validação `IsViewIdValidForPreview`) |
| Fechamento | `doc.Close(False)` só no fim do fluxo normal | `try/finally`: a família é fechada mesmo se houver erro |
| Avisos do Revit | podiam interromper/abrir janelas | `IFailuresPreprocessor` (`silenciar_avisos`) descarta os avisos de **todas** as transações |
| Janela "Remover restrições / OK" | o lote parava esperando um clique do usuário | respondida **automaticamente com "OK"** (`DialogBoxShowing` + `OverrideResult(1)`), sem nunca escolher "Remover restrições" |
| Segurança dos originais | nenhuma | backup em `_backup_upgrade\` |
| Rastreabilidade | apenas `OUT` | `OUT` + log `_log_atualiza_familias.txt` |
| Arquivo já aberto | podia falhar | é **pulado** com aviso (`arquivo ja aberto no Revit`) |
| **Tipo de vista do preview** | fixo em `Vista 1` (View3D) | escolhido em `IN[1]`: `Vista 3D` / `Planta` / `Corte` / `Detalhe` / `Elevação` |
| **Direção da vista 3D** | 4 fixas em código (`SE/SO/NE/NO Isometric`) | escolhida em `IN[2]`: **6 vistas do cubo** (`FSD`, `FSE`, `TSD`, `TSE`, `FID`, `FIE`) — os nomes antigos continuam aceitos como apelido |
| **Estilo visual** | constante `ESTILO_VISUAL_VISTA_3D` no `.py` | escolhido em `IN[3]` (`Wireframe`, `Hidden Lines`, `Shading`, `Shading With Edges`, `Flat Colors`, `Realistic`, `Realistic With Edges`) — a constante continua valendo como padrão |
| **Interface do usuário** | editar o `.py` a cada mudança | Custom Selection no grafo; valor desconhecido cai no padrão com `AVISO` no `OUT` |
| Nomes das vistas | mantidos em inglês (`Ref. Level`, `Front`, `View 2`...) | traduzidos para pt-BR (`Nível de Referência`, `Parte Frontal`, `Vista 2`...), com comparação que **ignora acento/caixa/ponto final** e que também cobre **francês e espanhol** |

---

## 🛠️ Como usar no Dynamo (Revit 2026)

1. Abra o **Revit 2026** com um documento qualquer aberto.
2. Aba **Gerenciar** → **Dynamo** → abra o arquivo `Atualiza Familias em Lote.dyn`.
3. Confira o grafo — ele deve ter 5 nós:
   - **Directory Path** → `IN[0]` (pasta com as famílias `.rfa`);
   - **Custom Selection** (tipo de vista) → `IN[1]`;
   - **Custom Selection** (isométrica) → `IN[2]`;
   - **Custom Selection** (estilo visual) → `IN[3]`;
   - **Python Script** (engine **CPython3**).
4. **Confira as opções dos Custom Selections** — veja
   [Escolhas no Dynamo](#️-escolhas-no-dynamo-custom-selection-in1in2in3) para as tabelas
   Display/Value que devem estar configuradas em cada um.
5. (Opcional) Conecte a saída `OUT` a um nó **Watch** para ver o resultado.
6. Deixe a execução em **Manual** e clique em **Executar**.

> Também é aceito: `IN[0]` com uma **lista** de caminhos `.rfa`, ou o caminho de
> **um único** arquivo.

### Saída (`OUT`)

Uma lista de textos, iniciando pelo resumo, por exemplo:

```
RESUMO | familias encontradas: 12 | OK: 11 | puladas: 1 | falhas: 0 | IN[1] tipo de vista: VISTA_3D | IN[2] isometrica: FSD | IN[3] estilo: SHADING | janelas do Revit respondidas: 1 | log: D:\...\_log_atualiza_familias.txt
OK     | Double-Glass 1.rfa | purgados: 8 | vista preview: Vista 1 (VISTA_3D) | estilo: SOMBREADO_COM_ARESTAS (de SOMBREADO + MOSTRAR_ARESTAS_VISTA_3D) | categorias ocultas: 12 | vistas renomeadas: 3 | salvo em: Double-Glass 1.rfa
OK     | Porta Simples.rfa | purgados: 4 | vista preview: Vista 1 (VISTA_3D) | estilo: SHADING | categorias ocultas: 11 | vistas renomeadas: 0 | salvo em: Porta Simples.rfa
FALHA  | Exemplo.rfa | <mensagem de erro>
AVISO  | IN[2] (isometrica): valor desconhecido 'One' - usando padrao 'FSD'
JANELA | OK: TaskDialog_... | <mensagem da janela do Revit respondida automaticamente>
```

- `IN[1] tipo de vista:` mostra o tipo escolhido (o que será usado como preview).
- `IN[2] isometrica:` mostra a isométrica escolhida (`FSD`, `FSE`, `TSD`, `TSE`, `FID`, `FIE`).
- `IN[3] estilo:` mostra o estilo escolhido (`WIREFRAME`, `HIDDEN_LINES`, `SHADING`,
  `SHADING_WITH_EDGES`, `FLAT_COLORS`, `REALISTIC`, `REALISTIC_WITH_EDGES`).
- `vista preview: NOME (TIPO)` mostra a vista usada como preview e o tipo efetivo
  (`VISTA_3D`, `PLANTA`, `CORTE`, `DETALHE`, `ELEVACAO`) — pode diferir de `IN[1]`
  quando o fallback para `Vista 3D` foi acionado.
- `estilo:` mostra a chave que valeu de fato; `nao aplicado` quando o estilo não pôde
  ser trocado ou está desligado (o motivo aparece em `avisos:`).
- `categorias ocultas:` é a **quantidade** de categorias de `CATEGORIAS_OCULTAS_VISTA_3D`
  efetivamente ocultadas.
- `vistas renomeadas:` é quantas vistas receberam nome em português (Brasil).
- Avisos não fatais (ex.: orientação não gravada, nome já em uso, valor desconhecido em
  `IN[x]`) aparecem no fim da linha, após `avisos:` ou como linha `AVISO  |`.
- `janelas do Revit respondidas:` (no `RESUMO`) e as linhas `JANELA | OK: ...` mostram as
  janelas modais que o script respondeu sozinho.

---

## ⚙️ Configurações (topo do script)

| Constante | Padrão | Para que serve |
|---|---|---|
| `SALVAR_NO_MESMO_ARQUIVO` | `True` | `True` = sobrescreve o original; `False` = grava em outra pasta |
| `PASTA_DESTINO` | `""` | Pasta de destino quando `SALVAR_NO_MESMO_ARQUIVO = False` (vazio = `<origem>_2026`) |
| `FAZER_BACKUP` | `True` | Copia o `.rfa` original antes de sobrescrever |
| `PASTA_BACKUP` | `_backup_upgrade` | Subpasta de backup criada na **raiz da pasta pesquisada** (`IN[0]`), preservando as subpastas (não é reprocessada) |
| `IGNORAR_JA_ATUALIZADAS` | `False` | `True` = pula arquivos já salvos no Revit atual (`BasicFileInfo.IsSavedInCurrentVersion`) |
| `SISTEMA_METRICO_COMPLETO` | `True` | `True` = todas as especificações em métrico; `False` = só comprimento/área/volume |
| `ACCURACY_COMPRIMENTO` | `0.001` | Precisão do comprimento **na unidade de exibição** (0.001 mm = 3 decimais) |
| `USAR_AGRUPAMENTO_UNIDADES` | `True` | Agrupamento de milhar também nos formatos de comprimento/área/volume |
| `MAX_PASSES_PURGE` | `30` | Limite de iterações do Purge Unused (evita loop infinito) |
| `ESCREVER_LOG` / `NOME_LOG` | `True` / `_log_atualiza_familias.txt` | Grava o log na **raiz da pasta pesquisada** (`IN[0]`) |
| `RESPONDER_DIALOGOS_COM_OK` | `True` | `True` = responde **"OK"** sozinho nas janelas de aviso do Revit (nunca escolhe "Remover restrições") |
| `RESULTADO_OK` | `1` | Código do botão **OK** (`TaskDialogResult.Ok` / `IDOK`); `1001` = primeiro *command link* |
| `IDS_DIALOGOS_IGNORADOS` | `()` | `DialogId`s que **não** devem ser respondidos (a janela fica para o usuário) |
| `REGISTRAR_DIALOGOS` | `True` | `True` = grava no `OUT`/log cada janela respondida (linhas `JANELA`) |
| `UNIDADE_COMPRIMENTO` / `UNIDADE_AREA` / `UNIDADE_VOLUME` | `Millimeters` / `SquareMeters` / `CubicMeters` | Unidades aplicadas explicitamente em cada especificação |
| `NOME_VISTA_3D` | `"Vista 1"` | Nome imposto à vista 3D salva no arquivo (e usada como preview) |
| `CRIAR_VISTA_3D_SE_FALTAR` | `True` | `True` = cria uma vista 3D isométrica quando a família não tiver nenhuma |
| `DIRECAO_VISTA_3D` | `"FSD"` | Direção **padrão** da vista 3D quando `IN[2]` não vem (`FSD`, `FSE`, `TSD`, `TSE`, `FID`, `FIE`) |
| `FATOR_DISTANCIA_VISTA_3D` | `2.0` | Distância do olho = fator × diagonal do modelo |
| `TAMANHO_MINIMO_VISTA_3D` | `3.0` | Diagonal mínima considerada, em unidades internas (pés) |
| `GRAVAR_ORIENTACAO_VISTA_3D` | `True` | `True` = chama `View3D.SaveOrientation()` (o `.rfa` reabre na isométrica escolhida); `False` = só orienta na sessão atual |
| `ESTILO_VISUAL_VISTA_3D` | `"SOMBREADO"` | **Padrão** de estilo visual quando `IN[3]` não vem: `ESTRUTURA_ARAME`, `LINHAS_OCULTAS`, `SOMBREADO`, `SOMBREADO_COM_ARESTAS`, `CORES_CONSISTENTES`, `REALISTA`, `REALISTA_COM_ARESTAS`. Aceita apelidos e `""` = não mexer no estilo |
| `MOSTRAR_ARESTAS_VISTA_3D` | `True` | `True` = troca o estilo pedido pela variante **com arestas** (`SOMBREADO` → `SOMBREADO_COM_ARESTAS`, `REALISTA` → `REALISTA_COM_ARESTAS`); `ESTRUTURA_ARAME`/`LINHAS_OCULTAS` não mudam. **Não existe `View.ShowEdges` na API** |
| `OCULTAR_CATEGORIAS_VISTA_3D` | `True` | `True` = oculta **por categoria** as anotações/cotas e os elementos auxiliares na vista de preview |
| `CATEGORIAS_OCULTAS_VISTA_3D` | 12 `OST_*` | `BuiltInCategory`s ocultadas: `OST_Dimensions`, `OST_TextNotes`, `OST_GenericAnnotation`, `OST_Levels`, `OST_Grids`, `OST_CLines`, `OST_ReferenceLines`, `OST_ReferencePoints`, `OST_Walls`, `OST_Floors`, `OST_Ceilings`, `OST_Roofs` (a categoria da própria família é sempre preservada) |
| `RENOMEAR_VISTAS_PT_BR` | `True` | `True` = traduz nomes de vistas padrão do Revit para português (Brasil) |

---

## 📌 Observações importantes

- **Unidades = exibição.** Alterar as unidades do projeto/família **não redimensiona
  a geometria** nem converte valores: os valores continuam os mesmos (internamente o
  Revit sempre trabalha em unidades internas). Se uma família foi desenhada em pés,
  ela continuará com o mesmo tamanho físico — apenas exibido em mm/m.
- **`FormatOptions.Accuracy` é dado na unidade de exibição** (não nas unidades
  internas). Para mm, `0.001` = 3 casas decimais; use `0.1` ou `1.0` para menos casas.
- **`GetUnusedElements` existe a partir do Revit 2024** (por isso funciona no 2026).
  Ele devolve apenas elementos que **podem** ser excluídos (os da janela Purge Unused).
- **Coleções da API no CPython3:** `Document.GetUnusedElements()` e `Document.Delete()`
  devolvem coleções que o pythonnet entrega ao Python como **listas** (sem a
  propriedade `.Count` do IronPython). Por isso o script usa o auxiliar
  `contar()` — funciona tanto com listas Python (`len()`) quanto com coleções
  .NET (`.Count`). O erro `'list' object has no attribute 'Count'` vem de código
  escrito para IronPython rodando no CPython3.
- **Famílias já abertas no Revit são puladas**, para evitar conflito de arquivo.
- Ao sobrescrever, o Revit pode criar arquivos auxiliares de backup (ex.: `.0001.rfa`).
  O backup do script (`_backup_upgrade\`) é uma cópia do original **antes** do upgrade.
- **O `_backup_upgrade\` e o log nascem na raiz da pesquisa** — a pasta informada em
  `IN[0]` (ou a pasta do arquivo, quando `IN[0]` é um `.rfa`) —, **nunca** dentro da
  primeira subpasta que tiver uma família. Com uma **lista** de pastas em `IN[0]`,
  cada pasta pesquisada recebe o **seu** `_backup_upgrade\`, preservando a árvore de
  cada uma a partir dela mesma; o log fica na **primeira** pasta de `IN[0]`.
- **A vista de preview pode não ser 3D.** Se `IN[1]` for `Planta`/`Corte`/`Detalhe`/
  `Elevação`, o script **valida** com `IsViewIdValidForPreview` — se o Revit recusar,
  cai na `Vista 3D` com aviso. Nem toda versão do Revit aceita essas vistas como preview
  de família; o fallback é intencional.
- **A API não permite "ativar" uma vista de um documento aberto em segundo plano**; o
  que define a miniatura do arquivo é o **preview** — que o script grava.
- **Orientação gravada ≠ orientação da sessão:** `SetOrientation` só muda a vista na
  sessão atual; é `View3D.SaveOrientation` que grava a direção no arquivo. Como a API
  proíbe gravar a orientação da vista 3D **padrão** do documento, essa vista é
  renomeada para `Vista 1` antes — e é isso que faz o `.rfa` reabrir na isométrica
  escolhida.
- **As 6 isométricas vêm do ViewCube** (`FSD`, `FSE`, `TSD`, `TSE`, `FID`, `FIE`). As
  4 primeiras são idênticas às antigas `SE/SO/NE/NO Isometric` — os nomes antigos
  continuam aceitos como apelido para não quebrar grafos.
- **Estilo visual e categorias ocultas também são propriedades da VISTA**
  (`View.DisplayStyle` e `View.SetCategoryHidden`), não do documento: ficam gravados
  no `.rfa` junto com a vista e são exatamente o que aparece no preview/miniatura.
  `DisplayStyle.Shaded` **não existe** — "Sombreado" é `DisplayStyle.Shading`.
- **A API não tem `View.ShowEdges` nem `View3D.ShowEdges`**: o checkbox *Mostrar
  arestas* não é acessível por propriedade (conferido na `RevitAPI.xml` do Revit 2026).
  Para o preview sair sombreado **com** as arestas, o script usa
  `DisplayStyle.ShadingWithEdges` ("Sombreado com arestas").
- **Não existe `View.HideElements` em documento de família:** ocultar elementos
  isolados não é possível pela API; o script oculta por **categoria**. A categoria
  da própria família (`Family.FamilyCategory`) é sempre preservada.
- Se a família não tiver tipo de vista 3D (caso raro), o script não consegue criar a
  vista, segue normalmente e registra o aviso no `OUT`.
- **Nomes de vistas:** apenas `View.Name` é alterado. Agrupamentos do Navegador de
  Projeto (`Views`, `3D Views`...) são textos da interface do Revit (definidos pelo
  idioma instalado) e **não** existem como propriedade renomeável na API.
- **Respostas automáticas = "OK", nunca "Remover restrições".** O script descarta os
  avisos das próprias transações (`IFailuresPreprocessor`) e responde "OK" nas janelas
  que o Revit abre por conta própria (`DialogBoxShowing`) — em nenhum caso ele altera
  as restrições da família para "resolver" um aviso.
- **O handler de janelas é temporário:** é assinado em `ativar_respostas_automaticas()`
  (início do lote) e removido em `desativar_respostas_automaticas()` (dentro de
  `try/finally`), então o Revit volta ao comportamento normal ao terminar — inclusive
  se o script falhar.

---

## ✅ Requisitos

- Revit 2026 (testado com `RevitAPI.dll` 2026) e Dynamo 3.4+ (**Dynamo 2.16+ para o
  nó `Custom Selection`** — Revit 2023.1+)
- Engine do nó Python: **CPython3** (não usar IronPython 2.7)
- Permissão de escrita na pasta das famílias (evite arquivos marcados como somente leitura)
- (Opcional) Python 3 para rodar `validar_traducao.py`, `validar_respostas_revit.py` e
  `validar_vista_3d.py` fora do Revit — o Python do próprio Dynamo serve
  (ex.: `%LOCALAPPDATA%\python-3.9.12-embed-amd64\python.exe`)

## 🧰 Solução de problemas

| Sintoma | Provável causa / solução |
|---|---|
| Não encontro o nó `Custom Selection` no Dynamo | Use **Dynamo 2.16+ (Revit 2023.1+)**. Em versões antigas, use o pacote **Data-Shapes** (`UI.DropDown Data`) ou escreva os valores manualmente em Code Blocks |
| `AVISO \| IN[x]: valor desconhecido 'One'` no `OUT` | O Custom Selection está com o valor padrão (`One`) — abra o nó e configure as opções Display/Value conforme as tabelas em [Escolhas no Dynamo](#️-escolhas-no-dynamo-custom-selection-in1in2in3) |
| `File already exists!` | Use `doc.Save(SaveOptions)` (já corrigido) ou `OverwriteExistingFile = True` (singular) no `SaveAs` |
| `The file is read-only, can not be saved` | Desmarque "Somente leitura" no arquivo/pasta |
| `options.PreviewViewId is not valid for generation of a preview` | A vista escolhida em `IN[1]` não serve como preview — o script valida antes e, se falhar, cai na Vista 3D |
| Arquivo pulado com "ja aberto no Revit" | Feche a família no Revit e execute novamente |
| `_backup_upgrade` criado **dentro de uma subpasta** | Era um **bug**: a raiz era deduzida do **primeiro `.rfa`**. Já corrigido — cada família leva a **sua raiz da pesquisa** (`IN[0]`). **Rode `sincronizar_dyn.ps1`** |
| Log com o nome antigo `_log_formatar_unidades.txt` | O log passou a se chamar `_log_atualiza_familias.txt`. Logs antigos podem ser apagados e é preciso **rodar `sincronizar_dyn.ps1`** |
| Aviso `Backup: nao foi possivel copiar o original` | O `_backup_upgrade\` não pôde ser criado/copiado. O `.rfa` seria sobrescrito **sem** cópia do original — libere a pasta e execute de novo |
| `'list' object has no attribute 'Count'` | No engine **CPython3 (pythonnet)** as coleções vêm como **listas**; o script usa `contar()` (`len()` com fallback para `.Count`) — já corrigido |
| A vista de preview não abre na isométrica escolhida | (1) `IN[2]` está com valor desconhecido (aparece `AVISO` no `OUT`); (2) `IN[1]` não é `Vista 3D` — só ela aceita `SetOrientation`; (3) `GRAVAR_ORIENTACAO_VISTA_3D = False`; (4) a vista ainda é a padrão do documento (o script renomeia para `Vista 1` justamente por isso) |
| `AVISO \| IN[1] (tipo de vista): ... usando a vista 3D como fallback` | A vista escolhida não pôde ser obtida/criada ou não é válida como `PreviewViewId` — o script cai na Vista 3D. Escolha `Vista 3D` ou verifique se a família tem o tipo de vista necessário |
| O preview/miniatura não fica no estilo pedido | (1) `IN[3]` está com valor desconhecido (aparece `AVISO`); (2) `ESTILO_VISUAL_VISTA_3D` no `.py` está `""`/`None`; (3) o **`.dyn` está desatualizado** — rode `sincronizar_dyn.ps1`; (4) aparece `o arquivo ficou em 'X' (pedido: 'Y')` em `avisos:` — o Revit recusou o estilo naquela vista |
| **Mudei `IN[3]` no dropdown e a miniatura não mudou** | (1) `MOSTRAR_ARESTAS_VISTA_3D = True` está trocando `SHADING` por `SHADING_WITH_EDGES` — veja a seção [Arestas visíveis](#arestas-visíveis-no-preview-mostrar_arestas_vista_3d); (2) o arquivo pode ter sido `PULADO` (já aberto no Revit / `IGNORAR_JA_ATUALIZADAS`); (3) o Windows mantém **cache de miniaturas** — pressione F5/feche e reabra a pasta |
| As arestas não aparecem no preview sombreado | Não existe `View.ShowEdges`/`View3D.ShowEdges` na API. Use `MOSTRAR_ARESTAS_VISTA_3D = True` (aplica `DisplayStyle.ShadingWithEdges`) ou escolha `Shading With Edges` direto em `IN[3]`. Em uma versão sem esse valor do enum, use `Hidden Lines` (`DisplayStyle.HLR`) |
| As anotações/cotas continuam aparecendo na vista de preview | (1) `OCULTAR_CATEGORIAS_VISTA_3D = False`; (2) a categoria não está em `CATEGORIAS_OCULTAS_VISTA_3D`; (3) o `.dyn` está desatualizado |
| `categoria(s) nao encontrada(s)` nos `avisos:` | Algum nome de `CATEGORIAS_OCULTAS_VISTA_3D` não existe como valor de `BuiltInCategory`. Ele é ignorado com aviso — corrija o nome |
| `DisplayStyle.Shaded` / `AttributeError: Shaded` | Esse valor **não existe** na API: "Sombreado" é `DisplayStyle.Shading` |
| A vista de preview ficou vazia depois de ocultar categorias | Não deveria acontecer: a categoria da própria família nunca é ocultada. Se a geometria estiver em outra categoria (ex.: `OST_GenericModel`), remova essa categoria de `CATEGORIAS_OCULTAS_VISTA_3D` |
| `Could not save the orientation of the view` / aviso "a orientacao nao pode ser gravada" | `View3D.SaveOrientation()` foi chamado em uma vista 3D padrão (`CanSaveOrientation()` = `False`) — renomeie a vista (o script já faz com `NOME_VISTA_3D`) |
| Aviso/erro de "up vector is not perpendicular to the view direction" | O par `forward`/`up` de alguma entrada de `DIRECOES_VISTA_3D` não é ortogonal; use uma das 6 já validadas |
| Nomes de vistas continuam em inglês | (1) `RENOMEAR_VISTAS_PT_BR = False`; (2) o `.dyn` está **desatualizado** — rode `sincronizar_dyn.ps1`; (3) o nome não corresponde a nenhum padrão conhecido |
| Vistas em francês/espanhol continuam sem tradução | Falta cadastrar o nome: ligue `RELATAR_VISTAS_NAO_TRADUZIDAS = True`, rode o lote e veja `vistas sem traducao: ...` no log/`OUT` |
| Agrupamentos `Views` / `3D Views` continuam em inglês | São textos da interface do Revit (idioma instalado), não propriedades da API |
| O lote **parou** na janela *"As restrições entre a geometria..."* | Confirme `RESPONDER_DIALOGOS_COM_OK = True` e **rode `sincronizar_dyn.ps1`** |
| Aviso `nao foi possivel assinar o evento de janelas do Revit` | O evento `DialogBoxShowing` não pôde ser assinado (incomum): o lote segue, mas alguma janela pode continuar aparecendo |
| Janela respondida com "OK" mas o passo não foi feito (`avisos: ... Revit: ... (transacao desfeita)`) | Era uma **falha de erro** (não um aviso): o Revit só "resolve" alterando alguma coisa, e o script prefere desfazer a transação |
| O aviso de restrições voltou a aparecer em outros fluxos | A causa é a geometria sem restrição na família — edite-a e **restringir** (alinhar + bloquear). O script sempre responde "OK" |
````