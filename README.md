# Mercado — Sistema de Estoque

Aplicação web desenvolvida com Django para cadastro e consulta de produtos por código de barras. O sistema utiliza a câmera do dispositivo para ler códigos de barras e consulta a base Open Food Facts para preencher automaticamente as informações disponíveis do produto.

O projeto está sendo desenvolvido com foco em uma interface simples, responsiva e adequada para uso em dispositivos móveis.

## Funcionalidades

* **Cadastro de produtos:** registro de código de barras, nome, quantidade e preço.
* **Leitura de códigos de barras:** utilização da câmera do celular para identificar produtos.
* **Preenchimento automático:** consulta à API Open Food Facts para obter nome e marca do produto, quando disponíveis.
* **Consulta de estoque:** visualização dos produtos cadastrados em uma tabela.
* **Deploy em nuvem:** aplicação publicada no Google Cloud Run.

## Tecnologias utilizadas

* Python
* Django
* SQLite
* HTML e CSS
* JavaScript
* [html5-qrcode](https://github.com/mebjas/html5-qrcode)
* [Open Food Facts API](https://world.openfoodfacts.org/)
* Docker
* Google Cloud Run
* Google Artifact Registry

## Estrutura do projeto

```text
config/
├── settings.py
├── urls.py
└── ...

mercado/
├── migrations/
├── templates/
│   ├── base.html
│   ├── scan.html
│   └── stock.html
├── admin.py
├── apps.py
├── models.py
├── urls.py
└── views.py

Dockerfile
requirements.txt
manage.py
```

## Modelo de dados

O sistema utiliza o modelo `Product` para armazenar os produtos cadastrados.

| Campo      | Descrição                        |
| ---------- | -------------------------------- |
| `name`     | Nome do produto                  |
| `barcode`  | Código de barras único           |
| `quantity` | Quantidade disponível em estoque |
| `price`    | Preço do produto                 |

## Executando localmente

### 1. Pré-requisitos

* Python 3.12 ou compatível
* Git
* Pip

### 2. Clone o repositório

```bash
git https://github.com/RenatoHT/PI-2.git
cd PI-2
```

### 3. Crie e ative um ambiente virtual

No Linux ou macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

No Windows:

```powershell
python -m venv venv
venv\Scripts\activate
```

### 4. Instale as dependências

```bash
pip install -r requirements.txt
```

### 5. Execute as migrações

```bash
python manage.py migrate
```

### 6. Inicie o servidor

```bash
python manage.py runserver
```

A aplicação estará disponível em:

http://127.0.0.1:8000/mercado/stock/

## Principais rotas

| Rota                      | Descrição                                 |
| ------------------------- | ----------------------------------------- |
| `/mercado/stock/`         | Cadastro e consulta de estoque            |
| `/mercado/scan/`          | Página de leitura de códigos de barras    |
| `/mercado/lookup/CODIGO/` | Consulta de produto pelo código de barras |

## Consulta de produtos

O sistema utiliza a API Open Food Facts para consultar informações de produtos a partir do código de barras.

As informações retornadas dependem da disponibilidade e da qualidade dos dados cadastrados na base externa. Quando um produto não é encontrado, seus dados podem precisar ser preenchidos manualmente.

## Implantação

A aplicação está preparada para execução em contêiner Docker e implantação no Google Cloud Run, utilizando o Google Artifact Registry para armazenar as imagens.

Para uma implantação de produção, recomenda-se configurar corretamente as variáveis de ambiente, os arquivos estáticos, o servidor de aplicação e um banco de dados persistente adequado ao ambiente.

## Observações

Este projeto está em desenvolvimento e pode receber novas funcionalidades e alterações na estrutura.
