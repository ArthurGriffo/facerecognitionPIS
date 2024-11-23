import os
import cv2
import numpy as np
import pickle as pkl
from time import time
from glob import glob
import face_recognition
from PIL import Image, ImageDraw
from scipy.spatial import distance
from msgs_pb2 import ObjectAnnotation
from is_utils import load_options, create_exporter, get_topic_id, draw_faces, to_np, annotate_image



class FaceRecognition(object):
    def __init__(self, persons, cosine_distance = True, threshold = 0.4):
        self.persons = persons
        self.threshold = threshold
        self.cosine_distance = cosine_distance
 
    def normalize(self,v):
        norm = np.linalg.norm(v)
        if norm == 0: 
            return v
        return v / norm

    def calculate_cosine_distance(self,encodings, compare):
        compare = self.normalize(compare)
        distances = np.array([float(distance.cosine(self.normalize(enc), compare)) for enc in encodings])
        return distances

    def calculate_euclidian_distance(self,encodings, compare):
        compare = self.normalize(compare)
        distances = np.array([float(distance.euclidean(self.normalize(enc), compare)) for enc in encodings])
        return distances



    def recognize(self, image):
        locations = face_recognition.api.face_locations(image, model = "cnn")
        face_encoding = face_recognition.face_encodings(image, locations)
        faces = []
        for enc, loc in zip(face_encoding, locations):
            dists = self.calculate_euclidian_distance(list(self.persons.values()), enc)
            index = np.argmin(dists)
            match = dists[index] < self.threshold
            person = "{}-{:.2f}".format(list(self.persons.keys())[index], dists[index]) if match else None
            # image = draw_faces(person, loc, image)
            faces.append((loc, dists[index], match, person ))
        return faces
            
    

