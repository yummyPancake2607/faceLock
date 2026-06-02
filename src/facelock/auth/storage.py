import typing as t
import json
import time
import uuid
from pathlib import Path
import numpy as np

StoreRecord = t.Dict[str, t.Any]

class FileStore:
    """
    File-backed store:
    - metadata: <base>/index.json (maps id -> {label, file, created_at})
    - encodings: <base>/encodings/<id>.npy
    """

    def __init__(self, base_dir: t.Union[str, Path] = "face_store"):
        self.base = Path(base_dir)
        self.meta_file = self.base / "index.json"
        self.enc_dir = self.base / "encodings"
        self.base.mkdir(parents=True, exist_ok=True)
        self.enc_dir.mkdir(parents=True, exist_ok=True)
        self._meta: t.Dict[str, StoreRecord] = {}
        self._load_meta()

    def _load_meta(self) -> None:
        if self.meta_file.exists():
            try:
                with self.meta_file.open("r", encoding="utf-8") as fh:
                    self._meta = json.load(fh)
            except Exception:
                self._meta = {}
        else:
            self._meta = {}

    def _save_meta(self) -> None:
        with self.meta_file.open("w", encoding="utf-8") as fh:
            json.dump(self._meta, fh, indent=2, ensure_ascii=False)

    def _encoding_path(self, key: str) -> Path:
        return self.enc_dir / f"{key}.npy"

    def save(self, encoding: np.ndarray, label: str) -> str:
        """
        Save `encoding` (numpy array) with `label`. Returns generated key.
        """
        key = uuid.uuid4().hex
        enc_path = self._encoding_path(key)
        np.save(str(enc_path), encoding)
        self._meta[key] = {"label": label, "file": enc_path.name, "created_at": time.time()}
        self._save_meta()
        return key

    def _load_encoding(self, key: str) -> t.Optional[np.ndarray]:
        rec = self._meta.get(key)
        if not rec:
            return None
        p = self.enc_dir / rec["file"]
        if not p.exists():
            return None
        try:
            return np.load(str(p))
        except Exception:
            return None

    def list(self) -> t.Dict[str, dict]:
        """
        Return mapping key -> {"encoding": np.ndarray, "label": str, "created_at": float}
        Loads encodings into memory.
        """
        out: t.Dict[str, dict] = {}
        for k, rec in self._meta.items():
            enc = self._load_encoding(k)
            out[k] = {"encoding": enc, "label": rec.get("label"), "created_at": rec.get("created_at")}
        return out

    def get(self, key: str) -> t.Optional[dict]:
        rec = self._meta.get(key)
        if not rec:
            return None
        enc = self._load_encoding(key)
        return {"encoding": enc, "label": rec.get("label"), "created_at": rec.get("created_at")}

    def remove(self, key: str) -> bool:
        rec = self._meta.pop(key, None)
        if rec is None:
            return False
        # delete file if present
        p = self.enc_dir / rec.get("file", "")
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass
        self._save_meta()
        return True