
import os
import io
import numpy as np
import platform
from PIL import ImageFont, ImageDraw, Image
import matplotlib.pyplot as plt
import cv2
from google.cloud import vision

def plt_imshow(title='image', img=None, figsize=(8 ,5)):
    plt.figure(figsize=figsize)

    if type(img) == list:
        if type(title) == list:
            titles = title
        else:
            titles = []

            for i in range(len(img)):
                titles.append(title)

        for i in range(len(img)):
            if len(img[i].shape) <= 2:
                rgbImg = cv2.cvtColor(img[i], cv2.COLOR_GRAY2RGB)
            else:
                rgbImg = cv2.cvtColor(img[i], cv2.COLOR_BGR2RGB)

            plt.subplot(1, len(img), i + 1), plt.imshow(rgbImg)
            plt.title(titles[i])
            plt.xticks([]), plt.yticks([])

        plt.show()
    else:
        if len(img.shape) < 3:
            rgbImg = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        else:
            rgbImg = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        plt.imshow(rgbImg)
        plt.title(title)
        plt.xticks([]), plt.yticks([])
        plt.show()

# 이미지에 텍스트 표시를 위한 함수 정의
def putText(image, text, x, y, color=(0, 255, 0), font_size=22):
    if type(image) == np.ndarray:
        color_converted = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(color_converted)

    # 기본 폰트를 로드
    image_font = ImageFont.load_default()
    draw = ImageDraw.Draw(image)

    draw.text((x, y), text, font=image_font, fill=color)

    numpy_image = np.array(image)
    opencv_image = cv2.cvtColor(numpy_image, cv2.COLOR_RGB2BGR)

    return opencv_image

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/content/summer-branch-410822-fc2d8cfced84.json'

client_options = {'api_endpoint': 'eu-vision.googleapis.com'}
client = vision.ImageAnnotatorClient(client_options=client_options)

path = '/content/img4.jpg'
with io.open(path, 'rb') as image_file:
    content = image_file.read()

image = vision.Image(content=content)

response = client.text_detection(image=image)
texts = response.text_annotations

# 텍스트와 바운딩 박스 정보를 담을 리스트
text_boxes = []

# 텍스트 바운딩 박스 좌표 출력
for i, text in enumerate(texts):
    if (i == 0):
      continue;

    vertices = [(vertex.x, vertex.y) for vertex in text.bounding_poly.vertices]
    # 중점 계산
    center_x = sum([v[0] for v in vertices]) / 4
    center_y = sum([v[1] for v in vertices]) / 4

    text_info = {
        "text": text.description,
        "bbox": vertices,
        "center": (center_x, center_y)
    }
    text_boxes.append(text_info)
    print(f'Text {i + 1}: {text_info["text"]}')
    print(f'Bounding Box Vertices===: {text_info["bbox"]}')
    print(f'Center===: {text_info["center"]}')
    print('---')

# 중점의 y 좌표를 기준으로 정렬
sorted_boxes_y = sorted(text_boxes, key=lambda x: x["center"][1])

# 바운딩 박스를 그룹화할 리스트
grouped_boxes = []

# 그룹화할 첫 번째 박스 추가
current_group = [sorted_boxes_y[0]]

# 그룹 내에서의 tolerance factor
group_tolerance_factor = 20

# 바운딩 박스를 그룹화
for i in range(1, len(sorted_boxes_y)):
    prev_center_y = current_group[-1]["center"][1]
    current_center_y = sorted_boxes_y[i]["center"][1]

    if abs(current_center_y - prev_center_y) < group_tolerance_factor:
        current_group.append(sorted_boxes_y[i])
    else:
        # 그룹 내에서 x 좌표를 기준으로 정렬
        sorted_group = sorted(current_group, key=lambda x: x["center"][0])
        grouped_boxes.extend(sorted_group)
        current_group = [sorted_boxes_y[i]]

# 마지막 그룹에 대한 정렬
sorted_group = sorted(current_group, key=lambda x: x["center"][0])
grouped_boxes.extend(sorted_group)

# 정렬된 바운딩 박스의 텍스트 출력
for box in grouped_boxes:
    print(box["text"])
    print(box["center"])

# 중점의 y 좌표를 기준으로 정렬
sorted_boxes_y = sorted(text_boxes, key=lambda x: x["center"][1])

# 바운딩 박스를 그룹화할 리스트
grouped_boxes = []

# 그룹 내에서의 tolerance factor
group_tolerance_factor_y = 40
group_tolerance_factor_x = 300

# 바운딩 박스를 그룹화
current_group = [sorted_boxes_y[0]]

for i in range(1, len(sorted_boxes_y)):
    prev_center_y = current_group[-1]["center"][1]
    current_center_y = sorted_boxes_y[i]["center"][1]

    if abs(current_center_y - prev_center_y) < group_tolerance_factor_y:
        current_group.append(sorted_boxes_y[i])
    else:
        # 그룹 내에서 x 좌표를 기준으로 정렬
        sorted_group_x = sorted(current_group, key=lambda x: x["center"][0])

        # 형성된 그룹에서 새로운 그룹 형성
        new_group = [sorted_group_x[0]]

        for j in range(1, len(sorted_group_x)):
            prev_center_x = new_group[-1]["center"][0]
            current_center_x = sorted_group_x[j]["center"][0]

            if abs(current_center_x - prev_center_x) < group_tolerance_factor_x:
                new_group.append(sorted_group_x[j])
            else:
                # 같은 줄에 있는 바운딩 박스를 한 줄로 합치기
                line_text = ' '.join(box["text"] for box in new_group)
                grouped_boxes.append(line_text)

                new_group = [sorted_group_x[j]]

        # 마지막 그룹에 대한 정렬
        sorted_group_x = sorted(new_group, key=lambda x: x["center"][0])
        line_text = ' '.join(box["text"] for box in sorted_group_x)
        grouped_boxes.append(line_text)

        current_group = [sorted_boxes_y[i]]

# 마지막 그룹에 대한 정렬
sorted_group_x = sorted(current_group, key=lambda x: x["center"][0])
line_text = ' '.join(box["text"] for box in sorted_group_x)
grouped_boxes.append(line_text)

# 정렬된 바운딩 박스의 텍스트 출력
for line_text in grouped_boxes:
    print(line_text)

import re

employee_name_match = re.search(r'Employee Name : (.+)', grouped_boxes[0])
employee_name = employee_name_match.group(1) if employee_name_match else None
print(employee_name) #Jerry

manager_name_match = re.search(r'Manager Name : (.+)', grouped_boxes[1])
manager_name = manager_name_match.group(1) if manager_name_match else None
print(manager_name) #Melinda

weekStart_match = re.search(r'Week Starting : (.+)', grouped_boxes[2])
weekStart = weekStart_match.group(1) if weekStart_match else None
print(weekStart) #6/23/2022

# Assuming grouped_boxes is a list of strings
combined_text = '\n'.join(grouped_boxes)

# Use regular expressions to extract the relevant portion
info_match = re.search(r'Date.*Total Hours\n(.*?)Total Hours', combined_text, re.DOTALL)
info = info_match.group(0) if info_match else None

print("info match: ", info_match)
print("info: ", info)
print()

# Now 'extracted_text' contains the portion you want to process further

# Split the extracted text into lines
lines = info.strip().split('\n')

# Assuming the header is in the first line and the data starts from the second line
header = re.split(r'\s+', lines[0])

# Combine consecutive elements with similar prefixes
grouped_header = []
current_group = []

for element in header:
    # Check if the current element is 'Time' or 'Total'
    if element in ['In', 'Out', 'Hours']:
        current_group.append(element)
    # Check if there's a current group, and the current element starts with the last element in the group
    elif current_group and element.startswith(current_group[-1]):
        current_group[-1] += ' ' + element
    else:
        # Combine consecutive elements with similar prefixes only when not 'Time' or 'Total'
        if not any(prefix in element for prefix in ['In', 'Out', 'Hours']):
            grouped_header.append(' '.join(current_group))
            current_group = [element]
        else:
            current_group.append(element)

# Add the last group
grouped_header.append(' '.join(current_group))
list = grouped_header[1:]

print(current_group)
print(list)

header = []

# 리스트를 순회하면서 Time In과 Time Out에 "_2"를 붙여서 새로운 리스트에 추가
for i in list:
    if i in header:
        header.append(i + '_2')
    else:
        header.append(i)

print(header)

data = [re.split(r'\s+', line) for line in lines[1:-1]]

print("header: ", header)
print("data: ", data)
print()

# Access the data by column
for row in data:
    print(
        f"Date: {row[header.index('Date')]}, Day: {row[header.index('Day')]}, "
        f"Time In: {row[header.index('Time In')]}, Time Out: {row[header.index('Time Out')]}, "
        f"Time In_2: {row[header.index('Time In_2')]}, Time Out_2: {row[header.index('Time Out_2')]}, "
        f"Total Hours: {row[header.index('Total Hours')]}"
    )

employeeSign_match = re.search(r'Employee Signature :  (.+)', grouped_boxes[12])
employeeSign = employeeSign_match.group(1) if employeeSign_match else None
print(employeeSign) #Jerry

managerSign_match = re.search(r'Manager Signature : (.+)', grouped_boxes[14])
managerSign = managerSign_match.group(1) if managerSign_match else None
print(managerSign) #Melinda