# ECAL Rotation Tests

## Overview

This test suite verifies the image rotation logic to prevent regressions when modifying the display code.

## Running the Tests

### Quick Run
```bash
./run_tests.sh
```

### Manual Run
```bash
python3 test_rotation.py
```

### Verbose Output
```bash
python3 test_rotation.py -v
```

## What's Tested

### Rotation Modes
1. **Landscape Mode** - Verifies no rotation is applied
2. **Portrait Mode** - Verifies 270° counterclockwise rotation is applied
3. **Auto Mode** - Verifies intelligent rotation based on image/display aspect ratios

### Auto-Zoom
- Verifies auto-zoom works with landscape mode
- Verifies auto-zoom works with portrait mode
- Verifies auto-zoom can be disabled

### Edge Cases
- Invalid rotation mode defaults to landscape
- Default rotation mode is landscape
- Auto mode doesn't rotate when orientations match

## Test Coverage

The tests mock the e-paper hardware (`epd13in3E`) so they can run on any system without physical hardware.

### Test Cases

| Test | Description | Expected Behavior |
|------|-------------|-------------------|
| `test_landscape_mode_no_rotation` | Landscape mode with portrait image | No rotation applied |
| `test_portrait_mode_270_rotation` | Portrait mode with landscape image | 270° CCW rotation applied |
| `test_auto_mode_portrait_to_landscape` | Auto mode: portrait image on landscape display | 270° rotation applied |
| `test_auto_mode_no_rotation_when_aligned` | Auto mode: landscape image on landscape display | No rotation applied |
| `test_auto_zoom_with_landscape_mode` | Auto-zoom enabled in landscape mode | Image zooms to fill display |
| `test_auto_zoom_with_portrait_mode` | Auto-zoom enabled in portrait mode | Image zooms to fill display |
| `test_default_rotation_mode_is_landscape` | No rotation mode specified | Defaults to landscape (no rotation) |
| `test_invalid_rotation_mode_defaults_to_landscape` | Invalid rotation mode | Falls back to landscape |

## Adding New Tests

When modifying rotation logic, add tests to verify:
1. The new behavior works as expected
2. Existing behaviors are not broken
3. Edge cases are handled properly

Example test structure:
```python
@patch('display_image.epd13in3E')
def test_new_rotation_feature(self, mock_epd):
    """Test description"""
    # Setup mocks
    mock_epd.EPD_WIDTH = 960
    mock_epd.EPD_HEIGHT = 680
    mock_display = MagicMock()
    mock_epd.EPD.return_value = mock_display
    
    # Run test
    result = display_image.display_image(
        self.test_image_path,
        rotation_mode='your_mode',
        auto_zoom_after_rotation=False
    )
    
    # Verify expectations
    self.assertTrue(result)
```

## CI/CD Integration

These tests can be integrated into a CI/CD pipeline:

```bash
# In your CI pipeline
cd code/ecal
python3 test_rotation.py
```

## Dependencies

- Python 3
- PIL/Pillow
- unittest (standard library)

The tests mock hardware dependencies, so no e-paper display is required.

