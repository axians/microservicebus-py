import os, json, time, threading, asyncio
from collections import defaultdict
from datetime import datetime
from typing import Callable, Any, List

class TTLCollection:
    """
    TTLCollection provides a time-to-live collection with periodic persistence and expiration checks.
    Items are grouped, labeled, and can be aggregated or filtered by time and group.
    """
    MAXCOLLECTIONCOUNT = 10000 
    
    def __init__(self, persist_dir: str, persist_file_name: str, ttl: int, check_period: int, persist_period: int):
        self._event_listeners = []
        self.options = {
            'persistDir': persist_dir,
            'persistFileName': persist_file_name,
            'ttl': ttl,
            'checkPeriod': check_period,
            'persistPeriod': persist_period
        }
        self._collection: List[dict] = []
        self.file_name = os.path.join(persist_dir, persist_file_name)
        os.makedirs(persist_dir, exist_ok=True)
        if not os.path.exists(self.file_name):
            with open(self.file_name, 'w', encoding='utf-8') as f:
                f.write('[]')
        self._restore()
        
        print(f"TTLCollection initialized with TTL: {ttl} ms, Check Period: {check_period} s, Persist Period: {persist_period}")

    def add_event_listener(self, listener: callable):
        self._event_listeners.append(listener)

    async def start_async_loops(self):
        asyncio.create_task(self.async_check_loop())
        asyncio.create_task(self.async_persist_loop())

    async def async_check_loop(self):
        while True:
            try:
                self._check()
            except Exception as e:
                print(f"Error in async_check_loop: {e}")

            await asyncio.sleep(self.options['checkPeriod'])

    async def async_persist_loop(self):
        while True:
            try:
                self._persist()
            except Exception as e:
                print(f"Error in async_persist_loop: {e}")
                
            await asyncio.sleep(self.options['persistPeriod'])

    def _restore(self):
        try:
            with open(self.file_name, 'r', encoding='utf-8') as f:
                collection = json.load(f)
                if collection:
                    self._collection = collection + self._collection
        except Exception as e:
            print(f'Unable to deserialize TTL Collection: {e}')

    def _persist(self):
        try:
            print(f'Persisting TTL Collection with {len(self._collection)} items to {self.file_name}')
            with open(self.file_name, 'w', encoding='utf-8') as f:
                json.dump(self._collection, f)
        except Exception as e:
            print(f'Unable to persist TTL Collection: {e}')

    def _check(self):
        print(f"Checking TTLCollection with {len(self._collection)} items")
        
        if len(self._collection) > self.MAXCOLLECTIONCOUNT: 
            del_count = len(self._collection) - self.MAXCOLLECTIONCOUNT
            msg = f'History exceeded max length. Removing {del_count} items'
            print(msg)
            self._collection = self._collection[del_count:]

        first_none_expired = next((i for i, el in enumerate(self._collection) if not self._has_expired(el)), None)
        
        if first_none_expired is not None and first_none_expired > 0:
            msg = f'Removed {first_none_expired} expired items from {self.options["persistFileName"]}'
            print(msg)
            self._collection = self._collection[first_none_expired:]

        print(f"...TTLCollection length: {len(self._collection)} items")

    def _has_expired(self, element: dict) -> bool:
        now = int(time.time() * 1000)
        exprired = element['expire'] < now
        if exprired:
            print(f"Item expired: {element} at {now}")
        return exprired

    def push(self, element: Any, label: str = "", group: str = ""):
        self._collection.append({
            'created': int(time.time() * 1000),
            'label': label if label is not None else "",
            'group': group if group is not None else "",
            'expire': int(time.time() * 1000) + self.options['ttl'] * 1000,
            'val': element
        })  

    def push_unique(self, element: Any, label: str, group: str):
        item = next((i for i in self._collection if i['label'] == label and i['group'] == group), None)
        if item:
            item['created'] = int(time.time() * 1000)
            item['group'] = group
            item['expire'] = int(time.time() * 1000) + self.options['ttl']
            item['val'] = element
        else:
            self.push(element, label, group)

    def get_length(self) -> int:
        return len(self._collection)

    def group_collection(self, unit: str) -> List[dict]:
        grouped = defaultdict(list)
        for item in self._collection:
            dt = self._start_of_unit(item['created'], unit)
            grouped[dt].append(item)
        return [{'dt': dt, 'count': len(arr)} for dt, arr in grouped.items()]

    def filter_collection(self, from_ts: int, to_ts: int, unit: str) -> List[dict]:
        selection = [el for el in self._collection if from_ts <= el['created'] <= to_ts]
        grouped = defaultdict(list)
        for item in selection:
            dt = self._start_of_unit(item['created'], unit)
            grouped[dt].append(item)
        result = []
        for dt, arr in grouped.items():
            label = ''.join([i['label'] + ':' if i['label'] else '' for i in arr])
            result.append({'dt': dt, 'count': len(arr), 'label': label})
        return result

    def filter_by_group(self, group: str) -> List[Any]:
        return [i['val'] for i in self._collection if i['group'] == group]

    def remove_item(self, item: Any):
        self._collection = [m for m in self._collection if m['val'] != item]

    def _start_of_unit(self, timestamp: int, unit: str) -> str:
        dt = datetime.fromtimestamp(timestamp / 1000)
        if unit == 'minute':
            return dt.replace(second=0, microsecond=0).isoformat()
        elif unit == 'hour':
            return dt.replace(minute=0, second=0, microsecond=0).isoformat()
        elif unit == 'day':
            return dt.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        else:
            return dt.isoformat()
