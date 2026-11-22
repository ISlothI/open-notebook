"""Runs the embedding model on the CPU."""

from pathlib import Path

import numpy as np
import onnxruntime
import sentencepiece

from open_notebook.domain.search import Vector

MODEL_DIRECTORY = Path("/opt/model")
# What the model was trained for; longer text would be cut silently.
MAX_TOKENS = 128
BATCH_SIZE = 8


class XlmRobertaTokenizer:
    """SentencePiece with the token numbering of XLM-RoBERTa models.

    The tokenizers library gives the same result but needs about 220 MiB more memory.
    """

    START, PAD, END, UNKNOWN = 0, 1, 2, 3
    OFFSET = 1

    def __init__(self, model_file: Path) -> None:
        self._pieces = sentencepiece.SentencePieceProcessor(model_file=str(model_file))

    def encode(self, text: str) -> list[int]:
        pieces: list[int] = self._pieces.encode(text)[: MAX_TOKENS - 2]
        unknown = self._pieces.unk_id()
        ids = [self.UNKNOWN if piece == unknown else piece + self.OFFSET for piece in pieces]
        return [self.START, *ids, self.END]


class OnnxEmbedder:
    """paraphrase-multilingual-MiniLM-L12-v2 with mean pooling."""

    def __init__(self, threads: int, model_directory: Path = MODEL_DIRECTORY) -> None:
        onnxruntime.disable_telemetry_events()
        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = threads
        # The memory arena would keep the peak usage of the longest batch forever.
        options.enable_cpu_mem_arena = False
        self._session = onnxruntime.InferenceSession(
            model_directory / "model.onnx", options, providers=["CPUExecutionProvider"]
        )
        self._inputs = {item.name for item in self._session.get_inputs()}
        self._tokenizer = XlmRobertaTokenizer(model_directory / "sentencepiece.model")

    def embed(self, texts: list[str]) -> list[Vector]:
        return [
            vector
            for start in range(0, len(texts), BATCH_SIZE)
            for vector in self._embed_batch(texts[start : start + BATCH_SIZE])
        ]

    def _embed_batch(self, texts: list[str]) -> list[Vector]:
        encoded = [self._tokenizer.encode(text) for text in texts]
        length = max(len(ids) for ids in encoded)
        ids = np.full((len(texts), length), XlmRobertaTokenizer.PAD, dtype=np.int64)
        for row, tokens in enumerate(encoded):
            ids[row, : len(tokens)] = tokens
        mask = (ids != XlmRobertaTokenizer.PAD).astype(np.int64)
        inputs = {
            "input_ids": ids,
            "attention_mask": mask,
            "token_type_ids": np.zeros_like(ids),
        }
        hidden = self._session.run(
            None, {name: value for name, value in inputs.items() if name in self._inputs}
        )[0]
        weights = mask[:, :, None].astype(np.float32)
        means = (hidden * weights).sum(axis=1) / weights.sum(axis=1)
        normalised = means / np.linalg.norm(means, axis=1, keepdims=True)
        vectors: list[Vector] = normalised.astype(float).tolist()
        return vectors
