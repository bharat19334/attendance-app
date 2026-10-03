"""Chehra detect + pehchaan (dlib). Koi internet ya extra download nahi chahiye."""
from __future__ import annotations

import importlib.util
import os
from functools import lru_cache

import cv2
import dlib
import numpy as np

GREEN = (22, 163, 74)
RED = (220, 38, 38)


@lru_cache(maxsize=1)
def _models():
    spec = importlib.util.find_spec("face_recognition_models")
    if spec is None or not spec.submodule_search_locations:
        raise RuntimeError("face_recognition_models install nahi hai. `pip install -r requirements.txt` chalao.")
    folder = os.path.join(list(spec.submodule_search_locations)[0], "models")
    detector = dlib.get_frontal_face_detector()
    predictor = dlib.shape_predictor(os.path.join(folder, "shape_predictor_68_face_landmarks.dat"))
    encoder = dlib.face_recognition_model_v1(os.path.join(folder, "dlib_face_recognition_resnet_model_v1.dat"))
    return detector, predictor, encoder


def decode_image(data: bytes, max_side: int = 1600) -> np.ndarray:
    """Bytes -> RGB image (bahut badi photo ko chhota karke, taaki tez chale)."""
    bgr = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("Photo read nahi ho payi. JPG ya PNG photo use karo.")
    h, w = bgr.shape[:2]
    scale = max_side / max(h, w)
    if scale < 1:
        bgr = cv2.resize(bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def _detect(img: np.ndarray, upsample: int) -> list:
    detector, _, _ = _models()
    h, w = img.shape[:2]
    rects = []
    for r in detector(img, upsample):
        rects.append(
            dlib.rectangle(max(0, r.left()), max(0, r.top()), min(w - 1, r.right()), min(h - 1, r.bottom()))
        )
    return rects


def _encode(img: np.ndarray, rect, jitters: int = 1) -> np.ndarray:
    _, predictor, encoder = _models()
    shape = predictor(img, rect)
    return np.array(encoder.compute_face_descriptor(img, shape, jitters), dtype=np.float64)


def _area(r) -> int:
    return max(0, r.right() - r.left()) * max(0, r.bottom() - r.top())


def encode_registration_photo(data: bytes) -> tuple[np.ndarray | None, str | None]:
    """Registration photo se ek embedding. (embedding, None) ya (None, error message)."""
    try:
        img = decode_image(data, max_side=1600)
    except ValueError as exc:
        return None, str(exc)

    rects = _detect(img, 1) or _detect(img, 2)
    if not rects:
        return None, "Chehra nahi mila. Roshni mein, seedha camera ki taraf dekhkar photo lo."
    rects.sort(key=_area, reverse=True)
    if len(rects) > 1 and _area(rects[0]) < 3 * _area(rects[1]):
        return None, "Photo mein ek se zyada chehre hain. Sirf ek student ki photo lo."
    return _encode(img, rects[0], jitters=3), None


def recognize_faces(data: bytes, roster: list[dict], tolerance: float = 0.55, upsample: int = 1) -> dict:
    """Classroom photo mein chehre dhoondo aur class ke students se match karo.

    roster: [{"id", "roll_no", "name", "embeddings": [[128 numbers], ...]}, ...]
    Return: n_faces, matched {student_id: distance}, unknown (count), annotated (RGB image)
    """
    img = decode_image(data, max_side=2400)
    rects = _detect(img, upsample)
    encodings = [_encode(img, r) for r in rects]

    # Har (chehra, student) jodi ki doori; sabse paas wali jodi pehle assign hoti hai,
    # taaki ek student ek hi chehre se match ho.
    pairs: list[tuple[float, int, int]] = []
    if encodings and roster:
        faces = np.stack(encodings)
        for j, student in enumerate(roster):
            emb = np.asarray(student["embeddings"], dtype=np.float64)
            dist = np.linalg.norm(faces[:, None, :] - emb[None, :, :], axis=2).min(axis=1)
            for i, d in enumerate(dist):
                if d <= tolerance:
                    pairs.append((float(d), i, j))
    pairs.sort()

    owner: dict[int, tuple[int, float]] = {}
    taken: set[int] = set()
    for d, i, j in pairs:
        if i in owner or j in taken:
            continue
        owner[i] = (j, d)
        taken.add(j)

    annotated = img.copy()
    h, w = annotated.shape[:2]
    thickness = max(2, w // 600)
    font_scale = max(0.5, w / 1800)
    for i, r in enumerate(rects):
        if i in owner:
            label, color = str(roster[owner[i][0]]["roll_no"]), GREEN
        else:
            label, color = "Unknown", RED
        label = label.encode("ascii", "ignore").decode() or "?"
        cv2.rectangle(annotated, (r.left(), r.top()), (r.right(), r.bottom()), color, thickness)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        y0 = max(0, r.top() - th - 8)
        cv2.rectangle(annotated, (r.left(), y0), (r.left() + tw + 8, y0 + th + 8), color, -1)
        cv2.putText(annotated, label, (r.left() + 4, y0 + th + 2), cv2.FONT_HERSHEY_SIMPLEX,
                    font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

    matched = {roster[j]["id"]: d for j, d in owner.values()}
    return {
        "n_faces": len(rects),
        "matched": matched,
        "unknown": len(rects) - len(owner),
        "annotated": annotated,
    }
