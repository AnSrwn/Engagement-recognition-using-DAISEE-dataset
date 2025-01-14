from flask import Flask, render_template, Response
from camera import VideoCameraModel
import logging
import tensorflow as tf
from tensorflow import keras
from tensorflow.compat.v1 import graph_util
from tensorflow.python.keras import backend as K
from tensorflow.python.keras.models import load_model
import os
import cv2
import numpy as np

physical_devices = tf.config.experimental.list_physical_devices('GPU')
if len(physical_devices) > 0:
    tf.config.experimental.set_memory_growth(physical_devices[0], True)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


def gen(camera):
    face_cascade_path = "dataset/haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(face_cascade_path)
    labels_ = ['Bored', 'Engaged', 'Confused', 'Frustrated']
    IMG_HEIGHT, IMG_WIDTH = 224, 224
    with detection_graph.as_default():
        with tf.compat.v1.Session(graph=detection_graph) as sess:
            while True:
                frame = camera.get_frame()
                # Detect face using haar cascade classifier
                faces_rects = face_cascade.detectMultiScale(frame, 1.3, 5)
                for x, y, w, h in faces_rects:
                    # Resizing
                    image = np.array(frame)
                    image = image[y:y + h, x:x + w]
                    image = cv2.resize(image, (IMG_HEIGHT, IMG_WIDTH), interpolation=cv2.INTER_AREA)
                    image = np.expand_dims(image, axis=0)
                    # classification
                    if use_pretrained:
                        input_tensor_name = 'mobilenetv2_1.00_224_input:0'
                    else:
                        if data_augmentation:
                            input_tensor_name = 'input_2:0'
                        else:
                            input_tensor_name = 'conv2d_input:0'

                    # # read pb into graph_def
                    # with tf.io.gfile.GFile('checkpoints/scratch_aug/model.pb', "rb") as f:
                    #     graph_def = tf.compat.v1.GraphDef()
                    #     graph_def.ParseFromString(f.read())

                    # # import graph_def
                    # with tf.Graph().as_default() as graph:
                    #     tf.import_graph_def(graph_def)

                    # # print operations
                    # for op in graph.get_operations():
                    #     if op.type == "Placeholder":
                    #         print(op.name)

                    input_tensor = detection_graph.get_tensor_by_name(input_tensor_name)
                    output_tensor = detection_graph.get_tensor_by_name('prediction/Sigmoid:0')
                    output_logits = sess.run(output_tensor, feed_dict={input_tensor: image})
                    text_up = 'Bored: '+str(round(output_logits[0][0]))+' Engaged: '+str(round(output_logits[0][1]))
                    text_down = 'Confused: '+str(round(output_logits[0][2]))+' Frustrated: '+str(round(output_logits[0][2]))
                    # Draw rect
                    cv2.rectangle(frame, (int(x), int(y)), (int(x+w), int(y+h)), (0, 255, 0), 2)
                    # Write label Up
                    cv2.putText(frame, text_up, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36, 255, 12), 2)
                    # Write label Down
                    cv2.putText(frame, text_down, (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36, 255, 12), 2)
                    break
                try:
                    ret, jpeg = cv2.imencode('.jpg', frame)
                    frame = jpeg.tobytes()
                    yield (b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
                except cv2.error as e:
                    print("No frame: {e}")


@app.route('/video_feed')
def video_feed():
    return Response(gen(VideoCameraModel()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    checkpoint_dir = 'checkpoints/'
    use_pretrained = False
    data_augmentation = True
    pretrained_name = 'mobilenet'
    if use_pretrained:
        checkpoint_dir += pretrained_name
    else:
        checkpoint_dir += 'scratch'

    if data_augmentation:
        checkpoint_dir += '_aug/'

    # necessary !!!
    tf.compat.v1.disable_eager_execution()

    last_model = os.listdir(checkpoint_dir)[-1]
    # chosen_model = 'Epoch_439_model.hp5'
    chosen_model = last_model
    save_pb = True
    if save_pb:
        h5_path = checkpoint_dir + chosen_model
        model = load_model(h5_path, compile=False)
        # save pb
        with K.get_session() as sess:
            output_names = [out.op.name for out in model.outputs]
            input_graph_def = sess.graph.as_graph_def()
            for node in input_graph_def.node:
                node.device = ""
            graph = graph_util.remove_training_nodes(input_graph_def)
            graph_frozen = graph_util.convert_variables_to_constants(sess, graph, output_names)
            tf.io.write_graph(graph_frozen, checkpoint_dir, 'model.pb', as_text=False)
        logging.info("save pb successfully！")

    # Load Frozen graph
    pb_file = checkpoint_dir + 'model.pb'
    # Load a (frozen) Tensorflow model into memory.
    detection_graph = tf.Graph()
    with detection_graph.as_default():
        od_graph_def = tf.compat.v1.GraphDef()
        with tf.io.gfile.GFile(pb_file, 'rb') as fid:
            serialized_graph = fid.read()
            od_graph_def.ParseFromString(serialized_graph)
            tf.import_graph_def(od_graph_def, name='')

    app.run(host='0.0.0.0', debug=True)
