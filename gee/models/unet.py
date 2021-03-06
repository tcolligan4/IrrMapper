import os
import tensorflow as tf
import tensorflow.keras.backend as K
from tensorflow.keras.models import Model, Sequential
from tensorflow.keras.layers import *
from tensorflow.keras.regularizers import l2
from tensorflow.keras.activations import relu


def ConvBlock(x, filters, weight_decay_const, apply_batchnorm, padding='same'):
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


def ConvBNRelu(x, filters, weight_decay_const, apply_batchnorm):
    x = Conv2D(filters=filters, kernel_size=3, strides=1, padding='same',
            kernel_regularizer=l2(weight_decay_const))(x)
    if apply_batchnorm:
        x = BatchNormalization()(x)
    return Activation('relu')(x)


def unet_dropout(input_shape, initial_exp, n_classes, weight_decay_const,
        apply_batchnorm):
     
    features = Input(shape=input_shape)
    base = 2

    c1 = ConvBlock(features, base**initial_exp, weight_decay_const,
            apply_batchnorm)
    mp1 = MaxPooling2D(pool_size=2, strides=2)(c1)

    initial_exp += 1

    c2 = ConvBlock(mp1, base**initial_exp, weight_decay_const,
            apply_batchnorm)
    mp2 = MaxPooling2D(pool_size=2, strides=2)(c2)

    initial_exp += 1

    filters = base**initial_exp
    padding = 'same'
    # c3 = ConvBlock(mp2, base**initial_exp, weight_decay_const,
    #         apply_batchnorm)
    x = Conv2D(filters=filters, kernel_size=3, strides=1, padding=padding,
            kernel_regularizer=l2(weight_decay_const))(mp2)
    x = Activation('relu')(x)
    x = SpatialDropout2D(0.2)(x)

    x = Conv2D(filters=filters, kernel_size=3, strides=1, padding=padding,
            kernel_regularizer=l2(weight_decay_const))(x)
    x = Activation('relu')(x)
    c3 = SpatialDropout2D(0.5)(x)

    mp3 = MaxPooling2D(pool_size=2, strides=2)(c3)

    initial_exp += 1 

    # c4 = ConvBlock(mp3, base**initial_exp, weight_decay_const,
    #         apply_batchnorm)
    filters = base**initial_exp
    padding = 'same'
    x = Conv2D(filters=filters, kernel_size=3, strides=1, padding=padding,
            kernel_regularizer=l2(weight_decay_const))(mp3)
    x = Activation('relu')(x)
    x = SpatialDropout2D(0.2)(x)

    x = Conv2D(filters=filters, kernel_size=3, strides=1, padding=padding,
            kernel_regularizer=l2(weight_decay_const))(x)
    x = Activation('relu')(x)
    c4 = SpatialDropout2D(0.5)(x)
    mp4 = MaxPooling2D(pool_size=2, strides=2)(c4)

    initial_exp += 1

    # 1024 filters
    c5 = ConvBlock(mp4, base**initial_exp, weight_decay_const,
            apply_batchnorm)
    initial_exp -= 1

    u1 = UpSampling2D(size=(2, 2))(c5)
    c6 = ConvBNRelu(u1, base**initial_exp, weight_decay_const,
            apply_batchnorm)
    u1_c4 = Concatenate()([c6, c4])
    c7 = ConvBlock(u1_c4, base**initial_exp, weight_decay_const,
            apply_batchnorm)

    initial_exp -= 1
    
    u2 = UpSampling2D(size=(2, 2))(c7)
    c8 = ConvBNRelu(u2, base**initial_exp, weight_decay_const,
            apply_batchnorm)
    u2_c3 = Concatenate()([c8, c3])
    c9 = ConvBlock(u2_c3, base**initial_exp, weight_decay_const,
            apply_batchnorm)

    initial_exp -= 1
    
    u3 = UpSampling2D(size=(2, 2))(c9)
    c10 = ConvBNRelu(u3, base**initial_exp, weight_decay_const,
            apply_batchnorm)
    u3_c2 = Concatenate()([c10, c2])
    c11 = ConvBlock(u3_c2, base**initial_exp, weight_decay_const,
            apply_batchnorm)

    initial_exp -= 1
    u4 = UpSampling2D(size=(2, 2))(c11)
    c12 = ConvBNRelu(u4, base**initial_exp, weight_decay_const,
            apply_batchnorm)
    u4_c1 = Concatenate()([c12, c1])

    filters = base**initial_exp
    padding = 'same'
    x = Conv2D(filters=filters, kernel_size=3, strides=1, padding=padding,
            kernel_regularizer=l2(weight_decay_const))(u4_c1)
    x = Activation('relu')(x)

    x = Conv2D(filters=filters, kernel_size=3, strides=1, padding=padding,
            kernel_regularizer=l2(weight_decay_const))(x)
    x = Activation('relu')(x)

    softmax = Conv2D(n_classes, kernel_size=1, strides=1,
                        activation='softmax', name='softmax',
                        kernel_regularizer=l2(weight_decay_const))(x)
    
    return Model(inputs=[features], outputs=[softmax])


def unet(input_shape, initial_exp, n_classes, weight_decay_const,
        apply_batchnorm):
     
    features = Input(shape=input_shape)
    base = 2

    c1 = ConvBlock(features, base**initial_exp, weight_decay_const,
            apply_batchnorm)
    mp1 = MaxPooling2D(pool_size=2, strides=2)(c1)

    initial_exp += 1

    c2 = ConvBlock(mp1, base**initial_exp, weight_decay_const,
            apply_batchnorm)
    mp2 = MaxPooling2D(pool_size=2, strides=2)(c2)

    initial_exp += 1

    c3 = ConvBlock(mp2, base**initial_exp, weight_decay_const,
            apply_batchnorm)
    mp3 = MaxPooling2D(pool_size=2, strides=2)(c3)

    initial_exp += 1 

    c4 = ConvBlock(mp3, base**initial_exp, weight_decay_const,
            apply_batchnorm)
    mp4 = MaxPooling2D(pool_size=2, strides=2)(c4)

    initial_exp += 1

    # 1024 filters
    c5 = ConvBlock(mp4, base**initial_exp, weight_decay_const,
            apply_batchnorm)
    initial_exp -= 1

    u1 = UpSampling2D(size=(2, 2))(c5)
    c6 = ConvBNRelu(u1, base**initial_exp, weight_decay_const,
            apply_batchnorm)
    u1_c4 = Concatenate()([c6, c4])
    c7 = ConvBlock(u1_c4, base**initial_exp, weight_decay_const,
            apply_batchnorm)

    initial_exp -= 1
    
    u2 = UpSampling2D(size=(2, 2))(c7)
    c8 = ConvBNRelu(u2, base**initial_exp, weight_decay_const,
            apply_batchnorm)
    u2_c3 = Concatenate()([c8, c3])
    c9 = ConvBlock(u2_c3, base**initial_exp, weight_decay_const,
            apply_batchnorm)

    initial_exp -= 1
    
    u3 = UpSampling2D(size=(2, 2))(c9)
    c10 = ConvBNRelu(u3, base**initial_exp, weight_decay_const,
            apply_batchnorm)
    u3_c2 = Concatenate()([c10, c2])
    c11 = ConvBlock(u3_c2, base**initial_exp, weight_decay_const,
            apply_batchnorm)

    initial_exp -= 1
    u4 = UpSampling2D(size=(2, 2))(c11)
    c12 = ConvBNRelu(u4, base**initial_exp, weight_decay_const,
            apply_batchnorm)
    u4_c1 = Concatenate()([c12, c1])
    c13 = ConvBlock(u4_c1, base**initial_exp, weight_decay_const,
            apply_batchnorm)

    softmax = Conv2D(n_classes, kernel_size=1, strides=1,
                        activation='softmax', name='softmax',
                        kernel_regularizer=l2(weight_decay_const))(c13)
    
    return Model(inputs=[features], outputs=[softmax])

if __name__ == '__main__':
    m = unet((None, None, 36), initial_exp=4)
    m.summary(line_length=150)
