import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import os
import sys

VERSAO_SISTEMA = '0.3'
CENT = Decimal('0.01')
LIMITE = Decimal('1250000.00')
TAXAS = [Decimal('1.6'), Decimal('8'), Decimal('16'), Decimal('32')]
LINHAS = ['01', '02', '03', '04']
ALIQUOTA_IRPJ = Decimal('15.00')
LIMITE_ADICIONAL_IRPJ = Decimal('60000.00')
ALIQUOTA_ADICIONAL_IRPJ = Decimal('10.00')


def arred(valor):
    """Converte entradas numéricas para Decimal e arredonda a centavos."""
    numero = valor if isinstance(valor, Decimal) else Decimal(str(valor))
    return numero.quantize(CENT, rounding=ROUND_HALF_UP)


def moeda(valor):
    s = f'{arred(valor):,.2f}'
    return 'R$ ' + s.replace(',', '#').replace('.', ',').replace('#', '.')


def ler_moeda(texto):
    s = texto.strip().replace('R$', '').replace(' ', '')
    if not s:
        return Decimal('0')
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    elif s.count('.') > 1:
        s = s.replace('.', '')
    elif '.' in s and len(s.split('.')[-1]) == 3:
        s = s.replace('.', '')
    valor = arred(Decimal(s))
    if valor < 0:
        raise ValueError('Receitas não podem ser negativas.')
    return valor


def distribuir(total_unidades, pesos):
    """Distribui unidades inteiras com método dos maiores restos."""
    soma = sum(pesos)
    if soma == 0:
        return [0] * len(pesos)
    quotas = [Decimal(total_unidades) * p / soma for p in pesos]
    bases = [int(q) for q in quotas]
    restantes = total_unidades - sum(bases)
    ordem = sorted(range(len(pesos)), key=lambda i: (-(quotas[i] - bases[i]), i))
    for i in ordem[:restantes]:
        bases[i] += 1
    return bases


def calcular(receitas):
    total = sum(receitas, Decimal('0'))
    excedeu = total > LIMITE
    # 10000 centésimos de ponto percentual equivalem a 100,00%.
    percentuais_unidades = distribuir(10000, receitas) if total else [0] * 4
    percentuais = [Decimal(u) / 100 for u in percentuais_unidades]
    if excedeu:
        # A base da distribuição são os percentuais exibidos, já arredondados.
        centavos = distribuir(125000000, [Decimal(u) for u in percentuais_unidades])
        limites = [Decimal(c) / 100 for c in centavos]
    else:
        limites = [Decimal('0')] * 4
    excessos = [arred(receitas[i] - limites[i]) if excedeu else Decimal('0') for i in range(4)]
    bases_normais = [arred((limites[i] if excedeu else receitas[i]) * TAXAS[i] / 100) for i in range(4)]
    bases_acrescimo = [arred(excessos[i] * TAXAS[i] * Decimal('1.10') / 100) for i in range(4)]
    resultado = sum(bases_normais + bases_acrescimo, Decimal('0'))
    return total, percentuais, limites, excessos, bases_normais, bases_acrescimo, resultado


def calcular_irpj(resultado_presuncao, rendimentos, deducoes):
    """Apura as linhas 22, 23, 24 e 34 pelas regras informadas no projeto.

    A única informação recebida da primeira etapa é seu resultado final.
    Cada valor monetário é arredondado a centavos antes da etapa seguinte.
    """
    resultado_presuncao = arred(resultado_presuncao)
    rendimentos = arred(rendimentos)
    deducoes = arred(deducoes)
    base_calculo = arred(resultado_presuncao + rendimentos)
    imposto_15 = arred(base_calculo * ALIQUOTA_IRPJ / 100)
    base_adicional = arred(max(base_calculo - LIMITE_ADICIONAL_IRPJ, Decimal('0')))
    adicional = arred(base_adicional * ALIQUOTA_ADICIONAL_IRPJ / 100)
    # Preserva a subtração solicitada, inclusive se as deduções superarem o imposto.
    imposto_pagar = arred(imposto_15 + adicional - deducoes)
    return {
        'base_calculo': base_calculo,
        'imposto_15': imposto_15,
        'base_adicional': base_adicional,
        'adicional': adicional,
        'imposto_pagar': imposto_pagar,
    }


def porcentagem(valor):
    return f'{arred(valor):.2f}%'.replace('.', ',')


def gerar_resumo(receitas, calculo):
    """Explica os mesmos valores calculados e exibidos na tabela."""
    total, percentuais, limites, excessos, normais, acrescimos, resultado = calculo
    excedeu = total > LIMITE
    textos = [
        'RESUMO DO CÁLCULO DE PRESUNÇÃO E ACRÉSCIMO IRPJ',
        '',
        f'Limite do trimestre: {moeda(LIMITE)}',
        'Total das receitas = ' + ' + '.join(moeda(r) for r in receitas)
        + f' = {moeda(total)}',
    ]
    if excedeu:
        textos.extend([
            'O total ultrapassou o limite trimestral.',
            f'Excedente total: {moeda(total)} - {moeda(LIMITE)} = {moeda(total - LIMITE)}',
            'Aplicam-se os percentuais normais aos limites proporcionais e os',
            'percentuais com acréscimo de 10,00% às receitas excedentes.',
        ])
    else:
        textos.extend([
            'O total é menor ou igual ao limite trimestral.',
            'Aplicam-se somente os percentuais normais à receita de cada linha.',
            'Os limites proporcionais não são calculados e os acréscimos ficam zerados.',
        ])
    textos.extend([
        '',
        'CRITÉRIO DE ARREDONDAMENTO',
        'Valores monetários e percentuais têm duas casas decimais.',
        'Os valores monetários usam ROUND_HALF_UP (5 arredonda para cima).',
        'As proporções são distribuídas pelo método dos maiores restos para',
        'totalizar exatamente 100,00% quando há receitas. Esses percentuais',
        'de duas casas são os utilizados no cálculo dos limites proporcionais.',
        'Com todas as receitas zeradas, as proporções são 0,00%.',
        '',
        'DETALHAMENTO POR LINHA',
    ])
    for i, (linha, taxa) in enumerate(zip(LINHAS, TAXAS)):
        taxa_extra = taxa * Decimal('1.10')
        textos.extend([
            '',
            f'LINHA {linha} - Receita bruta sujeita a {porcentagem(taxa)}',
            f'Receita informada: {moeda(receitas[i])}',
        ])
        if total:
            textos.append(
                f'Proporção = {moeda(receitas[i])} / {moeda(total)} x 100'
                f' = {porcentagem(percentuais[i])} (após distribuição em duas casas)'
            )
        else:
            textos.append('Proporção: 0,00% (total zerado; não há divisão).')
        if excedeu:
            textos.extend([
                f'Limite proporcional = {moeda(LIMITE)} x {porcentagem(percentuais[i])}'
                f' = {moeda(limites[i])}',
                f'Linha {linha}.01 - Receita excedente = {moeda(receitas[i])}'
                f' - {moeda(limites[i])} = {moeda(excessos[i])}',
                f'Base normal = {moeda(limites[i])} x {porcentagem(taxa)}'
                f' = {moeda(normais[i])}',
                f'Percentual com acréscimo = {porcentagem(taxa)} x 1,10'
                f' = {porcentagem(taxa_extra)}',
                f'Base com acréscimo = {moeda(excessos[i])} x {porcentagem(taxa_extra)}'
                f' = {moeda(acrescimos[i])}',
            ])
        else:
            textos.extend([
                'Limite proporcional: não calculado.',
                f'Linha {linha}.01 - Receita excedente: {moeda(0)}',
                f'Base normal = {moeda(receitas[i])} x {porcentagem(taxa)}'
                f' = {moeda(normais[i])}',
                f'Base com acréscimo: {moeda(0)}',
            ])
        textos.append(f'Subtotal da linha: {moeda(normais[i] + acrescimos[i])}')
    textos.extend([
        '',
        'TOTAIS',
        f'Soma das proporções: {porcentagem(sum(percentuais))}',
        f'Soma das bases normais: {moeda(sum(normais))}',
        f'Soma das bases com acréscimo: {moeda(sum(acrescimos))}',
        '',
        'RESULTADO DA APLICAÇÃO DOS PERCENTUAIS SOBRE A RECEITA BRUTA',
        f'{moeda(sum(normais))} + {moeda(sum(acrescimos))} = {moeda(resultado)}',
    ])
    return '\n'.join(textos) + '\n'


def gerar_resumo_irpj(resultado_presuncao, rendimentos, deducoes, calculo_irpj):
    """Detalha a segunda etapa usando os mesmos resultados exibidos na janela."""
    base = calculo_irpj['base_calculo']
    imposto_15 = calculo_irpj['imposto_15']
    adicional = calculo_irpj['adicional']
    imposto_pagar = calculo_irpj['imposto_pagar']
    textos = [
        'SEGUNDA ETAPA - APURAÇÃO DO IMPOSTO DE RENDA',
        '',
        'RESULTADO DA APLICAÇÃO DOS PERCENTUAIS SOBRE A RECEITA BRUTA',
        f'Valor recebido da primeira etapa: {moeda(resultado_presuncao)}',
        '',
        'Rendimentos e Ganhos Líquidos de Aplicações Renda Fixa/Variável',
        f'Valor informado pelo usuário: {moeda(rendimentos)}',
        '',
        '22. BASE DE CÁLCULO DO IMPOSTO SOBRE O LUCRO PRESUMIDO',
        'Resultado da primeira etapa + rendimentos e ganhos líquidos',
        f'{moeda(resultado_presuncao)} + {moeda(rendimentos)} = {moeda(base)}',
        '',
        '23. À Alíquota de 15%',
        f'Linha 22 x {porcentagem(ALIQUOTA_IRPJ)}',
        f'{moeda(base)} x {porcentagem(ALIQUOTA_IRPJ)} = {moeda(imposto_15)}',
        '',
        '24. Adicional',
    ]
    if base > LIMITE_ADICIONAL_IRPJ:
        textos.extend([
            f'A linha 22 ultrapassou {moeda(LIMITE_ADICIONAL_IRPJ)}.',
            f'Base do adicional = {moeda(base)} - {moeda(LIMITE_ADICIONAL_IRPJ)}'
            f' = {moeda(calculo_irpj["base_adicional"])}',
            f'Adicional = ({moeda(base)} - {moeda(LIMITE_ADICIONAL_IRPJ)})'
            f' x {porcentagem(ALIQUOTA_ADICIONAL_IRPJ)} = {moeda(adicional)}',
        ])
    else:
        textos.extend([
            f'A linha 22 é menor ou igual a {moeda(LIMITE_ADICIONAL_IRPJ)}.',
            'Não há parcela acima desse limite para aplicar o adicional.',
            f'Adicional: {moeda(adicional)}',
        ])
    textos.extend([
        '',
        'DEDUÇÕES',
        f'Valor informado pelo usuário: {moeda(deducoes)}',
        '',
        '34. IMPOSTO DE RENDA À PAGAR',
        'Linha 23 + linha 24 - deduções',
        f'{moeda(imposto_15)} + {moeda(adicional)} - {moeda(deducoes)}'
        f' = {moeda(imposto_pagar)}',
    ])
    return '\n'.join(textos) + '\n'

def caminho_recurso(nome):
    if getattr(sys, "frozen", False):
        pasta = sys._MEIPASS
    else:
        pasta = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(pasta, nome)

class Aplicacao:
    def __init__(self, root):
        self.root = root
        root.title('Calculadora de Presunção IRPJ')
        # Ícone da janela do Tkinter
        root.iconbitmap(caminho_recurso('icone.ico'))
        root.geometry('1200x900')
        root.minsize(1100, 760)
        self.entradas = []
        self.percentuais = []
        self.limites = []
        self.excessos = []
        self.bases_normais = []
        self.bases_acrescimo = []
        self.total_var = tk.StringVar(value=moeda(0))
        self.resultado_var = tk.StringVar(value=moeda(0))
        self.rendimentos_var = tk.StringVar(value='0,00')
        self.deducoes_var = tk.StringVar(value='0,00')
        self.base_calculo_irpj_var = tk.StringVar(value=moeda(0))
        self.imposto_15_var = tk.StringVar(value=moeda(0))
        self.adicional_var = tk.StringVar(value=moeda(0))
        self.imposto_pagar_var = tk.StringVar(value=moeda(0))
        self.status_var = tk.StringVar(value='Informe as receitas para calcular.')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Titulo.TLabel', font=('Segoe UI', 17, 'bold'))
        style.configure('Cab.TLabel', font=('Segoe UI', 10, 'bold'))
        style.configure('Destaque.TLabel', font=('Segoe UI', 12, 'bold'))
        corpo = ttk.Frame(root, padding=18)
        corpo.pack(fill='both', expand=True)

        # Cabeçalho: título à esquerda e versão à direita.
        cabecalho = ttk.Frame(corpo)
        cabecalho.pack(fill='x', pady=(0, 12))

        ttk.Label(
            cabecalho,
            text='Cálculo de Presunção e Apuração IRPJ',
            style='Titulo.TLabel',
        ).pack(side='left')

        ttk.Label(
            cabecalho,
            text=f'v{VERSAO_SISTEMA}',
            font=('Segoe UI', 9),
            foreground='#777777',
        ).pack(side='right')
        abas = ttk.Notebook(corpo)
        abas.pack(fill='x', pady=(0, 8))
        pagina_receitas = ttk.Frame(abas, padding=8)
        abas.add(pagina_receitas, text='1. Receitas e presunção')
        topo = ttk.Frame(pagina_receitas)
        topo.pack(fill='x', pady=(0, 12))
        ttk.Label(topo, text='Limite do trimestre: ' + moeda(LIMITE), style='Cab.TLabel').pack(side='left')
        ttk.Label(topo, text='Total das receitas: ', style='Cab.TLabel').pack(side='left', padx=(35, 0))
        ttk.Label(topo, textvariable=self.total_var, style='Destaque.TLabel').pack(side='left')
        tabela = ttk.Frame(pagina_receitas)
        tabela.pack(fill='x')
        colunas = ['Linha / descrição', 'Receita informada', 'Proporção', 'Limite proporcional', 'Excedente / base', 'Valor da presunção']
        larguras = [34, 19, 13, 21, 21, 20]
        for c, (nome, largura) in enumerate(zip(colunas, larguras)):
            ttk.Label(tabela, text=nome, style='Cab.TLabel', width=largura).grid(row=0, column=c, sticky='w', padx=3, pady=7)
        for i, (linha, taxa) in enumerate(zip(LINHAS, TAXAS)):
            r = i * 2 + 1
            ttk.Label(tabela, text=f'{linha} - Receita bruta sujeita a {taxa}%').grid(row=r, column=0, sticky='w', pady=8)
            entrada = ttk.Entry(tabela, width=18)
            entrada.insert(0, '0,00')
            entrada.grid(row=r, column=1, sticky='w', padx=3)
            entrada.bind('<FocusOut>', self.recalcular)
            entrada.bind('<Return>', self.recalcular)
            self.entradas.append(entrada)
            pct = tk.StringVar(value='0,00%')
            lim = tk.StringVar(value=moeda(0))
            exced = tk.StringVar(value=moeda(0))
            base = tk.StringVar(value=moeda(0))
            base_extra = tk.StringVar(value=moeda(0))
            self.percentuais.append(pct)
            self.limites.append(lim)
            self.excessos.append(exced)
            self.bases_normais.append(base)
            self.bases_acrescimo.append(base_extra)
            ttk.Label(tabela, textvariable=pct).grid(row=r, column=2, sticky='w')
            ttk.Label(tabela, textvariable=lim).grid(row=r, column=3, sticky='w')
            ttk.Label(tabela, textvariable=base).grid(row=r, column=5, sticky='w')
            ttk.Label(tabela, text=f'{linha}.01 - Presunção ao acréscimo 10%').grid(row=r+1, column=0, sticky='w', pady=(0, 12))
            ttk.Label(tabela, textvariable=exced).grid(row=r+1, column=4, sticky='w')
            ttk.Label(tabela, textvariable=base_extra).grid(row=r+1, column=5, sticky='w')
            ttk.Separator(tabela).grid(row=r+1, column=0, columnspan=6, sticky='sew', pady=(25, 0))
        rodape = ttk.Frame(pagina_receitas)
        rodape.pack(fill='x', pady=(18, 10))
        ttk.Label(rodape, text='RESULTADO DA APLICAÇÃO DOS PERCENTUAIS SOBRE A RECEITA BRUTA', style='Cab.TLabel').pack(anchor='w')
        ttk.Label(rodape, textvariable=self.resultado_var, style='Titulo.TLabel').pack(anchor='w', pady=5)
        self.criar_aba_irpj(abas)
        ttk.Label(corpo, textvariable=self.status_var).pack(anchor='w')
        botoes = ttk.Frame(corpo)
        botoes.pack(anchor='w', pady=12)
        ttk.Button(botoes, text='Calcular', command=self.recalcular).pack(side='left', padx=(0, 10))
        ttk.Button(botoes, text='Limpar', command=self.limpar).pack(side='left')
        ttk.Button(botoes, text='Copiar resumo', command=self.copiar_resumo).pack(side='left', padx=10)
        ttk.Button(botoes, text='Salvar resumo em TXT', command=self.salvar_resumo).pack(side='left')
        resumo_frame = ttk.LabelFrame(corpo, text='Resumo explicativo dos cálculos', padding=8)
        resumo_frame.pack(fill='both', expand=True)
        self.txt_resumo = ScrolledText(
            resumo_frame, height=10, wrap=tk.WORD, font=('Consolas', 10),
            state=tk.DISABLED,
        )
        self.txt_resumo.pack(fill='both', expand=True)
        self.resumo = ''
        self.recalcular()

    def criar_aba_irpj(self, abas):
        pagina = ttk.Frame(abas, padding=14)
        abas.add(pagina, text='2. Apuração do IRPJ')
        pagina.columnconfigure(0, weight=1)
        ttk.Label(
            pagina,
            text='RESULTADO DA APLICAÇÃO DOS PERCENTUAIS SOBRE A RECEITA BRUTA',
            style='Cab.TLabel', wraplength=760,
        ).grid(row=0, column=0, sticky='w', padx=(0, 16), pady=10)
        ttk.Label(pagina, textvariable=self.resultado_var, style='Destaque.TLabel').grid(
            row=0, column=1, sticky='e', pady=10,
        )
        ttk.Label(
            pagina,
            text='Rendimentos e Ganhos Líquidos de Aplicações Renda Fixa/Variável',
            wraplength=760,
        ).grid(row=1, column=0, sticky='w', padx=(0, 16), pady=12)
        self.entrada_rendimentos = ttk.Entry(
            pagina, textvariable=self.rendimentos_var, width=22,
        )
        self.entrada_rendimentos.grid(row=1, column=1, sticky='e', pady=12)
        self.entrada_rendimentos.bind('<FocusOut>', self.recalcular)
        self.entrada_rendimentos.bind('<Return>', self.recalcular)
        ttk.Separator(pagina).grid(row=2, column=0, columnspan=2, sticky='ew', pady=8)
        for linha, descricao, variavel in [
            (3, '22. BASE DE CÁLCULO DO IMPOSTO SOBRE O LUCRO PRESUMIDO', self.base_calculo_irpj_var),
            (4, '23. À Alíquota de 15%', self.imposto_15_var),
            (5, '24. Adicional', self.adicional_var),
        ]:
            ttk.Label(
                pagina, text=descricao, style='Cab.TLabel', wraplength=760,
            ).grid(row=linha, column=0, sticky='w', padx=(0, 16), pady=12)
            ttk.Label(pagina, textvariable=variavel, style='Destaque.TLabel').grid(
                row=linha, column=1, sticky='e', pady=12,
            )
        ttk.Label(pagina, text='DEDUÇÕES', style='Cab.TLabel').grid(
            row=6, column=0, sticky='w', pady=12,
        )
        self.entrada_deducoes = ttk.Entry(pagina, textvariable=self.deducoes_var, width=22)
        self.entrada_deducoes.grid(row=6, column=1, sticky='e', pady=12)
        self.entrada_deducoes.bind('<FocusOut>', self.recalcular)
        self.entrada_deducoes.bind('<Return>', self.recalcular)
        ttk.Separator(pagina).grid(row=7, column=0, columnspan=2, sticky='ew', pady=12)
        ttk.Label(
            pagina, text='34. IMPOSTO DE RENDA À PAGAR', style='Destaque.TLabel',
        ).grid(row=8, column=0, sticky='w', pady=12)
        ttk.Label(pagina, textvariable=self.imposto_pagar_var, style='Titulo.TLabel').grid(
            row=8, column=1, sticky='e', pady=12,
        )

    def recalcular(self, event=None):
        try:
            receitas = [ler_moeda(e.get()) for e in self.entradas]
            rendimentos = ler_moeda(self.entrada_rendimentos.get())
            deducoes = ler_moeda(self.entrada_deducoes.get())
        except (InvalidOperation, ValueError):
            messagebox.showerror(
                'Valor inválido',
                'Informe receitas, rendimentos e deduções com valores não negativos '
                'em formato brasileiro, por exemplo: 125.000,50',
            )
            return False
        calculo = calcular(receitas)
        total, percentuais, limites, excessos, normais, acrescimos, resultado = calculo
        calculo_irpj = calcular_irpj(resultado, rendimentos, deducoes)
        self.total_var.set(moeda(total))
        self.resultado_var.set(moeda(resultado))
        self.base_calculo_irpj_var.set(moeda(calculo_irpj['base_calculo']))
        self.imposto_15_var.set(moeda(calculo_irpj['imposto_15']))
        self.adicional_var.set(moeda(calculo_irpj['adicional']))
        self.imposto_pagar_var.set(moeda(calculo_irpj['imposto_pagar']))
        for i in range(4):
            self.percentuais[i].set(f'{percentuais[i]:.2f}%'.replace('.', ','))
            self.limites[i].set(moeda(limites[i]))
            self.excessos[i].set(moeda(excessos[i]))
            self.bases_normais[i].set(moeda(normais[i]))
            self.bases_acrescimo[i].set(moeda(acrescimos[i]))
        self.status_var.set('Limite trimestral ultrapassado: acréscimo aplicado ao excedente.' if total > LIMITE else 'Dentro do limite trimestral: somente percentuais normais.')
        self.resumo = gerar_resumo(receitas, calculo) + '\n' + gerar_resumo_irpj(
            resultado, rendimentos, deducoes, calculo_irpj,
        )
        self.txt_resumo.configure(state=tk.NORMAL)
        self.txt_resumo.delete('1.0', tk.END)
        self.txt_resumo.insert('1.0', self.resumo)
        self.txt_resumo.configure(state=tk.DISABLED)
        return True

    def copiar_resumo(self):
        if not self.recalcular():
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.resumo)
        self.status_var.set('Resumo copiado para a área de transferência.')

    def salvar_resumo(self):
        # Atualiza antes de exportar, inclusive se a entrada ainda estiver em foco.
        if not self.recalcular():
            return
        caminho = filedialog.asksaveasfilename(
            parent=self.root,
            title='Salvar resumo dos cálculos',
            defaultextension='.txt',
            initialfile='resumo_calculo_irpj.txt',
            filetypes=[('Arquivo de texto', '*.txt')],
        )
        if not caminho:
            return
        try:
            with open(caminho, 'w', encoding='utf-8-sig') as arquivo:
                arquivo.write(self.resumo)
        except OSError as erro:
            messagebox.showerror('Erro ao salvar', f'Não foi possível salvar o resumo.\n{erro}')
            return
        self.status_var.set('Resumo salvo em TXT.')

    def limpar(self):
        for entrada in self.entradas + [self.entrada_rendimentos, self.entrada_deducoes]:
            entrada.delete(0, tk.END)
            entrada.insert(0, '0,00')
        self.recalcular()


if __name__ == '__main__':
    raiz = tk.Tk()
    Aplicacao(raiz)
    raiz.mainloop()
