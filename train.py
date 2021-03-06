import numpy as np
import tensorflow as tf
import os
from scipy.io import wavfile
from text import *
from parameters import params as pm
os.environ["CUDA_VISIBLE_DEVICES"] = '0'
def normalize(inputs,
              epsilon = 1e-8):
    inputs_shape = inputs.get_shape()
    params_shape = inputs_shape[-1:]
    mean, variance = tf.nn.moments(inputs, [-1], keep_dims=True)
    beta= tf.Variable(tf.zeros(params_shape))
    gamma = tf.Variable(tf.ones(params_shape))
    normalized = (inputs - mean) / (variance + epsilon)
    outputs = gamma * normalized + beta
    return outputs

def feed_forward(inputs, w):
    outputs = [tf.matmul(inputs[i, :, :], w) for i in range(pm.batch_size)]
    outputs = tf.stack(outputs)
    return outputs

def positional_encoding(inputs,
                        num_units):

    N, T = inputs.get_shape().as_list()
    position_ind = tf.tile(tf.expand_dims(tf.range(T), 0), [N, 1])

    # First part of the PE function: sin and cos argument
    position_enc = np.array([
            [pos / np.power(10000, 2.*i/num_units) for i in range(num_units)]
            for pos in range(T)])
    # Second part, apply the cosine to even columns and sin to odds.
    position_enc[:, 0::2] = np.sin(position_enc[:, 0::2])  # dim 2i
    position_enc[:, 1::2] = np.cos(position_enc[:, 1::2])  # dim 2i+1
    # Convert to a tensor
    lookup_table = tf.convert_to_tensor(position_enc, dtype = tf.float32)
    outputs = tf.nn.embedding_lookup(lookup_table, position_ind)
    return outputs

labels = []
with open('samples/labels/labels.txt', 'r', encoding = 'utf-8') as lb:
    for l in lb.readlines():
        l = l.strip()
        l = l.split('||')[1]
        labels.append(text2label(l))
labels = np.array(labels)
audio = os.listdir('processed/wavs')
wavs = np.array([np.load(os.path.join('processed/wavs', audio[i])) for i in range(len(audio))])
x = tf.placeholder("int32", [pm.batch_size, pm.Tx], name = "x")
y = tf.placeholder("float32", [pm.batch_size, pm.Dy, pm.Ty], name = "y")
y_enc = tf.concat((tf.zeros(shape=[pm.batch_size, 1, pm.Ty]), y[:, :-1, :]), 1)
lookup_table = tf.Variable(tf.random_uniform((pm.vocab_size, pm.num_units), minval=-1, maxval=1,dtype=tf.float32), name = 'lookup_table')
x_enc = tf.nn.embedding_lookup(lookup_table, x, name = 'x_enc')
x_enc += positional_encoding(x, pm.num_units)
x_enc = tf.concat((tf.zeros(shape=[pm.batch_size, 1, pm.num_units]), x_enc[:, :-1, :]), 1)
Q1 = tf.layers.dense(x_enc, pm.num_units)
K1 = tf.layers.dense(x_enc, pm.num_units)
V1 = tf.layers.dense(x_enc, pm.num_units)
net = tf.matmul(Q1, tf.transpose(K1, [0, 2, 1]))
net = tf.matmul(net, V1)
net = tf.nn.relu(net)
net += V1
net = normalize(net)
'''
w2 = tf.tile(tf.truncated_normal((pm.step_size, pm.num_units), mean=0.0, stddev=1, dtype=tf.float32, seed=None), [int(pm.num_units/pm.step_size), 1], name = 'w2')
w3 = tf.tile(tf.truncated_normal((pm.step_size, pm.num_units), mean=0.0, stddev=1, dtype=tf.float32, seed=None), [int(pm.num_units/pm.step_size), 1], name = 'w3')
w4 = tf.tile(tf.truncated_normal((pm.step_size, pm.num_units), mean=0.0, stddev=1, dtype=tf.float32, seed=None), [int(pm.num_units/pm.step_size), 1], name = 'w4')
w5 = tf.tile(tf.truncated_normal((pm.step_size, pm.num_units), mean=0.0, stddev=1, dtype=tf.float32, seed=None), [int(pm.num_units/pm.step_size), 1], name = 'w5')
w6 = tf.tile(tf.truncated_normal((pm.step_size, pm.num_units), mean=0.0, stddev=1, dtype=tf.float32, seed=None), [int(pm.num_units/pm.step_size), 1], name = 'w6')
net += feed_forward(net, w2)
net = tf.nn.relu(net)
net = normalize(net)
net += tf.layers.dense(net, pm.num_units)
net = tf.nn.relu(net)
net = normalize(net)
net += feed_forward(net, w3)
net = tf.nn.relu(net)
net = normalize(net)
net += tf.layers.dense(net, pm.num_units)
net = tf.nn.relu(net)
net = normalize(net)
net += feed_forward(net, w4)
net = tf.nn.relu(net)
net = normalize(net)
net += tf.layers.dense(net, pm.num_units)
net = tf.nn.relu(net)
net = normalize(net)
net += feed_forward(net, w5)
net = tf.nn.relu(net)
net = normalize(net)
net += tf.layers.dense(net, pm.num_units)
net = tf.nn.relu(net)
net = normalize(net)
net += feed_forward(net, w6)
net = tf.nn.relu(net)
net = normalize(net)
'''
w7 = tf.tile(tf.truncated_normal((1, pm.Dy,), mean=0.0, stddev=1, dtype=tf.float32, seed=None), [pm.num_units, 1], name = 'w7')
net = feed_forward(net, w7)
net = tf.nn.relu(net)
net = normalize(net)
net = tf.transpose(net, [0, 2, 1])
Q2 = tf.layers.dense(net, pm.num_units)
K2 = tf.layers.dense(net, pm.num_units)
V2 = tf.layers.dense(y_enc, pm.num_units)
net = tf.matmul(Q2, tf.transpose(K2, [0, 2, 1]))
net = tf.matmul(net, V2)
net = tf.nn.relu(net)
net += V2
yhat = tf.layers.dense(net, pm.Ty)
loss = tf.reduce_mean(tf.abs(y - yhat), name = 'loss')
lr = tf.train.exponential_decay(0.1, 20000, 100, 0.96, staircase=True)
optimizer = tf.train.AdamOptimizer(learning_rate=lr, beta1=0.9, beta2=0.9, epsilon=1e-08).minimize(loss)

with tf.Session() as sess:
    sess.run(tf.global_variables_initializer())
    for i in range(20000):
        _ = sess.run(optimizer, feed_dict = {x:labels, y:wavs})
        print('Step: ', i, 'loss: ', sess.run(loss, feed_dict = {x:labels, y:wavs}))
    ypred = sess.run(yhat, feed_dict = {x:labels, y:wavs})
    ypred = ypred[0, :, :]
    ypred = ypred.reshape(1, -1)[0]
    ypred = ypred.astype(np.int16)
    wavfile.write('output.wav', 16000, ypred)
