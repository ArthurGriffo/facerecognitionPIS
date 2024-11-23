import re
import sys
import cv2
import numpy as np
from datetime import datetime
from msgs_pb2 import Image, ObjectAnnotations
from google.protobuf.json_format import Parse
from is_wire.core import Logger, AsyncTransport
from opencensus.ext.zipkin.trace_exporter import ZipkinExporter

from options_pb2 import FaceRecognitionOptions

def annotate_image(frame, faces):
    h,w = frame.shape[:2]
    image = to_image(frame)
    image.resolution.width = w
    image.resolution.height = h
    if len(faces)>0:
        obs = ObjectAnnotations()
        for loc, dist, match, person in faces:
            (y1, x2, y2, x1) = loc
            ob = obs.objects.add()
            v1 = ob.region.vertices.add()
            v1.x = x1
            v1.y = y1
            v2 = ob.region.vertices.add()
            v2.x = x2
            v2.y = y2
            ob.label = person if person is not None else "unknown"
            ob.score = dist
        image.annotations.CopyFrom(obs)
    return image

def increase_bbox(img_shape,bboxes, borders = 0.0):
    if (len(bboxes)==0) or (bboxes is None): return bboxes
    bboxes = bboxes.reshape(-1,bboxes.shape[-1]).copy()
    if borders >0:
        h,w  = img_shape
        shift = (bboxes*borders).astype(int)
        bboxes[...,[0,1]] = np.where((bboxes[...,[0,1]]-shift[...,[0,1]]) > 0, bboxes[...,[0,1]]-shift[...,[0,1]],bboxes[...,[0,1]])
        bboxes[...,2] = np.where((bboxes[...,2]+shift[...,2]) <=w, bboxes[...,2]+shift[...,2],bboxes[...,2])
        bboxes[...,3] = np.where((bboxes[...,3]+shift[...,3]) <=h, bboxes[...,3]+shift[...,3],bboxes[...,3])
    return bboxes


def crop_image(image,rois):
    if rois is None: return img
    rois = rois.reshape(-1,rois.shape[-1])
    cropped_images = [image[r[1]:r[3],r[0]:r[2]]  for r in rois]
    return cropped_images
    


def get_topic_id(topic):
    values = str(topic).split(".")
    return values[1] if len(values)==3 else None


def create_exporter(service_name, uri):
    log = Logger(name="CreateExporter")
    zipkin_ok = re.match("http:\\/\\/([a-zA-Z0-9\\.]+)(:(\\d+))?", uri)
    if not zipkin_ok:
        log.critical("Invalid zipkin uri \"{}\", expected http://<hostname>:<port>", uri)
    exporter = ZipkinExporter(service_name=service_name,
                              host_name=zipkin_ok.group(1),
                              port=zipkin_ok.group(3),
                              transport=AsyncTransport)
    return exporter


def load_options():
    log = Logger(name='LoadingOptions')
    op_file = sys.argv[1] if len(sys.argv) > 1 else '/conf/options.json'
    try:
        with open(op_file, 'r') as f:
            try:
                op = Parse(f.read(), FaceRecognitionOptions())
                log.info('FaceRecognitionOptions: \n{}', op)
                return op
            except Exception as ex:
                log.critical('Unable to load options from \'{}\'. \n{}', op_file, ex)
    except Exception as ex:
        log.critical('Unable to open file \'{}\'', op_file)

def to_np(input_image):
    if isinstance(input_image, np.ndarray):
        output_image = input_image
    elif isinstance(input_image, Image):
        buffer = np.frombuffer(input_image.data, dtype=np.uint8)
        output_image = cv2.imdecode(buffer, flags=cv2.IMREAD_COLOR)
    else:
        output_image = np.array([], dtype=np.uint8)
    return output_image


def to_image(input_image, encode_format='.jpeg', compression_level=0.8):
    if isinstance(input_image, np.ndarray):
        if encode_format == '.jpeg':
            params = [cv2.IMWRITE_JPEG_QUALITY, int(compression_level * (100 - 0) + 0)]
        elif encode_format == '.png':
            params = [cv2.IMWRITE_PNG_COMPRESSION, int(compression_level * (9 - 0) + 0)]
        else:
            return Image()
        cimage = cv2.imencode(ext=encode_format, img=input_image, params=params)
        return Image(data=cimage[1].tobytes())
    elif isinstance(input_image, Image):
        return input_image
    else:
        return Image()

def draw_faces(image, annotations):
    if annotations is None: return image
    for obj in annotations.objects:
        x1 = int(obj.region.vertices[0].x)
        y1 = int(obj.region.vertices[0].y)
        x2 = int(obj.region.vertices[1].x)
        y2 = int(obj.region.vertices[1].y)
        name = str(obj.label)
        if (name is None) or (name == "unknown"): continue
        color  = (0,255,0)
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        w,h = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, thickness=2)[0]
        image = cv2.rectangle(image, (x1, y1 - h - 12), (x1+w+6, y1), color, cv2.FILLED)
        image = cv2.putText(image, name, (x1 + 6, y1 - 6),  cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 1)
    return image


def generate_default_image(size = (1920,180), text = "Aguardando Conexao!!!", title = "Videomonitoramento", with_header = True):
    font = cv2.FONT_HERSHEY_SIMPLEX
    textsize = cv2.getTextSize(text, font, 2, 2)[0]
    shiftx, shifty= textsize[0]//2, textsize[1]//2
    w,h = size
    header = 70 if with_header else 0
    img =np.zeros((h+header,w,3), np.uint8)
    textX, textY = w//2-shiftx, h//2-shifty+header
    cv2.putText(img, text,(textX, textY), font, 2, (255, 255, 255), 2, cv2.LINE_AA)
    if with_header:
      img[5:header-15] = 255
      img[header-5:header] = 255
      plot_date(img)
      plot_logos(img, title)
    return img

def plot_date(frame):
    x1, y1 = 5, 10

   # if self.frame.ndim == 3 else cv2.merge((self.frame,self.frame,self.frame))
    date = datetime.now()
    text = "{}".format(date.strftime("%d-%m-%Y %H:%M:%S"))
    t_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, thickness=2)[0]
    x2,y2 = t_size[0] + 5, 50
    cv2.rectangle(frame, (x1,y1), (x2,y2), (255,255,255), -1, cv2.LINE_AA)  # filled
    cv2.putText(frame, text, (x1,y1+t_size[1]//2+t_size[1]), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2, cv2.LINE_AA)

def plot_logos(frame, title = "Videomonitoramento"):
    logos = [("static/logo_pmes.jpg",(50,45)), ("static/logo_viros.jpg",(70,50)), ("static/logo_ufes.png", (70,45))]
    x_before = None
    pixels_between = 30
    fw = frame.shape[1]
    x = fw
    for idx,(logo, logo_shape) in enumerate(logos):
        logo = cv2.resize(cv2.imread(logo),logo_shape)
        if frame.ndim == 2:
            logo = cv2.cvtColor(logo, cv2.COLOR_BGR2GRAY)
        lw,lh = logo_shape
        x -= (lw + pixels_between)
        shift = (70-lh)//2 -5
        frame[shift:lh+shift, x:x+lw] = logo
        t_size = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, fontScale=1, thickness=2)[0]
        x1 = (frame.shape[1]//2) - (t_size[0]//2) + 100
        y1 = (70-t_size[1])//2
        x2,y2 = t_size[0] + 5, t_size[1] + 30
        cv2.rectangle(frame, (x1,y1), (x2,y2), (255,255,255), -1, cv2.LINE_AA)  # filled
        cv2.putText(frame, title, (x1,10+t_size[1]//2+t_size[1]), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,0), 2, cv2.LINE_AA)
        
def prepare_to_display(img, new_shape=(640, 640), color=114, title = None, border = 6, border_color = (255,255,255)):
    h,w = img.shape[:2]
    shift_border = 4
    c = None if img.ndim ==2 else img.shape[2]  
    if isinstance(new_shape, int):
        new_shape = (new_shape, new_shape)
    r = min(new_shape[0] / w, new_shape[1] / h)
    ratio = r, r  # width, height ratios
    new_unpad = int(round(w * r))-shift_border, int(round(h * r))-shift_border
    dw, dh = (new_shape[0] - new_unpad[0])//2, (new_shape[1] - new_unpad[1])//2  # wh padding
    if [w,h] != new_unpad:  # resize
        img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
    nw,nh = new_unpad
    top, left = dh, dw
    bottom, right = nh+dh, nw+dw
    img_border = np.empty((new_shape[1], new_shape[0],c)) if c is not None else np.empty((new_shape[1], new_shape[0]))
    img_border.fill(color)
    img_border[top:bottom, left:right] = img
    
    if title is not None:
        x1 = y1 = shift_border + border if border is not None else shift_border
        text_size = cv2.getTextSize(title, cv2.FONT_HERSHEY_COMPLEX, fontScale=1, thickness=2)[0]
        (x2, y2) = x1+text_size[0]+5, y1+text_size[1]+10
        cv2.rectangle(img_border, (x1+3,y1), (x2, y2), (255,255,255) , -1)  # filled
        cv2.putText(img_border, title, (x1+3,y1+text_size[1]+4 ), cv2.FONT_HERSHEY_COMPLEX, 1, (0,0,0), 2)

    if border:
        shift = border//2+1
        cv2.rectangle(img_border,(shift,shift),(new_shape[0]-shift,new_shape[1]-shift), border_color, int(border) )
    return img_border, ratio, (dw, dh)