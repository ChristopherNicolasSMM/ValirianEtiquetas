import sys
import os

# Adiciona o diretório src ao path do Python
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from api.brewfather_api import BrewfatherAPI
from word_handler import WordEtiquetaHandler
from db.sqlite_db import init_schema, upsert_batch, upsert_batch_with_events
from settings import get_template_path_from_settings, prompt_for_template_path, save_template_as_default, get_start_mode
from gui.app import run_gui

def clear_screen():
    """Limpa a tela do terminal"""
    os.system('cls' if os.name == 'nt' else 'clear')

def display_batches_list(batches):
    """Exibe a lista de batches de forma formatada"""
    print("\n" + "="*80)
    print("LISTA DE LOTES DISPONÍVEIS")
    print("="*80)
    
    for i, batch in enumerate(batches, 1):
        print(f"{i}. Lote #{batch.get('batchNo', 'N/A')}")
        print(f"   Data: {batch.get('brewDate', 'N/A')}")
        print(f"   Receita: {batch.get('recipe_name', 'N/A')}")
        print(f"   Brewer: {batch.get('brewer', 'N/A')}")
        print(f"   ID: {batch.get('_id')}")
        print("-" * 80)

def display_batch_details(batch_details):
    """Exibe os detalhes completos de um batch"""
    print("\n" + "="*80)
    print("DETALHES COMPLETOS DO LOTE")
    print("="*80)
    
    print(f"Identificador Único: {batch_details['_id']}")
    print(f"Número do Lote: {batch_details['batchNo']}")
    print(f"Nome: {batch_details['name']}")
    print(f"Data de Brassagem: {batch_details['brewDate']}")
    print(f"ABV Medido: {batch_details['measuredAbv']}%")
    print(f"IBU Estimado: {batch_details['estimatedIbu']}")
    print(f"Cor Estimada: {batch_details['estimatedColor']} EBC")
    
    if batch_details.get('bottling_event'):
        print(f"Data de Engarrafamento: {batch_details['bottling_event']['time']}")
    else:
        print("Data de Engarrafamento: Não encontrada")
    
    print("="*80)

def gerar_etiquetas(batch_details):
    """Função para gerar etiquetas para um lote"""
    try:
        # Perguntar quantidade de etiquetas
        quantidade = input("\n🏷️  Quantas etiquetas deseja imprimir? ")
        quantidade = int(quantidade)
        
        if quantidade <= 0:
            print("❌ Quantidade deve ser maior que zero.")
            return
        
        # Selecionar template (padrão ou customizado) e opcionalmente salvar como novo padrão
        template_path, salvar_como_padrao = prompt_for_template_path()
        if salvar_como_padrao:
            save_template_as_default(template_path)

        if not os.path.exists(template_path):
            print(f"❌ Modelo não encontrado em: {template_path}")
            return

        # Inicializar handler de Word
        word_handler = WordEtiquetaHandler(template_path)
        
        print("🖨️  Gerando etiquetas...")
        
        # Gerar etiquetas
        arquivos_gerados = word_handler.criar_multiplas_paginas(batch_details, quantidade)
        
        print(f"✅ Etiquetas geradas com sucesso!")
        for arquivo in arquivos_gerados:
            print(f"📄 Arquivo: {os.path.basename(arquivo)}")
        
        input("\nPressione Enter para continuar...")
        
    except ValueError:
        print("❌ Por favor, digite um número válido.")
    except Exception as e:
        print(f"❌ Erro ao gerar etiquetas: {e}")

def salvar_lotes_no_banco(batches):
    """Salva/atualiza lotes (visão de lista) no SQLite."""
    salvos = 0
    for b in batches:
        # Converte estrutura da lista para o formato esperado pelo upsert
        payload = {
            '_id': b.get('_id'),
            'batchNo': b.get('batchNo'),
            'brewer': b.get('brewer'),
            'brewDate': b.get('brewDate'),
            'name': b.get('recipe_name'),
            # Campos não disponíveis na listagem ficam como None
            'measuredAbv': None,
            'estimatedIbu': None,
            'estimatedColor': None,
            'recipe': None,
        }
        try:
            upsert_batch(payload)
            salvos += 1
        except Exception as e:
            print(f"⚠️  Falha ao salvar lote {b.get('_id')}: {e}")
    print(f"💾 {salvos} lote(s) salvos/atualizados no banco.")

def salvar_detalhes_no_banco(batch_details):
    """Salva/atualiza um lote detalhado (inclui evento de engarrafamento)."""
    try:
        upsert_batch_with_events(batch_details)
        print("💾 Lote salvo/atualizado no banco com eventos (se houver).")
    except Exception as e:
        print(f"⚠️  Falha ao salvar detalhes do lote: {e}")

def main():
    # Seletor de modo com .env
    start_mode = get_start_mode()
    modo = None
    if start_mode == 'gui':
        modo = '2'
    elif start_mode == 'cli':
        modo = '1'
    else:
        print("Selecione o modo de execução:")
        print("1 - Terminal (CLI)")
        print("2 - Interface Gráfica (GUI)")
        modo = input("Escolha (Enter = 1): ").strip()

    if modo == '2':
        try:
            init_schema()
        except Exception:
            pass
        return run_gui()

    # Inicializar o schema do banco
    try:
        init_schema()
    except Exception as e:
        print(f"⚠️  Não foi possível inicializar o banco: {e}")

    # Inicializar a API
    try:
        brewfather = BrewfatherAPI()
        print("✅ Conexão com Brewfather API estabelecida com sucesso!")
    except ValueError as e:
        print(f"❌ Erro: {e}")
        print("ℹ️  Certifique-se de que o arquivo .env contém BREWFATHER_USER_ID e BREWFATHER_API_KEY")
        return
    
    # Verificar template padrão e avisar se ausente, mas não bloquear execução
    default_template_path = get_template_path_from_settings()
    if not os.path.exists(default_template_path):
        print("⚠️  Modelo padrão não encontrado.")
        print(f"ℹ️  Esperado em: {default_template_path}")
        print("ℹ️  Você poderá escolher outro caminho ao gerar etiquetas.")
    
    while True:
        clear_screen()
        print("🍺 BREWFATHER BATCH MANAGER & ETIQUETAS")
        print("="*50)
        
        try:
            # Perguntar quantos lotes trazer
            limit = input("Quantos lotes você deseja listar? (Enter para 1): ").strip()
            limit = int(limit) if limit else 1
            
            if limit <= 0:
                print("❌ Por favor, digite um número positivo.")
                input("Pressione Enter para continuar...")
                continue
                
        except ValueError:
            print("❌ Por favor, digite um número válido.")
            input("Pressione Enter para continuar...")
            continue
        
        # Obter lotes
        print(f"\n📋 Buscando {limit} lote(s)...")
        batches = brewfather.listBatches(limit)
        
        if not batches:
            print("❌ Nenhum lote encontrado ou erro na requisição.")
            input("Pressione Enter para tentar novamente...")
            continue
        
        # Mostrar lista de lotes
        display_batches_list(batches)

        # Oferecer salvar a lista no banco
        try:
            salvar_lista = input("\n💾 Deseja salvar estes lotes no banco? (s/n): ").strip().lower()
            if salvar_lista in ['s', 'sim', 'y', 'yes']:
                salvar_lotes_no_banco(batches)
        except Exception as e:
            print(f"⚠️  Erro ao salvar lotes: {e}")
        
        # Perguntar qual lote ver detalhes
        try:
            choice = input("\n🔢 Digite o número do lote para ver detalhes (0 para voltar): ").strip()
            
            if choice == '0':
                continue
                
            choice_index = int(choice) - 1
            
            if 0 <= choice_index < len(batches):
                selected_batch = batches[choice_index]
                print(f"\n🔍 Buscando detalhes do lote #{selected_batch['batchNo']}...")
                
                # Obter detalhes do lote selecionado
                batch_details = brewfather.listBatch(selected_batch['_id'])
                
                if batch_details:
                    display_batch_details(batch_details)

                    # Oferecer salvar detalhes no banco
                    try:
                        salvar_detalhe = input("\n💾 Deseja salvar este lote no banco? (s/n): ").strip().lower()
                        if salvar_detalhe in ['s', 'sim', 'y', 'yes']:
                            salvar_detalhes_no_banco(batch_details)
                    except Exception as e:
                        print(f"⚠️  Erro ao salvar detalhes do lote: {e}")
                    
                    # Perguntar se quer gerar etiquetas
                    gerar_etiq = input("\n🏷️  Deseja gerar etiquetas para este lote? (s/n): ").strip().lower()
                    if gerar_etiq in ['s', 'sim', 'y', 'yes']:
                        
                        gerar_etiquetas(batch_details)
                        
                else:
                    print("❌ Erro ao buscar detalhes do lote.")
                    
            else:
                print("❌ Número inválido. Escolha um número da lista.")
                
        except ValueError:
            print("❌ Por favor, digite um número válido.")
        
        # Perguntar se quer continuar
        continuar = input("\n🔄 Deseja fazer outra consulta? (s/n): ").strip().lower()
        if continuar not in ['s', 'sim', 'y', 'yes']:
            print("👋 Até logo!")
            break
        
        input("Pressione Enter para continuar...")

if __name__ == "__main__":
    main()