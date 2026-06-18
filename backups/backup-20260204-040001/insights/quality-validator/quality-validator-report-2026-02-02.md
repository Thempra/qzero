# QZero Data Quality Validator Report

**Timestamp:** 2026-02-02 06:08:04

## Validation Summary

- **Total Files Checked:** 6
- **Valid Files:** 0
- **Corrupted Files:** 6
- **Data Drifts Detected:** 4

## Overall Quality Score

**0/100**

## Detailed Validation Reports

### augmented-20260202-013639.json

**Status:** ❌ FAIL

- **File Size:** 76796 bytes
- **Total Records:** 50
- **Corrupted Records:** 150
- **Corruption Rate:** 300.0%
- **Invalid Features:** None

### augmented-20260202-013845.json

**Status:** ❌ FAIL

- **File Size:** 76729 bytes
- **Total Records:** 50
- **Corrupted Records:** 150
- **Corruption Rate:** 300.0%
- **Invalid Features:** None

### augmented-20260202-020001.json

**Status:** ❌ FAIL

- **File Size:** 76710 bytes
- **Total Records:** 50
- **Corrupted Records:** 150
- **Corruption Rate:** 300.0%
- **Invalid Features:** None

### augmented-20260202-030001.json

**Status:** ❌ FAIL

- **File Size:** 76705 bytes
- **Total Records:** 50
- **Corrupted Records:** 150
- **Corruption Rate:** 300.0%
- **Invalid Features:** None

### augmented-20260202-040002.json

**Status:** ❌ FAIL

- **File Size:** 76710 bytes
- **Total Records:** 50
- **Corrupted Records:** 150
- **Corruption Rate:** 300.0%
- **Invalid Features:** None

### augmented-20260202-050001.json

**Status:** ❌ FAIL

- **File Size:** 76658 bytes
- **Total Records:** 50
- **Corrupted Records:** 150
- **Corruption Rate:** 300.0%
- **Invalid Features:** None

## Data Drift Analysis

### augmented-20260202-013639.json -> augmented-20260202-013845.json

- **Timestamp:** 1769996325.023291
- **Drift Detected:** Yes
- **Feature:** total_fwd_packets
- **New Mean:** 468.55
- **Baseline Mean:** 681.92
- **Drift Percentage:** 31.29%

### augmented-20260202-013845.json -> augmented-20260202-020001.json

- **Timestamp:** 1769997601.9587932
- **Drift Detected:** Yes
- **Feature:** flow_duration
- **New Mean:** 5411.92
- **Baseline Mean:** 4504.81
- **Drift Percentage:** 20.14%

### augmented-20260202-020001.json -> augmented-20260202-030001.json

- **Timestamp:** 1770001201.46166
- **Drift Detected:** Yes
- **Feature:** total_fwd_packets
- **New Mean:** 483.78
- **Baseline Mean:** 583.87
- **Drift Percentage:** 17.14%

### augmented-20260202-030001.json -> augmented-20260202-040002.json

- **Timestamp:** 1770004802.0282485
- **Drift Detected:** Yes
- **Feature:** total_fwd_packets
- **New Mean:** 694.64
- **Baseline Mean:** 483.78
- **Drift Percentage:** 43.59%

