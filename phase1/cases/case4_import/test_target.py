from target import compute_circle_area
import math

def test_circle_area():
    assert abs(compute_circle_area(2) - (math.pi * 4)) < 0.0001

def test_circle_area_zero():
    assert compute_circle_area(0) == 0