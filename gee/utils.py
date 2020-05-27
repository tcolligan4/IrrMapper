import numpy as np
import time
import os
import tensorflow as tf

from sklearn.metrics import confusion_matrix
import feature_spec

features_dict = feature_spec.features_dict()
bands = feature_spec.bands()
features = feature_spec.features()

def one_hot(labels, n_classes):
    h, w, d = labels.shape
    labels = tf.squeeze(labels)
    ls = []
    for i in range(n_classes):
        if i == 0:
            where = tf.where(labels != i+1, tf.zeros((h, w)), 1*tf.ones((h,w)))
        else:
            where = tf.where(labels != i+1, tf.zeros((h, w)), tf.ones((h,w)))
        ls.append(where)
    temp = tf.stack(ls, axis=-1)
    return temp

def mask_unlabeled_values(y_true, y_pred):
    '''
    y_pred: softmaxed tensor
    y_true: one-hot tensor of labels
    Returns two vectors of labels. Assumes input
    tensors are 4-dimensional (batchxrowxcolxdepth)
    '''
    mask = tf.not_equal(tf.reduce_sum(y_true, axis=-1), 0)
    y_true = tf.argmax(y_true, axis=-1)
    y_pred = tf.argmax(y_pred, axis=-1)
    y_true = tf.boolean_mask(y_true, mask)
    y_pred = tf.boolean_mask(y_pred, mask)
    return y_true, y_pred


def confusion_matrix_from_generator(datasets, batch_size, model, n_classes=3):
    ''' 
    inputs: list of tf.data.Datasets, not batched, without repeat.
    '''   
    out_cmat = np.zeros((n_classes, n_classes))
    labels = range(n_classes)
    instance_count = 0
    for dataset in datasets:
        dataset = dataset.batch(batch_size)
        for batch in dataset:
            features, y_true = batch[0], batch[1]
            y_pred = model.predict(features)
            instance_count += y_pred.shape[0]
            y_true, y_pred = mask_unlabeled_values(y_true, y_pred)
            cmat = confusion_matrix(y_true, y_pred, labels=labels)
            out_cmat += cmat
    precision_dict = {}
    recall_dict = {}
    for i in range(n_classes):
        precision_dict[i] = 0
        recall_dict[i] = 0
    for i in range(n_classes):
        precision_dict[i] = out_cmat[i, i] / np.sum(out_cmat[i, :]) # row i
        recall_dict[i] = out_cmat[i, i] / np.sum(out_cmat[:, i]) # column i
    return out_cmat.astype(np.int), recall_dict, precision_dict, instance_count

def get_dataset(pattern):
  """Function to read, parse and format to tuple a set of input tfrecord files.
  Get all the files matching the pattern, parse and convert to tuple.
  Args:
    pattern: A file pattern to match in a Cloud Storage bucket.
  Returns:
    A tf.data.Dataset
  """
  glob = tf.io.gfile.glob(pattern)
  dataset = tf.data.TFRecordDataset(glob, compression_type='GZIP')
  dataset = dataset.map(parse_tfrecord, num_parallel_calls=5)
  dataset = dataset.map(to_tuple, num_parallel_calls=5)

  return dataset

def parse_tfrecord(example_proto):
  """the parsing function.
  read a serialized example into the structure defined by features_dict.
  args:
    example_proto: a serialized example.
  returns:
    a dictionary of tensors, keyed by feature name.
  """
  return tf.io.parse_single_example(example_proto, features_dict)

def to_tuple(inputs):
  """Function to convert a dictionary of tensors to a tuple of (inputs, outputs).
  Turn the tensors returned by parse_tfrecord into a stack in HWC shape.
  Args:
    inputs: A dictionary of tensors, keyed by feature name.
  Returns:
    A tuple of (inputs, outputs).
  """
  inputsList = [inputs.get(key) for key in sorted(features)]
  stacked = tf.stack(inputsList, axis=0)
  # Convert from CHW to HWC
  stacked = tf.transpose(stacked, [1, 2, 0])
  inputs = stacked[:,:,:len(bands)] 
  labels = one_hot(stacked[:,:,len(bands):], n_classes=3)
  labels = tf.cast(labels, tf.int32)
  return inputs, labels

def make_dataset(root, batch_size=16, training=True):
    paths = ['irrigated', 'uncultivated', 'unirrigated']
    pattern = "*gz"
    datasets = []
    for path in paths:
        if os.path.isdir(os.path.join(root, path)):
            training_root = os.path.join(root, path, pattern)
            dataset = get_dataset(training_root)
            if training:
                datasets.append(dataset.repeat())
            else:
                datasets.append(dataset)
    if not len(datasets):
        training_root = os.path.join(root, pattern)
        datasets = [get_dataset(training_root)]
    if not training:
        return datasets
    choice_dataset = tf.data.Dataset.range(len(paths)).repeat()
    dataset = tf.data.experimental.choose_from_datasets(datasets,
            choice_dataset).batch(batch_size).repeat().shuffle(buffer_size=30)
    return dataset

if __name__ == '__main__':

    from models import unet
    model = unet((None, None, 36), initial_exp=4, n_classes=3)
    model_path = './models/model-0.980-0.919.h5'
    # model_path = './fully_trained.h5'
    model.load_weights(model_path)

    #datasets = make_dataset('/home/thomas/ee-test/data/training_data/train/', training=False)
    datasets = make_dataset('./data/2015SRl7l8mean2015/', training=False)

    c, p, r, i = confusion_matrix_from_generator(datasets, batch_size=16, model=model)