import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
import tensorflow.keras as keras
from tensorflow.keras import regularizers
from tensorflow.keras.callbacks import LearningRateScheduler
from tensorflow.keras.datasets import cifar10
from tensorflow.keras.optimizers import SGD

import data_generator
import data_loader
from build_resnet import ResNet20, ResNet56
from build_vgg import VGG9_BN, VGG9_QN, VGG16_BN, VGG16_QN, VGG9_no_BN
from quantization.build_vgg_qn import f_build_vgg_qua


def lr_decay(epoch):
    init_lr = 0.1
    factor = 0.1
    if epoch < 150:
        return init_lr
    elif epoch < 225:
        return init_lr * (factor ** 1)
    elif epoch < 275:
        return init_lr * (factor ** 2)
    else:
        return init_lr * (factor ** 3)


def plot_result(history):
    acc = history.history['accuracy']
    val_acc = history.history['val_accuracy']
    loss = history.history['loss']
    val_loss = history.history['val_loss']
    epochs_idx = range(1, len(acc) + 1)

    fig1 = plt.figure('Training Result', figsize = (8, 10))
    plt.figure('Training Result')
    ax2 = plt.subplot(212)
    plt.plot(epochs_idx[::1], acc[::1], 'bo', label='Training acc')
    plt.plot(epochs_idx[::1], val_acc[::1], 'b', label='Validation acc')
    plt.xlabel('Epochs')
    plt.ylabel('Accuracy')
    plt.legend()
    ax1 = plt.subplot(211, sharex = ax2)
    plt.plot(epochs_idx[::1], loss[::1], 'bo', label='Training loss')
    plt.plot(epochs_idx[::1], val_loss[::1], 'b', label='Validation loss')
    plt.title('Training and validation loss / acc')
    plt.ylabel('Loss')
    plt.legend()
    plt.show()


class Cyclic_LR_Scheduler():
    
    def __init__(self, initial_rate, cycle_length=33, end_rate=1e-10, drop_rate=1.):
        self.initial_rate = initial_rate
        self.cycle_length = cycle_length
        self.end_rate     = end_rate
        self.drop_rate    = drop_rate
        
    def cyc_decay(self, epoch):
        return self.end_rate + 0.5* self.initial_rate * ( 1+np.cos(np.mod(epoch, self.cycle_length+1)*np.pi/(self.cycle_length+1)) ) * self.drop_rate**(np.floor(epoch / self.cycle_length))


class build_model(object):

    def __init__(self, 
                 model_type, 
                 dataset, 
                 l2_reg_rate= None, 
                 fc_type    = None, 
                 pre_mode   = 'norm',
                 L_A        = [3, 5],
                 L_W        = [1, 7]):

        self.model_type = model_type

        if dataset in ['cifar10', 'svhn_equal', 'cifar10_pre']:
            self.num_class = 10
            self.input_shape = (32, 32, 3)
        elif dataset in ['cifar100']:
            self.num_class = 100
            self.input_shape = (32, 32, 3)
        else:
            raise Exception('Unknown Dataset: %s' % (dataset))

        self.dataset = dataset
        self.pre_mode = pre_mode

        if l2_reg_rate is not None:
            self.l2_reg = regularizers.l2(l=l2_reg_rate)
            self.l2_reg_rate = l2_reg_rate
        else:
            self.l2_reg = None
            self.l2_reg_rate = 0

        self.fc_type = fc_type

        self.L_A = L_A
        self.L_W = L_W

        if model_type == 'vgg9':
            self.model = VGG9_no_BN(self.input_shape, self.l2_reg, num_class=self.num_class, fc_type=self.fc_type)
        elif model_type == 'vgg9_bn':
            self.model = VGG9_BN(self.input_shape, self.l2_reg, num_class=self.num_class, fc_type=self.fc_type)
        elif model_type == 'vgg9_qn':
            self.model = f_build_vgg_qua(self.input_shape, self.l2_reg_rate, self.num_class, L_A=self.L_A, L_W=self.L_W, layers='7')
        elif model_type == 'vgg16_bn':
            self.model = VGG16_BN(self.input_shape, self.l2_reg, num_class=self.num_class, fc_type=self.fc_type)
        elif model_type == 'vgg16_qn':
            self.model = f_build_vgg_qua(self.input_shape, self.l2_reg_rate, self.num_class, L_A=self.L_A, L_W=self.L_W, layers='13')
        elif model_type == 'resnet20':
            self.model = ResNet20(input_shape=self.input_shape, num_class=self.num_class, l2_reg=self.l2_reg)
        elif model_type == 'resnet56':
            self.model = ResNet56(input_shape=self.input_shape, num_class=self.num_class, l2_reg=self.l2_reg)
        else:
            raise Exception('Unknown model type: %s' % model_type)

    def train_model(self, optimizer=None, batch_size=128, epochs=20, load_mode='tfds', plot_history=False, add_aug=False, aug_pol='baseline', callbacks=None, workers=1):
        
        if optimizer is None:
            self.optimizer = SGD(learning_rate=0.1)
        else:
            self.optimizer = optimizer

        if 'qn' in self.model_type:
            self.model.compile(optimizer=self.optimizer, loss=tf.keras.losses.CategoricalCrossentropy(from_logits=True), metrics=['accuracy'])
        else:
            self.model.compile(optimizer=self.optimizer, loss=tf.keras.losses.CategoricalCrossentropy(from_logits=False), metrics=['accuracy'])

        x_train, y_train, x_test, y_test = data_loader.load_data(self.dataset, load_mode=load_mode)
        x_mean = np.mean(x_train).astype('float32')
        x_std = np.std(x_train).astype('float32')
        if add_aug:
            train_gen = data_generator.Image_Generator(x_train, y_train, batch_size, aug_pol, x_mean=x_mean, x_std=x_std, pre_mode=self.pre_mode)
        else:
            #x_train = (x_train.astype('float32') - x_mean) / (x_std + 1e-7)
            x_train = data_generator.preprocess_input(x_train, x_mean, x_std, mode=self.pre_mode)
        
        #x_test = (x_test.astype('float32') - x_mean) / (x_std + 1e-7)
        x_test = data_generator.preprocess_input(x_test, x_mean, x_std, mode=self.pre_mode)

        if not add_aug:
            self.history = self.model.fit(x_train, y_train, validation_data=(x_test, y_test), epochs=epochs, batch_size=batch_size, callbacks=callbacks, workers=workers)
        else:
            self.history = self.model.fit(train_gen, validation_data=(x_test, y_test), epochs=epochs, steps_per_epoch=len(train_gen), callbacks=callbacks, workers=workers)
        
        if plot_history:
            plot_result(self.history)

        
if __name__ == "__main__":
    
    pass
