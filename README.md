# Atualiza Famílias em Lote — atualização e formatação em lote de famílias do Revit (.rfa) — Revit 2026

Script em Python para rodar dentro do **Dynamo do Revit 2026** (engine **CPython3**).
Processa uma **pasta inteira** (e subpastas) de famílias `.rfa`, atualizando cada
arquivo para o Revit 2026 e padronizando unidades/formato numérico.

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
5. **Vista 3D `Vista 1` garantida, em SE Isometric** — o script assegura uma vista
   3D chamada `NOME_VISTA_3D` (`"Vista 1"`): renomeia a vista 3D existente (ou cria
   uma com `View3D.CreateIsometric` se a família não tiver nenhuma), aplica a direção
   `DIRECAO_VISTA_3D` (`View3D.SetOrientation`) e **grava a orientação dentro do
   arquivo** (`View3D.SaveOrientation`) — o `.rfa` reabre já em SE Isometric.
   Sem vista 3D para preview, o script cria uma; sem tipo de vista 3D, segue e
   registra o aviso.
6. **Vista 3D em estilo "Sombreado com arestas", sem anotações/cotas** — na **mesma**
   vista 3D gravada como preview, o script aplica o estilo visual
   (`View.DisplayStyle`, via `ESTILO_VISUAL_VISTA_3D`) e, com
   `MOSTRAR_ARESTAS_VISTA_3D = True`, usa a variante **com arestas** do estilo
   (`DisplayStyle.ShadingWithEdges` = "Sombreado com arestas"). Em seguida
   **oculta por categoria** as anotações/cotas (cotas, notas de texto, símbolos de
   anotação, níveis, eixos) e os elementos auxiliares (planos/linhas/pontos de
   referência, paredes, pisos, forros, telhados) com `View.SetCategoryHidden()`
   (`OCULTAR_CATEGORIAS_VISTA_3D` / `CATEGORIAS_OCULTAS_VISTA_3D`). A categoria da
   **própria família** nunca é ocultada — o preview nunca fica vazio. Veja
   [Estilo visual e categorias ocultas na vista 3D](#estilo-visual-e-categorias-ocultas-na-vista-3d).
7. **Preview/miniatura** — a vista 3D é gravada como preview permanente do documento
   (`DocumentPreviewSettings.PreviewViewId`, validada antes por
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
> [Como usar no Dynamo](#️-como-usar-no-dynamo-revit-2026)); sem isso o Dynamo
> continua rodando a **versão antiga** do código — foi exatamente por isso que as
> traduções novas não surtiram efeito.

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
if vista3d is not None:
    opcoes.PreviewViewId = vista3d.Id
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

## 🧭 Vista 3D `Vista 1` em SE Isometric (orientação gravada no arquivo)

### Ordem das ações no lote

1. `obter_vista_3d(doc)` escolhe a vista 3D, nesta ordem de preferência:
   1. a vista 3D que **já** se chama `NOME_VISTA_3D` (`"Vista 1"`);
   2. uma vista 3D válida para preview (`DocumentPreviewSettings.IsViewIdValidForPreview`),
      preferindo os nomes típicos criados pelo Revit (`View 1`, `Vista 3D`, `{3D}`...);
   3. **cria** uma vista 3D isométrica com `View3D.CreateIsometric(doc, tipo.Id)`
      (tipo de vista cujo `ViewFamily == ViewFamily.ThreeDimensional`), se
      `CRIAR_VISTA_3D_SE_FALTAR = True`.

   Modelos de vista (`View3D.IsTemplate = True`) são sempre ignorados.
2. `padronizar_nome_vista_3d(doc, vista)` garante o nome `Vista 1` (`View.Name`); se
   o nome já estiver em uso por outra vista, avisa e não renomeia.
3. `orientar_vista_3d(doc, vista)` aplica a direção de `DIRECAO_VISTA_3D` e **grava**.
4. `definir_estilo_vista_3d(doc, vista, avisos)` aplica o estilo visual de
   `ESTILO_VISUAL_VISTA_3D` (`View.DisplayStyle`); se a vista já está no estilo pedido,
   devolve `True` sem criar transação.
5. `ocultar_categorias_vista_3d(doc, vista, avisos)` oculta **por categoria** o que está
   em `CATEGORIAS_OCULTAS_VISTA_3D` (uma única transação) e devolve a lista do que foi
   ocultado — a categoria da própria família é sempre preservada.
6. `definir_preview_permanente(doc, vista)` grava a vista como preview permanente.
7. `renomear_vistas_pt_br(doc)` traduz as vistas que continuam com nome padrão em inglês.

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

### SE Isometric e as demais direções

`ViewOrientation3D(eye, up, forward)` recebe o **ponto do olho**, o vetor *up* e o vetor
*forward*. O Revit exige que *up* seja **perpendicular** a *forward* (caso contrário
lança exceção). Todos os pares da tabela são ortogonais e mantêm o eixo Z na vertical
da tela — a mesma direção da vista 3D padrão do Revit:

| `DIRECAO_VISTA_3D` | Direção | forward | up | forward · up |
|---|---|---|---|---|
| `SE_ISOMETRIC` (padrão) | Sudeste | `(-1, 1, -1)` | `(-1, 1, 2)` | 0 |
| `SO_ISOMETRIC` | Sudoeste | `(1, 1, -1)` | `(1, 1, 2)` | 0 |
| `NE_ISOMETRIC` | Nordeste | `(-1, -1, -1)` | `(-1, -1, 2)` | 0 |
| `NO_ISOMETRIC` | Noroeste | `(1, -1, -1)` | `(1, -1, 2)` | 0 |

O **olho** é calculado a partir do modelo:
`olho = centro − forward × (diagonal × FATOR_DISTANCIA_VISTA_3D)`, em que `centro` e
`diagonal` vêm da união das caixas de envolvimento dos elementos — obtidas com
`Element.BoundingBox(View)`, a **propriedade indexada** que em Python se acessa como
`elemento.get_BoundingBox(vista)` (o script tenta primeiro com a vista `Vista 1` e
depois com `None`). Se nenhuma geometria for encontrada, usa a origem e
`TAMANHO_MINIMO_VISTA_3D`, para a vista nunca ficar sem enquadramento.

### Estilo visual e categorias ocultas na vista 3D

Dois ajustes são feitos **na mesma vista 3D** que vira preview, depois de orientar e
**antes** de salvar:

| Constante | Padrão | Efeito |
|---|---|---|
| `ESTILO_VISUAL_VISTA_3D` | `"SOMBREADO"` | Estilo pedido: `View.DisplayStyle` |
| `MOSTRAR_ARESTAS_VISTA_3D` | `True` | `True` = troca o estilo pedido pela variante **com arestas** (`DisplayStyle.ShadingWithEdges`) |
| `OCULTAR_CATEGORIAS_VISTA_3D` | `True` | liga/desliga o passo que oculta categorias |
| `CATEGORIAS_OCULTAS_VISTA_3D` | 12 `BuiltInCategory` | `View.SetCategoryHidden(cat.Id, True)` |

`View.DisplayStyle` é propriedade da **vista** (não do documento): fica gravada no `.rfa`
e é o estilo que aparece na miniatura. Valores aceitos:

| `ESTILOS_VISUAIS_VISTA_3D` | `DisplayStyle` | Rótulo no Revit |
|---|---|---|
| `ESTRUTURA_ARAME` | `DisplayStyle.Wireframe` | Estrutura de arame |
| `LINHAS_OCULTAS` | `DisplayStyle.HLR` | Linhas ocultas |
| `SOMBREADO` (padrão) | `DisplayStyle.Shading` | Sombreado |
| `SOMBREADO_COM_ARESTAS` | `DisplayStyle.ShadingWithEdges` | **Sombreado com arestas** (é o padrão de fato) |
| `CORES_CONSISTENTES` | `DisplayStyle.FlatColors` | Cores consistentes |
| `REALISTA` | `DisplayStyle.Realistic` | Realista |
| `REALISTA_COM_ARESTAS` | `DisplayStyle.RealisticWithEdges` | Realista com arestas |

`estilo_visual_configurado()` aceita a **chave**, um **apelido** (`SHADING`, `Shaded`,
`Wireframe`, `Hidden_Lines`, `SHADING_WITH_EDGES`, `FlatColors`, `Realistic`...) ou o
**próprio valor do enum** (`ESTILO_VISUAL_VISTA_3D = DisplayStyle.Shading`). A comparação
normaliza caixa e espaços (`"_".join(valor.split()).upper()`), então `"Estrutura de arame"`
e `"Sombreado com arestas"` também funcionam. Com `""` (string vazia) ou `None` o estilo
**não é mexido** (`estilo 3D: nao aplicado` no `OUT`).

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

| `ESTILO_VISUAL_VISTA_3D` | Estilo aplicado de fato |
|---|---|
| `"SOMBREADO"` / `SHADING` | `SOMBREADO_COM_ARESTAS` (`DisplayStyle.ShadingWithEdges`) |
| `"REALISTA"` / `REALISTIC` | `REALISTA_COM_ARESTAS` (`DisplayStyle.RealisticWithEdges`) |
| `"ESTRUTURA_ARAME"` / `"LINHAS_OCULTAS"` | iguais (já mostram as arestas) |
| `"CORES_CONSISTENTES"` | igual (não há variante com arestas na API) |
| `"SOMBREADO_COM_ARESTAS"` / `"REALISTA_COM_ARESTAS"` | iguais (já pedem as arestas) |
| `""` / `None` | nada é mexido |

Com `MOSTRAR_ARESTAS_VISTA_3D = False` vale exatamente o que estiver em
`ESTILO_VISUAL_VISTA_3D`. Em uma versão do Revit sem `ShadingWithEdges` /
`RealisticWithEdges` o ajuste é ignorado em silêncio (o estilo simples continua sendo
aplicado). `chave_estilo_visual()` e `descricao_estilo_visual()` fazem esse cálculo, e é
ele que aparece no `OUT`: `estilo 3D: SOMBREADO_COM_ARESTAS (de SOMBREADO + MOSTRAR_ARESTAS_VISTA_3D)`.

> 🔎 **Conferência depois de gravar:** `definir_estilo_vista_3d()` lê `View.DisplayStyle`
> de volta. Se o Revit aplicar outro estilo (a API recusa alguns estilos em algumas
> vistas), aparece `Vista 3D (estilo visual): o arquivo ficou em 'X' (pedido: 'Y')` em
> `avisos:` — em vez de a miniatura sair diferente do esperado sem ninguém perceber.

> ⚠️ **"Sombreado" é `DisplayStyle.Shading`.** O valor `DisplayStyle.Shaded` **não existe**
> na API. Se a constante não for reconhecida, o script **não altera a vista** e registra
> `Vista 3D (estilo visual): valor desconhecido '...' (use um de: ...)` em `avisos:`.

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
- Se **uma** categoria falhar, as outras continuam (`Vista 3D (ocultar X): ...`).
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
| Vista 3D | nenhuma garantia — a família ficava com a vista 3D que tivesse (ou nenhuma) | sempre uma vista 3D chamada `Vista 1`, orientada em **SE Isometric** e com a orientação **gravada** no arquivo (`View3D.SaveOrientation`) |
| Estilo/anotações no preview | a vista 3D ficava no estilo que estivesse e o preview aparecia cheio de cotas e anotações | estilo visual **"Sombreado"** (`ESTILO_VISUAL_VISTA_3D` → `View.DisplayStyle`) e anotações/cotas/elementos auxiliares **ocultos por categoria** (`View.SetCategoryHidden`), preservando a categoria da própria família |
| Nomes das vistas | mantidos em inglês (`Ref. Level`, `Front`, `View 2`...) | traduzidos para pt-BR (`Nível de Referência`, `Parte Frontal`, `Vista 2`...), com comparação que **ignora acento/caixa/ponto final** e que também cobre **francês e espanhol** |

---

## 🛠️ Como usar no Dynamo (Revit 2026)

1. Abra o **Revit 2026** com um documento qualquer aberto.
2. Aba **Gerenciar** → **Dynamo** → abra o arquivo `Atualiza Familias em Lote.dyn`
   (ou crie um novo grafo).
3. O grafo tem 2 nós:
   - **Directory Path**: selecione a pasta com as famílias `.rfa`;
   - **Python Script**: o código já vem **embutido** no `.dyn` (engine **CPython3**).

> **Sincronização do código:** o `.dyn` guarda o Python inteiro dentro de um único campo
> JSON (`"Code"`), em **uma só linha**, com aspas/barras escapadas. Para não colar à mão,
> use o script `sincronizar_dyn.ps1` sempre que `batch_format_families.py` mudar:
>
> ```powershell
> powershell -ExecutionPolicy Bypass -File ".\sincronizar_dyn.ps1"
> ```
>
> Ele grava o conteúdo do `.py` no campo `Code` (preservando o resto do grafo), **lê o
> `.dyn` de volta como JSON** e compara com o arquivo — se algo não bater, o script
> falha com aviso. Saída esperada:
> `OK | .dyn sincronizado com batch_format_families.py | NNNN caracteres | Engine: CPython3`

> **Conferência rápida, sem abrir o Revit:** `validar_traducao.py` testa a tradução dos
> nomes de vista (inglês, francês e espanhol) e, de quebra, confere se o `.dyn` está
> sincronizado com o `.py`:
>
> ```powershell
> python .\validar_traducao.py
> ```
>
> Saída esperada: `Dicionario: 112 entradas | regras: 16 | casos: 146` e
> `OK: todas as traducoes esperadas foram confirmadas.` (código de saída `0`; cada caso
> que não bater aparece listado). Rode-o depois de mexer em `NOMES_VISTAS_PT_BR` /
> `REGRAS_NOMES_VISTAS_PT_BR` e **antes** de `sincronizar_dyn.ps1`: se o `.dyn` estiver
> desatualizado, o próprio validador avisa — em vez de você descobrir só no Revit.

> **Validando as respostas automáticas:** `validar_respostas_revit.py` testa, **fora do
> Revit**, o handler de `DialogBoxShowing` (`OverrideResult(1)`, `IDS_DIALOGOS_IGNORADOS`,
> registro no log, tolerância a erro ao responder) e o `IFailuresPreprocessor` de
> `silenciar_avisos()` (aviso descartado = "OK"; falha de erro = rollback + registro). Ele
> usa stubs simples da API do Revit, lê o próprio `batch_format_families.py` e **não grava
> nada em disco**:
>
> ```powershell
> python .\validar_respostas_revit.py
> ```
>
> Saída esperada: uma linha `OK   | ...` por verificação e, no fim,
> `VERIFICACOES FALHAS: 0` (código de saída `0`; cada verificação que falhar aparece
> listada). Rode-o depois de mexer em `_ao_mostrar_dialogo()`, `silenciar_avisos()`,
> `RESULTADO_OK` ou `IDS_DIALOGOS_IGNORADOS`. Ele **não** confere o `.dyn` (isso é com
> `validar_traducao.py`), então o fluxo completo é: `validar_traducao.py` →
> `validar_respostas_revit.py` → `validar_vista_3d.py` → `sincronizar_dyn.ps1`.

> **Validando o estilo visual e as categorias ocultas:** `validar_vista_3d.py` testa,
> **fora do Revit**, o que o script faz na vista 3D antes de salvar:
> `definir_estilo_vista_3d()` (`DisplayStyle.ShadingWithEdges` = "Sombreado com arestas",
> chaves de `ESTILOS_VISUAIS_VISTA_3D`, apelidos, valor inválido → **aviso** sem mexer na
> vista, e a **conferência** do estilo que ficou na vista), `chave_estilo_visual()` /
> `descricao_estilo_visual()` / `MOSTRAR_ARESTAS_VISTA_3D` (o ajuste de arestas e o texto
> que sai no `OUT`) e `ocultar_categorias_vista_3d()` (`View.SetCategoryHidden` por
> categoria, `BuiltInCategory` inexistente ignorado, falha em uma categoria tolerada e a
> categoria da **própria família nunca ocultada**), além da ordem dos passos em
> `processar_familia()`.
> Usa stubs da API do Revit, lê o próprio `batch_format_families.py` e **não grava nada em
> disco**:
>
> ```powershell
> python .\validar_vista_3d.py
> ```
>
> Saída esperada: uma linha `OK   | ...` por verificação e, no fim,
> `VERIFICACOES FALHAS: 0` (código de saída `0`; cada falha aparece listada). Rode-o depois
> de mexer em `ESTILO_VISUAL_VISTA_3D`, `ESTILOS_VISUAIS_VISTA_3D`,
> `CATEGORIAS_OCULTAS_VISTA_3D` ou nas funções da vista 3D.

4. Conecte a saída do `Directory Path` em `IN[0]` do `Python Script`.
5. (Opcional) Conecte a saída `OUT` a um nó **Watch** para ver o resultado.
6. Deixe a execução em **Manual** e clique em **Executar**.

> Também é aceito: `IN[0]` com uma **lista** de caminhos `.rfa`, ou o caminho de
> **um único** arquivo.

### Saída (`OUT`)

Uma lista de textos, iniciando pelo resumo, por exemplo:

```
RESUMO | familias encontradas: 12 | OK: 11 | puladas: 1 | falhas: 0 | janelas do Revit respondidas: 1 | log: D:\...\_log_atualiza_familias.txt
OK     | Double-Glass 1.rfa | purgados: 8 | vista 3D: Vista 1 | estilo 3D: SOMBREADO | categorias ocultas: 12 | vistas renomeadas: 3 | salvo em: Double-Glass 1.rfa
OK     | Porta Simples.rfa | purgados: 4 | vista 3D: Vista 1 | estilo 3D: SOMBREADO | categorias ocultas: 11 | vistas renomeadas: 0 | salvo em: Porta Simples.rfa
FALHA  | Exemplo.rfa | <mensagem de erro>
JANELA | OK: TaskDialog_... | <mensagem da janela do Revit respondida automaticamente>
```

- `vista 3D:` mostra o nome da vista 3D usada como preview (`Vista 1` quando tudo correu bem).
- `estilo 3D:` mostra o valor de `ESTILO_VISUAL_VISTA_3D` que ficou na vista (`nao aplicado`
  quando o estilo não pôde ser trocado ou está desligado — o motivo aparece em `avisos:`).
- `categorias ocultas:` é a **quantidade** de categorias de `CATEGORIAS_OCULTAS_VISTA_3D`
  efetivamente ocultadas (categorias que a família não tem ou cujo nome não existe no Revit
  são ignoradas; a categoria da própria família é preservada).
- `vistas renomeadas:` é quantas vistas receberam nome em português (Brasil).
- Avisos não fatais (ex.: orientação não gravada, nome já em uso) aparecem no fim da
  linha, após `avisos:`.
- `janelas do Revit respondidas:` (no `RESUMO`) e as linhas `JANELA | OK: ...` mostram as
  janelas modais que o script respondeu sozinho — veja
  [Janelas de aviso do Revit respondidas com "OK"](#-janelas-de-aviso-do-revit-respondidas-com-ok).

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
| `DIRECAO_VISTA_3D` | `"SE_ISOMETRIC"` | Direção aplicada à vista 3D (`SE_ISOMETRIC`, `SO_ISOMETRIC`, `NE_ISOMETRIC`, `NO_ISOMETRIC`) |
| `FATOR_DISTANCIA_VISTA_3D` | `2.0` | Distância do olho = fator × diagonal do modelo |
| `TAMANHO_MINIMO_VISTA_3D` | `3.0` | Diagonal mínima considerada, em unidades internas (pés) |
| `GRAVAR_ORIENTACAO_VISTA_3D` | `True` | `True` = chama `View3D.SaveOrientation()` (o `.rfa` reabre em SE Isometric); `False` = só orienta na sessão atual |
| `ESTILO_VISUAL_VISTA_3D` | `"SOMBREADO"` | Estilo visual (`View.DisplayStyle`) da vista 3D: `ESTRUTURA_ARAME`, `LINHAS_OCULTAS`, `SOMBREADO` (= `DisplayStyle.Shading`), `SOMBREADO_COM_ARESTAS` (= `DisplayStyle.ShadingWithEdges`), `CORES_CONSISTENTES`, `REALISTA`, `REALISTA_COM_ARESTAS` (= `RealisticWithEdges`). Aceita apelidos (`SHADING`, `Shaded`, `SHADING_WITH_EDGES`, `Realistic`...) e `""` = não mexer no estilo |
| `MOSTRAR_ARESTAS_VISTA_3D` | `True` | `True` = troca o estilo pedido pela variante **com arestas** (`SOMBREADO` → `SOMBREADO_COM_ARESTAS` = `DisplayStyle.ShadingWithEdges`); `ESTRUTURA_ARAME`/`LINHAS_OCULTAS` não mudam (já mostram as arestas). **Não existe `View.ShowEdges` na API** |
| `OCULTAR_CATEGORIAS_VISTA_3D` | `True` | `True` = oculta **por categoria** as anotações/cotas e os elementos auxiliares na vista 3D |
| `CATEGORIAS_OCULTAS_VISTA_3D` | 12 `OST_*` | `BuiltInCategory`s ocultadas na vista 3D: `OST_Dimensions`, `OST_TextNotes`, `OST_GenericAnnotation`, `OST_Levels`, `OST_Grids`, `OST_CLines`, `OST_ReferenceLines`, `OST_ReferencePoints`, `OST_Walls`, `OST_Floors`, `OST_Ceilings`, `OST_Roofs` (a categoria da própria família é sempre preservada) |
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
- **Vista 3D:** a API não permite "ativar" uma vista de um documento aberto em segundo
  plano; o que define a miniatura do arquivo é o **preview** — que o script grava
  (vista 3D permanente + `SaveOptions.PreviewViewId`).
- **Orientação gravada ≠ orientação da sessão:** `SetOrientation` só muda a vista na
  sessão atual; é `View3D.SaveOrientation` que grava a direção no arquivo. Como a API
  proíbe gravar a orientação da vista 3D **padrão** do documento, essa vista é
  renomeada para `Vista 1` antes — e é isso que faz o `.rfa` reabrir em SE Isometric.
- **Estilo visual e categorias ocultas também são propriedades da VISTA** (`View.DisplayStyle`
  e `View.SetCategoryHidden`), não do documento: ficam gravados no `.rfa` junto com a vista e
  são exatamente o que aparece no preview/miniatura. `DisplayStyle.Shaded` **não existe** —
  "Sombreado" é `DisplayStyle.Shading`, e "Sombreado com arestas" é
  `DisplayStyle.ShadingWithEdges` (o valor que `MOSTRAR_ARESTAS_VISTA_3D` usa).
- **A API não tem `View.ShowEdges` nem `View3D.ShowEdges`**: o checkbox *Mostrar arestas* não
  é acessível por propriedade (conferido na `RevitAPI.xml` do Revit 2026). Para o preview sair
  sombreado **com** as arestas, o script usa `DisplayStyle.ShadingWithEdges`
  ("Sombreado com arestas") — veja
  [Arestas visíveis no preview](#arestas-visíveis-no-preview-mostrar_arestas_vista_3d).
- **Não existe `View.HideElements` em documento de família:** ocultar elementos isolados não é
  possível pela API; o script oculta por **categoria** (o mesmo efeito de desmarcar a categoria
  em *Visibilidade/Substituições*). A categoria da própria família (`Family.FamilyCategory`)
  é sempre preservada, para a vista 3D — e o preview — nunca ficarem vazios.
- Se a família não tiver tipo de vista 3D (caso raro), o script não consegue criar a
  vista, segue normalmente e registra o aviso no `OUT`.
- **Nomes de vistas:** apenas `View.Name` é alterado. Agrupamentos do Navegador de
  Projeto (`Views`, `3D Views`...) são textos da interface do Revit (definidos pelo
  idioma instalado) e **não** existem como propriedade renomeável na API.
- **Respostas automáticas = "OK", nunca "Remover restrições".** O script descarta os avisos
  das próprias transações (`IFailuresPreprocessor`) e responde "OK" nas janelas que o Revit
  abre por conta própria (`DialogBoxShowing`) — em nenhum caso ele altera as restrições da
  família para "resolver" um aviso. Se um passo depender de uma resolução, ele é desfeito e
  registrado nos `avisos:` da família.
- **O handler de janelas é temporário:** é assinado em `ativar_respostas_automaticas()`
  (início do lote) e removido em `desativar_respostas_automaticas()` (dentro de `try/finally`),
  então o Revit volta ao comportamento normal ao terminar — inclusive se o script falhar.

---

## ✅ Requisitos

- Revit 2026 (testado com `RevitAPI.dll` 2026) e Dynamo 3.4+
- Engine do nó Python: **CPython3** (não usar IronPython 2.7)
- Permissão de escrita na pasta das famílias (evite arquivos marcados como somente leitura)
- (Opcional) Python 3 para rodar `validar_traducao.py`, `validar_respostas_revit.py` e
  `validar_vista_3d.py` fora do Revit — o Python do próprio Dynamo serve
  (ex.: `%LOCALAPPDATA%\python-3.9.12-embed-amd64\python.exe`)

## 🧰 Solução de problemas

| Sintoma | Provável causa / solução |
|---|---|
| `File already exists!` | Use `doc.Save(SaveOptions)` (já corrigido) ou `OverwriteExistingFile = True` (singular) no `SaveAs` |
| `The file is read-only, can not be saved` | Desmarque "Somente leitura" no arquivo/pasta |
| `options.PreviewViewId is not valid for generation of a preview` | A vista escolhida não serve como preview — o script valida antes e, se falhar, ignora o preview |
| Arquivo pulado com "ja aberto no Revit" | Feche a família no Revit e execute novamente |
| `_backup_upgrade` criado **dentro de uma subpasta** (em vez da raiz da pasta pesquisada) | Era um **bug**: a raiz era deduzida do **primeiro `.rfa`** encontrado (`os.path.dirname(lista_final[0])`). Já corrigido — cada família leva a **sua raiz da pesquisa** (`IN[0]`). **Rode `sincronizar_dyn.ps1`**: o `.dyn` guarda o Python embutido e, sem sincronizar, o Dynamo continua com o código antigo |
| Log com o nome antigo `_log_formatar_unidades.txt` | O log passou a se chamar `_log_atualiza_familias.txt` junto com o novo nome do projeto (`NOME_LOG`). Os logs antigos que ficaram nas pastas podem ser apagados e é preciso **rodar `sincronizar_dyn.ps1`** para o `.dyn` valer |
| Aviso `Backup: nao foi possivel copiar o original` | O `_backup_upgrade\` não pôde ser criado/copiado (pasta sem permissão de escrita, caminho muito longo ou arquivo em uso). O `.rfa` seria sobrescrito **sem** cópia do original — libere a pasta e execute de novo |
| `'list' object has no attribute 'Count'` | No engine **CPython3 (pythonnet)** as coleções da API do Revit chegam ao Python como **listas**, que não têm `.Count`. O script agora usa o auxiliar `contar()` (`len()` com fallback para `.Count`) — já corrigido |
| A vista 3D não abre em SE Isometric no arquivo salvo | A orientação não foi gravada: verifique se a vista **não** é a vista 3D padrão do documento (o script renomeia para `Vista 1` justamente por isso) e se `GRAVAR_ORIENTACAO_VISTA_3D = True`. O aviso aparece no `OUT` após `avisos:` |
| O preview/miniatura não fica no estilo pedido | (1) `ESTILO_VISUAL_VISTA_3D` está `""`/`None` (o script não mexe no estilo); (2) valor não reconhecido — aparece `Vista 3D (estilo visual): valor desconhecido '...'` em `avisos:`; (3) o **`.dyn` está desatualizado** (o grafo guarda uma cópia do Python) — rode `sincronizar_dyn.ps1`; (4) aparece `o arquivo ficou em 'X' (pedido: 'Y')` em `avisos:` — o Revit recusou o estilo naquela vista |
| **Mudei `ESTILO_VISUAL_VISTA_3D` no `.py` e a miniatura não mudou** | (1) O `.dyn` guarda uma **cópia** do script: editar o `.py` não muda o grafo — rode `sincronizar_dyn.ps1` (ele confere e falha se ficar fora de sincronia) e execute de novo; confirme no `OUT` a linha `estilo 3D: ...` com o valor novo; (2) o arquivo pode ter sido `PULADO` (já aberto no Revit / `IGNORAR_JA_ATUALIZADAS`); (3) o Windows mantém **cache de miniaturas** — pressione F5/feche e reabra a pasta (ou limpe `thumbcache_*.db`) antes de concluir que o `.rfa` não mudou; para conferir "por dentro", abra a família e olhe a vista `Vista 1` |
| As arestas não aparecem no preview sombreado | Não existe `View.ShowEdges`/`View3D.ShowEdges` na API. Use `MOSTRAR_ARESTAS_VISTA_3D = True` (aplica `DisplayStyle.ShadingWithEdges` = "Sombreado com arestas") ou `ESTILO_VISUAL_VISTA_3D = "SOMBREADO_COM_ARESTAS"`. Em uma versão do Revit sem esse valor do enum o ajuste é ignorado em silêncio — nesse caso use `LINHAS_OCULTAS` (`DisplayStyle.HLR`), que sempre mostra as arestas |
| As anotações/cotas continuam aparecendo na vista 3D | (1) `OCULTAR_CATEGORIAS_VISTA_3D = False`; (2) a categoria não está em `CATEGORIAS_OCULTAS_VISTA_3D` — acrescente o nome do `BuiltInCategory`; (3) o `.dyn` está desatualizado — rode `sincronizar_dyn.ps1` |
| `categoria(s) nao encontrada(s)` nos `avisos:` | Algum nome de `CATEGORIAS_OCULTAS_VISTA_3D` não existe como valor de `BuiltInCategory` (erro de digitação). Ele é ignorado com aviso — o lote não para. Corrija o nome na lista |
| `DisplayStyle.Shaded` / `AttributeError: Shaded` | Esse valor **não existe** na API: "Sombreado" é `DisplayStyle.Shading`. Use uma das chaves de `ESTILOS_VISUAIS_VISTA_3D` |
| A vista 3D (e o preview) ficou vazia depois de ocultar categorias | Não deveria acontecer: a categoria da própria família (`Family.FamilyCategory`) nunca é ocultada. Se a geometria estiver em outra categoria (ex.: `OST_GenericModel`), remova essa categoria de `CATEGORIAS_OCULTAS_VISTA_3D` |
| `Could not save the orientation of the view` / aviso "a orientacao nao pode ser gravada" | `View3D.SaveOrientation()` foi chamado em uma vista 3D padrão (`CanSaveOrientation()` retornou `False`) — renomeie a vista 3D (o script já faz isso automaticamente com `NOME_VISTA_3D`) |
| Aviso/erro de "up vector is not perpendicular to the view direction" | O par `forward`/`up` escolhido em `DIRECOES_VISTA_3D` não é ortogonal; use uma das quatro direções já validadas (todas com produto escalar 0) |
| Nomes de vistas continuam em inglês | (1) `RENOMEAR_VISTAS_PT_BR = False`; (2) o `.dyn` está **desatualizado** — rode `sincronizar_dyn.ps1` (o validador `validar_traducao.py` detecta isso); (3) o nome não corresponde a nenhum padrão conhecido (nomes personalizados são preservados de propósito) |
| Vistas em francês/espanhol continuam sem tradução | Falta cadastrar o nome no dicionário: ligue `RELATAR_VISTAS_NAO_TRADUZIDAS = True`, rode o lote e veja a lista `vistas sem traducao: ...` no log/`OUT` |
| Agrupamentos `Views` / `3D Views` continuam em inglês | São textos da interface do Revit (idioma instalado), não propriedades da API — não há como renomeá-los por script |
| O lote **parou** na janela *"As restrições entre a geometria..."* (Remover restrições / OK) | Confirme `RESPONDER_DIALOGOS_COM_OK = True` e **rode `sincronizar_dyn.ps1`** (o `.dyn` guarda o Python embutido: sem sincronizar, o Dynamo continua rodando o código antigo, sem a resposta automática) |
| Aviso `nao foi possivel assinar o evento de janelas do Revit` no `OUT` | O evento `DialogBoxShowing` não pôde ser assinado (situação incomum): o lote segue, mas alguma janela pode continuar aparecendo — responda manualmente ou feche a janela e execute de novo |
| Janela respondida com "OK" mas o passo pretendido não foi feito (aparece `avisos: ... Revit: ... (transacao desfeita)`) | Era uma **falha de erro** (não um aviso): o Revit só "resolve" esse tipo de falha alterando alguma coisa, e o script prefere desfazer a transação (rollback) a escolher uma resolução sozinho |
| O aviso de restrições voltou a aparecer em outros fluxos (fora do Dynamo) | A causa é a geometria sem restrição na família — recomenda-se editá-la e **restringir** (alinhar + bloquear). O script sempre responde "OK"; "Remover restrições" muda a família e não é usado de propósito |
