"""Strict JSON retains non-finite metrics as explicit strings, never JSON numbers."""
import math


def json_numbers(value):
    if isinstance(value,float) and not math.isfinite(value):
        return 'NaN' if math.isnan(value) else ('Infinity' if value>0 else '-Infinity')
    if isinstance(value,dict):
        return {k:json_numbers(v) for k,v in value.items()}
    if isinstance(value,list):
        return [json_numbers(v) for v in value]
    return value
