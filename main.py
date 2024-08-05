import json
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from decouple import config

# Se 1, irá salvar a lista de concursos dentro de um arquivo em /listas/arquivo_data_horario.json
salvar_json = config('SALVAR_ARQUIVO_JSON')


def lista_concursos(uf):
    html_text = requests.get('https://concursosnobrasil.com/concursos/'+uf).text
    soup = BeautifulSoup(html_text, 'lxml')
    table_concursos = soup.find('main', class_='taxonomy')
    concursos = []

    for row in table_concursos.table.tbody:
        concurso = row.find_all('td')
        concurso_link = concurso[0].find('a')['href']
        concurso_titulo = concurso[0].find('a')['title']
        concurso_previsto = concurso[0].find('span', class_='label-previsto').text if concurso[0].find('span', class_='label-previsto') else False
        vagas = concurso[0].next_sibling.text
        concurso_pagina = get_concurso_pagina(concurso_link)
        criado_em = concurso_pagina['data_criacao']
        concurso_conteudo_html = concurso_pagina['conteudo_html']

        concursos.append({
            'titulo': concurso_titulo,
            'data': criado_em,
            'previsto': concurso_previsto,
            'vagas': vagas,
            'link': concurso_link,
            'conteudo_html': concurso_conteudo_html,
            'uf': uf.upper()
        })

    # Ordena os concursos conforme a data de criação
    concursos.sort(key=lambda x: datetime.strptime(x['data'], '%d/%m/%Y'))
    concursos.reverse()
    return concursos


# pega a data de criação e o texto sobre o concurso
def get_concurso_pagina(link):
    pagina_concurso_html_text = requests.get(link).text
    soup = BeautifulSoup(pagina_concurso_html_text, 'lxml')
    data_criacao = soup.find('time').text if soup.find('time') else soup.find('time').datetime
    data_criacao = data_criacao.split()[0]

    conteudo_html = soup.find('div', class_='entry-info-text')
    propagandas = conteudo_html.find_all('div', attrs={'class': re.compile('^concur-prebid-lendo-*.*')})
    for ads in propagandas:
        ads.decompose()

    return {'data_criacao': data_criacao, 'conteudo_html': str(conteudo_html)}


# envia a lista de concursos em json para a api que vai armazenar e servir para os clientes
def enviar_lista(lista_json):
    headers = {'accept': 'application/json'}
    data = {'lista_de_concursos': lista_json}
    res = requests.post(
        config('ENVIAR_JSON_PARA_URL') + '/' + config('API_CHAVE'),
        json=data,
        headers=headers
    )
    print(res.json())


# os concursos serão filtrados conforme os estados abaixo
#estados = [
#    "AC", "AL", "AP", "AM", "BA", "CE",
#    "DF", "ES", "GO", "MA", "MT", "MS",
#    "MG", "PA", "PB", "PR", "PE", "PI",
#    "RJ", "RN", "RS", "RO", "RR", "SC",
#    "SP", "SE", "TO",
#]
estados = [ "MS" ]

lista_de_concursos = []

# faz a extração dos dados a cada 6 horas
if __name__ == '__main__':
    while True:
        print('Iniciando scraping...')

        for uf in estados:
            #print(lista_concursos(uf))
            lista_de_concursos.append(lista_concursos(uf))

        lista_de_concursos = json.dumps(lista_de_concursos)

        if salvar_json == '1':
            timestamps = time.strftime('%d_%m_%Y_as_%H_%M_%S')
            nome_arquivo = 'listas/concursos_extraidos_em_' + timestamps + '.json'
            with open(nome_arquivo, 'w') as f:
                f.write(lista_de_concursos)
            print('Arquivo salvo em: /' + nome_arquivo)

        print('Enviando lista de concursos para: ' + config('ENVIAR_JSON_PARA_URL'))
        enviar_lista(lista_de_concursos)

        intervalo = 6
        print(f'Esperando {intervalo} horas até a próxima extração...')
        time.sleep((60 * 60) * 6)
