import requests
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import sys
import shutil
from dotenv import load_dotenv



def get_base_dir():
    """Retorna a pasta base (compatível com PyInstaller)."""
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', None) or os.path.dirname(sys.executable)
    ###return os.path.dirname(__file__)
    # Em modo de desenvolvimento, retorne a pasta 'src'
    # Navega um nível acima do diretório do arquivo atual
    return os.path.dirname(os.path.dirname(__file__))

def ensure_env_file():
    """Garante que existe um .env na raiz do programa."""
    base_dir = get_base_dir()
    env_path = os.path.join(base_dir, ".env")

    # Se não existir .env, cria a partir do exemplo
    if not os.path.exists(env_path):
        example_path = os.path.join(base_dir, "env.example", "exemplo.env.txt")
        if os.path.exists(example_path):
            shutil.copy(example_path, env_path)
        else:
            # Cria vazio se nem o exemplo existir
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("# Arquivo .env criado automaticamente\n")

    return env_path

class BrewfatherAPI:
    def __init__(self):
        
        # Se não encontrar, tenta carregar da pasta ./_internal
        # útil para empacotamento com PyInstaller
        env_file = ensure_env_file()
        load_dotenv(env_file)  
        #load_dotenv()
        
        self.user_id = os.getenv('BREWFATHER_USER_ID')
        self.api_key = os.getenv('BREWFATHER_API_KEY')
        self.base_url = "https://api.brewfather.app/v2"
        
        if not self.user_id or not self.api_key:
            raise ValueError("Credenciais não encontradas no arquivo .env")

    
    def _get_auth(self) -> tuple:
        """Retorna as credenciais para autenticação básica"""
        return (self.user_id, self.api_key)
    
    def _make_request(self, endpoint: str) -> Optional[Dict]:
        """Faz uma requisição para a API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(url, auth=self._get_auth())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Erro na requisição: {e}")
            return None
    
    def GetBatches(self, limit: int = 1) -> Optional[Dict]:
        """
        Obtém todos os batches em formato JSON
        """
        endpoint = f"/batches?complete=True&order_by_direction=desc&limit={limit}"
        return self._make_request(endpoint)
    
    def listBatches(self, limit: int = 1) -> Optional[List[Dict]]:
        """
        Lista batches com campos específicos
        """
        batches_data = self.GetBatches(limit)
        
        if not batches_data:
            return None
        
        formatted_batches = []
        for batch in batches_data:
            formatted_batch = {
                '_id': batch.get('_id'),
                'brewer': batch.get('brewer'),
                'batchNo': batch.get('batchNo'),
                'brewDate': datetime.fromtimestamp(batch.get('brewDate') / 1000).strftime('%d/%m/%Y') if batch.get('brewDate') else None,             
                'recipe_name': batch.get('recipe', {}).get('name') if batch.get('recipe') else None
            }
            formatted_batches.append(formatted_batch)
        
        return formatted_batches
    
    def GetBatch(self, batch_id: str) -> Optional[Dict]:
        """
        Obtém um batch específico em formato JSON
        """
        endpoint = f"/batches/{batch_id}"
        return self._make_request(endpoint)
    
    def listBatch(self, batch_id: str) -> Optional[Dict]:
        """
        Lista um batch específico com campos específicos
        """
        batch_data = self.GetBatch(batch_id)
        
        if not batch_data:
            return None
        
        
  
        # Processar eventos para encontrar o evento de bottling
        bottling_event = None
        envase_via_notes = None
        envase_via_notes = batch_data.get('notes', [])
        for note in envase_via_notes:
            if note.get('status') == 'Conditioning':
                data_envase_via_notes = note.get('timestamp', None)
                break        
        
        
        events = batch_data.get('events', [])
        for event in events:
            if event.get('eventType') == 'event-batch-bottling-day':
                bottling_event = event
                break
        
        # Converter timestamp para data e hora se existir
        bottling_time = None
        if data_envase_via_notes != None:
            try:
                bottling_time = datetime.fromtimestamp(data_envase_via_notes / 1000)
            except (ValueError, TypeError):
                bottling_time = None
        elif bottling_event and 'time' in bottling_event:
            try:
                bottling_time = datetime.fromtimestamp(bottling_event['time'] / 1000)
            except (ValueError, TypeError):
                bottling_time = None
        
        formatted_batch = {
            '_id': batch_data.get('_id'),
            'batchNo': batch_data.get('batchNo'),
            'brewDate': datetime.fromtimestamp(batch_data.get('brewDate') / 1000).strftime('%d/%m/%Y') if batch_data.get('brewDate') else None,             
            'name': batch_data.get('recipe', {}).get('name') if batch_data.get('recipe') else None,
            'measuredAbv': batch_data.get('measuredAbv'),
            'estimatedIbu': batch_data.get('estimatedIbu'),
            'estimatedColor': batch_data.get('estimatedColor'),           
            'bottling_event': {
            'eventType': 'event-batch-bottling-day' if bottling_event else None,
            'time': bottling_time.strftime('%d/%m/%Y %H:%M:%S') if bottling_time else None,
            'timestamp': bottling_event.get('time') if bottling_event else None
        } if bottling_event else None
        }
        
        return formatted_batch
    
    def get_batch_ids(self) -> Optional[List[str]]:
        """
        Retorna uma lista de IDs dos batches disponíveis
        """
        batches_data = self.GetBatches()
        
        if not batches_data:
            return None
        
        return [batch.get('_id') for batch in batches_data if batch.get('_id')]

# Exemplo de uso da classe
if __name__ == "__main__":
    # Teste da classe
    brewfather = BrewfatherAPI()
    
    # Obter todos os batches
    print("=== LISTANDO BATCHES ===")
    batches = brewfather.listBatches()
    if batches:
        for batch in batches:
            print(batch)
    
    # Obter um batch específico (usando o primeiro ID disponível)
    print("\n=== LISTANDO BATCH ESPECÍFICO ===")
    batch_ids = brewfather.get_batch_ids()
    if batch_ids:
        specific_batch = brewfather.listBatch(batch_ids[0])
        if specific_batch:
            print(specific_batch)