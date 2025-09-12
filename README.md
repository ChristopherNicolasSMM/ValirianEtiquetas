# 🏷️ Gerador de Etiquetas Word

![GitHub Actions Workflow Status](https://github.com/ChristopherNicolasSMM/ValirianEtiquetas/actions/workflows/main.yml/badge.svg)


Aplicação em **Python** para geração automática de etiquetas em documentos **Microsoft Word (.docx)**, a partir de um modelo pré-formatado.  
O projeto permite preencher tabelas com dados dinâmicos, aplicar estilos personalizados (como tamanho de fonte) e exportar documentos prontos para impressão.  
Pensado para auxiliar na geração de etiquetas com dados do lote para cervejas artesanais utilizando o consumo da API do BrewFather.

---

## ✨ Funcionalidades

- 📄 Clonagem de tabelas de um modelo `.docx`
- 🔄 Substituição automática de placeholders (`{campo}`) pelos valores do lote
- 🎨 Ajustes de formatação (fontes, tamanhos, bordas da tabela, etc.)
- 📦 Exportação em arquivos `.docx` nomeados automaticamente
- 🖨️ Preparado para impressão de etiquetas em papel A4 

---

## 🛠️ Tecnologias Utilizadas

- [Python 3.10+](https://www.python.org/)
- [python-docx](https://python-docx.readthedocs.io/en/latest/) – manipulação de arquivos Word
- [lxml](https://lxml.de/) – validação e ajustes em XML do documento
- [copy](https://docs.python.org/3/library/copy.html) – clonagem de objetos internos

---

## 👨‍💻 Manual do usuário
- [Clique aqui para navegar até o manual](https://github.com/ChristopherNicolasSMM/ValirianEtiquetas/blob/main/manual_usuario/README.md)

---

## 📂 Estrutura do Projeto

```bash
src/
│── main.py                  # Script principal (CLI)
│── word_handler.py          # Geração de etiquetas em Word
│── api/
│   └── brewfather_api.py    # Cliente da Brewfather API
│── templates/
│   ├── etiqueta_template.docx
│   └── output/              # Etiquetas geradas
│── db/
│   └── sqlite_db.py         # Banco de dados SQLite (schema e persistência)
requirements.txt             # Dependências do projeto
```

---

## 🚀 Como Executar

1. Clone o repositório:

   ```bash
   git clone https://github.com/ChristopherNicolasSMM/ValirianEtiquetas.git
   cd ValirianEtiquetas
   ```

2. Crie e ative um ambiente virtual:

   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate      # Windows
   ```

3. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

4. Execute o script (modo CLI padrão):

   ```bash
   python src/main.py
   ```

5. Para usar a Interface Gráfica (GUI):

   - Ao iniciar `python src/main.py`, escolha a opção `2` quando solicitado, ou
   - Crie um atalho do Windows apontando para `python.exe src\main.py` (opção 2 selecionada na execução).

   Requisitos para GUI:
   - Windows 10+ com Python instalado (Tkinter já vem com CPython oficial)
   - Variáveis `.env` configuradas para a API Brewfather

---

## 📦 Build para Windows (EXE + Instalador)

1) Gerar o executável com PyInstaller:

```bash
scripts\venv\activate  # ative seu venv se necessário
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --clean --noconfirm pyinstaller.spec
```

Saída em `dist/ValirianEtiquetas/ValirianEtiquetas.exe`.

2) Gerar instalador (Inno Setup):

- Instale o Inno Setup (ISCC) no Windows.
- Abra/compile `installer/ValirianEtiquetas.iss` (ou use `ISCC.exe installer\ValirianEtiquetas.iss`).
- O instalador resultante instala em `C:\ValirianEtiquetas`, cria atalho na área de trabalho e executa ao final.

3) Atalho manual (opcional):

```bat
build_scripts\create_desktop_shortcut.bat
```

Notas de empacotamento:

- O template `src/templates/etiqueta_template.docx` é incluído na build e, em runtime, fica disponível em `{instalação}\templates`.
- O banco SQLite será criado em `C:\ValirianEtiquetas\db\valirian.db` na primeira execução.

---

## ⚙️ Configuração

* O **modelo de etiquetas** deve estar em `src/templates/`.

* No documento modelo, utilize **placeholders** no formato:

  ```text
  {lote}
  {receita}
  {abv}
  {ibu}
  {estimatedColor}
  {data_brassagem}
  {data_engarrafamento}
  {data_impressao}
  ```

* Esses placeholders serão substituídos automaticamente pelos valores do lote informado.

---

## 💾 Banco de Dados (SQLite)

O projeto agora oferece opção de salvar os dados consultados na API localmente em SQLite.

Diretivas:

- O arquivo do banco é criado automaticamente em `src/db/valirian.db` na primeira execução.
- O schema inclui:
  - `recipes(id, name, style, created_at)`
  - `batches(id, batch_no, brewer, brew_date, name, measured_abv, estimated_ibu, estimated_color, recipe_id, created_at)`
  - `batch_events(id, batch_id, event_type, time_ts, time_human, created_at)`
- Após listar lotes ou abrir os detalhes de um lote, o CLI pergunta se deseja salvar no banco.

Como usar em código:

```python
from db.sqlite_db import init_schema, upsert_batch, upsert_batch_with_events, fetch_batches, fetch_batch_events

init_schema()

# upsert de lista (dados resumidos)
upsert_batch({
    '_id': 'abc123',
    'batchNo': 42,
    'brewer': 'Valirian',
    'brewDate': '01/01/2025',
    'name': 'American IPA',
})

# upsert de detalhes (inclui evento de engarrafamento quando houver)
upsert_batch_with_events({
    '_id': 'abc123',
    'batchNo': 42,
    'brewDate': '01/01/2025',
    'name': 'American IPA',
    'measuredAbv': 6.5,
    'estimatedIbu': 45,
    'estimatedColor': 12,
    'bottling_event': {
        'eventType': 'event-batch-bottling-day',
        'time': '05/01/2025 12:00:00',
        'timestamp': 1736078400000
    }
})

print(fetch_batches(10))
print(fetch_batch_events('abc123'))
```

---

## ⚙️ Configurações (settings)

O projeto possui configurações persistentes para o modelo padrão de etiquetas.

- Local: armazenadas na tabela `app_settings` do SQLite.
- Chaves usadas:
  - `template_dir`: diretório do modelo padrão
  - `template_file`: nome do arquivo do modelo padrão
- Padrões (se não configurado): `src/templates/` + `etiqueta_template.docx`.

Durante a geração de etiquetas, o CLI:

1. Mostra o modelo padrão atual e pergunta se deseja usá-lo (Enter para sim).
2. Se escolher não, pede um caminho completo de `.docx`.
3. Pergunta se deseja salvar esse caminho como novo padrão.

Uso programático:

```python
from settings import get_template_path_from_settings, save_template_as_default

path = get_template_path_from_settings()
print(path)

# Para alterar o padrão:
save_template_as_default(r"C:\\meus_modelos\\meu_template.docx")
```

---

## 📑 Exemplo de Uso

```python
from etiquetas import GeradorEtiquetas

dados_lote = {
    "receita": "Witbier Clássica",
    "batchNo": "14_p1",
    "data": "04/09/2025"
}

gerador = GeradorEtiquetas("src/template/etiqueta_template.docx", "src/template/output")
arquivo = gerador.gerar(dados_lote)

print(f"Etiqueta gerada em: {arquivo}")
```

Saída esperada:

```text
Etiqueta gerada em: src/template/output/etiqueta_14_p1_20250904_103228.docx
```

---

## 📝 Roadmap

* [ ] Adicionar suporte para exportar também em PDF
* [ ] Incluir mais elementos de navegação, opção de mais templates
* [ ] Implementar mais consultas ao Brewfather (ex: estoque, relatórios avançados)
* [ ] Opção de usar banco local para armazenar dados dos rótulos (harmonização, novos campos)
* [ ] Interface gráfica (GUI) para selecionar dados de entrada
* [ ] Integração com planilhas Excel como fonte de dados

---

## 🤝 Contribuindo

Contribuições são sempre bem-vindas!
Para sugerir melhorias:

1. Fork o projeto
2. Crie sua branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas alterações (`git commit -m 'Adiciona nova funcionalidade'`)
4. Faça push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um **Pull Request**

---

## 📜 Licença

Este projeto está sob a licença **MIT** – veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

## 👨‍💻 Autor

Desenvolvido por **Christopher Nicolas Mauricio**
📧 [LinkedIn](https://www.linkedin.com/in/christophernicolassmm/)

