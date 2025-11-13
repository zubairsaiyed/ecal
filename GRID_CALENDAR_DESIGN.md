# Grid Calendar Design Mock

## Overview
This document describes the new grid-based calendar design for the ECAL e-paper display system.

## Design Specifications

### Layout
- **7-column grid**: One column for each day of the week (Sunday through Saturday)
- **Full width responsive**: Utilizes 100% of viewport width
- **Configurable weeks**: Display 1-4 weeks at a time (user configurable)
- **Grid structure**: CSS Grid for clean, responsive layout

### Visual Design

#### Color Scheme (E-paper Optimized)
- **Primary**: Black (#000000) for borders and text
- **Background**: White (#ffffff) for day cells
- **Secondary backgrounds**: Light gray (#f5f5f5, #f9f9f9) for headers and other-month days
- **Event indicators**: Shades of gray (#000000, #333333, #666666, #999999) for event borders
- **Today highlight**: Light gray background (#f0f0f0) with black border

**Note**: The design uses high-contrast black/white/gray colors suitable for e-paper displays. If your e-paper supports limited colors (red, blue, yellow), those can be optionally enabled via CSS.

#### Typography
- **Font**: System fonts (-apple-system, BlinkMacSystemFont, 'Segoe UI', Arial)
- **Day numbers**: 14px, bold, with bottom border
- **Event text**: 11px, compact but readable
- **Time display**: Bold, inline with event title

#### Event Display
- **Time format**: 24-hour format (e.g., "9:00", "14:30")
- **All-day events**: Displayed as "All Day" with different styling
- **Event layout**: 
  - Left border (3px) indicates event color/calendar
  - Time shown first, then title
  - Text wraps to 2 lines max, then truncates
- **Multiple events**: Stacked vertically with 4px gap

### Responsive Behavior
- **Large screens** (>1200px): Full-size cells (120px min-height)
- **Medium screens** (800-1200px): Slightly reduced (100px min-height)
- **Small screens** (<800px): Compact mode (80px min-height, smaller fonts)

### Data Integration
- Pulls events from Google Calendar API (same endpoint as existing calendar)
- Displays events in chronological order within each day
- Shows start time for timed events
- Handles all-day events with special styling

## Mock File
See `templates/calendar_grid_mock.html` for a visual mockup with sample data.

## Key Features

1. **Minimal Design**: Clean lines, high contrast, no unnecessary elements
2. **E-paper Friendly**: Black/white/gray color scheme optimized for e-ink displays
3. **Time Display**: Every event shows its start time prominently
4. **Week Configuration**: User can choose 1-4 weeks to display
5. **Full Width**: Responsive grid uses entire viewport width
6. **Today Indicator**: Current day highlighted with border and background

## Implementation Notes

### Feature Flag
- Will be controlled via settings page
- Toggle between "FullCalendar" (existing) and "Grid Calendar" (new)
- Stored in `settings.json` as `calendar_view: "grid"` or `"fullcalendar"`

### Configuration Options
- `weeks_to_display`: Integer 1-4 (default: 2)
- `first_day_of_week`: 0 (Sunday) or 1 (Monday) - inherits from existing setting
- `show_time`: Boolean (always true for grid view)
- `event_colors`: Array of colors for different calendars (grayscale for e-paper)

### Data Structure
Uses same event format as existing calendar:
```json
{
  "title": "Event Title",
  "start": "2025-11-10T09:00:00",
  "end": "2025-11-10T10:00:00",
  "allDay": false,
  "calendarId": "calendar_id_here"
}
```

## Comparison with Existing Calendar

| Feature | FullCalendar (Current) | Grid Calendar (New) |
|---------|------------------------|---------------------|
| Layout | Month/week/day views | Fixed 7-column grid |
| Weeks shown | Variable | 1-4 configurable |
| Time display | Optional | Always shown |
| Color scheme | Full color | E-paper optimized |
| Responsiveness | FullCalendar responsive | Custom responsive grid |
| Event density | Can be cluttered | More structured |

## Next Steps

1. Review the mock HTML file (`templates/calendar_grid_mock.html`)
2. Provide feedback on design, colors, layout
3. Once approved, implement:
   - Feature flag in settings
   - Grid calendar template
   - Backend logic for week calculation
   - Integration with existing calendar API

