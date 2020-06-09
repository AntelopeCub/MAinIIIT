import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import data_loader
import direction
import h5py
import h5_util
import numpy as np
import tensorflow as tf
import time

def setup_surface_file(surf_path, dir_path):

    f = h5py.File(surf_path, 'a')
    f['dir_path'] = dir_path

    xcoordinates = np.linspace(-1, 1, num=51)
    f['xcoordinates'] = xcoordinates

    f.close()

def load_directions(dir_path):
    f = h5py.File(dir_path, 'r')

    if 'xdirection' in f.keys():
        directions_data = h5_util.read_list(f, 'xdirection')
        directions = [[tf.convert_to_tensor(data) for data in directions_data]]

    f.close()
    return directions

def set_weights(model, weights, directions=None, step=None):
    
    changes = [d*step for d in directions[0]]

    for idx in range(len(weights)):
        model.weights[idx].assign(w[idx] + tf.convert_to_tensor(changes[idx]))

def eval_loss(model, cce, x_train_list, y_train_list, batch_size):
    loss, acc = model.evaluate(x_train_list, y_train_list, batch_size=batch_size)
    return loss, acc

def crunch(surf_path, model, w, d, x_train_list, y_train_list, loss_key, acc_key, batch_size=128):
    
    f = h5py.File(surf_path, 'r+')
    losses, accuracies = [], []
    xcoordinates = f['xcoordinates'][:]

    if loss_key not in f.keys():
        shape = xcoordinates.shape
        losses = -np.ones(shape=shape)
        accuracies = -np.ones(shape=shape)
        f[loss_key] = losses
        f[acc_key] = accuracies

    cce = tf.keras.losses.CategoricalCrossentropy()

    start_time = time.time()

    for idx, coord in enumerate(xcoordinates):
        set_weights(model, w, d, coord)
        loss, acc = eval_loss(model, cce, x_train_list, y_train_list, batch_size)
        losses[idx] = loss
        accuracies[idx] = acc

        f[loss_key][:] = losses
        f[acc_key][:] = accuracies
        f.flush()

    f.close()
    total_time = time.time() - start_time
    print('Finished! Total time:%.2fs' % total_time)


if __name__ == "__main__":

    gpus = tf.config.experimental.list_physical_devices('GPU') #must limit gpu memory growth
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)

    model_path = "D:/Rain/text/Python/MA_IIIT/models/vgg9/vgg9_sgd_lr=0.1_bs=128_wd=0.0_epochs=15.h5"
    dir_path = "D:/Rain/text/Python/MA_IIIT/models/vgg9/directions/vgg9_sgd_lr=0.1_bs=128_wd=0.0_epochs=15_weights.h5"
    surf_path = "D:/Rain/text/Python/MA_IIIT/models/vgg9/surface/vgg9_sgd_lr=0.1_bs=128_wd=0.0_epochs=15_surface.h5"
    batch_size = 128

    model = tf.keras.models.load_model(model_path)
    w = direction.get_weights(model)
    d = load_directions(dir_path)

    setup_surface_file(surf_path, dir_path)

    x_train_list, y_train_list = data_loader.load_data(batch_size=-1)

    crunch(surf_path, model, w, d, x_train_list, y_train_list, 'train_loss', 'train_acc', batch_size)