import numpy as np

from src.facelock.auth.storage import FileStore


def test_save_get_list_remove(tmp_path):
    store = FileStore(tmp_path)

    encoding = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    key = store.save(encoding, "alice")

    assert key
    assert key in store.list()

    item = store.get(key)
    assert item is not None
    assert item["label"] == "alice"
    assert item["created_at"] is not None
    np.testing.assert_array_equal(item["encoding"], encoding)

    assert store.remove(key) is True
    assert store.get(key) is None
    assert key not in store.list()


def test_store_persists_across_reloads(tmp_path):
    encoding = np.array([1.0, 2.0, 3.0], dtype=np.float32)

    store1 = FileStore(tmp_path)
    key = store1.save(encoding, "bob")

    store2 = FileStore(tmp_path)
    item = store2.get(key)

    assert item is not None
    assert item["label"] == "bob"
    np.testing.assert_array_equal(item["encoding"], encoding)


def test_remove_missing_key_returns_false(tmp_path):
    store = FileStore(tmp_path)

    assert store.remove("missing") is False