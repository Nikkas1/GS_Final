"""Acesso ao modelo de fissuras treinado pelo grupo no Colab (MobileNetV2, .keras),
na disciplina de Visão Computacional. Opcional: sem o arquivo ou sem TensorFlow,
a API responde 503 e o resto do sistema segue funcionando."""
import io
from pathlib import Path


class ModeloIndisponivel(Exception):
    pass


class ModeloFissura:
    def __init__(self, caminho: Path):
        self._caminho = Path(caminho)
        self._modelo = None

    @property
    def disponivel(self) -> bool:
        return self._caminho.exists()

    def _carregar(self):
        if self._modelo is None:
            if not self._caminho.exists():
                raise ModeloIndisponivel(f"modelo não encontrado em {self._caminho}")
            try:
                import tensorflow as tf
            except ImportError as e:
                raise ModeloIndisponivel("tensorflow não instalado") from e
            self._modelo = tf.keras.models.load_model(self._caminho)
        return self._modelo

    def prever(self, imagem_bytes: bytes) -> float:
        """Probabilidade (0 a 1) de a imagem conter fissura."""
        modelo = self._carregar()
        try:
            import numpy as np
            from PIL import Image
        except ImportError as e:
            raise ModeloIndisponivel("dependências de visão não instaladas") from e
        img = Image.open(io.BytesIO(imagem_bytes)).convert("RGB").resize((224, 224))
        x = np.asarray(img, dtype="float32") / 127.5 - 1.0   # mesmo preprocess_input do MobileNetV2
        return float(modelo(x[None], training=False)[0][0])
