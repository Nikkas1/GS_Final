from conftest import LLMFalso
from core.deps import get_llm
from providers.llm import ProvedorIndisponivel

PEDIDO = {"texto": "Ligaram dizendo que são do INSS e pediram o código do celular", "local": "Itaquera"}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/health/ready").json()["llm"] == "simulado"


def test_fluxo_completo_com_human_in_the_loop(client):
    r = client.post("/v1/pedidos", json=PEDIDO)
    assert r.status_code == 201
    p = r.json()
    assert p["protocolo"].startswith("OA-") and p["status"] == "aguardando_confirmacao"
    assert p["triagem"]["categoria"] == "golpe" and "X-Tempo-ms" in r.headers

    assert client.get("/v1/pedidos").json() == []   # só aparece depois de confirmado

    c = client.post(f"/v1/pedidos/{p['id']}/confirmacao", json={"categoria": "golpe", "urgencia": "media", "util": True})
    assert c.status_code == 200 and c.json()["corrigido"] is True

    assert len(client.get("/v1/pedidos", params={"categoria": "golpe"}).json()) == 1
    assert client.get("/v1/pedidos", params={"categoria": "transporte"}).json() == []
    assert client.get("/v1/painel/resumo").json()["taxa_correcao"] == 1.0


def test_validacao_com_mensagem_simples(client):
    r = client.post("/v1/pedidos", json={"texto": "curto"})
    assert r.status_code == 422 and r.json()["campos"] == ["texto"]


def test_confirmar_pedido_inexistente(client):
    assert client.post("/v1/pedidos/999/confirmacao", json={"categoria": "outro", "urgencia": "baixa"}).status_code == 404


def test_ia_fora_do_formato_vira_502_sem_detalhe_tecnico(client):
    client.app_ref.dependency_overrides[get_llm] = lambda: LLMFalso({"lixo": 1}, {"lixo": 2})
    r = client.post("/v1/pedidos", json=PEDIDO)
    assert r.status_code == 502 and "Não foi possível" in r.json()["detail"]


def test_sem_chave_vira_503(client):
    client.app_ref.dependency_overrides[get_llm] = lambda: LLMFalso(ProvedorIndisponivel("sem chave"))
    assert client.post("/v1/pedidos", json=PEDIDO).status_code == 503


def test_semana_demo_carregada_e_filtros(client):
    todos = client.get("/v1/eventos", params={"limite": 1000}).json()
    assert len(todos) == 109
    campainhas = client.get("/v1/eventos", params={"classe": "campainha", "confianca_min": 0.6}).json()
    assert campainhas and all(e["classe"] == "campainha" and e["confianca"] >= 0.6 for e in campainhas)


def test_receber_evento_e_feedback(client):
    r = client.post("/v1/eventos", json=[{"momento": "2026-11-20T03:10:00", "classe": "batida_porta",
                                          "confianca": 0.88, "dispositivo": "celular-teste"}])
    assert r.status_code == 201
    ev = r.json()[0]
    assert ev["alerta"] == "alta"
    assert client.patch(f"/v1/eventos/{ev['id']}/feedback", json={"acertou": True}).json()["acertou"] is True
    assert client.patch("/v1/eventos/99999/feedback", json={"acertou": True}).status_code == 404


def test_evento_fora_do_contrato(client):
    r = client.post("/v1/eventos", json=[{"momento": "2026-11-20T03:10:00", "classe": "latido",
                                          "confianca": 88, "dispositivo": "Dona Lúcia (11) 9999"}])
    assert r.status_code == 422


def test_cors_restrito(client):
    pre = {"Access-Control-Request-Method": "POST"}
    assert client.options("/v1/pedidos", headers={**pre, "Origin": "http://localhost:8501"}).status_code == 200
    assert client.options("/v1/pedidos", headers={**pre, "Origin": "http://site-qualquer.com"}).status_code == 400


def test_visao_valida_tipo_e_responde_503_sem_modelo(client):
    assert client.post("/v1/visao/classificar", files={"arquivo": ("a.txt", b"oi", "text/plain")}).status_code == 415
    assert client.post("/v1/visao/classificar", files={"arquivo": ("a.jpg", b"\xff\xd8\xff", "image/jpeg")}).status_code == 503
