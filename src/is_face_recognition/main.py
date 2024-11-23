import os
import sys
import pickle as pkl
sys.path.append("./")
import dateutil.parser as dp
from msgs_pb2 import Image
from is_wire.core import Logger, Subscription, Message, Tracer

from is_face_recognition import FaceRecognition
from is_utils import load_options, create_exporter, get_topic_id, draw_faces, to_np, annotate_image
from stream_channel import StreamChannel





def span_duration_ms(span):
    dt = dp.parse(span.end_time) - dp.parse(span.start_time)
    return dt.total_seconds() * 1000.0

def load_persons(file_name = "/conf/persons.pkl"):
    with open(file_name, "rb") as file:
        persons = pkl.load(file)
    return persons

    
def main():
    service_name = "FaceRecognition.Recognize"
    log = Logger(name=service_name)
    op = load_options()
    persons = load_persons(op.persons_encondings)
    fr = FaceRecognition(persons)

    channel = StreamChannel(op.broker_uri)
    log.info('Connected to broker {}', op.broker_uri)

    exporter = create_exporter(service_name=service_name, uri=op.zipkin_uri)

    subscription = Subscription(channel=channel, name=service_name)
    subscription.subscribe(topic='CameraGateway.*.Frame')

    while True:
        msg, dropped = channel.consume_last(return_dropped=True)
        
        tracer = Tracer(exporter, span_context=msg.extract_tracing())
        span = tracer.start_span(name='recognize_and_render')
        recognition_span = None

        with tracer.span(name='unpack'):
            im = msg.unpack(Image)
            im_np = to_np(im)

        with tracer.span(name='recognize') as _span:
            camera_id = get_topic_id(msg.topic)
            faces = fr.recognize(im_np)
            recognition_span = _span

        with tracer.span(name='image_and_annotation_publish'):
            image = annotate_image(im_np, faces)
            ann_image_msg = Message()
            ann_image_msg.topic = 'FaceRecognition.{}.Frame'.format(camera_id)
            ann_image_msg.pack(image)
            channel.publish(ann_image_msg)
            

        span.add_attribute('Detections', len(faces))
        tracer.end_span()

        info = {
            'faces': len(faces),
            'dropped_messages': dropped,
            'took_ms': {
                'detection': round(span_duration_ms(recognition_span), 2),
                'service': round(span_duration_ms(span), 2)
            }
        }
        log.info('{}', str(info).replace("'", '"'))


if __name__ == "__main__":
    main()