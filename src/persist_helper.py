import os
import uuid
import pickle
import time
from threading import Lock

class PersistHelper:
    """
    Provides persistent storage management using pickle files.
    Initializes the storage directory, sets up TTL-based cleanup, and exposes methods to persist various types of data.
    """
    def __init__(self, persist_directory, retention_period=None):
        self.persist_directory = persist_directory
        self.retention_period = retention_period  # in seconds
        self.lock = Lock()
        os.makedirs(self.persist_directory, exist_ok=True)
        self._cleanup_expired_files()

    def _cleanup_expired_files(self):
        if not self.retention_period:
            return
        now = time.time()
        for filename in os.listdir(self.persist_directory):
            filepath = os.path.join(self.persist_directory, filename)
            try:
                ctime = os.path.getctime(filepath)
                if now > ctime + self.retention_period:
                    os.remove(filepath)
            except Exception:
                pass

    def persist(self, obj, type_):
        """
        Persists an object to storage based on the specified type.
        Types supported: 'history', 'event', 'message', 'tracking'.
        """
        self._cleanup_expired_files()
        if type_ == "history":
            filename = f"_h_{time.strftime('%Y%m%dT%H%M%S')}"
        elif type_ == "event":
            filename = f"_e_{uuid.uuid1()}"
        elif type_ == "message":
            filename = f"_m_{uuid.uuid1()}"
        elif type_ == "tracking":
            filename = f"_t_{uuid.uuid1()}"
        else:
            raise ValueError("Unsupported storage type")
        filepath = os.path.join(self.persist_directory, filename)
        with self.lock, open(filepath, 'wb') as f:
            pickle.dump(obj, f)

    def remove(self, key):
        """
        Removes an item from storage by key (filename).
        """
        filepath = os.path.join(self.persist_directory, key)
        if os.path.exists(filepath):
            os.remove(filepath)

    def for_each(self, callback):
        """
        Iterates over all keys in storage and executes the provided callback for each key.
        """
        for filename in os.listdir(self.persist_directory):
            filepath = os.path.join(self.persist_directory, filename)
            callback(filename, filepath)
