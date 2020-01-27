import nnabla.functions as F

from .module import Module


class Merging(Module):
    r"""Merging layer.
    Merges a list of nnabla variables.

    Args:
        mode (str): The merging mode ('concat', 'add').
        axis (int, optional): The axis for merging when 'concat' is used.
            Defaults to 1.

    """

    def __init__(self, mode, axis=1):
        super().__init__()
        if mode not in ('concat', 'add'):
            raise KeyError(f'{mode} is not supported.')
        self._mode = mode
        self._axis = axis

    def call(self, *input):
        if self._mode == 'concat' and len(input) > 1:
            input = F.concatenate(*input, axis=self._axis)
        elif self._mode == 'add':
            input = sum(input)
        return input

    def __extra_repr__(self):
        return f'mode={self._mode}, axis={self._axis}'