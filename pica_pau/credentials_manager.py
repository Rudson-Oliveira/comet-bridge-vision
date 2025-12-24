"""
Credentials Manager - Gerenciador de credenciais criptografadas
Parte do Agente PicaPau - COMET Bridge Vision

Este módulo gerencia credenciais de forma segura usando criptografia Fernet.
Todas as senhas são armazenadas criptografadas e nunca em texto plano.
"""

import os
import json
import logging
import hashlib
import base64
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logging.warning("[CREDENTIALS] cryptography não instalado. Execute: pip install cryptography")

logger = logging.getLogger("CredentialsManager")


class CredentialsManager:
    """
    Gerenciador seguro de credenciais.
    
    Características:
    - Criptografia Fernet (AES-128-CBC)
    - Derivação de chave com PBKDF2
    - Logs de auditoria LGPD compliant
    - Sem armazenamento de senhas em texto plano
    """
    
    def __init__(self, 
                 credentials_file: str = None,
                 master_password: str = None,
                 auto_create: bool = True):
        """
        Inicializa o gerenciador de credenciais.
        
        Args:
            credentials_file: Caminho para o arquivo de credenciais
            master_password: Senha mestra para criptografia
            auto_create: Se deve criar arquivo automaticamente
        """
        if not CRYPTO_AVAILABLE:
            raise ImportError("cryptography não está instalado. Execute: pip install cryptography")
        
        self.credentials_file = credentials_file or os.path.join(
            os.path.dirname(__file__),
            "credentials.enc"
        )
        
        self.audit_log_file = os.path.join(
            os.path.dirname(__file__),
            "audit_log.json"
        )
        
        # Gerar ou usar senha mestra
        self._master_password = master_password or self._get_or_create_master_key()
        
        # Derivar chave de criptografia
        self._fernet = self._create_fernet()
        
        # Criar arquivo se não existir
        if auto_create and not os.path.exists(self.credentials_file):
            self._create_empty_credentials()
        
        logger.info(f"[CREDENTIALS] Inicializado | Arquivo: {self.credentials_file}")
    
    def _get_or_create_master_key(self) -> str:
        """Obtém ou cria a chave mestra"""
        key_file = os.path.join(os.path.dirname(__file__), ".master_key")
        
        if os.path.exists(key_file):
            with open(key_file, "r") as f:
                return f.read().strip()
        else:
            # Gerar nova chave mestra
            key = Fernet.generate_key().decode()
            
            # Salvar em arquivo protegido
            with open(key_file, "w") as f:
                f.write(key)
            
            # Proteger arquivo (apenas leitura para owner)
            try:
                os.chmod(key_file, 0o600)
            except:
                pass
            
            logger.info("[CREDENTIALS] Nova chave mestra gerada")
            return key
    
    def _create_fernet(self) -> Fernet:
        """Cria instância Fernet com chave derivada"""
        # Usar PBKDF2 para derivar chave da senha mestra
        salt = b"comet_pica_pau_salt_v1"  # Salt fixo para consistência
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(
            kdf.derive(self._master_password.encode())
        )
        
        return Fernet(key)
    
    def _create_empty_credentials(self):
        """Cria arquivo de credenciais vazio"""
        empty_data = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "credentials": {}
        }
        
        self._save_credentials(empty_data)
        logger.info("[CREDENTIALS] Arquivo de credenciais criado")
    
    def _load_credentials(self) -> Dict:
        """Carrega e descriptografa credenciais"""
        if not os.path.exists(self.credentials_file):
            return {"version": "1.0", "credentials": {}}
        
        try:
            with open(self.credentials_file, "rb") as f:
                encrypted_data = f.read()
            
            decrypted_data = self._fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        
        except Exception as e:
            logger.error(f"[CREDENTIALS] Erro ao carregar credenciais: {str(e)}")
            return {"version": "1.0", "credentials": {}, "error": str(e)}
    
    def _save_credentials(self, data: Dict):
        """Criptografa e salva credenciais"""
        try:
            json_data = json.dumps(data, ensure_ascii=False)
            encrypted_data = self._fernet.encrypt(json_data.encode())
            
            with open(self.credentials_file, "wb") as f:
                f.write(encrypted_data)
            
            # Proteger arquivo
            try:
                os.chmod(self.credentials_file, 0o600)
            except:
                pass
            
        except Exception as e:
            logger.error(f"[CREDENTIALS] Erro ao salvar credenciais: {str(e)}")
            raise
    
    def _log_audit(self, action: str, service: str, success: bool, details: str = ""):
        """Registra ação no log de auditoria (LGPD compliant)"""
        try:
            # Carregar log existente
            if os.path.exists(self.audit_log_file):
                with open(self.audit_log_file, "r") as f:
                    audit_log = json.load(f)
            else:
                audit_log = {"entries": []}
            
            # Adicionar entrada (sem dados sensíveis)
            entry = {
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "service": service,
                "success": success,
                "details": details,
                # Hash do serviço para rastreabilidade sem expor dados
                "service_hash": hashlib.sha256(service.encode()).hexdigest()[:16]
            }
            
            audit_log["entries"].append(entry)
            
            # Manter apenas últimas 1000 entradas
            if len(audit_log["entries"]) > 1000:
                audit_log["entries"] = audit_log["entries"][-1000:]
            
            # Salvar
            with open(self.audit_log_file, "w") as f:
                json.dump(audit_log, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            logger.warning(f"[CREDENTIALS] Erro ao registrar auditoria: {str(e)}")
    
    def store_credential(self, 
                        service: str, 
                        username: str, 
                        password: str,
                        metadata: Dict = None) -> bool:
        """
        Armazena uma credencial de forma segura.
        
        Args:
            service: Nome do serviço (ex: "hotmail", "gmail")
            username: Nome de usuário ou email
            password: Senha (será criptografada)
            metadata: Dados adicionais (URL, notas, etc.)
            
        Returns:
            True se armazenado com sucesso
        """
        try:
            data = self._load_credentials()
            
            # Criar entrada de credencial
            credential = {
                "username": username,
                "password": password,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            # Armazenar
            data["credentials"][service] = credential
            self._save_credentials(data)
            
            # Log de auditoria
            self._log_audit("STORE", service, True, "Credencial armazenada")
            
            logger.info(f"[CREDENTIALS] Credencial armazenada para: {service}")
            return True
        
        except Exception as e:
            self._log_audit("STORE", service, False, str(e))
            logger.error(f"[CREDENTIALS] Erro ao armazenar credencial: {str(e)}")
            return False
    
    def get_credential(self, service: str) -> Optional[Dict]:
        """
        Recupera uma credencial.
        
        Args:
            service: Nome do serviço
            
        Returns:
            Dicionário com username, password e metadata, ou None
        """
        try:
            data = self._load_credentials()
            credential = data.get("credentials", {}).get(service)
            
            if credential:
                self._log_audit("ACCESS", service, True, "Credencial acessada")
                logger.info(f"[CREDENTIALS] Credencial acessada para: {service}")
                return credential
            else:
                self._log_audit("ACCESS", service, False, "Credencial não encontrada")
                return None
        
        except Exception as e:
            self._log_audit("ACCESS", service, False, str(e))
            logger.error(f"[CREDENTIALS] Erro ao recuperar credencial: {str(e)}")
            return None
    
    def delete_credential(self, service: str) -> bool:
        """
        Remove uma credencial.
        
        Args:
            service: Nome do serviço
            
        Returns:
            True se removido com sucesso
        """
        try:
            data = self._load_credentials()
            
            if service in data.get("credentials", {}):
                del data["credentials"][service]
                self._save_credentials(data)
                
                self._log_audit("DELETE", service, True, "Credencial removida")
                logger.info(f"[CREDENTIALS] Credencial removida para: {service}")
                return True
            else:
                self._log_audit("DELETE", service, False, "Credencial não encontrada")
                return False
        
        except Exception as e:
            self._log_audit("DELETE", service, False, str(e))
            logger.error(f"[CREDENTIALS] Erro ao remover credencial: {str(e)}")
            return False
    
    def list_services(self) -> List[str]:
        """
        Lista todos os serviços com credenciais armazenadas.
        
        Returns:
            Lista de nomes de serviços
        """
        try:
            data = self._load_credentials()
            services = list(data.get("credentials", {}).keys())
            
            self._log_audit("LIST", "*", True, f"{len(services)} serviços")
            return services
        
        except Exception as e:
            logger.error(f"[CREDENTIALS] Erro ao listar serviços: {str(e)}")
            return []
    
    def update_password(self, service: str, new_password: str) -> bool:
        """
        Atualiza a senha de um serviço.
        
        Args:
            service: Nome do serviço
            new_password: Nova senha
            
        Returns:
            True se atualizado com sucesso
        """
        try:
            data = self._load_credentials()
            
            if service in data.get("credentials", {}):
                data["credentials"][service]["password"] = new_password
                data["credentials"][service]["updated_at"] = datetime.now().isoformat()
                self._save_credentials(data)
                
                self._log_audit("UPDATE", service, True, "Senha atualizada")
                logger.info(f"[CREDENTIALS] Senha atualizada para: {service}")
                return True
            else:
                self._log_audit("UPDATE", service, False, "Serviço não encontrado")
                return False
        
        except Exception as e:
            self._log_audit("UPDATE", service, False, str(e))
            logger.error(f"[CREDENTIALS] Erro ao atualizar senha: {str(e)}")
            return False
    
    def get_credentials_for_command(self, 
                                    entities: Dict,
                                    credential_keys: List[str]) -> Dict:
        """
        Obtém credenciais necessárias para um comando.
        
        Args:
            entities: Entidades extraídas do comando (contém site_name, email, etc.)
            credential_keys: Chaves de credenciais necessárias
            
        Returns:
            Dicionário com credenciais preenchidas
        """
        credentials = {}
        
        # Determinar serviço
        service = entities.get("site_name", "").lower()
        email = entities.get("email", "")
        
        # Tentar encontrar credencial pelo serviço
        if service:
            cred = self.get_credential(service)
            if cred:
                credentials["password"] = cred.get("password")
                credentials["username"] = cred.get("username")
        
        # Tentar encontrar pelo email
        if not credentials.get("password") and email:
            # Procurar credencial que tenha este email
            for svc in self.list_services():
                cred = self.get_credential(svc)
                if cred and cred.get("username") == email:
                    credentials["password"] = cred.get("password")
                    credentials["username"] = cred.get("username")
                    break
        
        # Se senha foi fornecida no comando, usar ela
        if entities.get("has_password") and entities.get("password"):
            credentials["password"] = entities["password"]
            
            # Opcionalmente salvar para uso futuro
            if entities.get("save_credentials") and service:
                self.store_credential(
                    service=service,
                    username=email or entities.get("username", ""),
                    password=entities["password"],
                    metadata={"auto_saved": True, "url": entities.get("site_url", "")}
                )
        
        return credentials
    
    def export_audit_log(self, 
                        start_date: str = None, 
                        end_date: str = None) -> List[Dict]:
        """
        Exporta log de auditoria para compliance LGPD.
        
        Args:
            start_date: Data inicial (ISO format)
            end_date: Data final (ISO format)
            
        Returns:
            Lista de entradas de auditoria
        """
        try:
            if not os.path.exists(self.audit_log_file):
                return []
            
            with open(self.audit_log_file, "r") as f:
                audit_log = json.load(f)
            
            entries = audit_log.get("entries", [])
            
            # Filtrar por data se especificado
            if start_date or end_date:
                filtered = []
                for entry in entries:
                    entry_date = entry.get("timestamp", "")[:10]
                    
                    if start_date and entry_date < start_date:
                        continue
                    if end_date and entry_date > end_date:
                        continue
                    
                    filtered.append(entry)
                
                return filtered
            
            return entries
        
        except Exception as e:
            logger.error(f"[CREDENTIALS] Erro ao exportar auditoria: {str(e)}")
            return []


# Teste standalone
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    manager = CredentialsManager()
    
    # Teste de armazenamento
    manager.store_credential(
        service="test_service",
        username="test@example.com",
        password="test_password_123",
        metadata={"url": "https://example.com"}
    )
    
    # Teste de recuperação
    cred = manager.get_credential("test_service")
    print(f"Credencial recuperada: {cred}")
    
    # Listar serviços
    services = manager.list_services()
    print(f"Serviços: {services}")
    
    # Exportar auditoria
    audit = manager.export_audit_log()
    print(f"Entradas de auditoria: {len(audit)}")
