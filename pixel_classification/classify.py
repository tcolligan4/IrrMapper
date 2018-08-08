# ===============================================================================
# Copyright 2018 dgketchum
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ===============================================================================

import os
import numpy as np
import tensorflow as tf
from rasterio import open as rasopen
from rasterio.dtypes import float32
from datetime import datetime

from numpy import zeros, array, float16
from numpy.ma import array as marray
from sklearn.preprocessing import StandardScaler

from pixel_classification.tf_multilayer_perceptron import multilayer_perceptron


def classify_raster(data, model=None, out_location=None):

    features = data.features.tolist()
    stack = None
    first = True
    arr = None
    for i, feat in enumerate(features):
        with rasopen(data.model_map[feat], mode='r') as src:
            arr = src.read()
            meta = src.meta.copy()
        if first:
            empty = zeros((len(features), arr.shape[1], arr.shape[2]), float16)
            stack = empty
            stack[i, :, :] = normalize_image_channel(arr)
            first = False
        else:
            stack[i, :, :] = normalize_image_channel(arr)

    final_shape = 1, stack.shape[1], stack.shape[2]
    stack = stack.reshape((stack.shape[0], stack.shape[1] * stack.shape[2]))
    stack[stack == 0.] = np.nan
    m_stack = marray(stack, mask=np.isnan(stack))

    new_array = np.zeros_like(arr.reshape((1, arr.shape[1] * arr.shape[2])), dtype=float16)

    with tf.Session() as sess:

        pixel = tf.placeholder("float", [None, n])
        classify = tf.add(tf.matmul(multilayer_perceptron(pixel, weights['hidden'], biases['hidden']),
                                    weights['output']), biases['output'])
        time = datetime.now()

        ct_nan = 0
        ct_out = 0

        for i in range(m_stack.shape[-1]):
            if not np.ma.is_masked(m_stack[:, i]):
                dat = m_stack[:, i]
                dat = array(dat).reshape((1, dat.shape[0]))
                loss = sess.run(classify, feed_dict={pixel: dat})
                new_array[0, i] = np.argmax(loss, 1)
                ct_out += 1
            else:
                new_array[0, i] = np.nan
                ct_nan += 1

            if i % 1000000 == 0:
                print('Count {} of {} pixels in {} seconds'.format(i, m_stack.shape[-1],
                                                                   (datetime.now() - time).seconds))

    new_array = new_array.reshape(final_shape)
    new_array = array(new_array, dtype=float32)

    meta['count'] = 1
    meta['dtype'] = float32
    with rasopen(os.path.join(out_location, 'binary_raster.tif'), 'w', **meta) as dst:
        dst.write(new_array)
    return None


def normalize_image_channel(data):
    data = data.reshape((data.shape[1], data.shape[2]))
    scaler = StandardScaler()
    scaler = scaler.fit(data)
    data = scaler.transform(data)
    data = data.reshape((1, data.shape[0], data.shape[1]))
    return data


if __name__ == '__main__':
    pass
# ========================= EOF ====================================================================
