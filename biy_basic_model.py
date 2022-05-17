from typing import List, Any, Optional

import torch


class BIYBasicModel(torch.nn.Module):
    def __init__(self, state_vec_len: int, moves: List[Any], enc_size: int = 50, predict_hidden_size: int = 30,
                 device: Optional[torch.device] = None):
        super().__init__()
        self.unit_seq_encoder = torch.nn.LSTM(state_vec_len, enc_size, 1, batch_first=True, device=device)
        self.future_value_predictor = torch.nn.Sequential(
            torch.nn.Linear(2 * enc_size + len(moves), predict_hidden_size, device=device),
            torch.nn.ReLU(),
            torch.nn.Linear(predict_hidden_size, predict_hidden_size, device=device),
            torch.nn.ReLU(),
            torch.nn.Linear(predict_hidden_size, 1, device=device)
        )

    def forward(self, state_seqs: torch.nn.utils.rnn.PackedSequence, action_batch: torch.Tensor):
        _, (final_hidden, final_cell) = self.unit_seq_encoder.forward(state_seqs.float())
        final_hidden, final_cell = torch.transpose(final_hidden, 0, 1), torch.transpose(final_cell, 0, 1)
        predictor_input = torch.concat([final_hidden, final_cell, action_batch.float()], dim=2)
        return torch.squeeze(self.future_value_predictor.forward(predictor_input))
