# Runtime State

This directory stores generated workflow state for the unified investing
operating system.

## What Lives Here

- coordinator session JSON files
- coordinator lock files
- temporary files created during atomic writes

## What Does Not Live Here

- approved rule snapshots
- evidence Packets
- traceability indexes
- credentials or broker exports

## Tracking Rule

Only the placeholder `.gitkeep` file, if present, may be committed. Generated
session files and locks stay local and untracked.
