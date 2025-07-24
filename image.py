#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import sys
import os
import argparse
picdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'pic')
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import epd13in3E
import time
from PIL import Image

def display_image(image_path, zoom_to_fit=False):
    """
    Display an image on the 13.3inch e-paper display
    
    Args:
        image_path (str): Path to the image file to display
        zoom_to_fit (bool): If True, scale to fill display (may crop). If False, scale to fit (no cropping).
    """
    print("13.3inch e-paper (E) Image Display...")
    
    # Convert relative path to absolute path and print it
    abs_image_path = os.path.abspath(image_path)
    print(f"Absolute file path: {abs_image_path}")
    
    # Check if image file exists
    if not os.path.exists(abs_image_path):
        print(f"Error: Image file '{image_path}' not found!")
        return False
    
    epd = epd13in3E.EPD()
    try:
        epd.Init()
        print("clearing display...")
        epd.Clear()

        # Load and process the image
        print(f"Loading image: {image_path}")
        Himage = Image.open(abs_image_path)
        
        # Print image details
        print(f"Image format: {Himage.format}")
        print(f"Image mode: {Himage.mode}")
        print(f"Image size: {Himage.size}")
        print(f"Image info: {Himage.info}")
        
        # Resize image to fit the display if necessary
        if Himage.size != (epd13in3E.EPD_WIDTH, epd13in3E.EPD_HEIGHT):
            print(f"Original image size: {Himage.size}")
            print(f"Target display size: ({epd13in3E.EPD_WIDTH}, {epd13in3E.EPD_HEIGHT})")
            
            # Check if rotating would give better scaling
            original_width, original_height = Himage.size
            if zoom_to_fit:
                # Zoom to fill (may crop) - use max scaling
                normal_scale = max(epd13in3E.EPD_WIDTH / original_width, epd13in3E.EPD_HEIGHT / original_height)
                rotated_scale = max(epd13in3E.EPD_WIDTH / original_height, epd13in3E.EPD_HEIGHT / original_width)
                print("Using zoom-to-fit mode (may crop image)")
            else:
                # Fit without cropping - use min scaling
                normal_scale = min(epd13in3E.EPD_WIDTH / original_width, epd13in3E.EPD_HEIGHT / original_height)
                rotated_scale = min(epd13in3E.EPD_WIDTH / original_height, epd13in3E.EPD_HEIGHT / original_width)
                print("Using fit-without-crop mode")
            
            print(f"Normal scaling factor: {normal_scale:.2f}")
            print(f"Rotated scaling factor: {rotated_scale:.2f}")
            
            # Use rotation if it provides better scaling (larger scale factor)
            if rotated_scale > normal_scale:
                print("Rotating image 90 degrees for better fit")
                Himage = Himage.rotate(90, expand=True)
                width_ratio = epd13in3E.EPD_WIDTH / Himage.size[0]
                height_ratio = epd13in3E.EPD_HEIGHT / Himage.size[1]
                scale_factor = max(width_ratio, height_ratio) if zoom_to_fit else min(width_ratio, height_ratio)
            else:
                print("Using normal orientation")
                width_ratio = epd13in3E.EPD_WIDTH / original_width
                height_ratio = epd13in3E.EPD_HEIGHT / original_height
                scale_factor = max(width_ratio, height_ratio) if zoom_to_fit else min(width_ratio, height_ratio)
            
            # Calculate new size maintaining aspect ratio
            new_width = int(Himage.size[0] * scale_factor)
            new_height = int(Himage.size[1] * scale_factor)
            
            print(f"Final scaling factor: {scale_factor:.2f}")
            print(f"New size: ({new_width}, {new_height})")
            
            # Resize image maintaining aspect ratio
            Himage = Himage.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            if zoom_to_fit:
                # For zoom-to-fit, crop the image to fill the display
                # Calculate crop box to center the image
                crop_x = max(0, (new_width - epd13in3E.EPD_WIDTH) // 2)
                crop_y = max(0, (new_height - epd13in3E.EPD_HEIGHT) // 2)
                crop_width = min(epd13in3E.EPD_WIDTH, new_width)
                crop_height = min(epd13in3E.EPD_HEIGHT, new_height)
                
                Himage = Himage.crop((crop_x, crop_y, crop_x + crop_width, crop_y + crop_height))
                print(f"Cropped to: {Himage.size}")
            else:
                # For fit-without-crop, center the image on white background
                final_image = Image.new('RGB', (epd13in3E.EPD_WIDTH, epd13in3E.EPD_HEIGHT), (255, 255, 255))
                paste_x = (epd13in3E.EPD_WIDTH - new_width) // 2
                paste_y = (epd13in3E.EPD_HEIGHT - new_height) // 2
                final_image.paste(Himage, (paste_x, paste_y))
                Himage = final_image
        
        # Convert to RGB if necessary
        if Himage.mode != 'RGB':
            Himage = Himage.convert('RGB')
        
        print("Displaying image...")
        epd.display(epd.getbuffer(Himage))
        time.sleep(3)

        print("goto sleep...")
        epd.sleep()
        return True
        
    except Exception as e:
        print(f"Error displaying image: {e}")
        print("goto sleep...")
        epd.sleep()
        return False

def main():
    parser = argparse.ArgumentParser(description='Display an image on 13.3inch e-paper display')
    parser.add_argument('image_path', help='Path to the image file to display')
    parser.add_argument('--sleep-time', type=int, default=3, 
                       help='Time to display the image in seconds (default: 3)')
    parser.add_argument('--zoom-to-fit', action='store_true',
                       help='Scale to fill display (may crop image). Default is to fit without cropping.')
    
    args = parser.parse_args()
    
    success = display_image(args.image_path, args.zoom_to_fit)
    if success:
        print("Image displayed successfully!")
    else:
        print("Failed to display image.")
        sys.exit(1)

if __name__ == "__main__":
    main() 