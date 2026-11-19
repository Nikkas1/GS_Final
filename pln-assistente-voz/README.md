# CitizenTech Voz — Assistente de Voz Acessível (SUS e CadÚnico)

Assistente de voz em português do Brasil desenvolvido para a disciplina de Processamento de Linguagem Natural (PLN — GS 2027), voltado à inclusão digital de cidadãos idosos e com baixa alfabetização funcional no acesso a informações sobre serviços públicos do SUS e do CadÚnico/CRAS.

## Integrantes
* Alexandre Ferreira — RM 565626
* Carlos Eduardo — RM 555812
* Filipe Melo — RM 564571

## Arquitetura
Fluxo modular desacoplado (`microfone/upload → STT → RAG → LLM → Adaptação para Fala → TTS → interface`):
1. **STT (`STTModule`)**: Transcrição local em português do Brasil com exclusão imediata do áudio (LGPD — retenção zero).
2. **RAG (`RAGModule`)**: Busca semântica com FAISS sobre base estruturada de serviços oficiais do SUS e CadÚnico.
3. **LLM (`LLMModule`)**: Geração de respostas curtas e acessíveis com memória de conversa (4 turnos) e guardrails de escopo/emergência.
4. **Adaptação para Fala (`SpeechAdapter`)**: Limpeza de markdown/emojis e expansão de siglas e números para pronúncia natural.
5. **TTS (`TTSModule`)**: Síntese de voz em português do Brasil com voz sintética padrão (sem clonagem).
6. **Interface (`Gradio`)**: Termo LGPD obrigatório, captura por microfone e upload, exibição simultânea de texto e áudio e telemetria de latência.

## Modelos Utilizados (Versão e Licença)

| Componente | Modelo / Biblioteca | Versão / Variante | Licença |
| :--- | :--- | :--- | :--- |
| **STT** | `faster-whisper` (OpenAI Whisper via CTranslate2) | `small` (principal) e `tiny` (comparativo) | MIT |
| **Embeddings** | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | v2 (384 dims) | Apache 2.0 |
| **Busca Vetorial** | `faiss-cpu` | IndexFlatIP | MIT |
| **LLM** | OpenAI `gpt-4o-mini` | API Chat Completions | Proprietária (OpenAI API Terms) |
| **TTS** | `edge-tts` (Microsoft Edge Neural TTS) | `pt-BR-FranciscaNeural` | LGPL-3.0 (cliente `edge-tts`) |

## Como Executar (Google Colab)
1. Abra o notebook `CitizenTech_PLN_Voz.ipynb` no Google Colab.
2. Execute a célula de instalação de dependências (`faster-whisper`, `jiwer`, `edge-tts`, `gradio`, `faiss-cpu`, `sentence-transformers`, `num2words`, `openai`, `pandas`).
3. Informe sua `OPENAI_API_KEY` quando solicitado via `getpass`.
4. Execute as células em sequência. A interface abrirá em um link público `gradio.live` (abra o link em uma aba do navegador para habilitar o microfone).
5. As células finais reproduzem os testes automatizados (30 perguntas LLM, 10 amostras TTS, 20 áudios STT com `jiwer` e 10 conversas ponta a ponta de 3 turnos) salvando os resultados em `material_teste/`.

## Estrutura do Repositório
* `CitizenTech_PLN_Voz.ipynb` — Notebook completo e executável.
* `requirements.txt` — Dependências do projeto.
* `material_teste/` — Áudios de teste (`audios_stt/` e `tts_amostras/`), gabaritos e planilhas CSV de avaliação.
* `Relatorio_CitizenTech_PLN.pdf` — Relatório técnico completo com métricas, LGPD e análise de viés.
Link do video do youtube
https://youtu.be/Y7p-Rb2cKwg
