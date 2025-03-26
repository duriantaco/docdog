# Changelog

All notable changes to DocDog will be documented in this file.

## [0.0.3] - 2025-03-26
### Fixed
-Fixed bug in `main.py` with relation to `find_project_root` function. Looking in the wrong dir to generate the reports. 
-Modified `test_find_project_root`

## [0.0.2] - 2025-03-25

### Added
- Added lru cache and multi-threading

### Fixed
- Removed openai api

## [0.0.1] - 2025-03-25

### Added
- Initial release of DocDog
- Core functionality for AI-assisted README generation
- Project chunking capabilities using pykomodo 
- CLI interface with basic options
- Validation phase for quality control
- Cleared tests 

### Fixed
- Proper handling of empty README generation
- Fixed path handling in project root detection