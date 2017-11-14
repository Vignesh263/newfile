# Copyright 2017 The TensorFlow Authors. All Rights Reserved.
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

"""This class manages the location of labels over an image.

The objective is to minimize overlapping. The current algo is pretty simple but covers
the majority of cases.
"""

# Max overlapping = 20%
MAX_COVERING = 0.2

class BoxLabelManager:

    label_bounding_boxes = []
    bounding_boxes       = []
    image_width  = 0
    image_height = 0
    draw_rectangle = False
    draw_label     = False

    def __init__(self, _image_width, _image_height):
        self.image_width  = _image_width
        self.image_height = _image_height
        self.label_bounding_boxes = []
        self.bounding_boxes       = []

    def setDrawRectangle(self, _value):
        self.draw_rectangle = _value;

    def isDrawRectangle(self):
        return self.draw_rectangle

    def isDrawLabel(self):
        return self.draw_label

    def setDrawLabel(self, _value):
        self.draw_label = _value;

    #
    def addBoundingBoxAndLabelBox(self, _bounding_box, _label_width, _label_height):
        """" Return the coordinates of the best label box and store it.

                Args:
                    _bounding_box: first box
                    _label_width: second box
                    _label_height:

                Returns:
                    A bounding box for the label as [left, top, right, bottom]

                """

        # Add the bounding box, for fun ;-)
        self.bounding_boxes.append(_bounding_box)

        left   = _bounding_box[0]
        right  = _bounding_box[2]
        top    = _bounding_box[1]
        bottom = _bounding_box[3]

        # Keep the initial propose
        first_proposal = [ left , top - _label_height, left + _label_width , top]

        # The offset will slide the box propose to the right or to the left
        x_offset = 0
        stay_in_the_loop =  True
        while stay_in_the_loop:

            #
            # Proposal 1
            #
            # First label box proposal, top/left

            proposal_label_box =  [ left + x_offset, top - _label_height, left + _label_width + x_offset, top]


            # Surface if over an existing label box 30% of area
            if self.isOverALabel(proposal_label_box)< MAX_COVERING:
                # We are done
                self.label_bounding_boxes.append(proposal_label_box)
                return proposal_label_box

            #
            # Proposal 2
            #
            # Second proposal, bottom/left
            proposal_label_box = [left + x_offset, bottom , left + _label_width + x_offset, bottom + _label_height]
            if self.isOverALabel(proposal_label_box) < MAX_COVERING:
                # We are done
                self.label_bounding_boxes.append(proposal_label_box)
                return proposal_label_box

            #
            # Proposal 3
            #
            # Third proposal, top/right
            proposal_label_box = [right-_label_width - x_offset, top - _label_height, right - x_offset, top]
            if self.isOverALabel(proposal_label_box) < MAX_COVERING:
                # We are done
                self.label_bounding_boxes.append(proposal_label_box)
                return proposal_label_box

            #
            # Proposal 4
            #
            # Third proposal, bottom/right
            proposal_label_box = [right-_label_width - x_offset, bottom , right - x_offset, bottom + _label_height]
            if self.isOverALabel(proposal_label_box) < MAX_COVERING:
                # We are done
                self.label_bounding_boxes.append(proposal_label_box)
                return proposal_label_box

            x_offset = x_offset + 20
            if x_offset < (right - left) - _label_width:
                stay_in_the_loop = False

        # End of the while

        # Last chance
        # Rectangle is as height as the image (95%)
        if (bottom - top) > (0.95 * self.image_height):
            # Inside the rectangle
            first_proposal = [left, top, left + _label_width, top + _label_height]

        return first_proposal

    # Does the box proposal over an existing label ?
    def isOverALabel(self, _label_box):
        iou = 0
        if (_label_box[0] < 0) or (_label_box[2]>self.image_width) or \
            (_label_box[1] < 0) or (_label_box[3] > self.image_height):
            return 1

        # Take the worst situation
        for current_box in self.label_bounding_boxes:
            current_iou = self.get_intersection_over_union_v2(_label_box, current_box)
            if current_iou > iou:
                iou = current_iou
        return iou

    def get_intersection_over_union_v2(self, boxA, boxB):
        """" Just compute the intersection over union of 2 boxes, the result is in [0,1].
        Args:
            boxA: first box
            boxB: second box

        Returns:
            The value of IOU as a float

        """

        # Is there an intersection
        if (max (boxA[0], boxA[2]) < min((boxB[0], boxB[2]))):
            return 0
        if (max (boxB[0], boxB[2]) < min((boxA[0], boxA[2]))):
            return 0
        if (max (boxA[1], boxA[3]) < min((boxB[1], boxB[3]))):
            return 0
        if (max (boxB[1], boxB[3]) < min((boxA[1], boxA[3]))):
            return 0

        # determine the (x, y)-coordinates of the intersection rectangle
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        # compute the area of intersection rectangle
        interArea = (xB - xA + 1) * (yB - yA + 1)

        # compute the area of both the prediction and ground-truth
        # rectangles
        boxAArea = (boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1)
        boxBArea = (boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1)

        # compute the intersection over union by taking the intersection
        # area and dividing it by the sum of prediction + ground-truth
        # areas - the interesection area
        iou = interArea / float(boxAArea + boxBArea - interArea)

        # return the intersection over union value
        return iou
