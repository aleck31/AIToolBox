# Copyright iX.
# SPDX-License-Identifier: MIT-0
import base64
from io import BytesIO
from pdf2image import convert_from_path



def pil_to_base64(image):
    """ Convert PIL Image object to base64 strings """
    img_buff = BytesIO()
    image.save(img_buff, format="JPEG")
    encoded_string = base64.b64encode(img_buff.getvalue()).decode("utf-8")
    return encoded_string


def path_to_base64(image_path):
    """ Load image from path and encode as base64 strings """
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return encoded_string


def pdf_to_imgs(pdf_path):
    """ Convert PDF into Pillow images, return a list of PIL.JpegImageFile """
    # define the max pages to convert
    max_pages = 16
    try:
        img_list = convert_from_path(pdf_path, dpi=300, thread_count=4, fmt='jpeg', last_page=max_pages)   
        return img_list
    except:
        raise
