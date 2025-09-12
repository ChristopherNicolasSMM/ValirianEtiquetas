# Manual do Usuário - Valirian Etiquetas

---
## Manual simplificado

1. Copie a pasta ValirianEtiquetas que esta dentro da pasta dist para o local de preferencia, como sugestão pode copiar para raiz C: e criar um atalho do arquivo para o desktop veja detalhadamente no video abaixo.


[Assista à demo em vídeo](https://www.youtube.com/watch?v=_1KP9zOtjXk)
---

## Manual Tecnico

### Modos de Execução

- Terminal (CLI): `python src/main.py` e escolha `1`.
- Interface Gráfica (GUI): `python src/main.py` e escolha `2`.

### Fluxo (GUI)

1. Defina o limite de lotes.
2. Clique em "Listar Lotes API" para buscar da API ou "Listar Lotes DB" para buscar do banco.
   - Para DB, você pode informar datas "De" e "Até" (dd/mm/aaaa) e usar o limite.
3. Selecione um lote e clique em "Buscar Detalhes".
4. Edite os campos no painel de detalhes, se desejar.
5. Clique em "Salvar Edição + Obs" para gravar suas alterações e observação.
6. Use a seção "Tags Personalizadas" para criar placeholders extras (ex.: `harmoniza`, `observacao`).
7. Clique em "Gerar Etiquetas" para produzir os arquivos `.docx`.

### Modelo de Etiqueta

- Ao clicar em "Escolher Modelo..." selecione um `.docx`. Você pode definir como padrão.
- Placeholders disponíveis no modelo:
  - {lote}, {receita}, {abv}, {ibu}, {estimatedColor}
  - {data_brassagem}, {data_engarrafamento}, {data_impressao}
  - Tags personalizadas adicionadas na GUI (ex.: {harmoniza}, {observacao})

### Edições Salvas

- "Edições Salvas" aparece quando um lote é selecionado.
- Dê duplo clique em uma edição salva (ou use "Carregar Selecionada") para carregar nos detalhes e continuar editando.

### Portátil (sem instalar)

- Use a pasta `dist/ValirianEtiquetas` gerada pelo PyInstaller.
- Em build empacotado, o aplicativo usa a própria pasta do executável: o banco fica em `db/` e o modelo em `templates/`.


