# Copyright 2018 The TensorFlow Authors All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import numpy as np
import cv2

from datasets.BasicDataset import BasicDataset
from datasets.WIDERFaceDataset import WIDERFaceDataset
from datasets.LandmarkDataset import LandmarkDataset
from datasets.InferenceBatch import InferenceBatch
from datasets.TensorFlowDataset import TensorFlowDataset

from nets.FaceDetector import FaceDetector
from nets.NetworkFactory import NetworkFactory

from utils.convert_to_square import convert_to_square
from utils.IoU import IoU

class HardDataset(BasicDataset):

	def __init__(self, name):	
		BasicDataset.__init__(self, name)	

	def _generate_hard_samples(self, wider_data, detected_boxes, minimum_face, target_root_dir):

		image_file_names = wider_data['images']
		ground_truth_boxes = wider_data['bboxes']
    		number_of_images = len(image_file_names)

		if(not (len(detected_boxes) == number_of_images)):
			return(False)

		image_size = NetworkFactory.network_size(self.network_name())

		positive_dir = os.path.join(target_root_dir, 'positive')
		part_dir = os.path.join(target_root_dir, 'part')
		negative_dir = os.path.join(target_root_dir, 'negative')

		if(not os.path.exists(positive_dir)):
    			os.makedirs(positive_dir)
		if(not os.path.exists(part_dir)):
    			os.makedirs(part_dir)
		if(not os.path.exists(negative_dir)):
    			os.makedirs(negative_dir)

		positive_file = open(WIDERFaceDataset.positive_file_name(target_root_dir), 'w')
		part_file = open(WIDERFaceDataset.part_file_name(target_root_dir), 'w')
		negative_file = open(WIDERFaceDataset.negative_file_name(target_root_dir), 'w')

    		negative_images = 0
    		positive_images = 0
    		part_images = 0

    		for image_file_path, detected_box, ground_truth_box in zip(image_file_names, detected_boxes, ground_truth_boxes):
        		ground_truth_box = np.array(ground_truth_box, dtype=np.float32).reshape(-1, 4)

        		if( detected_box.shape[0] == 0 ):
            			continue

        		detected_box = convert_to_square(detected_box)
        		detected_box[:, 0:4] = np.round(detected_box[:, 0:4])

        		current_image = cv2.imread(image_file_path)

        		neg_num = 0
        		for box in detected_box:
            			x_left, y_top, x_right, y_bottom, _ = box.astype(int)
            			width = x_right - x_left + 1
            			height = y_bottom - y_top + 1

            			if( (width < minimum_face) or (x_left < 0) or (y_top < 0) or (x_right > current_image.shape[1] - 1) or (y_bottom > current_image.shape[0] - 1) ):
                			continue

            			current_IoU = IoU(box, ground_truth_box)
            			cropped_image = current_image[y_top:y_bottom + 1, x_left:x_right + 1, :]
            			resized_image = cv2.resize(cropped_image, (image_size, image_size), interpolation=cv2.INTER_LINEAR)

            			if( (np.max(current_IoU) < WIDERFaceDataset.negative_IoU()) and (neg_num < 60) ):
                			file_path = os.path.join(negative_dir, "%s.jpg" % negative_images)
                			negative_file.write(file_path + ' 0\n')
                			cv2.imwrite(file_path, resized_image)
                			negative_images += 1
                			neg_num += 1
            			else:
                			idx = np.argmax(current_IoU)
                			assigned_gt = ground_truth_box[idx]
                			x1, y1, x2, y2 = assigned_gt

                			offset_x1 = (x1 - x_left) / float(width)
                			offset_y1 = (y1 - y_top) / float(height)
                			offset_x2 = (x2 - x_right) / float(width)
                			offset_y2 = (y2 - y_bottom) / float(height)

                			if( np.max(current_IoU) >= WIDERFaceDataset.positive_IoU() ):
                    				file_path = os.path.join(positive_dir, "%s.jpg" % positive_images)
                    				positive_file.write(file_path + ' 1 %.2f %.2f %.2f %.2f\n' % (offset_x1, offset_y1, offset_x2, offset_y2))
                    				cv2.imwrite(file_path, resized_image)
                    				positive_images += 1

                			elif( np.max(current_IoU) >= WIDERFaceDataset.part_IoU() ):
                    				file_path = os.path.join(part_dir, "%s.jpg" % part_images)
                    				part_file.write(file_path + ' -1 %.2f %.2f %.2f %.2f\n' % (offset_x1, offset_y1, offset_x2, offset_y2))
                    				cv2.imwrite(file_path, resized_image)
                    				part_images += 1
    		negative_file.close()
    		part_file.close()
    		positive_file.close()

		return(True)

	def _generate_image_samples(self, annotation_file_name, annotation_image_dir, model_train_dir, minimum_face, target_root_dir):

		wider_dataset = WIDERFaceDataset()
		if(wider_dataset.read_annotation(annotation_image_dir, annotation_file_name)):
			wider_data = wider_dataset.data()
		else:
			return(False)

		test_data = InferenceBatch(wider_data['images'])

		if(not model_train_dir):
			model_train_dir = NetworkFactory.model_train_dir()			
		face_detector = FaceDetector(model_train_dir)

		previous_network = NetworkFactory.previous_network(self.network_name())
		detected_boxes, landmarks = face_detector.detect_face(test_data, previous_network)

		return(self._generate_hard_samples(wider_data, detected_boxes, minimum_face, target_root_dir))

	def _generate_image_list(self, target_root_dir):
		positive_file = open(WIDERFaceDataset.positive_file_name(target_root_dir), 'r')
		positive_data = positive_file.readlines()

		part_file = open(WIDERFaceDataset.part_file_name(target_root_dir), 'r')
		part_data = part_file.readlines()

		negative_file = open(WIDERFaceDataset.negative_file_name(target_root_dir), 'r')
		negative_data = negative_file.readlines()

		landmark_file = open(LandmarkDataset.landmark_file_name(target_root_dir), 'r')
		landmark_data = landmark_file.readlines()

		image_list_file = open(self._image_list_file_name(target_root_dir), 'w')

    		for i in np.arange(len(positive_data)):
        		image_list_file.write(positive_data[i])

    		for i in np.arange(len(negative_data)):
        		image_list_file.write(negative_data[i])

    		for i in np.arange(len(part_data)):
        		image_list_file.write(part_data[i])

    		for i in np.arange(len(landmark_data)):
        		image_list_file.write(landmark_data[i])

		return(True)

	def _generate_dataset(self, target_root_dir):
		tensorflow_dataset = TensorFlowDataset()

		if(not tensorflow_dataset.generate(WIDERFaceDataset.positive_file_name(target_root_dir), target_root_dir, 'positive')):
			return(False) 

		if(not tensorflow_dataset.generate(WIDERFaceDataset.part_file_name(target_root_dir), target_root_dir, 'part')):
			return(False) 

		if(not tensorflow_dataset.generate(WIDERFaceDataset.negative_file_name(target_root_dir), target_root_dir, 'negative')):
			return(False) 

		if(not tensorflow_dataset.generate(self._image_list_file_name(target_root_dir), target_root_dir, 'image_list')):
			return(False) 

		return(True)

	def generate(self, annotation_image_dir, annotation_file_name, landmark_image_dir, landmark_file_name, model_train_dir, minimum_face, target_root_dir):

		if(not os.path.isfile(annotation_file_name)):
			return(False)

		if(not os.path.exists(annotation_image_dir)):
			return(False)

		if(not os.path.isfile(landmark_file_name)):
			return(False)

		if(not os.path.exists(landmark_image_dir)):
			return(False)

		target_root_dir = os.path.expanduser(target_root_dir)
		target_root_dir = os.path.join(target_root_dir, self.network_name())
		if(not os.path.exists(target_root_dir)):
			os.makedirs(target_root_dir)

		image_size = NetworkFactory.network_size(self.network_name())

		print('Generating landmark samples.')
		if(not super(HardDataset, self)._generate_landmark_samples(landmark_image_dir, landmark_file_name, image_size, target_root_dir)):
			print('Error generating landmark samples.')
			return(False)
		print('Generated landmark samples.')

		print('Generating image samples.')
		if(not self._generate_image_samples(annotation_file_name, annotation_image_dir, model_train_dir, minimum_face, target_root_dir)):
			print('Error generating image samples.')
			return(False)
		print('Generated image samples.')

		if(not self._generate_image_list(target_root_dir)):
			return(False)

		print('Generating TensorFlow dataset.')
		if(not self._generate_dataset(target_root_dir)):
			print('Error generating TensorFlow dataset.')
			return(False)
		print('Generated TensorFlow dataset.')

		return(True)

