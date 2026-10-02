#!/usr/bin/env python3
from pathlib import Path
from inputs import verify_inputs
verify_inputs(Path(__file__).resolve().parents[1])
print('Exact source/build/legal input inventory matches; not a runtime or permission certification.')
