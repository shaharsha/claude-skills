import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import crop_faces as C


def test_expand_box_grows_and_clamps_to_image():
    assert C.expand_box(10, 10, 100, 100, 400, 300, margin=0.6) == (0, 0, 220, 220)


def test_expand_box_never_exceeds_small_image():
    assert C.expand_box(50, 50, 200, 200, 300, 260) == (20, 0, 260, 260)


def test_expand_box_centered_when_room():
    assert C.expand_box(400, 300, 100, 100, 1000, 1000, margin=0.5) == (350, 250, 200, 200)
