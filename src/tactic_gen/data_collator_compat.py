"""
Compatibility shim for DataCollatorForCompletionOnlyLM removed from trl >= 0.12.
"""
from __future__ import annotations
from typing import Any, Optional, Union

import torch
from transformers import DataCollatorForLanguageModeling, PreTrainedTokenizerBase


class DataCollatorForCompletionOnlyLM(DataCollatorForLanguageModeling):
    """Masks all labels before the response_template so loss is computed on completions only."""

    def __init__(
        self,
        response_template: Union[str, list[int]],
        instruction_template: Optional[Union[str, list[int]]] = None,
        *args: Any,
        mlm: bool = False,
        ignore_index: int = -100,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, mlm=mlm, **kwargs)
        self.ignore_index = ignore_index

        if isinstance(response_template, str):
            self.response_template = response_template
            self.response_token_ids = self.tokenizer.encode(
                response_template, add_special_tokens=False
            )
        else:
            self.response_template = None
            self.response_token_ids = response_template

        if instruction_template is not None:
            if isinstance(instruction_template, str):
                self.instruction_template = instruction_template
                self.instruction_token_ids = self.tokenizer.encode(
                    instruction_template, add_special_tokens=False
                )
            else:
                self.instruction_template = None
                self.instruction_token_ids = instruction_template
        else:
            self.instruction_template = None
            self.instruction_token_ids = None

    def torch_call(self, examples: list[Any]) -> dict[str, Any]:
        batch = super().torch_call(examples)
        resp_ids = self.response_token_ids
        n = len(resp_ids)

        for i in range(batch["input_ids"].shape[0]):
            input_ids = batch["input_ids"][i].tolist()
            # Find last occurrence of response_template tokens
            start_idx = None
            for j in range(len(input_ids) - n + 1):
                if input_ids[j : j + n] == resp_ids:
                    start_idx = j
            if start_idx is None:
                # Template not found; mask entire sequence
                batch["labels"][i] = torch.full_like(
                    batch["labels"][i], self.ignore_index
                )
            else:
                # Mask everything up to and including the template
                batch["labels"][i, : start_idx + n] = self.ignore_index

        return batch
