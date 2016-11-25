"""
The main runtime file
"""

from __future__ import print_function
import tensorflow as tf
slim = tf.contrib.slim
from eegnet_v1 import eegnet_v1 as network
from read_preproc_dataset import read_dataset

##
# Directories
##
tf.app.flags.DEFINE_string('dataset_dir', '/shared/dataset/test/*.tfr',
                           'Where dataset TFReaders files are loaded from.')

tf.app.flags.DEFINE_string('checkpoint_dir', '/shared/checkpoints',
                           'Where checkpoints are loaded from.')

tf.app.flags.DEFINE_string('log_dir', '/shared/logs',
                           'Where checkpoints and event logs are written to.')

##
# Train configuration
##
tf.app.flags.DEFINE_boolean('is_training', False,
                            'Determines shuffling, dropout/batch_norm behaviour and removal.')

tf.app.flags.DEFINE_integer('num_splits', 1,
                            'Splits to perform on each TFRecord file.')

tf.app.flags.DEFINE_integer('batch_size', 1,
                            'Training batch size.')

FLAGS = tf.app.flags.FLAGS


def get_init_fn():
    return None
    """Loads the NN"""
    if FLAGS.checkpoint_dir is None:
        raise ValueError('None supplied. Supply a valid checkpoint directory with --checkpoint_dir')

    checkpoint_path = tf.train.latest_checkpoint(FLAGS.checkpoint_dir)

    if checkpoint_path is None:
        raise ValueError('No checkpoint found in %s. Supply a valid --checkpoint_dir' %
                         FLAGS.checkpoint_dir)

    tf.logging.info('Loading model from %s' % checkpoint_path)

    return slim.assign_from_checkpoint_fn(
        model_path=checkpoint_path,
        var_list=slim.get_model_variables(),
        ignore_missing_vars=True)



def save_submit(grades_list):
    """Save the Kaggle submition file for Epilepsia Challeng"""

    filep = open("submission.csv", "w") #open submition file for writing

    filep.write("File,Class\n") #save header

    for key in grades_list:
        filep.write("%s,%s\n"%(key[0][0].replace('tfr','mat'), key[1][0][0]))


    filep.close()



def main(_):
    """Generates the TF graphs and loads the NN"""
    tf.logging.set_verbosity(tf.logging.INFO)
    with tf.Graph().as_default() as graph:
        # Input pipeline
        filenames = tf.gfile.Glob(FLAGS.dataset_dir)
        data, fnames = read_dataset(filenames,
                                    num_splits=FLAGS.num_splits,
                                    batch_size=FLAGS.batch_size)

        shape = data.get_shape().as_list()
        tf.logging.info('Batch size/num_points: %d/%d' % (shape[0], shape[2]))

        # Create model
        _, predictions = network(data, is_training=FLAGS.is_training)
        predictions = tf.slice(predictions, [0, 1], [-1, 1]) #slicing for filename and P(1)


        # predictions = predictions[1] #slicing the predictions to contain only prob of 1s

        tf.logging.info('Network model created.')

        # This ensures that we make a single pass over all of the data.
        num_batches = len(filenames)*FLAGS.num_splits//float(FLAGS.batch_size)

        #
        # Evaluate
        #
        supervi = tf.train.Supervisor(graph=graph,
                                      logdir=FLAGS.log_dir,
                                      summary_op=None,
                                      summary_writer=None,
                                      global_step=slim.get_or_create_global_step(),
                                      init_fn=get_init_fn()) # restores checkpoint

        with supervi.managed_session(master='', start_standard_services=False) as sess:
            tf.logging.info('Starting evaluation.')
            # Start queues for TFRecords reading
            supervi.start_queue_runners(sess)

            grades = list()
            for i in range(int(3)):
                tf.logging.info('Executing eval_op %d/%d', i + 1, num_batches)
                grades.append(sess.run([fnames, predictions]))
                # print(grades)

            save_submit(grades)


if __name__ == '__main__':
    tf.app.run()