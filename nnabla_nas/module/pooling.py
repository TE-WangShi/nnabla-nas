import nnabla.functions as F

from .module import Module


class MaxPool(Module):
    r"""Max pooling layer.
    It pools the maximum values inside the scanning kernel.

    Args:
        kernel(:obj:`tuple` of :obj:`int`): Kernel sizes for each spatial axis.
        stride(:obj:`tuple` of :obj:`int`, optional): Subsampling factors for
            each spatial axis. Defaults to `None`.
        pad(:obj:`tuple` of :obj:`int`, optional): Border padding values for
            each spatial axis. Padding will be added both sides of the
            dimension. Defaults to ``(0,) * len(kernel)``.
        channel_last(bool): If True, the last dimension is considered as
            channel dimension, a.k.a NHWC order. Defaults to ``False``.
    """

    def __init__(self, kernel, stride=None, pad=None, channel_last=False):
        self._kernel = kernel
        self._stride = stride
        self._pad = pad
        self._channel_last = channel_last

    def call(self, input):
        out = F.max_pooling(input, kernel=self._kernel,
                            stride=self._stride, pad=self._pad)
        return out

    def extra_repr(self):
        return (f'kernel={self._kernel}, '
                f'stride={self._stride}, '
                f'pad={self._pad}, '
                f'channel_last={self._channel_last}')


class AvgPool(Module):
    r"""Average pooling layer.
    It pools the averaged values inside the scanning kernel.

    Args:
        kernel(:obj:`tuple` of :obj:`int`): Kernel sizes for each spatial axis.
        stride(:obj:`tuple` of :obj:`int`, optional): Subsampling factors for
            each spatial axis. Defaults to `None`.
        pad(:obj:`tuple` of :obj:`int`, optional): Border padding values for
            each spatial axis. Padding will be added both sides of the
            dimension. Defaults to ``(0,) * len(kernel)``.
        channel_last(bool): If True, the last dimension is considered as
            channel dimension, a.k.a NHWC order. Defaults to ``False``.
    """

    def __init__(self, kernel, stride=None, pad=None, channel_last=False):
        self._kernel = kernel
        self._stride = stride
        self._pad = pad
        self._channel_last = channel_last

    def call(self, input):
        out = F.average_pooling(input, kernel=self._kernel,
                                stride=self._stride, pad=self._pad,
                                channel_last=self._channel_last)
        return out

    def extra_repr(self):
        return (f'kernel={self._kernel}, '
                f'stride={self._stride}, '
                f'pad={self._pad}, '
                f'channel_last={self._channel_last}')


class GlobalAvgPool(Module):
    r"""Global average pooling layer.
    It pools an averaged value from the whole image.
    """

    def call(self, input):
        return F.reshape(F.global_average_pooling(input), shape=(input.shape[0], input.shape[1]))
