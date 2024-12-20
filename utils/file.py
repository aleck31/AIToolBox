# Copyright iX.
# SPDX-License-Identifier: MIT-0
"""Helper utilities for processing media files such as image and pdf"""
import base64
from io import BytesIO
# from pdf2image import convert_from_path


def pil_to_base64(image):
    """ Convert PIL Image object to base64 strings """
    img_buff = BytesIO()
    image.save(img_buff, format="JPEG")
    encoded_string = base64.b64encode(img_buff.getvalue()).decode("utf-8")
    return encoded_string


def path_to_base64(file_path):
    """ Load media file from path and encode as base64 strings """
    with open(file_path, "rb") as media_file:
        encoded_string = base64.b64encode(media_file.read()).decode("utf-8")
        return encoded_string


# def pdf_to_imgs(file_path):
#     """ Convert PDF file into Pillow images, return a list of PIL.JpegImageFile """
#     # Set maximum page size to avoid exceeding the message api limit: image_count <= 20
#     max_pages = 20
#     try:
#         img_list = convert_from_path(
#             file_path, dpi=300, thread_count=4, fmt='jpeg', last_page=max_pages)
#         return img_list
#     except:
#         raise
