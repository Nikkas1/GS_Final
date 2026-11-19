"""Único ponto de acesso ao LLM. Trocar de provedor = mexer só aqui.

A saída estruturada usa o recurso nativo da API (output_config.format com
json_schema): a resposta do modelo é obrigada a seguir o JSON Schema gerado
pelo próprio modelo Pydantic. Assim não dependemos de regex para achar um JSON
no meio do texto, e o que volta ainda é validado pelo Pydantic no pipeline.
"""
import json
from typing import Protocol

from pydantic import BaseModel


class ErroProvedor(Exception):
    """Falha ao falar com o provedor (rede, timeout, chave)."""


class ProvedorIndisponivel(ErroProvedor):
    """Sem chave configurada ou credencial recusada."""


class TempoEsgotado(ErroProvedor):
    pass


# palavras-chave do JSON Schema que a saída estruturada da API não aceita;
# os limites continuam valendo, porque o Pydantic valida (e corta) depois
NAO_SUPORTADAS = {"title", "minLength", "maxLength", "default", "examples"}


def schema_para_api(modelo: type[BaseModel]) -> dict:
    """JSON Schema do Pydantic com os $ref resolvidos e no formato aceito pela API."""
    schema = modelo.model_json_schema()
    defs = schema.pop("$defs", {})

    def resolver(no):
        if isinstance(no, dict):
            if "$ref" in no:
                extra = {k: v for k, v in no.items() if k != "$ref"}
                return {**resolver(defs[no["$ref"].split("/")[-1]]), **resolver(extra)}
            limpo = {k: resolver(v) for k, v in no.items() if k not in NAO_SUPORTADAS}
            if limpo.get("type") == "object":
                limpo["additionalProperties"] = False
                limpo["required"] = list(limpo.get("properties", {}))
            return limpo
        if isinstance(no, list):
            return [resolver(v) for v in no]
        return no

    return resolver(schema)


class LLM(Protocol):
    async def estruturar(self, system: str, usuario: str, schema: type[BaseModel]) -> dict: ...


class AnthropicLLM:
    def __init__(self, api_key: str, modelo: str, timeout_s: float, http_client=None):
        from anthropic import AsyncAnthropic
        self._cliente = (AsyncAnthropic(api_key=api_key, timeout=timeout_s, max_retries=1, http_client=http_client)
                         if api_key else None)
        self._modelo = modelo

    async def estruturar(self, system: str, usuario: str, schema: type[BaseModel]) -> dict:
        import anthropic

        if self._cliente is None:
            raise ProvedorIndisponivel("ANTHROPIC_API_KEY não configurada")
        try:
            resp = await self._cliente.messages.create(
                model=self._modelo,
                max_tokens=1024,
                system=system,
                output_config={"format": {"type": "json_schema", "schema": schema_para_api(schema)}},
                messages=[{"role": "user", "content": usuario}],
            )
        except anthropic.APITimeoutError as e:
            raise TempoEsgotado(str(e)) from e
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as e:
            raise ProvedorIndisponivel(str(e)) from e
        except anthropic.APIError as e:
            raise ErroProvedor(str(e)) from e

        texto = "".join(b.text for b in resp.content if b.type == "text")
        try:
            return json.loads(texto)
        except json.JSONDecodeError as e:
            raise ErroProvedor("o modelo não devolveu JSON") from e

    async def fechar(self):
        if self._cliente is not None:
            await self._cliente.close()


class LLMSimulado:
    """Regras simples por palavra-chave. Serve para os testes e para demonstrar
    a interface sem chave de API (LLM_PROVIDER=simulado). Não é IA."""

    REGRAS = [
        (("código", "codigo", "senha", "pix", "ligaram", "se passando"), "golpe", "alta",
         "Não passe código, senha nem faça PIX. Desligue e procure o órgão pelo canal oficial.", "Canal oficial do órgão (gov.br, 135 do INSS)"),
        (("aparelho", "auditivo", "escutar", "ouvir", "otorrino"), "saude_auditiva", "media",
         "Procure a UBS com documento com foto e cartão do SUS e peça encaminhamento para a saúde auditiva.", "UBS do bairro"),
        (("bpc", "loas", "cadastro único", "cadunico", "benefício", "beneficio"), "beneficio_bpc", "media",
         "Atualize o Cadastro Único no CRAS e depois peça o BPC pelo Meu INSS ou pelo 135.", "CRAS e INSS"),
        (("buraco", "calçada", "calcada", "fissura", "rachadura", "poste", "iluminação"), "manutencao_urbana", "media",
         "Evite o local e registre no SP156 pelo app ou site, que não precisam de ligação.", "SP156 / Subprefeitura"),
        (("ônibus", "onibus", "metrô", "metro", "bilhete", "passe"), "transporte", "baixa",
         "Peça o bilhete especial da pessoa com deficiência na SPTrans com o laudo médico.", "SPTrans"),
    ]

    async def estruturar(self, system: str, usuario: str, schema: type[BaseModel]) -> dict:
        texto = usuario.lower()
        for palavras, cat, urg, orient, enc in self.REGRAS:
            if any(p in texto for p in palavras):
                break
        else:
            cat, urg, orient, enc = "outro", "baixa", "Seu pedido foi registrado. Um atendente vai orientar você.", "Atendimento da prefeitura"
        return {
            "categoria": cat, "urgencia": urg,
            "resumo": usuario.split("Pedido:", 1)[-1].strip()[:180] or "Pedido sem descrição",
            "orientacao": orient, "encaminhamento": enc,
            "sinais_de_golpe": cat == "golpe",
        }

    async def fechar(self):
        pass


def criar_llm(provider: str, api_key: str, modelo: str, timeout_s: float):
    if provider == "simulado":
        return LLMSimulado()
    return AnthropicLLM(api_key, modelo, timeout_s)
