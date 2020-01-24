import numpy as np
import nnabla as nn
from collections import OrderedDict
from nnabla.initializer import ConstantInitializer
import nnabla_nas.module.static_module as smo
from nnabla_nas.module.parameter import Parameter

#---------------------Definition of the candidate layers for the zoph search space-------------------------------
class SepConv(smo.StaticGraph):
    def __init__(self, name, parent, channels, kernel, dilation):
        self._channels = channels
        self._kernel = kernel
        self._dilation = dilation
        if dilation is None:
            self._pad = tuple([ki//2 for ki in self._kernel])
        else:
            self._pad = tuple([(ki//2)*di for ki,di in zip(self._kernel, self._dilation)])
        smo.StaticGraph.__init__(self, name, parent)

    def _generate_graph(self, inputs):
        self.add_module(smo.StaticDwConcatenate(name=self.name+'/input_concat', parent=inputs))
        self.add_module(smo.StaticConv(name=self.name+'/input_conv', parent=[self._modules[-1]], in_channels=self._modules[-1].shape[1], out_channels=self._channels, kernel=(1,1)))
        self.add_module(smo.StaticSepConv(name=self.name+'/conv_1', parent=[self._modules[-1]], in_channels=self._modules[-1].shape[1], out_channels=self._channels, kernel=self._kernel, pad=self._pad, dilation=self._dilation))
        self.add_module(smo.StaticSepConv(name=self.name+'/conv_2', parent=[self._modules[-1]], in_channels=self._modules[-1].shape[1], out_channels=self._channels, kernel=self._kernel, pad=self._pad, dilation=self._dilation))
        self.add_module(smo.StaticBatchNormalization(name=self.name+'/bn', parent=[self._modules[-1]],
                                                     n_features=self._modules[-1].shape[1], n_dims=4))
        self.add_module(smo.StaticReLU(name=self.name+'/relu', parent=[self._modules[-1]]))
        return self._modules[-1]

class SepConv3x3(SepConv):
    def __init__(self, name, parent, channels):
        SepConv.__init__(self, name, parent, channels, (3,3), None)

class SepConv5x5(SepConv):
    def __init__(self, name, parent, channels):
        SepConv.__init__(self, name, parent, channels, (5,5), None)

class DilSepConv3x3(SepConv):
    def __init__(self, name, parent, channels):
        SepConv.__init__(self, name, parent, channels, (3,3), (2,2))

class DilSepConv5x5(SepConv):
    def __init__(self, name, parent, channels):
        SepConv.__init__(self, name, parent, channels, (5,5), (2,2))

class MaxPool3x3(smo.StaticGraph):
    def _generate_graph(self, inputs):
        self.add_module(smo.StaticMaxPool(name=self.name, parent=inputs, kernel=(3,3), pad=(1,1), stride=(1,1)))
        self.add_module(smo.StaticBatchNormalization(name=self.name+'/bn', parent=[self._modules[-1]],
                                                     n_features=self._modules[-1].shape[1], n_dims=4))
        self.add_module(smo.StaticReLU(name=self.name+'/relu', parent=[self._modules[-1]]))
        return self._modules[-1]

class AveragePool3x3(smo.StaticGraph):
    def _generate_graph(self, inputs):
        self.add_module(smo.StaticAveragePool(name=self.name, parent=inputs, kernel=(3,3), pad=(1,1), stride=(1,1)))
        self.add_module(smo.StaticBatchNormalization(name=self.name+'/bn', parent=[self._modules[-1]],
                                                     n_features=self._modules[-1].shape[1], n_dims=4))
        self.add_module(smo.StaticReLU(name=self.name+'/relu', parent=[self._modules[-1]]))
        return self._modules[-1]

#---------------------List of candidate layers for the zoph search space-------------------------------
ZOPH_CANDIDATES = [SepConv3x3,
                   SepConv5x5,
                   DilSepConv3x3,
                   DilSepConv5x5,
                   MaxPool3x3,
                   AveragePool3x3,
                   smo.Identity,
                   smo.Zero]

#-----------------------------------The definition of a Zoph cell--------------------------------------
class ZophBlock(smo.StaticGraph):
    def __init__(self, name, parent, candidates, channels, join_parameters=None):
        self._candidates = candidates
        self._channels = channels
        if join_parameters is None:
            self._join_parameters = Parameter(shape=(len(candidates),))
        else:
            self._join_parameters = join_parameters
        smo.StaticGraph.__init__(self, name, parent)

    def _generate_graph(self, inputs):
        for i,ci in enumerate(self._candidates):
            self.add_module(ci(name='{}/candidate_{}'.format(self.name, i), parent=inputs, channels=self._channels))
        self.add_module(smo.Join(name='{}/join'.format(self.name), parent=self._modules,        join_parameters=self._join_parameters))
        return self._modules[-1]

class ZophCell(smo.StaticGraph):
    def __init__(self, name, parent, candidates, channels, n_modules=3, reducing=False, join_parameters=[None]*3):
        self._candidates = candidates
        self._channels = channels
        self._n_modules = n_modules
        self._reducing = reducing
        self._join_parameters = join_parameters
        smo.StaticGraph.__init__(self, name, parent)

    def _generate_graph(self, inputs):
        #match the input dimensions
        shapes = [(list(ii.shape) + 4 * [1])[:4] for ii in self.parent]
        min_shape = np.min(np.array(shapes), axis=0)
        self._shape_adaptation = {i: np.array(si[2:]) / min_shape[2:] for i,si in enumerate(shapes) if tuple(si[2:]) != tuple(min_shape[2:])}

        #perform the input channel projection, using pointwise convolutions
        projected_inputs = []
        for i,ii in enumerate(inputs):
            self.add_module(smo.StaticConv(name='{}/input_conv_{}'.format(self.name, i), parent=[ii],
                                           in_channels=ii.shape[1], out_channels=self._channels, kernel=(1,1), with_bias=False))
            projected_inputs.append(self._modules[-1])

        #perform shape adaptation, using pooling, if needed
        for i,pii in enumerate(projected_inputs):
            if i in self._shape_adaptation:
                self.add_module(smo.StaticMaxPool(name='{}/shape_adapt_pool_{}'.format(self.name, i), parent=[pii],
                                              kernel=self._shape_adaptation[i], stride=self._shape_adaptation[i]))
                projected_inputs[i] = self._modules[-1]

        #in case of a reducing cell, we need to perform another max-pooling on all inputs
        if self._reducing:
            for i, pii in enumerate(projected_inputs):
                self.add_module(smo.StaticMaxPool(name='{}/shape_adapt_pool_{}'.format(self.name, i), parent=[pii],
                                              kernel=(2,2), stride=(2,2)))
                projected_inputs[i] = self._modules[-1]

        cell_modules=projected_inputs
        for i in range(self._n_modules):
            self.add_module(ZophBlock(name='{}/zoph_block_{}'.format(self.name, i), parent=cell_modules,
                                      candidates=self._candidates, channels=self._channels,
                                      join_parameters=self._join_parameters[i]))
            cell_modules.append(self._modules[-1])

        #perform output concatenation
        self.add_module(smo.StaticDwConcatenate(name=self.name+'/output_concat', parent=cell_modules))
        return self._modules[-1]

class ZophNetwork(smo.StaticModule):
    def __init__(self, name, parent, stem_channels=64, cells=[ZophCell]*3, candidates=, reducing):
        self._stem_channels = stem_channels
        self._cells = cells
        self._candidates = candidates
        self._reducing = reducing
        smo.StaticModule.__init__(self, name, parent)

    def _create_modules(self):
        #1. add the stem convolutions
        self.add_module()
        #2. add the cells using shared architecture parameters

        #3. add output convolution and global average pooling

if __name__ == '__main__':

    input = smo.Input(name='input', value=nn.Variable((10,20,32,16)))
    input2 = smo.Input(name='input', value=nn.Variable((10,20,32,32)))
    sep_conv3x3 = SepConv3x3(name='conv1', parent=[input], channels=30)
    sep_conv5x5 = SepConv5x5(name='conv2', parent=[input], channels=30)
    dil_sep_conv3x3 = DilSepConv3x3(name='conv3', parent=[input], channels=30)
    dil_sep_conv5x5 = DilSepConv5x5(name='conv4', parent=[input], channels=30)
    max_pool3x3 = MaxPool3x3(name='pool1', parent=[input])
    avg_pool3x3 = AveragePool3x3(name='pool2', parent=[input])
    zoph_block = ZophBlock(name='block1', parent=[input], channels=20, candidates=ZOPH_CANDIDATES)
    zoph_cell = ZophCell(name='cell1', parent=[input, input2], candidates=ZOPH_CANDIDATES, channels=32)

    out_1 = sep_conv3x3()
    out_2 = sep_conv5x5()
    out_3 = dil_sep_conv3x3()
    out_4 = dil_sep_conv5x5()
    out_5 = max_pool3x3()
    out_6 = avg_pool3x3()
    out_7 = zoph_block()
    import pdb; pdb.set_trace()
