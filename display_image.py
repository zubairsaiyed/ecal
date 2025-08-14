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
    
    Note:
        This display has a physical orientation offset - it rotates images 90° clockwise by default.
        When honoring EXIF orientation data, we compensate for this offset to ensure correct display.
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
        
        # Handle EXIF orientation data (backup handler)
        # Note: The server should have already rotated the image, but this ensures
        # the display script also honors EXIF data as a fallback
        try:
            from PIL import ExifTags
            exif = Himage.getexif()
            if exif is not None:
                print(f"EXIF data found: {exif is not None}")
                print(f"EXIF tags: {list(exif.keys())}")
                
                # Find orientation tag
                orientation = None
                for tag, value in ExifTags.TAGS.items():
                    if value == 'Orientation':
                        orientation = tag
                        break
                
                if orientation is not None and orientation in exif:
                    orientation_value = exif.get(orientation, None)
                    print(f"EXIF orientation value: {orientation_value}")
                    
                    # Apply EXIF rotation with compensation for display's physical orientation
                    # The display rotates images 90° clockwise by default, so we need to compensate
                    if orientation_value == 3:
                        # 180° rotation - no compensation needed (180° is symmetric)
                        Himage = Himage.rotate(180, expand=True)
                        print("Applied EXIF rotation: 180° (no compensation needed)")
                    elif orientation_value == 6:
                        # 90° clockwise rotation - compensate by rotating 270° to counter the display's 90° offset
                        Himage = Himage.rotate(270, expand=True)
                        print("Applied EXIF rotation: 90° → compensated with 270° rotation")
                    elif orientation_value == 8:
                        # 270° clockwise rotation - compensate by rotating 90° to counter the display's 90° offset
                        Himage = Himage.rotate(90, expand=True)
                        print("Applied EXIF rotation: 270° → compensated with 90° rotation")
                    else:
                        print(f"No rotation needed for orientation {orientation_value}")
                    
                    print(f"Image size after EXIF rotation: {Himage.size}")
                else:
                    print("No EXIF orientation data found")
            else:
                print("No EXIF data found")
        except Exception as e:
            print(f"Error processing EXIF data: {e}")
            import traceback
            traceback.print_exc()
        
        # Resize image to fit the display if necessary
        if Himage.size != (epd13in3E.EPD_WIDTH, epd13in3E.EPD_HEIGHT):
            print(f"Original image size: {Himage.size}")
            print(f"Target display size: ({epd13in3E.EPD_WIDTH}, {epd13in3E.EPD_HEIGHT})")
            
            # Honor EXIF orientation - don't do display optimization rotation
            # Just scale the image to fit while maintaining aspect ratio
            original_width, original_height = Himage.size
            display_width, display_height = epd13in3E.EPD_WIDTH, epd13in3E.EPD_HEIGHT
            
            if zoom_to_fit:
                # Zoom to fill (may crop) - use max scaling
                scale_factor = max(display_width / original_width, display_height / original_height)
                print("Using zoom-to-fit mode (may crop image)")
            else:
                # Fit without cropping - use min scaling
                scale_factor = min(display_width / original_width, display_height / original_height)
                print("Using fit-without-crop mode")
            
            print(f"Scaling factor: {scale_factor:.2f}")
            
            # Calculate new size maintaining aspect ratio
            new_width = int(original_width * scale_factor)
            new_height = int(original_height * scale_factor)
            
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