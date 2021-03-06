import random

import numpy as np
import PIL
from PIL import Image, ImageDraw, ImageEnhance, ImageOps


def add_autoaugment(img, policy):

    shape = img.shape #shape[0]:height, shape[1]: width, shape[2]: channel

    if shape[2] == 3:
        fcol = tuple(np.mean(img, axis=(0,1)).astype('uint8'))
        fmod = 'RGB'
        #fsha = (shape[1], shape[0], 3)

    for p in policy:

        if random.random() < p['prob']:
            
            #Numpy method
            #invert
            if p['op'] == 'inv':
                img = np.invert(img)

            #flip
            elif p['op'] == 'mrx':
                img = np.fliplr(img)

            #zero-padding & random crop
            elif p['op'] == 'p&c':
                img = np.pad(img, ((4, 4), (4, 4), (0, 0)), mode='constant', constant_values=0)
                pxl = np.random.randint(8, size=2)
                img = img[pxl[0]:pxl[0]+shape[0],pxl[1]:pxl[1]+shape[1]]

            #PIL method
            else:
                if isinstance(img, np.ndarray):
                    img = Image.fromarray(img)

                #shear
                if p['op'] == 'srx':
                    shear = 0.3 * p['mag'] / 10.
                    if random.random() < 0.5:
                        shear = -shear
                    img = img.transform((shape[1], shape[0]), Image.AFFINE, (1, shear, 0, 0, 1, 0), resample=Image.BICUBIC, fillcolor=fcol)
                elif p['op'] == 'sry':
                    shear = 0.3 * p['mag'] / 10.
                    if random.random() < 0.5:
                        shear = -shear
                    img = img.transform((shape[1], shape[0]), Image.AFFINE, (1, 0, 0, shear, 1, 0), resample=Image.BICUBIC, fillcolor=fcol)

                #translation
                elif p['op'] == 'tlx':
                    shift = shape[1] * 0.45 * p['mag'] / 10.
                    if random.random() < 0.5:
                        shift = -shift
                    img = img.transform((shape[1], shape[0]), Image.AFFINE, (1, 0, shift, 0, 1, 0), resample=Image.BICUBIC, fillcolor=fcol)
                elif p['op'] == 'tly':
                    shift = shape[0] * 0.45 * p['mag'] / 10.
                    if random.random() < 0.5:
                        shift = -shift
                    img = img.transform((shape[1], shape[0]), Image.AFFINE, (1, 0, 0, 0, 1, shift), resample=Image.BICUBIC, fillcolor=fcol)
                
                #rotation
                elif p['op'] == 'rot':
                    angle = 30 * p['mag'] / 10.
                    if random.random() < 0.5:
                        angle = -angle
                    img = img.rotate(angle, resample=Image.BICUBIC, fillcolor=fcol)

                #autocontrast
                elif p['op'] == 'auc':
                    img = ImageOps.autocontrast(img, cutoff=2)

                #equalize
                elif p['op'] == 'eqz':
                    img = ImageOps.equalize(img)        

                #solarize
                elif p['op'] == 'sol':
                    th = int(255 * p['mag'] / 10.)
                    img = ImageOps.solarize(img, threshold=th)

                #posterize
                elif p['op'] == 'pos':
                    bit = int(4 + 4 * p['mag'] / 10.)
                    img = ImageOps.posterize(img, bit)

                #contrast
                elif p['op'] == 'con':
                    enha = 0.1 + 1.8 * p['mag'] / 10.
                    img = ImageEnhance.Contrast(img).enhance(enha)
                
                #saturation
                elif p['op'] == 'clr':
                    enha = 0.1 + 1.8 * p['mag'] / 10.
                    img = ImageEnhance.Color(img).enhance(enha)

                #brightness
                elif p['op'] == 'bri':
                    enha = 0.1 + 1.8 * p['mag'] / 10.
                    img = ImageEnhance.Brightness(img).enhance(enha)
                
                #sharpness
                elif p['op'] == 'sha':
                    enha = 0.1 + 1.8 * p['mag'] / 10.
                    img = ImageEnhance.Sharpness(img).enhance(enha)

                #cutout
                elif p['op'] == 'cut':
                    #mag = 1 - p['mag'] / 10.
                    #pxls = (np.random.randint(int(shape[1]*mag)), np.random.randint(int(shape[0]*mag)))
                    box_size = int(shape[0] * p['mag'] / 20.)
                    box_center = (np.random.randint(shape[1]), np.random.randint(shape[0]))
                    box_w1 = box_center[0]-box_size
                    box_h1 = box_center[1]-box_size
                    box_w2 = box_center[0]+box_size
                    box_h2 = box_center[1]+box_size
                    draw = ImageDraw.Draw(img)
                    draw.rectangle([box_w1, box_h1, box_w2, box_h2], fill=tuple(fcol))

                else:
                    raise Exception('Unknown augment operation: %s' % (p['op']))
            
    img = np.asarray(img, dtype=np.uint8)

    return img


def get_auto_policies(name):
    name = name.lower()
    policies = []

    if 'base' in name:
        policies = []
    
    elif 'cifar' in name:
        policies.append(({'op': 'inv', 'prob': 0.1, 'mag': 7}, {'op': 'con', 'prob': 0.2, 'mag': 6}))
        policies.append(({'op': 'rot', 'prob': 0.7, 'mag': 2}, {'op': 'tlx', 'prob': 0.3, 'mag': 9}))
        policies.append(({'op': 'sha', 'prob': 0.8, 'mag': 1}, {'op': 'sha', 'prob': 0.9, 'mag': 3}))
        policies.append(({'op': 'sry', 'prob': 0.5, 'mag': 8}, {'op': 'tly', 'prob': 0.7, 'mag': 9}))
        policies.append(({'op': 'auc', 'prob': 0.5, 'mag': 8}, {'op': 'eqz', 'prob': 0.9, 'mag': 2}))
        policies.append(({'op': 'srx', 'prob': 0.2, 'mag': 7}, {'op': 'pos', 'prob': 0.3, 'mag': 7}))
        policies.append(({'op': 'clr', 'prob': 0.4, 'mag': 3}, {'op': 'bri', 'prob': 0.6, 'mag': 7}))
        policies.append(({'op': 'sha', 'prob': 0.3, 'mag': 9}, {'op': 'bri', 'prob': 0.7, 'mag': 9}))
        policies.append(({'op': 'eqz', 'prob': 0.6, 'mag': 5}, {'op': 'eqz', 'prob': 0.5, 'mag': 1}))
        policies.append(({'op': 'con', 'prob': 0.6, 'mag': 7}, {'op': 'sha', 'prob': 0.6, 'mag': 5}))
        policies.append(({'op': 'clr', 'prob': 0.7, 'mag': 7}, {'op': 'tlx', 'prob': 0.5, 'mag': 8}))
        policies.append(({'op': 'eqz', 'prob': 0.3, 'mag': 7}, {'op': 'auc', 'prob': 0.4, 'mag': 8}))
        policies.append(({'op': 'tly', 'prob': 0.4, 'mag': 3}, {'op': 'sha', 'prob': 0.2, 'mag': 6}))
        policies.append(({'op': 'bri', 'prob': 0.9, 'mag': 6}, {'op': 'clr', 'prob': 0.2, 'mag': 8}))
        policies.append(({'op': 'sol', 'prob': 0.5, 'mag': 2}, {'op': 'inv', 'prob': 0.0, 'mag': 3}))
        policies.append(({'op': 'eqz', 'prob': 0.2, 'mag': 0}, {'op': 'auc', 'prob': 0.6, 'mag': 0}))
        policies.append(({'op': 'eqz', 'prob': 0.2, 'mag': 8}, {'op': 'eqz', 'prob': 0.6, 'mag': 4}))
        policies.append(({'op': 'clr', 'prob': 0.9, 'mag': 9}, {'op': 'eqz', 'prob': 0.6, 'mag': 6}))
        policies.append(({'op': 'auc', 'prob': 0.8, 'mag': 4}, {'op': 'sol', 'prob': 0.2, 'mag': 8}))
        policies.append(({'op': 'bri', 'prob': 0.1, 'mag': 3}, {'op': 'clr', 'prob': 0.7, 'mag': 0}))
        policies.append(({'op': 'sol', 'prob': 0.4, 'mag': 5}, {'op': 'auc', 'prob': 0.9, 'mag': 3}))
        policies.append(({'op': 'tly', 'prob': 0.9, 'mag': 9}, {'op': 'tly', 'prob': 0.7, 'mag': 9}))
        policies.append(({'op': 'auc', 'prob': 0.9, 'mag': 2}, {'op': 'sol', 'prob': 0.8, 'mag': 3}))
        policies.append(({'op': 'eqz', 'prob': 0.8, 'mag': 8}, {'op': 'inv', 'prob': 0.1, 'mag': 3}))
        policies.append(({'op': 'tly', 'prob': 0.7, 'mag': 9}, {'op': 'auc', 'prob': 0.9, 'mag': 1}))

    elif 'svhn' in name:
        policies.append(({'op': 'srx', 'prob': 0.9, 'mag': 4}, {'op': 'inv', 'prob': 0.2, 'mag': 3}))
        policies.append(({'op': 'sry', 'prob': 0.9, 'mag': 8}, {'op': 'inv', 'prob': 0.7, 'mag': 5}))
        policies.append(({'op': 'eqz', 'prob': 0.6, 'mag': 5}, {'op': 'sol', 'prob': 0.6, 'mag': 6}))
        policies.append(({'op': 'inv', 'prob': 0.9, 'mag': 3}, {'op': 'eqz', 'prob': 0.6, 'mag': 3}))
        policies.append(({'op': 'eqz', 'prob': 0.6, 'mag': 1}, {'op': 'rot', 'prob': 0.9, 'mag': 3}))
        policies.append(({'op': 'srx', 'prob': 0.9, 'mag': 4}, {'op': 'auc', 'prob': 0.8, 'mag': 3}))
        policies.append(({'op': 'sry', 'prob': 0.9, 'mag': 8}, {'op': 'inv', 'prob': 0.4, 'mag': 5}))
        policies.append(({'op': 'sry', 'prob': 0.9, 'mag': 5}, {'op': 'sol', 'prob': 0.2, 'mag': 6}))
        policies.append(({'op': 'inv', 'prob': 0.9, 'mag': 6}, {'op': 'auc', 'prob': 0.8, 'mag': 1}))
        policies.append(({'op': 'eqz', 'prob': 0.6, 'mag': 3}, {'op': 'rot', 'prob': 0.9, 'mag': 3}))
        policies.append(({'op': 'srx', 'prob': 0.9, 'mag': 4}, {'op': 'sol', 'prob': 0.3, 'mag': 3}))
        policies.append(({'op': 'sry', 'prob': 0.8, 'mag': 8}, {'op': 'inv', 'prob': 0.7, 'mag': 4}))
        policies.append(({'op': 'eqz', 'prob': 0.9, 'mag': 5}, {'op': 'tly', 'prob': 0.6, 'mag': 6}))
        policies.append(({'op': 'inv', 'prob': 0.9, 'mag': 4}, {'op': 'eqz', 'prob': 0.6, 'mag': 7}))
        policies.append(({'op': 'con', 'prob': 0.3, 'mag': 3}, {'op': 'rot', 'prob': 0.8, 'mag': 4}))
        policies.append(({'op': 'inv', 'prob': 0.8, 'mag': 5}, {'op': 'tly', 'prob': 0.0, 'mag': 3}))
        policies.append(({'op': 'sry', 'prob': 0.7, 'mag': 6}, {'op': 'sol', 'prob': 0.4, 'mag': 8}))
        policies.append(({'op': 'inv', 'prob': 0.6, 'mag': 4}, {'op': 'rot', 'prob': 0.8, 'mag': 4}))
        policies.append(({'op': 'sry', 'prob': 0.3, 'mag': 7}, {'op': 'tlx', 'prob': 0.9, 'mag': 4}))
        policies.append(({'op': 'srx', 'prob': 0.1, 'mag': 6}, {'op': 'inv', 'prob': 0.6, 'mag': 5}))
        policies.append(({'op': 'sol', 'prob': 0.7, 'mag': 2}, {'op': 'tly', 'prob': 0.6, 'mag': 7}))
        policies.append(({'op': 'sry', 'prob': 0.8, 'mag': 4}, {'op': 'inv', 'prob': 0.8, 'mag': 8}))
        policies.append(({'op': 'srx', 'prob': 0.7, 'mag': 9}, {'op': 'tly', 'prob': 0.8, 'mag': 3}))
        policies.append(({'op': 'sry', 'prob': 0.8, 'mag': 5}, {'op': 'auc', 'prob': 0.7, 'mag': 3}))
        policies.append(({'op': 'srx', 'prob': 0.7, 'mag': 2}, {'op': 'inv', 'prob': 0.1, 'mag': 5}))

    else:
        raise Exception('Unknown policy: %s' % (name))

    return policies


if __name__ == "__main__":
    pass
