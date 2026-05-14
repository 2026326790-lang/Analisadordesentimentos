"""
ANALISADOR DE SENTIMENTOS - VERSÃO FINAL
----------------------------------------
Recursos:
- usa dicionário local como base
- usa IA para entender o contexto da frase
- detecta melhor frases como:
  "Nada do que eu faço parece dar certo no final."
  "Pequenos passos levam a grandes conquistas."
  "Você tem uma força interior maior do que imagina."
- salva o dicionário em JSON
- salva a configuração da IA em JSON
- funciona melhor quando virar .exe
- mostra resultado bonito e simples para leigos
"""

import copy
import json
import re
import sys
import unicodedata
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# =========================================================
# FUNÇÕES DE CAMINHO
# =========================================================

def pasta_base():
    """
    Descobre a pasta correta:
    - no .py: a pasta do arquivo
    - no .exe: a pasta do executável
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = pasta_base()


# =========================================================
# CONFIGURAÇÕES
# =========================================================

ARQUIVO_DICIONARIO = BASE_DIR / "dicionario_sentimentos.json"
ARQUIVO_CONFIG = BASE_DIR / "config_local.json"

MODELO_PADRAO = "gpt-5.5"

CONFIG_PADRAO = {
    "api_key": "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",
    "modelo": MODELO_PADRAO
}

DICIONARIO_PADRAO = {
    "positivas": [
        "feliz", "alegre", "ótimo", "excelente", "maravilhoso", "bom", "amor",
        "adorar", "incrível", "fantástico", "perfeito", "legal", "bacana",
        "sucesso", "vitória", "paz", "amizade", "sorrir", "esperança", "lindo",
        "bonito", "agradável", "divertido", "animado", "satisfeito", "grato",
        "conquista", "conquistas", "força", "força interior", "superação",
        "crescimento", "evolução", "dar certo", "vale a pena", "valeu a pena"
    ],
    "negativas": [
        "triste", "ruim", "péssimo", "horrível", "terrível", "ódio", "odiar",
        "chorar", "fracasso", "derrota", "medo", "raiva", "feio", "chato",
        "desagradável", "entediado", "frustrado", "decepcionado", "cansado",
        "preocupado", "ansioso", "difícil", "problema", "mal", "infeliz",
        "desânimo", "desanimo", "sem saída", "sem saida", "não consigo",
        "nao consigo", "não aguento", "nao aguento"
    ]
}

NEGADORES = {"nao", "nunca", "jamais", "nem", "sem", "nada"}

EXPRESSOES_POSITIVAS = [
    "dar certo",
    "vale a pena",
    "valeu a pena",
    "grandes conquistas",
    "conquistas",
    "conquista",
    "forca interior",
    "maior do que imagina",
    "mais forte do que imagina",
    "pequenos passos",
    "pequeno passo",
    "superacao",
    "crescimento",
    "evolucao",
    "esperanca",
    "vitoria",
    "sucesso",
    "orgulho",
    "forca",
    "feliz",
    "alegre",
    "bom",
    "otimo",
    "excelente",
    "incrivel",
    "maravilhoso"
]

EXPRESSOES_NEGATIVAS = [
    "fracasso",
    "medo",
    "raiva",
    "triste",
    "ansioso",
    "preocupado",
    "decepcionado",
    "cansado",
    "sem saida",
    "sem forca",
    "nao consigo",
    "nao aguento",
    "nada do que eu faco",
    "nada da certo",
    "nada deu certo",
    "ruim",
    "pessimo",
    "horrivel",
    "terrivel",
    "desanimo",
    "frustrado",
    "problema"
]


# =========================================================
# CONFIGURAÇÃO LOCAL DA IA
# =========================================================

def carregar_configuracao():
    """
    Carrega o arquivo de configuração local.
    Se não existir, cria um com valores padrão.
    """
    if not ARQUIVO_CONFIG.exists():
        dados = copy.deepcopy(CONFIG_PADRAO)
        salvar_configuracao(dados)
        return dados

    try:
        with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
            dados = json.load(f)

        if "api_key" not in dados:
            dados["api_key"] = CONFIG_PADRAO["api_key"]

        if "modelo" not in dados or not str(dados["modelo"]).strip():
            dados["modelo"] = MODELO_PADRAO

        return dados

    except Exception:
        dados = copy.deepcopy(CONFIG_PADRAO)
        salvar_configuracao(dados)
        return dados


def salvar_configuracao(config):
    """
    Salva o arquivo de configuração local.
    """
    with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def obter_modelo_configurado():
    """
    Retorna o modelo configurado no arquivo local.
    """
    config = carregar_configuracao()
    modelo = str(config.get("modelo", "")).strip()
    return modelo if modelo else MODELO_PADRAO


def chave_configurada():
    """
    Verifica se a chave foi realmente preenchida.
    """
    config = carregar_configuracao()
    api_key = str(config.get("api_key", "")).strip()

    if not api_key:
        return False

    if api_key == "COLE_SUA_CHAVE_AQUI":
        return False

    return True


# =========================================================
# FUNÇÕES DE TEXTO
# =========================================================

def remover_acentos(texto):
    """Remove acentos do texto."""
    return "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )


def normalizar_texto(texto):
    """
    Padroniza o texto:
    - minúsculas
    - sem acentos
    - sem pontuação desnecessária
    - sem espaços duplicados
    """
    texto = str(texto).lower().strip()
    texto = remover_acentos(texto)
    texto = re.sub(r"[^\w\s]", " ", texto, flags=re.UNICODE)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def tokenizar(texto):
    """Transforma a frase em lista de palavras."""
    texto_limpo = normalizar_texto(texto)
    return texto_limpo.split() if texto_limpo else []


# =========================================================
# DICIONÁRIO LOCAL EM JSON
# =========================================================

def carregar_dicionario():
    """
    Carrega o dicionário do arquivo.
    Se não existir, cria um novo com o padrão.
    """
    if not ARQUIVO_DICIONARIO.exists():
        dados = copy.deepcopy(DICIONARIO_PADRAO)
        salvar_dicionario(dados)
        return dados

    try:
        with open(ARQUIVO_DICIONARIO, "r", encoding="utf-8") as f:
            dados = json.load(f)

        if "positivas" not in dados:
            dados["positivas"] = []
        if "negativas" not in dados:
            dados["negativas"] = []

        return dados

    except Exception:
        dados = copy.deepcopy(DICIONARIO_PADRAO)
        salvar_dicionario(dados)
        return dados


def salvar_dicionario(dicionario):
    """Salva o dicionário no arquivo JSON."""
    with open(ARQUIVO_DICIONARIO, "w", encoding="utf-8") as f:
        json.dump(dicionario, f, ensure_ascii=False, indent=2)


def montar_sets_normalizados(dicionario):
    """
    Cria conjuntos normalizados para comparação rápida.
    """
    positivas = {normalizar_texto(p) for p in dicionario["positivas"]}
    negativas = {normalizar_texto(p) for p in dicionario["negativas"]}
    return positivas, negativas


# =========================================================
# FUNÇÕES AUXILIARES DE CONTEXTO
# =========================================================

def unir_listas_sem_repetir(lista1, lista2):
    """Une listas sem repetir itens equivalentes."""
    resultado = []
    vistos = set()

    for item in lista1 + lista2:
        chave = normalizar_texto(str(item))
        if chave and chave not in vistos:
            vistos.add(chave)
            resultado.append(item)

    return resultado


def ha_negacao_perto(tokens, indice_inicio, janela=4):
    """Verifica se existe negação perto da expressão."""
    inicio = max(0, indice_inicio - janela)
    trecho = tokens[inicio:indice_inicio]
    return any(token in NEGADORES for token in trecho)


def encontrar_ocorrencias(tokens, expr_tokens):
    """Encontra posições de uma expressão dentro dos tokens da frase."""
    posicoes = []
    tamanho = len(expr_tokens)

    if tamanho == 0:
        return posicoes

    for i in range(len(tokens) - tamanho + 1):
        if tokens[i:i + tamanho] == expr_tokens:
            posicoes.append(i)

    return posicoes


def detectar_contexto_local(frase):
    """
    Detecta sinais positivos e negativos pela estrutura da frase,
    e não apenas por palavras isoladas.
    """
    frase_norm = normalizar_texto(frase)
    tokens = tokenizar(frase)

    sinais_positivos = []
    sinais_negativos = []

    for expr in EXPRESSOES_POSITIVAS:
        expr_norm = normalizar_texto(expr)
        expr_tokens = expr_norm.split()

        for inicio in encontrar_ocorrencias(tokens, expr_tokens):
            if ha_negacao_perto(tokens, inicio):
                sinais_negativos.append(f"negação de '{expr}'")
            else:
                sinais_positivos.append(expr)

    for expr in EXPRESSOES_NEGATIVAS:
        expr_norm = normalizar_texto(expr)
        expr_tokens = expr_norm.split()

        for inicio in encontrar_ocorrencias(tokens, expr_tokens):
            if ha_negacao_perto(tokens, inicio):
                sinais_positivos.append(f"negação de '{expr}'")
            else:
                sinais_negativos.append(expr)

    if re.search(r"\bnada\b.*\bdar certo\b", frase_norm):
        sinais_negativos.append("nada ... dar certo")

    if re.search(r"\bnao\b.*\bdar certo\b", frase_norm):
        sinais_negativos.append("não ... dar certo")

    if re.search(r"\bpequen\w+\b.*\bconquist\w*\b", frase_norm):
        sinais_positivos.append("pequenos passos")
        sinais_positivos.append("conquistas")

    if re.search(r"\bforca interior\b", frase_norm):
        sinais_positivos.append("força interior")

    if re.search(r"\bmaior do que imagina\b", frase_norm):
        sinais_positivos.append("maior do que imagina")

    if re.search(r"\bmais forte do que imagina\b", frase_norm):
        sinais_positivos.append("mais forte do que imagina")

    if re.search(r"\bvaleu a pena\b|\bvale a pena\b", frase_norm):
        sinais_positivos.append("vale a pena")

    return {
        "sinais_positivos": unir_listas_sem_repetir([], sinais_positivos),
        "sinais_negativos": unir_listas_sem_repetir([], sinais_negativos),
    }


# =========================================================
# ANÁLISE LOCAL
# =========================================================

def analisar_localmente(frase, dicionario):
    """
    Faz a análise local usando:
    - palavras do dicionário
    - sinais contextuais da própria frase
    """
    tokens = tokenizar(frase)
    positivas_set, negativas_set = montar_sets_normalizados(dicionario)

    palavras_positivas = []
    palavras_negativas = []
    desconhecidas = []

    for token in tokens:
        if token in positivas_set:
            palavras_positivas.append(token)
        elif token in negativas_set:
            palavras_negativas.append(token)
        else:
            desconhecidas.append(token)

    contexto = detectar_contexto_local(frase)

    sinais_positivos = unir_listas_sem_repetir(
        palavras_positivas,
        contexto["sinais_positivos"]
    )

    sinais_negativos = unir_listas_sem_repetir(
        palavras_negativas,
        contexto["sinais_negativos"]
    )

    if len(sinais_positivos) > len(sinais_negativos):
        sentimento = "positivo"
    elif len(sinais_negativos) > len(sinais_positivos):
        sentimento = "negativo"
    else:
        sentimento = "neutro"

    return {
        "sentimento_geral": sentimento,
        "sinais_positivos": sinais_positivos,
        "sinais_negativos": sinais_negativos,
        "palavras_desconhecidas": desconhecidas
    }


# =========================================================
# OPENAI
# =========================================================

def obter_cliente_openai():
    """
    Cria o cliente da OpenAI usando o arquivo config_local.json.
    Se não estiver configurado, retorna None.
    """
    if OpenAI is None:
        return None

    config = carregar_configuracao()
    api_key = str(config.get("api_key", "")).strip()
    modelo = str(config.get("modelo", "")).strip()

    if not api_key or api_key == "COLE_SUA_CHAVE_AQUI":
        return None

    if not modelo:
        return None

    return OpenAI(api_key=api_key)


def obter_texto_resposta_openai(response):
    """
    Tenta pegar o texto da resposta da IA de forma mais segura.
    """
    texto = getattr(response, "output_text", None)

    if isinstance(texto, str) and texto.strip():
        return texto.strip()

    partes = []

    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", None) == "message":
            for content in getattr(item, "content", []) or []:
                if getattr(content, "type", None) == "output_text":
                    valor = getattr(content, "text", "")
                    if isinstance(valor, str) and valor.strip():
                        partes.append(valor.strip())

    return "\n".join(partes).strip()


def extrair_json_da_resposta(texto):
    """
    Extrai JSON da resposta do modelo.
    """
    texto = texto.strip()

    texto = re.sub(r"^```json\s*", "", texto)
    texto = re.sub(r"^```\s*", "", texto)
    texto = re.sub(r"\s*```$", "", texto)

    match = re.search(r"\{.*\}", texto, flags=re.DOTALL)
    if not match:
        raise ValueError("A resposta da IA não veio em JSON válido.")

    return json.loads(match.group(0))


def limpar_lista_vinda_da_ia(itens):
    """
    Limpa a lista vinda da IA sem exigir correspondência literal perfeita.
    """
    resultado = []
    vistos = set()

    for item in itens:
        if not isinstance(item, str):
            continue

        item = item.strip()
        if not item:
            continue

        chave = normalizar_texto(item)
        if not chave:
            continue

        if chave not in vistos:
            vistos.add(chave)
            resultado.append(item)

    return resultado


def analisar_com_ia(frase, dicionario, base_local):
    """
    Usa a IA para entender o contexto da frase.
    """
    client = obter_cliente_openai()

    if client is None:
        return None

    modelo = obter_modelo_configurado()

    prompt = f"""
Você vai analisar o sentimento de uma frase em português do Brasil.

OBJETIVO:
Dizer se a frase é positiva, negativa ou neutra.

REGRA PRINCIPAL:
Não se limite a palavras isoladas.
Considere o sentido da frase inteira.

O QUE VOCÊ DEVE PERCEBER:
- contexto geral
- negação
- contraste
- tom emocional
- incentivo, conquista, fracasso, desânimo, esperança
- elogio implícito ou crítica implícita

IMPORTANTE:
- Use o dicionário local apenas como base inicial.
- Se o sentimento estiver no contexto da frase, reconheça isso.
- Em "sinais_positivos" e "sinais_negativos", devolva trechos curtos ou expressões simples.
- Não invente nada muito técnico.
- Responda SOMENTE em JSON.

FRASE:
{frase}

DICIONÁRIO LOCAL POSITIVO:
{dicionario["positivas"]}

DICIONÁRIO LOCAL NEGATIVO:
{dicionario["negativas"]}

ANÁLISE LOCAL:
- sinais positivos: {base_local["sinais_positivos"]}
- sinais negativos: {base_local["sinais_negativos"]}
- palavras não reconhecidas: {base_local["palavras_desconhecidas"]}

RESPONDA EXATAMENTE ASSIM:
{{
  "sentimento_geral": "positivo",
  "sinais_positivos": [],
  "sinais_negativos": [],
  "sinais_neutros": [],
  "mensagem_amigavel": "..."
}}

VALORES ACEITOS EM "sentimento_geral":
- positivo
- negativo
- neutro
"""

    try:
        response = client.responses.create(
            model=modelo,
            input=prompt
        )

        texto_resposta = obter_texto_resposta_openai(response)
        if not texto_resposta:
            return None

        dados = extrair_json_da_resposta(texto_resposta)

        sentimento = str(dados.get("sentimento_geral", "")).strip().lower()
        if sentimento not in {"positivo", "negativo", "neutro"}:
            sentimento = "neutro"

        sinais_positivos = limpar_lista_vinda_da_ia(dados.get("sinais_positivos", []))
        sinais_negativos = limpar_lista_vinda_da_ia(dados.get("sinais_negativos", []))
        sinais_neutros = limpar_lista_vinda_da_ia(dados.get("sinais_neutros", []))

        mensagem = str(dados.get("mensagem_amigavel", "")).strip()

        return {
            "sentimento_geral": sentimento,
            "sinais_positivos": sinais_positivos,
            "sinais_negativos": sinais_negativos,
            "sinais_neutros": sinais_neutros,
            "mensagem_amigavel": mensagem
        }

    except Exception:
        return None


# =========================================================
# MONTAGEM DO RESULTADO FINAL
# =========================================================

def gerar_resumo_simples(sentimento):
    if sentimento == "positivo":
        return "A frase passou uma ideia positiva, de incentivo, conquista ou esperança."
    elif sentimento == "negativo":
        print("A frase passou uma ideia mais Negativa.")
    sentimento_pessoa=input("Você está bem? ")
    if sentimento_pessoa == "Não" or "nao" or "não" or "Nao":
        desabafo=input("Você pode desabafar aqui: ")
        print("\nse você estiver se sentindo triste ou solitário, você pode ligar para esse número aqui 188 que eles vão te ajudar\n")
        print("A SUA VIDA IMPORTA!!!!❤️😊🫂")
    elif sentimento == "Neutro":
        return "A frase ficou equilibrada, sem um tom claramente positivo ou negativo."
    
    
    


def analisar_sentimento(frase, dicionario):
    """
    Junta análise local + análise contextual por IA.
    """
    base_local = analisar_localmente(frase, dicionario)
    resultado_ia = analisar_com_ia(frase, dicionario, base_local)

    if resultado_ia is None:
        sinais_positivos = base_local["sinais_positivos"]
        sinais_negativos = base_local["sinais_negativos"]
        sinais_neutros = []
        sentimento = base_local["sentimento_geral"]
        mensagem = gerar_resumo_simples(sentimento)
    else:
        sinais_positivos = unir_listas_sem_repetir(
            base_local["sinais_positivos"],
            resultado_ia["sinais_positivos"]
        )

        sinais_negativos = unir_listas_sem_repetir(
            base_local["sinais_negativos"],
            resultado_ia["sinais_negativos"]
        )

        sinais_neutros = resultado_ia["sinais_neutros"]
        sentimento = resultado_ia["sentimento_geral"]

        if sentimento == "neutro":
            if len(sinais_positivos) > len(sinais_negativos):
                sentimento = "positivo"
            elif len(sinais_negativos) > len(sinais_positivos):
                sentimento = "negativo"

        if sentimento == "positivo" and not sinais_positivos:
            sinais_positivos = ["contexto positivo da frase"]

        if sentimento == "negativo" and not sinais_negativos:
            sinais_negativos = ["contexto negativo da frase"]

        mensagem = resultado_ia["mensagem_amigavel"] or gerar_resumo_simples(sentimento)

    return {
        "frase": frase,
        "sentimento_geral": sentimento,
        "sinais_positivos": sinais_positivos,
        "sinais_negativos": sinais_negativos,
        "sinais_neutros": sinais_neutros,
        "quantidade_positivos": len(sinais_positivos),
        "quantidade_negativos": len(sinais_negativos),
        "mensagem_amigavel": mensagem
    }


# =========================================================
# EXIBIÇÃO BONITA E SIMPLES
# =========================================================

def emoji_do_sentimento(sentimento):
    if sentimento == "positivo":
        return "😊"
    elif sentimento == "negativo":
        return "😞"
    return "😐"


def titulo_do_sentimento(sentimento):
    if sentimento == "positivo":
        return "POSITIVO"
    elif sentimento == "negativo":
        return "NEGATIVO"
    return "NEUTRO"


def mostrar_resultado(resultado):
    """
    Mostra o resultado de forma simples e bonita.
    """
    emoji = emoji_do_sentimento(resultado["sentimento_geral"])
    titulo = titulo_do_sentimento(resultado["sentimento_geral"])

    print("\n" + "🌟" * 25)
    print("      RESULTADO DA ANÁLISE")
    print("🌟" * 25)

    print(f"\n📝 Frase analisada:")
    print(f"“{resultado['frase']}”")

    print(f"\n{emoji} Sentimento da frase: {titulo}")

    print(f"\n💚 Sinais positivos percebidos: {resultado['quantidade_positivos']}")
    if resultado["sinais_positivos"]:
        print("   ➜ " + ", ".join(resultado["sinais_positivos"]))

    print(f"\n❤️‍🩹 Sinais negativos percebidos: {resultado['quantidade_negativos']}")
    if resultado["sinais_negativos"]:
        print("   ➜ " + ", ".join(resultado["sinais_negativos"]))

    if resultado["sinais_neutros"]:
        print(f"\n⚪ Sinais neutros:")
        print("   ➜ " + ", ".join(resultado["sinais_neutros"]))

    print(f"\n💬 Resumo:")
    print(resultado["mensagem_amigavel"])

    print("\n" + "✨" * 25)


# =========================================================
# FUNÇÕES DO MENU
# =========================================================

def adicionar_palavra(dicionario):
    """
    Permite adicionar palavra ao dicionário local.
    """
    print("\n📚 ADICIONAR PALAVRA AO DICIONÁRIO")

    palavra = input("Digite a palavra ou expressão: ").strip().lower()
    if not palavra:
        print("⚠️ Palavra inválida.")
        return

    palavra_norm = normalizar_texto(palavra)

    positivas_set, negativas_set = montar_sets_normalizados(dicionario)

    if palavra_norm in positivas_set:
        print("⚠️ Essa palavra já está na lista de positivas.")
        return

    if palavra_norm in negativas_set:
        print("⚠️ Essa palavra já está na lista de negativas.")
        return

    print("\nEssa palavra é:")
    print("1) 😊 Positiva")
    print("2) 😞 Negativa")

    escolha = input("Escolha 1 ou 2: ").strip()

    if escolha == "1":
        dicionario["positivas"].append(palavra)
        salvar_dicionario(dicionario)
        print(f"✅ '{palavra}' foi adicionada como positiva.")
    elif escolha == "2":
        dicionario["negativas"].append(palavra)
        salvar_dicionario(dicionario)
        print(f"✅ '{palavra}' foi adicionada como negativa.")
    else:
        print("⚠️ Opção inválida. Nada foi salvo.")


def ver_estatisticas(dicionario):
    """
    Mostra estatísticas simples do dicionário.
    """
    print("\n📊 ESTATÍSTICAS DO DICIONÁRIO")
    print(f"😊 Total de itens positivos: {len(dicionario['positivas'])}")
    print(f"😞 Total de itens negativos: {len(dicionario['negativas'])}")
    print(f"📚 Total geral: {len(dicionario['positivas']) + len(dicionario['negativas'])}")


# =========================================================
# PROGRAMA PRINCIPAL
# =========================================================

def main():
    """
    Controla o menu do programa.
    """
    dicionario = carregar_dicionario()
    config = carregar_configuracao()

    print("💡 ANALISADOR DE SENTIMENTOS COM IA")
    print("🤖 Contexto + significado + dicionário local")
    print("🎀 Resultado bonito e fácil de entender")

    if OpenAI is None:
        print("\n⚠️ A biblioteca 'openai' não está instalada.")
        print("   O programa vai funcionar só no modo local até você instalar a biblioteca.")

    if not chave_configurada():
        print("\n⚠️ A chave da OpenAI ainda não foi preenchida.")
        print(f"   Abra o arquivo: {ARQUIVO_CONFIG.name}")
        print("   e troque 'COLE_SUA_CHAVE_AQUI' pela sua chave.")

    if not str(config.get('modelo', '')).strip():
        print("\n⚠️ O modelo não foi preenchido no arquivo de configuração.")
        print(f"   Abra o arquivo: {ARQUIVO_CONFIG.name}")
        print("   e informe o modelo desejado.")

    while True:
        print("\n" + "=" * 45)
        print("MENU PRINCIPAL")
        print("=" * 45)
        print("1) ✍️ Analisar uma frase")
        print("2) 📚 Adicionar palavra ao dicionário")
        print("3) 📊 Ver estatísticas do dicionário")
        print("4) 🚪 Sair")

        opcao = input("\nEscolha uma opção (1-4): ").strip()

        if opcao == "1":
            frase = input("\nDigite a frase que deseja analisar: ").strip()

            if not frase:
                print("⚠️ Você não digitou nenhuma frase.")
                continue

            resultado = analisar_sentimento(frase, dicionario)
            mostrar_resultado(resultado)

        elif opcao == "2":
            adicionar_palavra(dicionario)
            dicionario = carregar_dicionario()

        elif opcao == "3":
            ver_estatisticas(dicionario)

        elif opcao == "4":
            print("\n👋 Obrigado por usar o programa!")
            break

        else:
            print("⚠️ Opção inválida. Tente novamente.")


if __name__ == "__main__":
    main()
