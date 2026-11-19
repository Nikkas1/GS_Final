"""Pedido de ajuda do cidadão (canal front_end do contrato de integração OuviAí)."""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from schemas.comum import TextoCurto


class Categoria(str, Enum):
    saude_auditiva = "saude_auditiva"        # aparelho auditivo, consulta, SUS
    beneficio_bpc = "beneficio_bpc"          # BPC/LOAS, CadÚnico
    direitos_idoso = "direitos_idoso"
    transporte = "transporte"                # passe livre, acessibilidade no transporte
    manutencao_urbana = "manutencao_urbana"  # calçada, buraco, fissura, iluminação
    golpe = "golpe"                          # suspeita de golpe por telefone/mensagem
    outro = "outro"


class Urgencia(str, Enum):
    baixa = "baixa"
    media = "media"
    alta = "alta"


class Status(str, Enum):
    aguardando_confirmacao = "aguardando_confirmacao"
    confirmado = "confirmado"


class PedidoEntrada(BaseModel):
    texto: str = Field(min_length=10, max_length=1000, description="O que está acontecendo, com as palavras do cidadão")
    local: str = Field(default="", max_length=120, description="Bairro ou endereço (opcional)")


class TriagemIA(BaseModel):
    """Saída estruturada que o LLM é obrigado a preencher (tool use + validação Pydantic)."""
    categoria: Categoria
    urgencia: Urgencia = Field(description="alta = risco imediato à pessoa, golpe em andamento ou perigo na via")
    resumo: TextoCurto(200, "Uma frase com o problema")
    orientacao: TextoCurto(400, "O que fazer agora, em linguagem simples, sem jargão")
    encaminhamento: TextoCurto(150, "Órgão ou serviço que resolve (ex.: UBS, CRAS, INSS, SP156)")
    sinais_de_golpe: bool = Field(description="true se o relato tem sinais de golpe (pedem código, senha, PIX, dados)")


class PedidoTriado(BaseModel):
    id: int
    protocolo: str
    criado_em: datetime
    texto_mascarado: str = Field(description="Texto como foi enviado à IA, com CPF/telefone/e-mail mascarados")
    local: str
    triagem: TriagemIA
    emergencia: bool = Field(description="Palavra de emergência detectada por regra, sem depender da IA")
    status: Status


class Confirmacao(BaseModel):
    """Human-in-the-loop: o cidadão confirma ou corrige o que a IA sugeriu."""
    categoria: Categoria
    urgencia: Urgencia
    util: bool | None = Field(default=None, description="A orientação ajudou?")


class PedidoRegistrado(BaseModel):
    id: int
    protocolo: str
    criado_em: datetime
    local: str
    resumo: str
    categoria: Categoria
    urgencia: Urgencia
    categoria_ia: Categoria
    urgencia_ia: Urgencia
    corrigido: bool
    util: bool | None
    status: Status
