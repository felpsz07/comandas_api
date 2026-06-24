from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from domain.schemas.FuncionarioSchema import FuncionarioResponse
from domain.schemas.ClienteSchema import ClienteResponse
from domain.schemas.ComandaSchema import ComandaProdutosResponse


# ── Item resumido do dashboard (GET /recebimento/dashboard) ──────────────────
class RecebimentoDashboardItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    comanda: str
    status: int
    cliente: Optional[ClienteResponse] = None
    total: float
    quantidade_produtos: int
    data_hora: datetime


# ── Detalhe de comanda para conferência (GET /recebimento/comandas/detalhe/{ids}) ──
class ComandaDetalheRecebimento(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    comanda: str
    status: int
    cliente: Optional[ClienteResponse] = None
    itens: List[ComandaProdutosResponse] = []
    total: float
    quantidade_produtos: int
    data_hora: datetime


# ── Request de recebimento completo (POST /recebimento/completo) ─────────────
class RecebimentoCompletoRequest(BaseModel):
    comandas_ids: List[int]
    cliente_id: Optional[int] = None
    funcionario_id: int
    desconto_valor: Optional[float] = 0
    acrescimo_valor: Optional[float] = 0

    @field_validator("comandas_ids")
    @classmethod
    def precisa_ter_ao_menos_uma_comanda(cls, v):
        if not v or len(v) == 0:
            raise ValueError("É necessário informar ao menos uma comanda")
        if len(v) != len(set(v)):
            raise ValueError("Lista de comandas não pode conter IDs repetidos")
        return v

    @field_validator("desconto_valor", "acrescimo_valor")
    @classmethod
    def valores_nao_negativos(cls, v):
        if v is not None and v < 0:
            raise ValueError("O valor não pode ser negativo")
        return v


# ── Comanda paga, dentro do response de recebimento completo ─────────────────
class ComandaPagaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    comanda: str
    total: float
    quantidade_produtos: int


# ── Response de recebimento completo ──────────────────────────────────────────
class RecebimentoCompletoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sucesso: bool
    mensagem: str
    recebimento_id: int
    comandas_pagas: List[ComandaPagaResponse]
    subtotal_geral: float
    desconto_total: float
    acrescimo_total: float
    valor_final: float
    cliente: Optional[ClienteResponse] = None
    funcionario: FuncionarioResponse
    data_hora: datetime


# ── Comprovante (GET /recebimento/comprovante/{recebimento_id}) ──────────────

class ComprovanteCabecalho(BaseModel):
    empresa: str = "Comandas do Zé"
    documento: str = "Comprovante de Recebimento"
    recebimento_id: int


class ComprovanteComandaItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    comanda: str
    itens: List[ComandaProdutosResponse] = []
    total: float


class ComprovanteResumoValores(BaseModel):
    subtotal_geral: float
    desconto_total: float
    acrescimo_total: float
    valor_final: float


class ComprovanteRecebimentoInfo(BaseModel):
    id: int
    data_hora: datetime


class ComprovanteRodape(BaseModel):
    mensagem: str = "Obrigado pela preferência! Volte sempre."


class ComprovanteRecebimento(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cabecalho: ComprovanteCabecalho
    cliente: Optional[ClienteResponse] = None
    funcionario: FuncionarioResponse
    comandas: List[ComprovanteComandaItem]
    resumo_valores: ComprovanteResumoValores
    recebimento: ComprovanteRecebimentoInfo
    rodape: ComprovanteRodape
    data_emissao: datetime