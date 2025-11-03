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

def display_image(image_path, zoom_to_fit=False, test_rotation=None, rotation_mode='landscape', auto_zoom_after_rotation=True):
    """
    Display an image on the 13.3inch e-paper display
    
    Args:
        image_path (str): Path to the image file to display
        zoom_to_fit (bool): If True, scale to fill display (may crop). If False, scale to fit (no cropping).
        test_rotation (int, optional): Test rotation angle (0, 90, 180, 270) to test display orientation
        rotation_mode (str): Rotation mode - 'landscape' (90° CCW), 'portrait' (no rotation), or 'auto' (smart rotation)
        auto_zoom_after_rotation (bool): If True, automatically zoom to fill display after rotation
    
    Note:
        Rotation modes:
        - 'landscape': Always rotate 90° counterclockwise (default for landscape displays)
        - 'portrait': No rotation applied (display image as-is)
        - 'auto': Intelligently rotates images to maximize screen usage by comparing
                  the aspect ratios of the image and display, rotating if it improves screen coverage by >5%.
                  Rotation direction is consistent based on orientation:
                  - Portrait images on landscape displays: rotate 270° (counterclockwise)
                  - Landscape images on portrait displays: rotate 90° (clockwise)
                  This ensures images are never displayed upside down.
        When combined with auto_zoom_after_rotation, images are rotated AND zoomed to fill the frame.
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
        
        # Test rotation override (for debugging display orientation)
        if test_rotation is not None:
            print(f"Applying test rotation: {test_rotation}°")
            Himage = Himage.rotate(test_rotation, expand=True)
            print(f"Image size after test rotation: {Himage.size}")
        
        # Apply rotation based on rotation_mode
        image_was_rotated = False
        if rotation_mode == 'auto':
            img_width, img_height = Himage.size
            display_width, display_height = epd13in3E.EPD_WIDTH, epd13in3E.EPD_HEIGHT
            
            # Determine orientations
            img_is_portrait = img_height > img_width
            display_is_portrait = display_height > display_width
            
            print(f"Image orientation: {'Portrait' if img_is_portrait else 'Landscape'} ({img_width}x{img_height})")
            print(f"Display orientation: {'Portrait' if display_is_portrait else 'Landscape'} ({display_width}x{display_height})")
            
            # Calculate how much of the screen would be used without rotation
            scale_no_rotation = min(display_width / img_width, display_height / img_height)
            area_no_rotation = (img_width * scale_no_rotation) * (img_height * scale_no_rotation)
            
            # Calculate how much of the screen would be used with rotation
            scale_with_rotation = min(display_width / img_height, display_height / img_width)
            area_with_rotation = (img_height * scale_with_rotation) * (img_width * scale_with_rotation)
            
            # Rotate if orientations don't match and it increases screen usage by more than 5%
            if area_with_rotation > area_no_rotation * 1.05:
                # Use consistent rotation direction based on orientations:
                # - Portrait image on landscape display: rotate 270° (counterclockwise)
                # - Landscape image on portrait display: rotate 90° (clockwise)
                if img_is_portrait and not display_is_portrait:
                    rotation_angle = 270  # Counterclockwise for portrait -> landscape
                    rotation_dir = "counterclockwise"
                elif not img_is_portrait and display_is_portrait:
                    rotation_angle = 90   # Clockwise for landscape -> portrait
                    rotation_dir = "clockwise"
                else:
                    # Fallback: use 270° for consistent behavior
                    rotation_angle = 270
                    rotation_dir = "counterclockwise"
                
                print(f"Auto-rotating image {rotation_angle}° ({rotation_dir}) to maximize screen usage")
                print(f"  Screen usage without rotation: {area_no_rotation:.0f} pixels²")
                print(f"  Screen usage with rotation: {area_with_rotation:.0f} pixels²")
                print(f"  Improvement: {((area_with_rotation / area_no_rotation - 1) * 100):.1f}%")
                Himage = Himage.rotate(rotation_angle, expand=True)
                print(f"  Image size after auto-rotation: {Himage.size}")
                image_was_rotated = True
                
                # Auto-zoom after rotation if enabled
                if auto_zoom_after_rotation:
                    print(f"  Auto-zoom enabled: image will fill the display frame (may crop)")
                    zoom_to_fit = True
            else:
                print(f"No auto-rotation needed (current orientation maximizes screen usage)")
        elif rotation_mode == 'landscape':
            # Landscape mode: apply fixed 270° counterclockwise rotation (same as 90° clockwise)
            print("Landscape mode: applying 270° counterclockwise rotation")
            Himage = Himage.rotate(270, expand=True)
            print(f"Image size after 270° counterclockwise rotation: {Himage.size}")
            image_was_rotated = True
            
            # Auto-zoom after rotation if enabled
            if auto_zoom_after_rotation:
                print(f"  Auto-zoom enabled: image will fill the display frame (may crop)")
                zoom_to_fit = True
        elif rotation_mode == 'portrait':
            # Portrait mode: apply 90° counterclockwise rotation
            print("Portrait mode: applying 90° counterclockwise rotation")
            Himage = Himage.rotate(90, expand=True)
            print(f"Image size after 90° counterclockwise rotation: {Himage.size}")
            image_was_rotated = True
            
            # Auto-zoom after rotation if enabled
            if auto_zoom_after_rotation:
                print(f"  Auto-zoom enabled: image will fill the display frame (may crop)")
                zoom_to_fit = True
        else:
            # Unknown mode, default to landscape for safety
            print(f"Unknown rotation mode '{rotation_mode}', defaulting to landscape (270° CCW)")
            Himage = Himage.rotate(270, expand=True)
            print(f"Image size after 270° counterclockwise rotation: {Himage.size}")
            image_was_rotated = True
            
            # Auto-zoom after rotation if enabled
            if auto_zoom_after_rotation:
                print(f"  Auto-zoom enabled: image will fill the display frame (may crop)")
                zoom_to_fit = True
        
        # Resize image to fit the display if necessary
        if Himage.size != (epd13in3E.EPD_WIDTH, epd13in3E.EPD_HEIGHT):
            print(f"Original image size: {Himage.size}")
            print(f"Target display size: ({epd13in3E.EPD_WIDTH}, {epd13in3E.EPD_HEIGHT})")
            
            # Scale the image to fit while maintaining aspect ratio
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
    parser.add_argument('--test-rotation', type=int, choices=[0, 90, 180, 270],
                       help='Test rotation: apply specific rotation angle to test display orientation')
    parser.add_argument('--rotation-mode', type=str, choices=['landscape', 'portrait', 'auto'], default='landscape',
                       help='Rotation mode: landscape (90° CCW), portrait (no rotation), or auto (smart rotation)')
    parser.add_argument('--no-auto-zoom', action='store_true',
                       help='Disable automatic zoom-to-fill after rotation')
    # Keep legacy argument for backwards compatibility
    parser.add_argument('--no-auto-rotate', action='store_true',
                       help='[DEPRECATED] Use --rotation-mode portrait instead')
    args = parser.parse_args()
    
    # Handle legacy --no-auto-rotate flag
    rotation_mode = args.rotation_mode
    if args.no_auto_rotate:
        print("Warning: --no-auto-rotate is deprecated. Use --rotation-mode portrait instead.")
        rotation_mode = 'portrait'
    
    success = display_image(args.image_path, args.zoom_to_fit, args.test_rotation, 
                           rotation_mode=rotation_mode,
                           auto_zoom_after_rotation=not args.no_auto_zoom)
    if success:
        print("Image displayed successfully!")
    else:
        print("Failed to display image.")
        sys.exit(1)

if __name__ == "__main__":
    main() 