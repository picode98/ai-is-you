from typing import Dict, Any

import torch


def int_tensor_hash(tensor: torch.Tensor):
    return torch.sum(torch.mul(torch.reshape(tensor, (1, -1)), torch.arange(1, torch.numel(tensor) + 1))).item() + \
        torch.numel(tensor)


class IntTensorMap(Dict):
    def __init__(self):
        super().__init__()

    def get(self, __key: torch.Tensor):
        submap = super().get(int_tensor_hash(__key))

        if submap is None:
            return None
        else:
            eq_tensor = next((ts for ts in submap.keys() if torch.all(ts == __key)), None)
            if eq_tensor is None:
                return None
            else:
                return submap[eq_tensor]

    def __getitem__(self, item):
        get_val = self.get(item)

        if get_val is None:
            raise KeyError(item)
        else:
            return get_val

    def __setitem__(self, key: torch.Tensor, value: Any):
        hash_val = int_tensor_hash(key)
        submap = super().get(hash_val)

        if submap is None:
            super().__setitem__(hash_val, {key: value})
        else:
            eq_tensor = next((ts for ts in submap.keys() if torch.all(ts == key)), None)
            submap[key if eq_tensor is None else eq_tensor] = value
