import os
import tensorflow as tf
import tensorflow.keras.backend as K
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.layers import *
from tensorflow.keras.regularizers import l2
from tensorflow.keras.activations import relu

def convblock(x, filters, weight_decay_const, apply_batchnorm, padding='same'):
    x = Conv2D(filters=filters, kernel_size=3, strides=1, padding=padding,
            kernel_regularizer=l2(weight_decay_const))(x)
    if apply_batchnorm:
        x = BatchNormalization()(x)
    x = Activation('relu')(x)
    x = Conv2D(filters=filters, kernel_size=3, strides=1, padding=padding,
            kernel_regularizer=l2(weight_decay_const))(x)
    if apply_batchnorm:
        x = BatchNormalization()(x)
    return Activation('relu')(x)

class TemporalAttention(tf.keras.layers.Layer):
    '''
    Temporal attention for embedded representations
    of satellite image tiles.
    '''

    def __init__(self, timesteps, input_shape, weight_decay_const):
        super(TemporalAttention, self).__init__()
        self.concat = Concatenate()
        self.b, self.inp_h, self.inp_w, self.inp_d = input_shape
        self.dk = tf.math.sqrt(tf.cast(self.inp_h * self.inp_w * self.inp_d, tf.float32))
        self.in_reshape = Reshape((self.inp_d*self.inp_h*self.inp_w, timesteps))
        self.out_reshape = Reshape((self.inp_h, self.inp_w, self.inp_d*timesteps))
        self.softmax_attention = Softmax()
        self.activation = Activation('relu')

    def __call__(self, queries, values):
        '''
        inputs: tuple of embedded 2D representations
        n x n x filters
        Uses shared QK attention.
        '''
        queries = self.concat(queries)
        values = self.concat(values)
        Q = self.in_reshape(queries)
        V = self.in_reshape(queries)
        QKT = self.softmax_attention(tf.matmul(Q, tf.transpose(Q, [0, 2, 1])) / self.dk)
        attention = tf.matmul(QKT, V)
        attention = self.out_reshape(attention)
        return attention


class ConvBlock(tf.keras.layers.Layer):

    def __init__(self, filters, weight_decay_const, apply_batchnorm, padding='same'):

        super(ConvBlock, self).__init__()
        self.apply_batchnorm = apply_batchnorm
        print(filters, apply_batchnorm, weight_decay_const)
        self.c1 = Conv2D(filters=filters, kernel_size=3, strides=1, padding=padding,
                kernel_regularizer=l2(weight_decay_const))
        self.c2 = Conv2D(filters=filters, kernel_size=3, strides=1, padding=padding,
                kernel_regularizer=l2(weight_decay_const))
        self.bn1 = BatchNormalization()
        self.bn2 = BatchNormalization()
        self.activation = Activation('relu')

    def __call__(self, inputs):
        x = self.c1(inputs)
        if self.apply_batchnorm:
            x = self.bn1(x)
        x = self.activation(x)
        x = self.c2(x)
        if self.apply_batchnorm:
            x = self.bn2(x)
        return self.activation(x)

class UnetDownsample(tf.keras.layers.Layer):

    def __init__(self, filters, weight_decay_const, apply_batchnorm):

        super(UnetDownsample, self).__init__()

        self.cb1 = ConvBlock(filters, weight_decay_const, apply_batchnorm)
        self.cb2 = ConvBlock(filters*2, weight_decay_const, apply_batchnorm)
        self.cb3 = ConvBlock(filters*4, weight_decay_const, apply_batchnorm)
        self.cb4 = ConvBlock(filters*8, weight_decay_const, apply_batchnorm)
        self.cb5 = ConvBlock(filters*8, weight_decay_const, apply_batchnorm)
    
        self.max_pool = MaxPooling2D(pool_size=2, strides=2)

    def __call__(self, inputs):

        x1 = self.cb1(inputs)
        mp1 = self.max_pool(x1)

        x2 = self.cb2(mp1)
        mp2 = self.max_pool(x2)

        x3 = self.cb3(mp2)
        mp3 = self.max_pool(x3)

        x4 = self.cb4(mp3)
        mp4 = self.max_pool(x4)

        x5 = self.cb5(mp4)

        return [x1, x2, x3, x4, x5]


def unet_attention(input_shape, initial_filters, timesteps, n_classes, 
        weight_decay_const, apply_batchnorm, batch_size):

    i1 = Input(input_shape)
    i2 = Input(input_shape)
    i3 = Input(input_shape)
    i4 = Input(input_shape)
    i5 = Input(input_shape)
    i6 = Input(input_shape)
     
    # now, apply embedding 
    inputs = [i1, i2, i3, i4, i5, i6]
    embeddings = []
    downsampler = UnetDownsample(initial_filters, weight_decay_const, apply_batchnorm)
    for inp in inputs:
        embeddings.append(downsampler(inp))

    temp_attn_1 = TemporalAttention(timesteps, (None, 32, 32, 1), weight_decay_const)
    temp_attn_2 = TemporalAttention(timesteps, (None, 16, 16, 2), weight_decay_const)

    attn1_inputs = []
    attn2_inputs = []

    for e in embeddings:
        attn1_inputs.append(e[-2])
        attn2_inputs.append(e[-1])

    query_embed_1 = Conv2D(filters=1, kernel_size=1, strides=1, padding='same',
            kernel_regularizer=l2(weight_decay_const)) # aggressive compression...
    value_embed_1 = Conv2D(filters=1, kernel_size=1, strides=1, padding='same',
            kernel_regularizer=l2(weight_decay_const)) # aggressive compression...
    value_embed_2 = Conv2D(filters=2, kernel_size=1, strides=1, padding='same',
            kernel_regularizer=l2(weight_decay_const)) 
    query_embed_2 = Conv2D(filters=2, kernel_size=1, strides=1, padding='same',
            kernel_regularizer=l2(weight_decay_const)) 

    query1 = []
    query2 = []
    value1 = []
    value2 = []

    for a1, a2 in zip(attn1_inputs, attn2_inputs):
        query1.append(Activation('relu')(query_embed_1(a1)))
        query2.append(Activation('relu')(query_embed_2(a2)))
        value1.append(Activation('relu')(value_embed_1(a1)))
        value2.append(Activation('relu')(value_embed_2(a2)))

    attention1 = temp_attn_1(query1, value1)
    attention2 = temp_attn_2(query2, value2)

    attention2 = convblock(attention2, initial_filters*8, weight_decay_const, apply_batchnorm)
    up1 = UpSampling2D(size=(2, 2))(attention2)

    attention1 = convblock(attention1, initial_filters*8, weight_decay_const, apply_batchnorm)
    concat1 = Concatenate()([up1, attention1])

    x = convblock(concat1, initial_filters*4, weight_decay_const, apply_batchnorm)
    x = UpSampling2D(size=(2, 2))(x)
    x = convblock(x, initial_filters*2, weight_decay_const, apply_batchnorm)
    x = UpSampling2D(size=(2, 2))(x)
    x = convblock(x, initial_filters, weight_decay_const, apply_batchnorm)
    x = UpSampling2D(size=(2, 2))(x)
    x = convblock(x, initial_filters, weight_decay_const, apply_batchnorm)
    softmax = Conv2D(n_classes, kernel_size=1, strides=1,
                        activation='softmax',
                        kernel_regularizer=l2(weight_decay_const))(x)
    return Model(inputs=[i1, i2, i3, i4, i5, i6], outputs=softmax)



if __name__ == '__main__':
    
    '''
    shape = (16, 64, 64, 1)
    timesteps = 6
    queries = []
    values = []
    weight_decay_const = 0.0001
    for _ in range(timesteps):
        queries.append(tf.random.normal(shape))
        values.append(tf.random.normal(shape))
    layer = TemporalAttention(timesteps, shape, weight_decay_const)
    attention = layer(queries, values)
    '''
    model = unet_attention(input_shape=(256, 256, 6), 
                           initial_filters=16,
                           timesteps=6,
                           n_classes=3,
                           weight_decay_const=0.0001,
                           apply_batchnorm=True,
                           batch_size=None)
    tensors = []
    timesteps = 6
    for _ in range(timesteps):
        tensors.append(tf.random.normal((16, 256, 256, 6)))
    print(model.predict(tensors))
    # print(model.summary(line_length=150))
