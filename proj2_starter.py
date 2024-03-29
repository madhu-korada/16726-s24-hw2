# --------------------------------------------------------
# Written by Yufei Ye and modified by Sheng-Yu Wang (https://github.com/JudyYe)
# Convert from MATLAB code https://inst.eecs.berkeley.edu/~cs194-26/fa18/hw/proj3/gradient_starter.zip
# --------------------------------------------------------
from __future__ import print_function

import argparse
import numpy as np
import cv2
import time
import imageio
import matplotlib.pyplot as plt

import scipy.sparse as sp
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import lsqr
from scipy.sparse.linalg import spsolve

def toy_recon(image):
    image = reconstruct_image(image)
    return image

# Function to reconstruct the image
def reconstruct_image(s):

    # Get the number of pixels in the image
    h, w = s.shape
    n_pixels = h * w
    
    # Initialize the sparse matrix A
    A = lil_matrix((n_pixels*2 + 1, n_pixels), dtype=np.float32)
    
    # The b vector is the known gradients and pixel intensity
    b = np.zeros((n_pixels*2 + 1, 1), dtype=np.float32)
    
    # Equation counter
    e = 0

    # Lambda function to convert 2D image coordinates to 1D variable index
    # im2var = lambda x, y: x * h + y
    im2var = np.arange(n_pixels).reshape((h, w)).astype(int)
    
    # Add gradient x es: v(x+1,y)−v(x,y) should match s(x+1,y)−s(x,y)
    for y in range(h):
        for x in range(w - 1):
            A[e, im2var[y, x + 1]] = 1
            A[e, im2var[y, x]] = -1
            b[e] = s[y, x + 1] - s[y, x]
            e += 1

    # Add gradient y es: v(x,y+1)−v(x,y) should match s(x,y+1)−s(x,y)
    for y in range(h - 1):
        for x in range(w):
            A[e, im2var[y + 1, x]] = 1
            A[e, im2var[y, x]] = -1
            b[e] = s[y + 1, x] - s[y, x]
            e += 1

    # Add the e for the top-left corner to match the source image
    A[e, im2var[0, 0]] = 1
    b[e] = s[0, 0]

    # Convert A to CSR format for efficient computation
    A = A.tocsr()

    # Solve the linear system
    # v = spsolve(A, b[:-1])
    v = lsqr(A, b)[0] * 255

    # Reshape the result into the original image shape
    v = v.reshape(s.shape)

    return v

def poisson_blend(fg, mask, bg):
    """
    Poisson Blending.
    :param fg: (H, W, C) source texture / foreground object
    :param mask: (H, W, 1)
    :param bg: (H, W, C) target image / background
    :return: (H, W, C)
    """
    # mask = mask.astype(bool)
    h_fg, w_fg, c = fg.shape
    h_bg, w_bg, _ = bg.shape
    h, w, c = min(h_fg, h_bg), min(w_fg, w_bg), c
    n_pixels = h * w
    im2var = np.arange(n_pixels).reshape((h, w)).astype(int)
    empty = np.zeros((h, w, c), dtype=int)
    
    # Initialize the sparse matrix A
    A = lil_matrix((n_pixels, n_pixels))
    mask_idx = np.where(mask)
    mask_len = len(mask_idx[0])
    # print(mask_len, n_pixels, h, w, c)
    for channel in range(c):
        e = 0
        b = np.zeros((n_pixels, 1))
        for index in range(mask_len):
            y, x = mask_idx[0][index], mask_idx[1][index]
            e = (y-1)*w + x
            
            # construct A
            if c == 0:
                # Handle boundary
                # if y > 0:
                #     A[e, im2var[y-1, x]] = -1
                # if y < h-1:
                #     A[e, im2var[y+1, x]] = -1
                # if x > 0:
                #     A[e, im2var[y, x-1]] = -1
                # if x < w-1:
                #     A[e, im2var[y, x+1]] = -1
                
                if (y - 1) >= 0:
                    if mask[y - 1, x]:
                        A[e, im2var[y - 1, x]] = -1
                if (y + 1) <= mask.shape[0] - 1:
                    if mask[y + 1, x]:
                        A[e, im2var[y + 1, x]] = -1
                if (x - 1) >= 0:
                    if mask[y, x - 1]:
                        A[e, im2var[y, x - 1]] = -1
                if (x + 1) <= mask.shape[1] - 1:
                    if mask[y, x + 1]:
                        A[e, im2var[y, x + 1]] = -1
                
                A[e, im2var[y, x]] = 4
            # construct b for all channels
            
            # construct fgs, bgs
            if y-1 < 0:
                fg_up = fg[y, x, channel]
                bg_up = 0
            else:
                fg_up = fg[y-1, x, channel]
                bg_up = bg[y-1, x, channel]
            if y+1 >= h:
                fg_down = fg[y, x, channel]
                bg_down = 0
            else:
                fg_down = fg[y+1, x, channel]
                bg_down = bg[y+1, x, channel]
            if x-1 < 0:
                fg_left = fg[y, x, channel]
                bg_left = 0
            else:
                fg_left = fg[y, x-1, channel]
                bg_left = bg[y, x-1, channel]
            if x+1 >= w:
                fg_right = fg[y, x, channel]
                bg_right = 0
            else:
                fg_right = fg[y, x+1, channel]
                bg_right = bg[y, x+1, channel]
            
            b[e] = 4 * fg[y, x, channel] - fg_up - fg_down - fg_left - fg_right #+ bg_up + bg_down + bg_left + bg_right
            
            # Handle boundary
            # if y > 0:
            #     b[e] += bg_up
            # if y < h-1:
            #     b[e] += bg_down
            # if x > 0:
            #     b[e] += bg_left
            # if x < w-1:
            #     b[e] += bg_right
            
            if y - 1 >= 0:
                if not mask[y - 1, x]:
                    b[e] += bg_up
            if y + 1 <= mask.shape[0] - 1:
                if not mask[y + 1, x]:
                    b[e] += bg_down
            if x - 1 >= 0:
                if not mask[y, x - 1]:
                    b[e] += bg_left
            if x + 1 <= mask.shape[1] - 1:
                if not mask[y, x + 1]:
                    b[e] += bg_right
                    
        # Solve the linear system
        v = lsqr(A.tocsr(), b)[0] * 255
        empty[:, :, channel] = v.reshape((h, w))
                
            
    empty = empty.astype(np.uint8) / 255.
    
    return empty * mask + bg * (1 - mask)


def mixed_blend(fg, mask, bg):
    """EC: Mix gradient of source and target"""
    return fg * mask + bg * (1 - mask)


def color2gray(rgb_image):
    """Naive conversion from an RGB image to a gray image."""
    return cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)


def mixed_grad_color2gray(rgb_image):
    """EC: Convert an RGB image to gray image using mixed gradients."""
    gray_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY) 
    hsv_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2HSV)
    s = hsv_image[:, :, 1] / 255.
    v = hsv_image[:, :, 2] / 255.
    mask = np.ones_like(gray_image)
    mixed_grad = mixed_blend(s, mask, v)
    return np.zeros_like(rgb_image)


if __name__ == '__main__':
    parser = argparse.ArgumentParser("Poisson blending.")
    parser.add_argument("-q", "--question", required=True, choices=["toy", "blend", "mixed", "color2gray"])
    args, _ = parser.parse_known_args()

    # Example script: python proj2_starter.py -q toy
    if args.question == "toy":
        image = imageio.imread('./data/toy_problem.png') / 255.
        image_hat = toy_recon(image)

        plt.subplot(121)
        plt.imshow(image, cmap='gray')
        plt.title('Input')
        plt.subplot(122)
        plt.imshow(image_hat, cmap='gray')
        plt.title('Output')
        plt.show()

        # Example script: python proj2_starter.py -q blend -s data/source_01_newsource.png -t data/target_01.jpg -m data/target_01_mask.png
    if args.question == "blend":
        parser.add_argument("-s", "--source", required=True)
        parser.add_argument("-t", "--target", required=True)
        parser.add_argument("-m", "--mask", required=True)
        args = parser.parse_args()

        source = imageio.imread(args.source) 
        target = imageio.imread(args.target) 
        mask = imageio.imread(args.mask)
        print(source.shape, target.shape, mask.shape)
        if source.shape[2] == 4:
            source = source[:, :, :3]
        if target.shape[2] == 4:
            target = target[:, :, :3]
        if mask.shape[2] == 4:
            mask = mask[:, :, :3]
        
        # if source and target are not the same size, resize them to the same size
        if source.shape[0] != target.shape[0] or source.shape[1] != target.shape[1]:
            source = cv2.resize(source, (target.shape[1], target.shape[0]))
            mask = cv2.resize(mask, (target.shape[1], target.shape[0]))
            print(source.shape, target.shape, mask.shape)    
        
        # after alignment (masking_code.py)
        ratio = 0.5
        fg = cv2.resize(source, (0, 0), fx=ratio, fy=ratio)
        bg = cv2.resize(target, (0, 0), fx=ratio, fy=ratio)
        mask = cv2.resize(mask, (0, 0), fx=ratio, fy=ratio)

        fg = fg / 255.
        bg = bg / 255.
        mask = (mask.sum(axis=2, keepdims=True) > 0)

        print(fg.shape, bg.shape, mask.shape)
        # exit()
        # print(mask)
        
        timer = time.time()
        blend_img = poisson_blend(fg, mask, bg)
        print("Time used:" + str(time.time() - timer))
        plt.subplot(121)
        plt.imshow(fg * mask + bg * (1 - mask))
        plt.title('Naive Blend')
        plt.subplot(122)
        plt.imshow(blend_img)
        plt.title('Poisson Blend')
        # save the plt result
        image_result = args.target.replace('.jpg', '_pb_result.png')
        # image_result = args.target.replace('.png', '_pb_result.png')
        print("Saving the result to", image_result)
        plt.savefig(image_result)
        plt.show()


    if args.question == "mixed":
        parser.add_argument("-s", "--source", required=True)
        parser.add_argument("-t", "--target", required=True)
        parser.add_argument("-m", "--mask", required=True)
        args = parser.parse_args()

        # after alignment (masking_code.py)
        ratio = 1
        fg = cv2.resize(imageio.imread(args.source), (0, 0), fx=ratio, fy=ratio)
        bg = cv2.resize(imageio.imread(args.target), (0, 0), fx=ratio, fy=ratio)
        mask = cv2.resize(imageio.imread(args.mask), (0, 0), fx=ratio, fy=ratio)

        fg = fg / 255.
        bg = bg / 255.
        mask = (mask.sum(axis=2, keepdims=True) > 0)

        blend_img = mixed_blend(fg, mask, bg)

        plt.subplot(121)
        plt.imshow(fg * mask + bg * (1 - mask))
        plt.title('Naive Blend')
        plt.subplot(122)
        plt.imshow(blend_img)
        plt.title('Mixed Blend')
        plt.show()

    if args.question == "color2gray":
        parser.add_argument("-s", "--source", required=True)
        args = parser.parse_args()

        rgb_image = imageio.imread(args.source)
        gray_image = color2gray(rgb_image)
        mixed_grad_img = mixed_grad_color2gray(rgb_image)

        plt.subplot(121)
        plt.imshow(gray_image, cmap='gray')
        plt.title('rgb2gray')
        plt.subplot(122)
        plt.imshow(mixed_grad_img, cmap='gray')
        plt.title('mixed gradient')
        plt.show()

    plt.close()
