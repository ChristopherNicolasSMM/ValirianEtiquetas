import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from api.brewfather_api import BrewfatherAPI
from word_handler import WordEtiquetaHandler
from db.sqlite_db import (
    init_schema,
    upsert_batch,
    upsert_batch_with_events,
    upsert_batch_override,
    get_batch_override,
    get_batch_by_id,
    get_batch_with_overrides,
    set_tag,
    delete_tag,
    list_tags,
    list_overridden_batches,
    fetch_batches_filtered,
)
from settings import (
    get_template_path_from_settings,
    save_template_as_default,
    read_env,
    write_env,
)


class BrewfatherGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Valirian Etiquetas - Brewfather")
        self.geometry("1000x700")
        self.minsize(900, 600)

        #Código para definir o icone da janela
        self._set_window_icon()

        # Init
        init_schema()
        try:
            self.api = BrewfatherAPI()
            self.status_var = tk.StringVar(value="Conectado à Brewfather API")
        except Exception as e:
            self.api = None
            self.status_var = tk.StringVar(value=f"Erro API: {e}")

        self._build_ui()


    def _set_window_icon(self):
        """Define o ícone da janela, tentando múltiplas localizações"""
        icon_paths = [
            # No desenvolvimento: caminho relativo
            os.path.join('src', 'IconEtiquetas.ico'),
            # No executável: pode estar no diretório de trabalho
            'IconEtiquetas.ico',
            os.path.join('_internal', 'IconEtiquetas.ico'),
            os.path.join('/', 'IconEtiquetas.ico'),
            # Caminho absoluto (fallback)
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'IconEtiquetas.ico'),
        ]
        
        for icon_path in icon_paths:
            try:
                if os.path.exists(icon_path):
                    self.iconbitmap(icon_path)
                    print(f"Ícone carregado: {icon_path}")
                    return
            except Exception as e:
                print(f"Erro ao carregar ícone {icon_path}: {e}")
                continue
        
        print("AVISO: Não foi possível carregar o ícone da janela")


    # UI
    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Top controls
        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        top.columnconfigure(5, weight=1)

        ttk.Label(top, text="Limite de lotes:").grid(row=0, column=0, padx=(0, 6))
        self.limit_var = tk.StringVar(value="5")
        self.limit_entry = ttk.Entry(top, width=6, textvariable=self.limit_var)
        self.limit_entry.grid(row=0, column=1)

        self.btn_listar_api = ttk.Button(top, text="Listar Lotes API", command=self._listar_lotes)
        self.btn_listar_api.grid(row=0, column=2, padx=6)

        self.btn_listar_db = ttk.Button(top, text="Listar Lotes DB", command=self._listar_lotes_db)
        self.btn_listar_db.grid(row=0, column=3)

        ttk.Label(top, text="De (dd/mm/aaaa):").grid(row=1, column=0, padx=(0,6), pady=(6,0))
        self.start_date_var = tk.StringVar()
        ttk.Entry(top, width=12, textvariable=self.start_date_var).grid(row=1, column=1, sticky="w", pady=(6,0))

        ttk.Label(top, text="Até (dd/mm/aaaa):").grid(row=1, column=2, padx=(6,6), pady=(6,0))
        self.end_date_var = tk.StringVar()
        ttk.Entry(top, width=12, textvariable=self.end_date_var).grid(row=1, column=3, sticky="w", pady=(6,0))

        self.btn_salvar_lista = ttk.Button(top, text="Salvar Lista no Banco", command=self._salvar_lista)
        self.btn_salvar_lista.grid(row=0, column=4)

        self.btn_template = ttk.Button(top, text="Escolher Modelo...", command=self._escolher_template)
        self.btn_template.grid(row=0, column=5, padx=6)

        self.btn_settings = ttk.Button(top, text="Configurações", command=self._open_settings)
        self.btn_settings.grid(row=0, column=6, padx=(6,0))

        # Main Paned
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        # Left: list of batches
        left = ttk.Frame(paned)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)

        ttk.Label(left, text="Lotes").grid(row=0, column=0, sticky="w")
        self.batches_list = tk.Listbox(left, height=20)
        self.batches_list.grid(row=1, column=0, sticky="nsew")
        self.batches_list.bind("<<ListboxSelect>>", self._on_select_batch)

        self.btn_detalhes = ttk.Button(left, text="Buscar Detalhes", command=self._buscar_detalhes)
        self.btn_detalhes.grid(row=2, column=0, sticky="ew", pady=(6, 0))

        paned.add(left, weight=1)

        # Right: details and actions
        right = ttk.Frame(paned)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        ttk.Label(right, text="Detalhes do Lote").grid(row=0, column=0, sticky="w")
        self.details_text = tk.Text(right, height=16)
        self.details_text.grid(row=1, column=0, sticky="nsew")

        actions = ttk.Frame(right)
        actions.grid(row=2, column=0, sticky="ew", pady=(6, 0))

        ttk.Label(actions, text="Qtd etiquetas:").grid(row=0, column=0)
        self.qtd_var = tk.StringVar(value="1")
        self.qtd_entry = ttk.Entry(actions, width=6, textvariable=self.qtd_var)
        self.qtd_entry.grid(row=0, column=1, padx=(4, 10))

        self.btn_salvar_detalhes = ttk.Button(actions, text="Salvar Edição + Obs", command=self._salvar_detalhes)
        self.btn_salvar_detalhes.grid(row=0, column=2)

        self.btn_etiquetas = ttk.Button(actions, text="Gerar Etiquetas", command=self._gerar_etiquetas)
        self.btn_etiquetas.grid(row=0, column=3, padx=(8, 0))

        # Tags editor
        tags_frame = ttk.LabelFrame(right, text="Tags Personalizadas (placeholders adicionais)")
        tags_frame.grid(row=3, column=0, sticky="nsew", pady=(6, 0))
        tags_frame.columnconfigure(1, weight=1)

        ttk.Label(tags_frame, text="Chave:").grid(row=0, column=0, padx=4, pady=4)
        self.tag_key_var = tk.StringVar()
        self.tag_key_entry = ttk.Entry(tags_frame, textvariable=self.tag_key_var, width=20)
        self.tag_key_entry.grid(row=0, column=1, sticky="ew", padx=(0, 4))

        ttk.Label(tags_frame, text="Valor:").grid(row=0, column=2, padx=4, pady=4)
        self.tag_value_var = tk.StringVar()
        self.tag_value_entry = ttk.Entry(tags_frame, textvariable=self.tag_value_var)
        self.tag_value_entry.grid(row=0, column=3, sticky="ew")

        self.btn_add_tag = ttk.Button(tags_frame, text="Adicionar/Atualizar", command=self._add_or_update_tag)
        self.btn_add_tag.grid(row=0, column=4, padx=6)

        self.tags_list = tk.Listbox(tags_frame, height=6)
        self.tags_list.grid(row=1, column=0, columnspan=5, sticky="nsew", padx=4, pady=(4, 6))
        tags_frame.rowconfigure(1, weight=1)

        self.btn_del_tag = ttk.Button(tags_frame, text="Remover Selecionada", command=self._remove_selected_tag)
        self.btn_del_tag.grid(row=2, column=0, columnspan=5, sticky="e", padx=4, pady=(0, 4))

        # Saved overrides quick view
        self.saved_frame = ttk.LabelFrame(right, text="Edições Salvas")
        self.saved_frame.grid(row=4, column=0, sticky="nsew", pady=(6, 0))
        self.saved_frame.columnconfigure(0, weight=1)
        self.saved_frame.rowconfigure(1, weight=1)
        self.saved_list = tk.Listbox(self.saved_frame, height=6)
        self.saved_list.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self.saved_list.bind('<Double-1>', self._load_saved_double_click)
        self.btn_reload_saved = ttk.Button(self.saved_frame, text="Recarregar", command=self._reload_saved)
        self.btn_reload_saved.grid(row=0, column=0, sticky="e", padx=4, pady=(4, 0))
        self.btn_load_saved = ttk.Button(self.saved_frame, text="Carregar Selecionada", command=self._load_saved_selected)
        self.btn_load_saved.grid(row=0, column=0, sticky="w", padx=4, pady=(4,0))

        paned.add(right, weight=2)

        # Status bar
        status = ttk.Frame(self)
        status.grid(row=2, column=0, sticky="ew")
        status.columnconfigure(0, weight=1)
        ttk.Label(status, textvariable=self.status_var).grid(row=0, column=0, sticky="w", padx=10, pady=(0, 10))

        # Internal state
        self._batches = []
        self._selected_batch = None
        self._template_path = get_template_path_from_settings()
        self._reload_saved()
        # Oculta edições salvas até selecionar um lote
        self._toggle_saved_frame(False)
        self._list_mode = 'api'

    # Helpers
    def _set_status(self, text: str) -> None:
        self.status_var.set(text)
        self.update_idletasks()

    def _run_bg(self, target, *args, **kwargs):
        t = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
        t.start()

    def _selected_index(self) -> int:
        sel = self.batches_list.curselection()
        return sel[0] if sel else -1

    # Actions
    def _listar_lotes(self) -> None:
        if not self.api:
            messagebox.showerror("Erro", "API não inicializada.")
            return

        def work():
            try:
                limit = int(self.limit_var.get() or "1")
            except ValueError:
                limit = 1
            self._set_status(f"Buscando {limit} lote(s)...")
            batches = self.api.listBatches(limit)
            self._batches = batches or []
            self._fill_batches_list()
            self._set_status("Listagem concluída.")

        self._run_bg(work)
        self._list_mode = 'api'

    def _listar_lotes_db(self) -> None:
        try:
            limit = int(self.limit_var.get() or "1")
        except ValueError:
            limit = 1
        start = (self.start_date_var.get() or '').strip() or None
        end = (self.end_date_var.get() or '').strip() or None

        def work():
            self._set_status("Carregando lotes do banco...")
            batches = fetch_batches_filtered(limit=limit, start_date=start, end_date=end)
            normalized = []
            for b in batches:
                normalized.append({
                    '_id': b.get('id'),
                    'brewer': b.get('brewer'),
                    'batchNo': b.get('batch_no'),
                    'brewDate': b.get('brew_date'),
                    'recipe_name': b.get('name'),
                })
            self._batches = normalized
            self._fill_batches_list()
            self._set_status("Listagem (DB) concluída.")

        self._run_bg(work)
        self._list_mode = 'db'

    def _fill_batches_list(self) -> None:
        self.batches_list.delete(0, tk.END)
        for b in self._batches:
            txt = f"#{b.get('batchNo')} | {b.get('brewDate')} | {b.get('recipe_name') or ''}"
            self.batches_list.insert(tk.END, txt)
        self.details_text.delete("1.0", tk.END)
        self._selected_batch = None

    def _on_select_batch(self, _evt=None) -> None:
        idx = self._selected_index()
        if idx < 0 or idx >= len(self._batches):
            self._toggle_saved_frame(False)
            return
        self._selected_batch = self._batches[idx]
        self._toggle_saved_frame(True)

    def _buscar_detalhes(self) -> None:
        if not self.api:
            messagebox.showerror("Erro", "API não inicializada.")
            return
        if not self._selected_batch:
            messagebox.showinfo("Info", "Selecione um lote na lista.")
            return

        def work():
            self._set_status("Buscando detalhes do lote...")
            details = self.api.listBatch(self._selected_batch['_id'])
            if not details:
                messagebox.showerror("Erro", "Não foi possível obter detalhes.")
                self._set_status("Falha ao obter detalhes.")
                return
            self._show_details(details)
            self._selected_batch = details  # promove a estrutura com detalhes
            self._set_status("Detalhes obtidos.")

        self._run_bg(work)

    def _show_details(self, d: dict) -> None:
        # Mescla overrides do banco (se existirem)
        merged = dict(d)
        try:
            ov = get_batch_override(d.get('_id'))
            if ov:
                if ov.get('name'):
                    merged['name'] = ov.get('name')
                if ov.get('brew_date'):
                    merged['brewDate'] = ov.get('brew_date')
                if ov.get('measured_abv'):
                    merged['measuredAbv'] = ov.get('measured_abv')
                if ov.get('estimated_ibu'):
                    merged['estimatedIbu'] = ov.get('estimated_ibu')
                if ov.get('estimated_color'):
                    merged['estimatedColor'] = ov.get('estimated_color')
                #cnsmm
                #if ov.get('engarrafamento'):
                #    merged['Engarrafamento'] = ov.get('engarrafamento')                    
        except Exception:
            pass

        self.details_text.delete("1.0", tk.END)
        lines = [
            f"ID: {merged.get('_id')}",
            f"Lote: {merged.get('batchNo')}",
            f"Nome: {merged.get('name')}",
            f"Brassagem: {merged.get('brewDate')}",
            f"ABV: {merged.get('measuredAbv')}",
            f"IBU: {merged.get('estimatedIbu')}",
            f"Cor: {merged.get('estimatedColor')}",
            #f"Engarrafamento: {merged.get('engarrafamento')}",
        ]
        #cnsmm
        #if 'Engarrafamento' not in lines:
        if merged.get('bottling_event'):
            lines.append(f"Engarrafamento: {merged['bottling_event'].get('time')}")
        # opcional: mostrar observação se houver override
        try:
            ov = get_batch_override(merged.get('_id'))
            if ov and ov.get('observation'):
                lines.append(f"Observação: {ov.get('observation')}")
        except Exception:
            pass

        self.details_text.insert("1.0", "\n".join(lines))
        # Exibir tags atuais
        self._load_tags_into_list(merged.get('_id'))

    def _salvar_lista(self) -> None:
        if not self._batches:
            messagebox.showinfo("Info", "Liste os lotes primeiro.")
            return

        def work():
            ok = 0
            for b in self._batches:
                payload = {
                    '_id': b.get('_id'),
                    'batchNo': b.get('batchNo'),
                    'brewer': b.get('brewer'),
                    'brewDate': b.get('brewDate'),
                    'name': b.get('recipe_name'),
                }
                try:
                    upsert_batch(payload)
                    ok += 1
                except Exception:
                    pass
            self._set_status(f"{ok} lote(s) salvos no banco.")
            messagebox.showinfo("Sucesso", f"{ok} lote(s) salvos/atualizados no banco.")

        self._run_bg(work)

    def _salvar_detalhes(self) -> None:
        if not self._selected_batch or not self._selected_batch.get('_id'):
            messagebox.showinfo("Info", "Busque os detalhes do lote primeiro.")
            return

        # Captura dados da UI no thread principal
        text = self.details_text.get("1.0", tk.END).strip()
        obs = tk.simpledialog.askstring("Observação", "Deseja incluir alguma observação?")
        batch_id = self._selected_batch['_id']
        selected_batch_copy = dict(self._selected_batch)

        def work():
            try:
                # Salva dados base (DB apena)
                upsert_batch_with_events(selected_batch_copy)
                # Constrói overrides a partir do texto
                overrides = {}
                for line in text.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        k = k.strip().lower()
                        v = v.strip()
                        if k.startswith("nome"):
                            overrides['name'] = v
                        elif k.startswith("brassagem"):
                            overrides['brewDate'] = v
                        elif k.startswith("abv"):
                            overrides['measuredAbv'] = v
                        elif k.startswith("ibu"):
                            overrides['estimatedIbu'] = v
                        elif k.startswith("cor"):
                            overrides['estimatedColor'] = v
                        # Salva overrides
                        #cnsmm                            
                        #elif k.startswith("engarrafamento:"):
                        #    overrides['engarrafamento'] = v
                
                upsert_batch_override(batch_id, overrides, obs)
                def after_save():
                    self._set_status("Edição salva.")
                    self._reload_saved()
                    # Se estiver em modo DB, recarrega a lista automaticamente
                    if self._list_mode == 'db':
                        self._listar_lotes_db()
                    else:
                        try:
                            if messagebox.askyesno("Atualizar lista local?", "Deseja atualizar a lista do banco com as alterações?"):
                                self._listar_lotes_db()
                        except Exception:
                            pass
                    messagebox.showinfo("Sucesso", "Edição/observação salva para este lote.")
                self.after(0, after_save)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Erro", f"Falha ao salvar: {e}"))

        self._run_bg(work)

    def _escolher_template(self) -> None:
        path = filedialog.askopenfilename(
            title="Escolher modelo .docx",
            filetypes=[("Word Document", "*.docx")],
        )
        if not path:
            return
        self._template_path = path
        if messagebox.askyesno("Modelo padrão", "Deseja salvar como modelo padrão?"):
            save_template_as_default(path)
        self._set_status(f"Modelo: {path}")

    def _gerar_etiquetas(self) -> None:
        if not self._selected_batch or not self._selected_batch.get('_id'):
            messagebox.showinfo("Info", "Busque os detalhes do lote primeiro.")
            return
        try:
            qtd = int(self.qtd_var.get() or "1")
        except ValueError:
            messagebox.showerror("Erro", "Quantidade inválida.")
            return

        path = self._template_path or get_template_path_from_settings()
        if not os.path.exists(path):
            messagebox.showerror("Erro", f"Modelo não encontrado: {path}")
            return

        def work():
            try:
                handler = WordEtiquetaHandler(path)
                # Carrega overrides e tags
                ov = get_batch_override(self._selected_batch['_id']) or {}
                tags = {t['tag_key']: t['tag_value'] for t in list_tags(self._selected_batch['_id'])}
                # Mescla overrides nos dados
                dados = dict(self._selected_batch)
                if ov:
                    if ov.get('name'):
                        dados['name'] = ov.get('name')
                    if ov.get('brew_date'):
                        dados['brewDate'] = ov.get('brew_date')
                    if ov.get('measured_abv'):
                        dados['measuredAbv'] = ov.get('measured_abv')
                    if ov.get('estimated_ibu'):
                        dados['estimatedIbu'] = ov.get('estimated_ibu')
                    if ov.get('estimated_color'):
                        dados['estimatedColor'] = ov.get('estimated_color')
                    if ov.get('observation'):
                        tags.setdefault('observacao', ov.get('observation'))

                arquivos = handler.criar_multiplas_paginas(dados, qtd, extra_tags=tags)
                msg = "\n".join(os.path.basename(a) for a in arquivos)
                self.after(0, lambda: (self._set_status("Etiquetas geradas."), messagebox.showinfo("Sucesso", f"Arquivos gerados:\n{msg}")))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Erro", f"Falha ao gerar: {e}"))
          
        #Executa via theading para não travar a UI
        self._set_status("Gerando etiquetas...")
        self._run_bg(work)    
                
                
    def _add_or_update_tag(self) -> None:
        if not self._selected_batch or not self._selected_batch.get('_id'):
            messagebox.showinfo("Info", "Busque os detalhes do lote primeiro.")
            return
        key = (self.tag_key_var.get() or '').strip()
        if not key:
            messagebox.showerror("Erro", "Informe a chave da tag.")
            return
        val = (self.tag_value_var.get() or '').strip()
        try:
            set_tag(self._selected_batch['_id'], key, val)
            self._load_tags_into_list(self._selected_batch['_id'])
            self._set_status("Tag salva.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar tag: {e}")

    def _remove_selected_tag(self) -> None:
        if not self._selected_batch or not self._selected_batch.get('_id'):
            return
        sel = self.tags_list.curselection()
        if not sel:
            return
        line = self.tags_list.get(sel[0])
        if "=" in line:
            key = line.split("=", 1)[0].strip()
            try:
                delete_tag(self._selected_batch['_id'], key)
                self._load_tags_into_list(self._selected_batch['_id'])
                self._set_status("Tag removida.")
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao remover tag: {e}")

    def _load_tags_into_list(self, batch_id: str) -> None:
        self.tags_list.delete(0, tk.END)
        try:
            for t in list_tags(batch_id):
                self.tags_list.insert(tk.END, f"{t['tag_key']} = {t['tag_value']}")
        except Exception:
            pass

    def _reload_saved(self) -> None:
        self.saved_list.delete(0, tk.END)
        try:
            self._saved_rows = list_overridden_batches(200)
            for r in self._saved_rows:
                self.saved_list.insert(tk.END, f"#{r['batch_no']} | {r['name']} | {r['updated_at']}")
        except Exception:
            pass

    def _load_saved_selected(self) -> None:
        sel = self.saved_list.curselection()
        if not sel:
            return
        idx = sel[0]
        self._load_saved_by_index(idx)

    def _load_saved_double_click(self, _evt=None) -> None:
        sel = self.saved_list.curselection()
        if not sel:
            return
        self._load_saved_by_index(sel[0])

    def _load_saved_by_index(self, idx: int) -> None:
        try:
            row = self._saved_rows[idx]
        except Exception:
            return
        b = get_batch_with_overrides(row['id']) or get_batch_by_id(row['id'])
        if not b:
            return
        details = {
            '_id': b.get('id'),
            'batchNo': b.get('batch_no'),
            'name': b.get('name'),
            'brewDate': b.get('brew_date'),
            'measuredAbv': b.get('measured_abv'),
            'estimatedIbu': b.get('estimated_ibu'),
            'estimatedColor': b.get('estimated_color'),
        }
        self._show_details(details)
        self._selected_batch = details

    def _toggle_saved_frame(self, visible: bool) -> None:
        if visible:
            try:
                self.saved_frame.grid()
            except Exception:
                pass
        else:
            try:
                self.saved_frame.grid_remove()
            except Exception:
                pass

    # Settings window
    def _open_settings(self) -> None:
        win = tk.Toplevel(self)
        win.title("Configurações")
        win.grab_set()
        pad = {'padx': 8, 'pady': 6}

        env = read_env()

        ttk.Label(win, text="Pasta padrão dos modelos:").grid(row=0, column=0, sticky="w", **pad)
        template_dir_var = tk.StringVar(value=env.get('TEMPLATE_DIR', ''))
        ttk.Entry(win, textvariable=template_dir_var, width=50).grid(row=0, column=1, sticky="ew", **pad)
        def choose_dir():
            d = filedialog.askdirectory(title='Escolher pasta de modelos')
            if d:
                template_dir_var.set(d)
        ttk.Button(win, text="...", command=choose_dir).grid(row=0, column=2, **pad)

        ttk.Label(win, text="Usuário API Brewfather:").grid(row=1, column=0, sticky="w", **pad)
        user_var = tk.StringVar(value=env.get('BREWFATHER_USER_ID', ''))
        ttk.Entry(win, textvariable=user_var, width=40).grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(win, text="Senha/Chave API Brewfather:").grid(row=2, column=0, sticky="w", **pad)
        key_var = tk.StringVar(value=env.get('BREWFATHER_API_KEY', ''))
        ttk.Entry(win, textvariable=key_var, width=40).grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(win, text="Modo de início:").grid(row=3, column=0, sticky="w", **pad)
        mode_var = tk.StringVar(value=env.get('START_MODE', 'ask'))
        mode_combo = ttk.Combobox(win, textvariable=mode_var, values=['ask', 'cli', 'gui'], state='readonly', width=10)
        mode_combo.grid(row=3, column=1, sticky="w", **pad)

        win.columnconfigure(1, weight=1)

        def save_settings():
            updates = {
                'TEMPLATE_DIR': template_dir_var.get().strip(),
                'BREWFATHER_USER_ID': user_var.get().strip(),
                'BREWFATHER_API_KEY': key_var.get().strip(),
                'START_MODE': mode_var.get().strip().lower(),
            }
            write_env(updates)
            messagebox.showinfo('Configurações', 'Configurações salvas com sucesso.')
            win.destroy()

        ttk.Button(win, text='Salvar', command=save_settings).grid(row=10, column=0, columnspan=3, pady=(10,8))



def run_gui() -> None:
    app = BrewfatherGUI()
    app.mainloop()


