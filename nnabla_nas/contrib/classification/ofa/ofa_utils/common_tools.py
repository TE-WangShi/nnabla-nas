# Copyright (c) 2020 Sony Corporation. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import numpy as np

import nnabla.functions as F


def label_smooth(target, n_classes: int, label_smoothing=0.1):
    """multiplies (1 - label_smoothing) to true label,
       otherwise multiples label_smoothing"""
    soft_target = F.one_hot(target, shape=(n_classes, ))
    soft_target = soft_target * (1 - label_smoothing) + label_smoothing / n_classes
    return soft_target


def cross_entropy_loss_with_soft_target(pred, soft_target):
    """cross entropy loss between pred and soft_target"""
    return F.mean(F.sum(- soft_target * F.log_softmax(pred), axis=1))


def cross_entropy_loss_with_label_smoothing(pred, target, label_smoothing=0.1):
    """cross entropy loss with label smoothing between pred and target"""
    soft_target = label_smooth(target, pred.shape[1], label_smoothing)
    return cross_entropy_loss_with_soft_target(pred, soft_target)


def val2list(val, repeat_time=1):
    """Converts values into list
       (if not list or tuple, repeats 'val' for 'repeat_time')"""
    if isinstance(val, list) or isinstance(val, np.ndarray):
        return val
    elif isinstance(val, tuple):
        return list(val)
    else:
        return [val for _ in range(repeat_time)]


def make_divisible(v, divisor=8, min_val=None):
    """
    This function is taken from the original tf repo.
    It ensures that all layers have a channel number that is divisible by 8
    It can be seen here:
    https://github.com/tensorflow/models/blob/master/research/slim/nets/mobilenet/mobilenet.py
    :param v:
    :param divisor:
    :param min_val:
    :return:
    """
    if min_val is None:
        min_val = divisor
    new_v = max(min_val, int(v + divisor / 2) // divisor * divisor)
    # Make sure that round down does not go down by more than 10%.
    if new_v < 0.9 * v:
        new_v += divisor
    return new_v


def get_same_padding(kernel_size):
    """get padding size that makes input and output size the same"""
    if isinstance(kernel_size, tuple):
        assert len(kernel_size) == 2, 'invalid kernel size: %s' % kernel_size
        p1 = get_same_padding(kernel_size[0])
        p2 = get_same_padding(kernel_size[1])
        return p1, p2
    assert isinstance(kernel_size, int), 'kernel size should be either `int` or `tuple`'
    assert kernel_size % 2 > 0, 'kernel size should be odd number'
    return kernel_size // 2


def sub_filter_start_end(kernel_size, sub_kernel_size):
    """ returns start and end point of the sub_filter """
    center = kernel_size // 2
    dev = sub_kernel_size // 2
    start, end = center - dev, center + dev + 1
    assert end - start == sub_kernel_size
    return start, end


def min_divisible_value(n1, v1):
    """ make sure v1 is divisible by n1, otherwise decrease v1 """
    if v1 >= n1:
        return n1
    while n1 % v1 != 0:
        v1 -= 1
    return v1
