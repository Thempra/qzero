# QZero Project Structure Documentation

**Generated:** 2026-02-06 09:00:02 (Europe/Madrid)

---

## 📊 Statistics

| Metric | Value |
|--------|-------|
| **Modules** | 8 |
| **Functions** | 104 |
| **Classes** | 27 |
| **Unique Dependencies** | 38 |

---

## 🧩 Modules Overview

### __init__
- Functions: `0`
- Classes: `0`
- Dependencies: `predictor`

### detection
- Functions: `15`
- Classes: `8`
- Dependencies: `enum, abc, typing, numpy, time`
  ...and 9 more

### api
- Functions: `5`
- Classes: `2`
- Dependencies: `os, pickle, pandas, typing, pathlib`
  ...and 6 more

### predictor
- Functions: `15`
- Classes: `1`
- Dependencies: `evaluation, pickle, typing, numpy, time`
  ...and 5 more

### classical
- Functions: `0`
- Classes: `0`
- Dependencies: `baseline`

### quantum
- Functions: `6`
- Classes: `1`
- Dependencies: `enum, qiskit, warnings, typing, numpy`

### evaluation
- Functions: `5`
- Classes: `1`
- Dependencies: `sklearn, dataclasses, typing, numpy`

### preprocessing
- Functions: `6`
- Classes: `1`
- Dependencies: `sklearn, typing, pandas, numpy, data_loader`

---

## 🚀 Key Services

### api
- Functions: `5`
- Classes: `2`

---

## 📦 Dependency Map

### __init__
- `predictor`

### api
- `fastapi, io, logging, os, pandas, pathlib, pickle, pydantic, src, typing, uvicorn`

### classical
- `baseline, dataclasses, numpy, preprocessing, sklearn, sys, time, typing`

### detection
- `abc, asyncio, dataclasses, datetime, enum, json, logging, numpy, pathlib, random, src, sys, time, typing`

### evaluation
- `dataclasses, metrics, numpy, sklearn, typing`

### predictor
- `classical, evaluation, json, numpy, pathlib, pickle, preprocessing, quantum, time, typing`

### preprocessing
- `data_loader, feature_engineering, numpy, pandas, pathlib, sklearn, typing`

### quantum
- `dataclasses, enum, feature_maps, numpy, qiskit, qiskit_machine_learning, qivae, qsvm, sklearn, src, sys, time, torch, typing, warnings`


*Document generated automatically by QZero README Generator*
