**Calculadora de Presunção IRPJ**

Aplicativo desktop desenvolvido em Python para simplificar o cálculo da base de presunção do IRPJ. Com uma interface organizada, permite informar receitas, acompanhar sua distribuição proporcional e visualizar um resumo explicativo de cada etapa do cálculo.

Uma ferramenta voltada à rotina contábil, que reúne cálculo e documentação dos resultados na mesma janela.

**Funcionalidades**

- **Receitas por percentual:** campos separados para receitas sujeitas aos percentuais de 1,6%, 8%, 16% e 32%.
- **Distribuição proporcional:** calcula a participação de cada receita no total, com duas casas decimais e soma de 100,00% quando existem receitas.
- **Controle do limite trimestral:** considera o limite de R$ 1.250.000,00 definido no projeto e identifica quando ele é ultrapassado.
- **Cálculo dos excedentes:** distribui o limite entre as receitas e aplica aos excedentes os percentuais de presunção acrescidos de 10%.
- **Arredondamento definido:** utiliza cálculos decimais e arredondamento monetário com duas casas decimais.
- **Resumo explicativo:** apresenta receitas, proporções, limites, excedentes, fórmulas e resultado consolidado.
- **Cópia e exportação:** permite copiar o resumo ou salvá-lo em arquivo `.txt`, preservando os acentos.
- **Atualização prática:** recalcula ao pressionar Enter, sair de um campo ou clicar em “Calcular”, além de oferecer um botão para limpar as entradas.
- **Formato brasileiro:** exibe valores em reais, com vírgula decimal e separador de milhares.

**Ferramentas e tecnologias**

| Tecnologia | Utilização |
|---|---|
| **Python** | Desenvolvimento da aplicação e das regras de cálculo. |
| **Tkinter e ttk** | Interface gráfica, campos, botões e organização da tabela. |
| **Decimal e ROUND_HALF_UP** | Aritmética decimal e controle do arredondamento monetário. |
| **ScrolledText** | Exibição do resumo com barra de rolagem. |
| **filedialog e messagebox** | Seleção do local de exportação e mensagens ao usuário. |
| **PyInstaller** | Empacotamento do projeto como executável `.exe` para Windows. |

O resultado apresentado corresponde à soma das bases de presunção calculadas conforme as regras implementadas neste projeto. O resumo permite conferir como cada receita contribuiu para esse valor. A intenção do projeto é criar uma ferramenta que resuma de forma prática e de fácil entendimento o cálculo realizado pelo sistema contábil, de acordo com a Lei  Complementar nº224/2025 instituída pelo governo para o cálculo de receitas de empresas que se enquadram na tributação do Lucro Presumido. 
