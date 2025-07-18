# Daily Report Generator

A PyQt6-based desktop application for generating production contribution reports in PDF format. Designed for manufacturing environments to track line performance, labor costs, and revenue contributions.

## Features

### Report Generation
- **Daily Production Reports**: Generate PDF reports with line-by-line production data
- **Automatic Calculations**: Revenue, labor costs, and contribution margins calculated automatically
- **Professional Formatting**: Clean, landscape-oriented PDF output with company branding
- **Configurable Pricing**: Dynamic pricing based on quantity thresholds and line types

### User Interface
- **Recent Names**: Auto-complete dropdown for frequently used names
- **Read-Only Price Display**: Clean interface with edit dialogs for price management
- **Visual Sections**: Clear separation between different data entry areas
- **Real-time Validation**: Input validation with helpful error messages

### Settings Management
- **Machine Price Configuration**: Set over/under threshold pricing for each production line
- **Handpack Management**: Add, edit, and delete custom handpack types with pricing
- **Quantity Threshold**: Configurable breakpoint for pricing tiers (default: 5000)
- **Wage Settings**: Set hourly labor rates for cost calculations

## Installation

### Prerequisites
- Windows 10/11
- No additional software required (standalone executable)

### Setup
1. Download the `latest release`
2. Export folder to desired directory
3. Run report.exe in dist\report

## Usage

### Generating a Report

1. **Enter Basic Information**
   - Type your full name (recent names will appear in dropdown)
   - Select shift (1 or 2)

2. **Configure Production Lines**
   - For each line (AZ, BZ, DZ, EZ, FZ, H1, H2):
     - Select run type from dropdown
     - Enter quantity produced
     - Set number of people working
     - Enter hours worked
   - Lines set to "Not Run" will be grayed out in the report

3. **Add Notes** (optional)
   - Enter any additional information or comments

4. **Generate PDF**
   - Click "Generate PDF" button
   - Report will open automatically when complete

### Managing Settings

#### Machine Prices
1. Go to **Settings** tab
2. Click **"Edit Machine Prices"**
3. Select line from dropdown
4. Enter over/under threshold prices
5. Click OK to save

#### Handpack Types
1. Go to **Settings** tab
2. Use **"Add Hand Pack"** to create new types
3. Use **"Edit Hand Pack"** to modify existing prices
4. Use **"Delete Hand Pack"** to remove types

#### Quantity Threshold
1. Go to **Settings** tab
2. Click **"Edit Quantity Threshold"**
3. Enter new threshold value
4. Click OK to save

## File Structure

```
DailyReportGenerator.exe
├── settings.json          # Application settings and pricing
├── logo.jpeg             # Company logo for PDF reports
└── README.md             # This file
```

## Configuration

The `settings.json` file contains:
- **wage**: Hourly labor rate
- **qty_threshold**: Quantity breakpoint for pricing tiers
- **recent_names**: List of recently used names
- **prices**: Machine line pricing [over_threshold, under_threshold]
- **handpacks**: Custom handpack types and pricing

## Version History

### [1.3.1] - 2024-12-19
**Added:**
- Recent names autocomplete feature
- Horizontal layout for name and shift fields
- "Production Lines Running" section label
- Visual spacers between sections
- Column minimum widths for better grid layout
- "Run Type" header label (instead of "Type")

### [1.2.4] - 2024-12-19
**Added:**
- Input validation for name and wage fields
- Better error handling and user feedback
- Improved notes handling in PDF reports
- Enhanced exception handling throughout

**Changed:**
- Price formatting to 4 decimal places for consistency
- Error messages to be more user-friendly
- Validation to require full name entry

### [1.2.0] - 2024-12-19
**Added:**
- Machine price editing functionality
- Configurable quantity threshold
- Read-only price displays in settings
- Edit machine prices dialog
- Edit quantity threshold dialog
- Dynamic label updates for threshold changes

**Changed:**
- Machine price fields to read-only with edit buttons
- Settings layout to include machine control buttons
- Report generation to use configurable threshold

### [1.1.0] - 2024-12-19
**Added:**
- Handpack management system
- Add, edit, delete handpack functionality
- Read-only handpack price displays
- Visual spacer between machine and handpack lines in PDF
- Handpack price editing dialogs

**Changed:**
- Handpack price fields to read-only
- Settings layout with horizontal button alignment
- UI refresh system for handpack management

### [1.0.1] - 2024-12-19
**Initial Release:**
- Basic PDF report generation
- Machine line configuration (AZ, BZ, DZ, EZ, FZ)
- Handpack lines (H1, H2)
- Settings management
- Wage and pricing configuration

## Semantic Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions
- **PATCH** version for backwards-compatible bug fixes

## Support

For issues or questions:
1. Check the version history for known issues
2. Verify your `settings.json` file is not corrupted
3. Ensure the application has write permissions in its directory

## Technical Details

- **Framework**: PyQt6
- **PDF Generation**: ReportLab
- **Data Storage**: JSON
- **Packaging**: PyInstaller
- **Platform**: Windows (standalone executable)

## License

This application is developed for internal company use. 