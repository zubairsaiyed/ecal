#!/usr/bin/env python3
"""Unit tests for whitespace detection in screenshot processing

Usage:
    # Run tests (will skip if no screenshot provided):
    python3 -m unittest test_whitespace_detection -v
    
    # Test with a specific screenshot:
    SCREENSHOT_PATH=/path/to/screenshot.png python3 -m unittest test_whitespace_detection -v
    
    # Or run directly:
    python3 test_whitespace_detection.py /path/to/screenshot.png
"""

import unittest
import os
import sys
from PIL import Image

# Add parent directory to path to import calendar_server functions if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestWhitespaceDetection(unittest.TestCase):
    """Test whitespace detection on screenshots"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.white_threshold = 240
        self.content_threshold = 0.02
        self.expected_width = 1600
        self.expected_height = 1200
    
    def detect_whitespace(self, image_path):
        """Detect whitespace in an image - extracted logic from calendar_server.py"""
        img = Image.open(image_path)
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        actual_width, actual_height = img.size
        pixels = img.load()
        sample_step = max(1, actual_width // 50)
        rows_to_check = min(400, actual_height)
        
        # Find the last row with significant content
        last_content_row = None
        for y in range(actual_height - 1, max(-1, actual_height - rows_to_check - 1), -1):
            non_white_count = 0
            sampled_pixels = 0
            
            for x in range(0, actual_width, sample_step):
                r, g, b = pixels[x, y]
                if not (r > self.white_threshold and g > self.white_threshold and b > self.white_threshold):
                    non_white_count += 1
                sampled_pixels += 1
            
            non_white_ratio = non_white_count / sampled_pixels if sampled_pixels > 0 else 0
            
            if non_white_ratio >= self.content_threshold:
                last_content_row = y
                break
        
        # Also check for consecutive white rows
        bottom_crop = actual_height
        consecutive_white_rows = 0
        required_white_rows = 3
        
        for y in range(actual_height - 1, max(-1, actual_height - rows_to_check - 1), -1):
            white_pixel_count = 0
            sampled_pixels = 0
            for x in range(0, actual_width, sample_step):
                r, g, b = pixels[x, y]
                if r > self.white_threshold and g > self.white_threshold and b > self.white_threshold:
                    white_pixel_count += 1
                sampled_pixels += 1
            
            white_ratio = white_pixel_count / sampled_pixels if sampled_pixels > 0 else 0
            if white_ratio > 0.90:
                consecutive_white_rows += 1
                if consecutive_white_rows >= required_white_rows:
                    bottom_crop = y + 1
                    break
            else:
                consecutive_white_rows = 0
        
        # Use the more aggressive of the two methods
        if last_content_row is not None:
            suggested_crop = last_content_row + 6
            if suggested_crop < bottom_crop:
                bottom_crop = suggested_crop
        
        return {
            'original_height': actual_height,
            'original_width': actual_width,
            'last_content_row': last_content_row,
            'bottom_crop': bottom_crop,
            'whitespace_height': actual_height - bottom_crop,
            'should_crop': bottom_crop < actual_height
        }
    
    def test_whitespace_detection_on_screenshot(self):
        """Test whitespace detection on an actual screenshot"""
        # Look for screenshot in common locations
        screenshot_paths = [
            'screenshot.png',
            'calendar_screenshot.png',
            '/tmp/calendar_screenshot.png',
            os.path.join(os.path.dirname(__file__), 'screenshot.png'),
        ]
        
        screenshot_path = None
        for path in screenshot_paths:
            if os.path.exists(path):
                screenshot_path = path
                break
        
        if screenshot_path is None:
            # If no screenshot found, skip the test but warn
            self.skipTest("No screenshot found to test. Provide a screenshot file to test whitespace detection.")
        
        result = self.detect_whitespace(screenshot_path)
        
        # Assertions
        self.assertIsNotNone(result['last_content_row'], "Should find last content row")
        self.assertLess(result['bottom_crop'], result['original_height'], "Should detect whitespace to crop")
        self.assertGreater(result['whitespace_height'], 0, "Should detect some whitespace")
        
        print(f"\nTest Results for {screenshot_path}:")
        print(f"  Original dimensions: {result['original_width']}x{result['original_height']}")
        print(f"  Last content row: {result['last_content_row']}")
        print(f"  Bottom crop position: {result['bottom_crop']}")
        print(f"  Whitespace height: {result['whitespace_height']} pixels")
        print(f"  Should crop: {result['should_crop']}")
        
        # If screenshot is taller than expected, it should definitely be cropped
        if result['original_height'] > self.expected_height:
            self.assertTrue(result['should_crop'], 
                          f"Screenshot height ({result['original_height']}) exceeds expected ({self.expected_height}), should be cropped")
    
    def test_whitespace_detection_with_path(self):
        """Test whitespace detection with explicit path from command line"""
        # Check for SCREENSHOT_PATH environment variable or command line arg
        screenshot_path = os.environ.get('SCREENSHOT_PATH')
        if screenshot_path is None and len(sys.argv) > 1:
            # Filter out unittest arguments
            for arg in sys.argv[1:]:
                if arg.endswith('.png') or arg.endswith('.jpg') or os.path.exists(arg):
                    screenshot_path = arg
                    break
        
        if screenshot_path is None:
            self.skipTest("No screenshot path provided. Set SCREENSHOT_PATH env var or pass as argument.")
        
        if not os.path.exists(screenshot_path):
            self.fail(f"Screenshot file not found: {screenshot_path}")
        
        result = self.detect_whitespace(screenshot_path)
        
        print(f"\nTest Results for {screenshot_path}:")
        print(f"  Original dimensions: {result['original_width']}x{result['original_height']}")
        print(f"  Last content row: {result['last_content_row']}")
        print(f"  Bottom crop position: {result['bottom_crop']}")
        print(f"  Whitespace height: {result['whitespace_height']} pixels")
        print(f"  Should crop: {result['should_crop']}")
        
        # Basic assertions
        self.assertIsNotNone(result['last_content_row'], "Should find last content row")
        self.assertLessEqual(result['bottom_crop'], result['original_height'], "Crop position should be within image")
        
        # If there's significant whitespace, verify it's detected
        if result['whitespace_height'] > 50:
            self.assertTrue(result['should_crop'], 
                          f"Detected {result['whitespace_height']} pixels of whitespace, should crop")


def run_tests():
    """Run the unit tests"""
    # unittest.main will handle command line arguments, but we need to filter them
    # Remove our script name and any screenshot paths from argv
    unittest_args = []
    for arg in sys.argv[1:]:
        if not (arg.endswith('.png') or arg.endswith('.jpg') or 
                (os.path.exists(arg) and os.path.isfile(arg))):
            unittest_args.append(arg)
    
    unittest.main(argv=[sys.argv[0]] + unittest_args, verbosity=2)


if __name__ == "__main__":
    run_tests()
