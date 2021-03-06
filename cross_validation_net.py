from dataLoader import DataLoader, compute_euclidean_distance, prepare_input_img
from network import create_model
import os
import numpy as np
from custom_KFold import MyKFold
from block_matching_utils import find_template_pixel, NCC_best_template_search
from PIL import Image
import pandas as pd
from tensorflow import keras
from utils import get_logger, get_default_params
import skimage
import tensorflow as tf

'''
Mélanie Bernhardt - ETH Zurich
CLUST Challenge

Defines the file to run cross-validation only on net performance
(not overall tracking.)
'''

def run_cv(fold_iterator, logger, params_dict, upsample=True):
    for traindirs, testdirs in fold_iterator:
        # TRAIN LOCAL PREDICTION MODEL
        # Generators
        logger.info('############ FOLD #############')
        logger.info('Training folders are {}'.format(traindirs))
        training_generator = DataLoader(
            data_dir, traindirs, 32,
            width_template=params_dict['width'], upsample=upsample)
        validation_generator = DataLoader(
            data_dir, testdirs, 32,
            width_template=params_dict['width'],
            type='val',upsample=upsample)

        # Design model
        model = create_model(params_dict['width']+1,
                             params_dict['h1'],
                             params_dict['h2'],
                             params_dict['h3'],
                             embed_size=params_dict['embed_size'],
                             drop_out_rate=params_dict['dropout_rate'],
                             use_batch_norm=params_dict['use_batchnorm'])
        # Train model on training dataset
        '''
        model.fit_generator(generator=training_generator,
                            validation_data=validation_generator,
                            use_multiprocessing=True,
                            epochs=params_dict['n_epochs'],
                            workers=6)
        '''
        try:
            model.load_weights(os.path.join(checkpoint_dir, 'model22.h5'))
        except OSError:
            print('here')
            model.fit_generator(generator=training_generator,
                                validation_data=validation_generator,
                                use_multiprocessing=True,
                                epochs=params_dict['n_epochs'],
                                workers=4, max_queue_size=20)
            model.save_weights(os.path.join(checkpoint_dir, 'model.h5'))
        metrics = model.evaluate_generator(generator=validation_generator, workers=4, max_queue_size=20)
        logger.info(metrics)

if __name__ == '__main__':
    np.random.seed(seed=42)
    exp_name = 'cv_25_0_64_50'
    params_dict = {'dropout_rate': 0.5, 'n_epochs': 25,
                   'h3':0, 'embed_size': 64, 'width': 50, 'search_w': 50}

    # ============ DATA AND SAVING DIRS SETUP ========== #
    data_dir = os.getenv('DATA_PATH')
    exp_dir = os.getenv('EXP_PATH')
    checkpoint_dir = os.path.join(exp_dir, exp_name)
    if not os.path.exists(checkpoint_dir):
        os.makedirs(checkpoint_dir)
    # ============= LOGGER SETUP ================= #
    # create logger
    logger = get_logger(checkpoint_dir)

    # Set the default parameters
    params_dict = get_default_params(params_dict)

    # ========= PRINT CONFIG TO LOG ======== #
    logger.info('Running %s experiment ...' % exp_name)
    logger.info('\n Settings for this expriment are: \n')
    for key in params_dict.keys():
        logger.info('  {}: {}'.format(key.upper(), params_dict[key]))
    logger.info('Saving checkpoint to {}'.format(checkpoint_dir))

    # KFold iterator
    kf = MyKFold(data_dir, n_splits=5)
    fold_iterator = kf.getFolderIterator()
    gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.666)

    sess = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options))
    tf.keras.backend.set_session(sess)
    run_cv(fold_iterator, logger, params_dict,upsample=True)

