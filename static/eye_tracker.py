"""
Eye Tracker module.

This module provides a modular EyeTracker class designed to:
- Open a camera stream or video/file input
- Process frames (preprocessing pipeline hook)
- Detect eyes and estimate gaze direction (placeholders/stubs)
- Run a simple calibration routine (collect samples, fit mapping)
- Offer integration points for AI/ML models

The implementation includes robust error handling, clear docstrings,
and type hints for easier maintenance and extension.

Note:
- This file intentionally contains placeholders and extension points
  where you can plug in your custom computer vision or AI models.
- Dependencies on heavy CV libraries (e.g., OpenCV, MediaPipe) are optional
  and imported lazily when needed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Deque, Dict, Generator, Iterable, List, Optional, Tuple, Union
import contextlib
import time
import collections

# Optional/lazy imports are wrapped to avoid hard dependency at import time.
# Real implementations will typically rely on OpenCV (cv2) and NumPy.
with contextlib.suppress(ImportError):
    import cv2  # type: ignore
with contextlib.suppress(ImportError):
    import numpy as np  # type: ignore


class EyeTrackerError(Exception):
    """Domain-specific exception for EyeTracker-related errors."""


@dataclass
class CameraConfig:
    """Configuration for camera/video input.

    Attributes:
        source: Camera index (int) or path/URL to a video stream/file.
        width: Desired capture width in pixels (if supported by backend).
        height: Desired capture height in pixels (if supported by backend).
        fps: Desired frames per second (best-effort; backend-dependent).
        backend: Optional backend API preference (e.g., cv2.CAP_DSHOW on Windows).
    """
    source: Union[int, str] = 0
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[int] = None
    backend: Optional[int] = None


@dataclass
class CalibrationSample:
    """A single calibration data point linking eye features to a screen point.

    Attributes:
        features: Extracted eye/face features (vector), content is model-defined.
        target_xy: Target screen or normalized coordinates (x, y) in [0, 1] or pixels.
        timestamp: Capture time in seconds.
    """
    features: List[float]
    target_xy: Tuple[float, float]
    timestamp: float


@dataclass
class CalibrationModel:
    """A simple linear calibration model as a placeholder.

    You can replace this with your custom regression/ML model.
    For example, scikit-learn LinearRegression, a neural network, etc.
    """
    # Simple affine mapping from features to 2D point: y = W f + b.
    W: Optional[List[List[float]]] = None
    b: Optional[List[float]] = None

    def fit(self, samples: List[CalibrationSample]) -> None:
        """Fit the model on collected calibration samples.

        This default implementation fits a trivial mean-based mapping to
        demonstrate the API. Replace with a proper model.
        """
        if not samples:
            raise EyeTrackerError("No calibration samples provided.")
        # Placeholder: compute mean of features and map to mean target.
        # Replace this with proper regression.
        feat_dim = len(samples[0].features)
        for s in samples:
            if len(s.features) != feat_dim:
                raise EyeTrackerError("Inconsistent feature dimensions in samples.")
        mean_feat = [0.0] * feat_dim
        mean_xy = [0.0, 0.0]
        for s in samples:
            for i, v in enumerate(s.features):
                mean_feat[i] += v
            mean_xy[0] += s.target_xy[0]
            mean_xy[1] += s.target_xy[1]
        n = float(len(samples))
        mean_feat = [v / n for v in mean_feat]
        mean_xy = [v / n for v in mean_xy]
        # Store as a degenerate mapping that always returns the mean target.
        self.W = [[0.0 for _ in range(feat_dim)] for _ in range(2)]
        self.b = mean_xy

    def predict(self, features: List[float]) -> Tuple[float, float]:
        """Predict gaze coordinates from features.

        Returns a tuple (x, y). If not fitted, returns (nan, nan).
        """
        if self.W is None or self.b is None:
            # Not fitted yet
            return float("nan"), float("nan")
        # Since W is zero in the placeholder, return the bias (mean target)
        return float(self.b[0]), float(self.b[1])


@dataclass
class EyeTracker:
    """Modular Eye Tracker with pluggable components.

    The class exposes hooks for frame acquisition, preprocessing, feature
    extraction, gaze estimation, and calibration.
    """
    camera_config: CameraConfig = field(default_factory=CameraConfig)
    preprocess_fn: Optional[Callable[["np.ndarray"], "np.ndarray"]] = None
    feature_extractor: Optional[Callable[["np.ndarray"], List[float]]] = None
    gaze_estimator: Optional[Callable[[List[float]], Tuple[float, float]]] = None
    calibration_model: CalibrationModel = field(default_factory=CalibrationModel)

    # Internal state
    _cap: Optional["cv2.VideoCapture"] = field(default=None, init=False, repr=False)
    _is_open: bool = field(default=False, init=False)
    _frame_count: int = field(default=0, init=False)
    _last_frame_ts: float = field(default=0.0, init=False)
    _recent_fps: Deque[float] = field(default_factory=lambda: collections.deque(maxlen=60), init=False)

    def open(self) -> None:
        """Open the camera/video stream as configured.

        Raises EyeTrackerError on failure or if OpenCV isn't available.
        """
        if "cv2" not in globals():
            raise EyeTrackerError("OpenCV (cv2) is required to open camera streams.")

        if self._is_open:
            return

        source = self.camera_config.source
        backend = self.camera_config.backend

        try:
            if isinstance(source, int) and backend is not None:
                cap = cv2.VideoCapture(source, backend)
            else:
                cap = cv2.VideoCapture(source)
        except Exception as e:
            raise EyeTrackerError(f"Failed to create VideoCapture: {e}") from e

        if not cap or not cap.isOpened():
            raise EyeTrackerError(f"Unable to open video source: {source}")

        # Apply optional properties
        if self.camera_config.width:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, float(self.camera_config.width))
        if self.camera_config.height:
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, float(self.camera_config.height))
        if self.camera_config.fps:
            cap.set(cv2.CAP_PROP_FPS, float(self.camera_config.fps))

        self._cap = cap
        self._is_open = True
        self._frame_count = 0
        self._last_frame_ts = time.time()
        self._recent_fps.clear()

    def close(self) -> None:
        """Release the camera/video stream safely."""
        cap = self._cap
        self._is_open = False
        self._cap = None
        if cap is not None:
            with contextlib.suppress(Exception):
                cap.release()

    def __enter__(self) -> "EyeTracker":
        """Context manager entry: open the stream."""
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """Context manager exit: ensure the stream is closed."""
        self.close()

    def frames(self) -> Generator[Tuple[float, "np.ndarray"], None, None]:
        """Yield frames as (timestamp, frame) tuples.

        The frame is a BGR image (OpenCV default). Raises EyeTrackerError if
        the stream is not open or if cv2/np are unavailable.
        """
        if "cv2" not in globals() or "np" not in globals():
            raise EyeTrackerError("OpenCV (cv2) and NumPy (np) are required for frame access.")
        if not self._is_open or self._cap is None:
            raise EyeTrackerError("Stream is not open. Call open() first.")

        while self._is_open and self._cap is not None:
            ok, frame = self._cap.read()
            ts = time.time()
            if not ok or frame is None:
                # End of stream or transient read error.
                break
            self._frame_count += 1
            # FPS estimate
            dt = ts - self._last_frame_ts
            self._last_frame_ts = ts
            if dt > 0:
                self._recent_fps.append(1.0 / dt)
            yield ts, frame

    def get_fps(self) -> float:
        """Return a recent FPS estimate (median over last ~60 frames)."""
        if not self._recent_fps:
            return 0.0
        arr = sorted(self._recent_fps)
        mid = len(arr) // 2
        if len(arr) % 2 == 1:
            return arr[mid]
        return 0.5 * (arr[mid - 1] + arr[mid])

    def process_frame(self, frame: "np.ndarray") -> "np.ndarray":
        """Run preprocessing on a frame.

        Default: returns the frame unchanged. Plug in your own function via
        preprocess_fn to convert color spaces, denoise, resize, etc.
        """
        if self.preprocess_fn is not None:
            try:
                return self.preprocess_fn(frame)
            except Exception as e:
                raise EyeTrackerError(f"Preprocess function failed: {e}") from e
        return frame

    def extract_features(self, frame: "np.ndarray") -> List[float]:
        """Extract eye/face features from the frame.

        This is a placeholder. Provide your own implementation via
        feature_extractor. For example:
        - Use a face/eye detector (Haar cascades, DNN, MediaPipe)
        - Locate pupils/iris landmarks
        - Return a vector of features such as landmark coords, pupil centers,
          eye aspect ratios, etc.
        """
        if self.feature_extractor is not None:
            try:
                return self.feature_extractor(frame)
            except Exception as e:
                raise EyeTrackerError(f"Feature extractor failed: {e}") from e
        # Placeholder: compute very simple intensity statistics as features.
        if "np" not in globals():
            raise EyeTrackerError("NumPy (np) is required for default feature extraction.")
        if "cv2" in globals():
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            # Fallback if cv2 missing but np present: average across color channels
            gray = frame.mean(axis=2)
        mean_intensity = float(gray.mean())
        std_intensity = float(gray.std())
        return [mean_intensity, std_intensity]

    def estimate_gaze(self, features: List[float]) -> Tuple[float, float]:
        """Estimate gaze coordinates from features.

        The default implementation delegates to the calibration model.
        Replace or wrap this method to integrate an AI gaze model.
        """
        if self.gaze_estimator is not None:
            try:
                return self.gaze_estimator(features)
            except Exception as e:
                raise EyeTrackerError(f"Gaze estimator failed: {e}") from e
        return self.calibration_model.predict(features)

    def calibrate(self, samples: List[CalibrationSample]) -> None:
        """Fit the calibration model using the provided samples."""
        try:
            self.calibration_model.fit(samples)
        except Exception as e:
            raise EyeTrackerError(f"Calibration failed: {e}") from e

    # --------- Convenience high-level routines ---------

    def run_calibration_routine(
        self,
        targets: Iterable[Tuple[float, float]],
        seconds_per_target: float = 1.0,
        max_samples_per_target: int = 10,
        on_sample: Optional[Callable[[CalibrationSample], None]] = None,
    ) -> List[CalibrationSample]:
        """Simple interactive calibration routine.

        Displays (or expects the app to display) targets in sequence and
        collects feature samples mapped to each target.

        Args:
            targets: Iterable of target (x, y) coordinates in screen or normalized space.
            seconds_per_target: How long to collect samples for each target.
            max_samples_per_target: Cap the number of samples per target.
            on_sample: Optional callback invoked on every collected sample.

        Returns:
            List of collected CalibrationSample objects.

        Notes:
            - This method does not draw UI. Your app should show targets
              while calling this routine. You can integrate UI callbacks.
            - Ensure the camera is open and frames() is being iterated.
        """
        if not self._is_open:
            raise EyeTrackerError("Camera must be open before running calibration.")

        collected: List[CalibrationSample] = []
        frame_iter = self.frames()

        for tx, ty in targets:
            start = time.time()
            count = 0
            while time.time() - start < seconds_per_target and count < max_samples_per_target:
                try:
                    ts, frame = next(frame_iter)
                except StopIteration:
                    break
                processed = self.process_frame(frame)
                feats = self.extract_features(processed)
                sample = CalibrationSample(features=feats, target_xy=(tx, ty), timestamp=ts)
                collected.append(sample)
                count += 1
                if on_sample is not None:
                    with contextlib.suppress(Exception):
                        on_sample(sample)

        # Fit model
        if collected:
            self.calibrate(collected)
        return collected

    def run_inference_loop(
        self,
        on_result: Optional[Callable[[float, "np.ndarray", Tuple[float, float], List[float]], None]] = None,
        stop_after_seconds: Optional[float] = None,
    ) -> None:
        """Run a read-process-estimate loop.

        Args:
            on_result: Optional callback called with (timestamp, frame, gaze_xy, features)
                       for each processed frame.
            stop_after_seconds: If provided, stop after the given duration.
        """
        if not self._is_open:
            raise EyeTrackerError("Camera must be open before inference loop.")

        start = time.time()
        for ts, frame in self.frames():
            processed = self.process_frame(frame)
            feats = self.extract_features(processed)
            gaze_xy = self.estimate_gaze(feats)
            if on_result is not None:
                with contextlib.suppress(Exception):
                    on_result(ts, processed, gaze_xy, feats)
            if stop_after_seconds is not None and (time.time() - start) >= stop_after_seconds:
                break

    # --------- Integration stubs for AI models ---------

    def set_preprocess(self, fn: Callable[["np.ndarray"], "np.ndarray"]) -> None:
        """Set a custom preprocessing function.

        Example:
            def preprocess(frame: np.ndarray) -> np.ndarray:
                return cv2.GaussianBlur(frame, (3, 3), 0)
            tracker.set_preprocess(preprocess)
        """
        self.preprocess_fn = fn

    def set_feature_extractor(self, fn: Callable[["np.ndarray"], List[float]]) -> None:
        """Set a custom feature extractor function.

        Example placeholder using MediaPipe/landmarks or your CNN:
            def extract(frame: np.ndarray) -> List[float]:
                # TODO: detect eyes, compute landmarks
                return features
        """
        self.feature_extractor = fn

    def set_gaze_estimator(self, fn: Callable[[List[float]], Tuple[float, float]]) -> None:
        """Set a custom gaze estimator function.

        Example using a trained regression/NN model:
            def estimate(features: List[float]) -> Tuple[float, float]:
                return model.predict(features)
        """
        self.gaze_estimator = fn

