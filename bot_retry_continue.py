import argparse
import glob
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import mss
import numpy as np

try:
    from pynput import keyboard as pynput_keyboard
except Exception:
    pynput_keyboard = None

try:
    import pydirectinput as clicker

    clicker.PAUSE = 0.03
    CLICKER_NAME = "pydirectinput"
except Exception:
    import pyautogui as clicker

    clicker.PAUSE = 0.03
    CLICKER_NAME = "pyautogui"


Point = Tuple[int, int]
MatchResult = Tuple[float, Point, Tuple[int, int]]
ROI = Tuple[int, int, int, int]


@dataclass
class BotConfig:
    threshold_button: float = 0.82
    threshold_rewards: float = 0.84
    scan_interval: float = 0.35
    post_click_sleep: float = 1.6
    loading_wait: float = 8.0
    decision_roi: Optional[ROI] = None
    ready_roi: Optional[ROI] = None
    enable_hotkeys: bool = True
    pause_hotkey: str = "<f8>"
    stop_hotkey: str = "<f9>"
    debug: bool = False
    dry_run: bool = False


class RuntimeControl:
    def __init__(self, enable_hotkeys: bool, pause_hotkey: str, stop_hotkey: str):
        self.enable_hotkeys = enable_hotkeys
        self.pause_hotkey = pause_hotkey
        self.stop_hotkey = stop_hotkey
        self.paused = False
        self.stop_requested = False
        self.listener = None

    def start(self) -> None:
        if not self.enable_hotkeys:
            print("[INFO] Hotkeys disabled")
            return

        if pynput_keyboard is None:
            print("[WARN] pynput is not available. Hotkeys are disabled.")
            return

        try:
            self.listener = pynput_keyboard.GlobalHotKeys(
                {
                    self.pause_hotkey: self.toggle_pause,
                    self.stop_hotkey: self.request_stop,
                }
            )
            self.listener.start()
            print(
                f"[INFO] Hotkeys active: pause/resume={self.pause_hotkey}, stop={self.stop_hotkey}"
            )
        except Exception as exc:
            print(f"[WARN] Failed to start hotkeys: {exc}")

    def close(self) -> None:
        if self.listener is not None:
            try:
                self.listener.stop()
            except Exception:
                pass

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        if self.paused:
            print("[INFO] Bot paused")
        else:
            print("[INFO] Bot resumed")

    def request_stop(self) -> None:
        self.stop_requested = True
        print("[INFO] Stop requested by hotkey")


class AdventureBot:
    def __init__(self, images_dir: Path, config: BotConfig):
        self.images_dir = images_dir
        self.config = config
        self.templates: Dict[str, List[np.ndarray]] = {
            "retry": self._load_templates("*Retry*"),
            "continue": self._load_templates("*Continue*"),
            "ready": self._load_templates("*Ready*"),
            "rewards_positive": self._load_templates("*rewards left*"),
            "rewards_zero": self._load_templates_any(
                ["*0 rewards*", "*zero rewards*", "*no rewards*"]
            ),
        }

        self._validate_templates()
        self.monitor = self._get_primary_monitor()

    def _load_templates(self, pattern: str) -> List[np.ndarray]:
        files = sorted(glob.glob(str(self.images_dir / pattern)))
        loaded: List[np.ndarray] = []
        for file in files:
            img = cv2.imread(file, cv2.IMREAD_COLOR)
            if img is not None:
                loaded.append(img)
        return loaded

    def _load_templates_any(self, patterns: List[str]) -> List[np.ndarray]:
        loaded: List[np.ndarray] = []
        for pattern in patterns:
            loaded.extend(self._load_templates(pattern))
        return loaded

    def _validate_templates(self) -> None:
        required = ["retry", "continue", "ready", "rewards_positive"]
        missing = [key for key in required if len(self.templates[key]) == 0]
        if missing:
            missing_str = ", ".join(missing)
            raise FileNotFoundError(
                f"Missing template images for: {missing_str}. Check folder: {self.images_dir}"
            )

    @staticmethod
    def _get_primary_monitor() -> Dict[str, int]:
        with mss.mss() as sct:
            # monitor[0] is a virtual monitor (all displays). monitor[1] is primary.
            return dict(sct.monitors[1])

    def _capture_screen(self) -> np.ndarray:
        with mss.mss() as sct:
            raw = np.array(sct.grab(self.monitor))
        return cv2.cvtColor(raw, cv2.COLOR_BGRA2BGR)

    @staticmethod
    def _crop_by_roi(screen: np.ndarray, roi: Optional[ROI]) -> Tuple[np.ndarray, Point]:
        if roi is None:
            return screen, (0, 0)

        x, y, w, h = roi
        h_screen, w_screen = screen.shape[:2]
        left = max(0, x)
        top = max(0, y)
        right = min(w_screen, x + w)
        bottom = min(h_screen, y + h)

        if right <= left or bottom <= top:
            return screen, (0, 0)

        return screen[top:bottom, left:right], (left, top)

    def _find_best(
        self, screen: np.ndarray, templates: List[np.ndarray], roi: Optional[ROI] = None
    ) -> Optional[MatchResult]:
        if len(templates) == 0:
            return None

        search_img, (off_x, off_y) = self._crop_by_roi(screen, roi)
        best_score = -1.0
        best_pos = (0, 0)
        best_size = (0, 0)

        for template in templates:
            t_h, t_w = template.shape[:2]
            s_h, s_w = search_img.shape[:2]
            if t_h > s_h or t_w > s_w:
                continue

            result = cv2.matchTemplate(search_img, template, cv2.TM_CCOEFF_NORMED)
            _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(result)
            if max_val > best_score:
                best_score = float(max_val)
                best_pos = (int(max_loc[0] + off_x), int(max_loc[1] + off_y))
                best_size = (int(template.shape[1]), int(template.shape[0]))

        if best_score < 0:
            return None

        return best_score, best_pos, best_size

    @staticmethod
    def _center(pos: Point, size: Tuple[int, int]) -> Point:
        return (pos[0] + size[0] // 2, pos[1] + size[1] // 2)

    def _click(self, x: int, y: int, reason: str) -> None:
        if self.config.dry_run:
            print(f"[DRY RUN] Click {reason} at ({x}, {y})")
            return

        clicker.moveTo(x, y)
        clicker.click(x, y)
        print(f"[ACTION] Click {reason} at ({x}, {y}) using {CLICKER_NAME}")

    @staticmethod
    def _match_box(match: MatchResult) -> ROI:
        _score, (x, y), (w, h) = match
        return (x, y, w, h)

    def _make_union_roi(self, boxes: List[ROI], padding: int = 40) -> Optional[ROI]:
        if len(boxes) == 0:
            return None

        min_x = min(x for x, _, _, _ in boxes)
        min_y = min(y for _, y, _, _ in boxes)
        max_x = max(x + w for x, _, w, _ in boxes)
        max_y = max(y + h for _, y, _, h in boxes)

        min_x = max(0, min_x - padding)
        min_y = max(0, min_y - padding)
        max_x = min(self.monitor["width"], max_x + padding)
        max_y = min(self.monitor["height"], max_y + padding)

        width = max_x - min_x
        height = max_y - min_y
        if width <= 0 or height <= 0:
            return None

        return (min_x, min_y, width, height)

    def _log_match(self, name: str, match: Optional[MatchResult]) -> None:
        if not self.config.debug:
            return

        if match is None:
            print(f"[DEBUG] {name}: not found")
            return

        score, pos, size = match
        cx, cy = self._center(pos, size)
        print(
            f"[DEBUG] {name}: score={score:.3f}, pos={pos}, size={size}, center=({cx}, {cy})"
        )

    def _detect_state(self, screen: np.ndarray) -> Dict[str, Optional[MatchResult]]:
        rewards_match = self._find_best(
            screen, self.templates["rewards_positive"], self.config.decision_roi
        )
        rewards_zero_match = self._find_best(
            screen, self.templates["rewards_zero"], self.config.decision_roi
        )
        retry_match = self._find_best(screen, self.templates["retry"], self.config.decision_roi)
        continue_match = self._find_best(
            screen, self.templates["continue"], self.config.decision_roi
        )
        ready_match = self._find_best(screen, self.templates["ready"], self.config.ready_roi)

        self._log_match("rewards_positive", rewards_match)
        self._log_match("rewards_zero", rewards_zero_match)
        self._log_match("retry", retry_match)
        self._log_match("continue", continue_match)
        self._log_match("ready", ready_match)

        return {
            "rewards_positive": rewards_match,
            "rewards_zero": rewards_zero_match,
            "retry": retry_match,
            "continue": continue_match,
            "ready": ready_match,
        }

    @staticmethod
    def _score(match: Optional[MatchResult]) -> float:
        return match[0] if match else 0.0

    def run(self) -> None:
        print("=== Roblox Adventure Retry/Continue Bot ===")
        print(f"Templates folder: {self.images_dir}")
        print(f"Threshold button: {self.config.threshold_button}")
        print(f"Threshold rewards: {self.config.threshold_rewards}")
        print(f"Decision ROI: {self.config.decision_roi}")
        print(f"Ready ROI: {self.config.ready_roi}")
        print(f"Dry run: {self.config.dry_run}")
        print(
            f"Hotkeys: {'on' if self.config.enable_hotkeys else 'off'}"
            f" (pause={self.config.pause_hotkey}, stop={self.config.stop_hotkey})"
        )
        print("Stop with Ctrl+C")

        runtime = RuntimeControl(
            enable_hotkeys=self.config.enable_hotkeys,
            pause_hotkey=self.config.pause_hotkey,
            stop_hotkey=self.config.stop_hotkey,
        )
        runtime.start()

        phase = "DECIDE"
        next_scan_at = time.time()

        try:
            while True:
                if runtime.stop_requested:
                    print("[INFO] Bot stopped by hotkey")
                    break

                if runtime.paused:
                    time.sleep(0.08)
                    continue

                now = time.time()
                if now < next_scan_at:
                    time.sleep(0.02)
                    continue

                screen = self._capture_screen()
                matches = self._detect_state(screen)

                rewards_score = self._score(matches["rewards_positive"])
                rewards_zero_score = self._score(matches["rewards_zero"])
                retry_score = self._score(matches["retry"])
                continue_score = self._score(matches["continue"])
                ready_score = self._score(matches["ready"])

                if phase == "DECIDE":
                    rewards_left_positive = rewards_score >= self.config.threshold_rewards
                    rewards_zero = rewards_zero_score >= self.config.threshold_rewards
                    retry_visible = retry_score >= self.config.threshold_button
                    continue_visible = continue_score >= self.config.threshold_button

                    if rewards_zero and continue_visible:
                        _, pos, size = matches["continue"]  # type: ignore[misc]
                        cx, cy = self._center(pos, size)
                        self._click(cx, cy, "Continue / Next Stage (0 reward)")
                        phase = "WAIT_READY"
                        next_scan_at = time.time() + self.config.loading_wait
                        continue

                    if rewards_left_positive and retry_visible:
                        _, pos, size = matches["retry"]  # type: ignore[misc]
                        cx, cy = self._center(pos, size)
                        self._click(cx, cy, "Retry Stage")
                        phase = "WAIT_READY"
                        next_scan_at = time.time() + self.config.loading_wait
                        continue

                    if (not rewards_left_positive) and continue_visible:
                        _, pos, size = matches["continue"]  # type: ignore[misc]
                        cx, cy = self._center(pos, size)
                        self._click(cx, cy, "Continue / Next Stage")
                        phase = "WAIT_READY"
                        next_scan_at = time.time() + self.config.loading_wait
                        continue

                    # Fallback rules when rewards text is not detected clearly.
                    if continue_visible and not retry_visible:
                        _, pos, size = matches["continue"]  # type: ignore[misc]
                        cx, cy = self._center(pos, size)
                        self._click(cx, cy, "Continue fallback")
                        phase = "WAIT_READY"
                        next_scan_at = time.time() + self.config.loading_wait
                        continue

                    if retry_visible and not continue_visible:
                        _, pos, size = matches["retry"]  # type: ignore[misc]
                        cx, cy = self._center(pos, size)
                        self._click(cx, cy, "Retry fallback")
                        phase = "WAIT_READY"
                        next_scan_at = time.time() + self.config.loading_wait
                        continue

                    next_scan_at = time.time() + self.config.scan_interval
                    continue

                if phase == "WAIT_READY":
                    if ready_score >= self.config.threshold_button:
                        _, pos, size = matches["ready"]  # type: ignore[misc]
                        cx, cy = self._center(pos, size)
                        self._click(cx, cy, "Ready")
                        phase = "DECIDE"
                        next_scan_at = time.time() + self.config.post_click_sleep
                        continue

                    next_scan_at = time.time() + self.config.scan_interval
                    continue
        finally:
            runtime.close()

    def suggest_rois(
        self, samples: int = 12, sample_interval: float = 0.15
    ) -> Tuple[Optional[ROI], Optional[ROI]]:
        print("=== ROI Suggestion Mode ===")
        print("Keep Roblox on the result screen while sampling runs.")
        print(f"Sampling frames: {samples}")

        decision_boxes: List[ROI] = []
        ready_boxes: List[ROI] = []

        for index in range(samples):
            screen = self._capture_screen()

            rewards_match = self._find_best(screen, self.templates["rewards_positive"], None)
            retry_match = self._find_best(screen, self.templates["retry"], None)
            continue_match = self._find_best(screen, self.templates["continue"], None)
            ready_match = self._find_best(screen, self.templates["ready"], None)

            if rewards_match and rewards_match[0] >= self.config.threshold_rewards:
                decision_boxes.append(self._match_box(rewards_match))
            if retry_match and retry_match[0] >= self.config.threshold_button:
                decision_boxes.append(self._match_box(retry_match))
            if continue_match and continue_match[0] >= self.config.threshold_button:
                decision_boxes.append(self._match_box(continue_match))
            if ready_match and ready_match[0] >= self.config.threshold_button:
                ready_boxes.append(self._match_box(ready_match))

            print(f"[SAMPLE {index + 1}/{samples}] done")
            time.sleep(sample_interval)

        decision_roi = self._make_union_roi(decision_boxes, padding=60)
        ready_roi = self._make_union_roi(ready_boxes, padding=50)

        print("\n=== Suggested ROI ===")
        if decision_roi is None:
            print("Decision ROI: not enough confident matches")
        else:
            x, y, w, h = decision_roi
            print(f"Decision ROI: {x},{y},{w},{h}")

        if ready_roi is None:
            print("Ready ROI: not enough confident matches")
        else:
            x, y, w, h = ready_roi
            print(f"Ready ROI: {x},{y},{w},{h}")

        if decision_roi or ready_roi:
            print("\nRun command example:")
            decision_part = ""
            ready_part = ""
            if decision_roi:
                x, y, w, h = decision_roi
                decision_part = f" --decision-roi {x},{y},{w},{h}"
            if ready_roi:
                x, y, w, h = ready_roi
                ready_part = f" --ready-roi {x},{y},{w},{h}"
            print(f"python bot_retry_continue.py --debug{decision_part}{ready_part}")

        return decision_roi, ready_roi


def _roi_to_str(roi: Optional[ROI]) -> Optional[str]:
    if roi is None:
        return None
    x, y, w, h = roi
    return f"{x},{y},{w},{h}"


def _save_roi_config(path: Path, decision_roi: Optional[ROI], ready_roi: Optional[ROI]) -> None:
    payload = {
        "decision_roi": _roi_to_str(decision_roi),
        "ready_roi": _roi_to_str(ready_roi),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_roi_config(path: Path) -> Tuple[Optional[ROI], Optional[ROI]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("ROI config must be a JSON object")

    decision_roi = _parse_roi(raw.get("decision_roi"))
    ready_roi = _parse_roi(raw.get("ready_roi"))
    return decision_roi, ready_roi


def _parse_roi(value: Optional[str]) -> Optional[ROI]:
    if value is None:
        return None

    parts = [item.strip() for item in value.split(",")]
    if len(parts) != 4:
        raise ValueError("ROI format must be x,y,w,h")

    x, y, w, h = [int(v) for v in parts]
    if w <= 0 or h <= 0:
        raise ValueError("ROI width and height must be > 0")
    return (x, y, w, h)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Roblox retry/continue + ready bot with OpenCV")
    parser.add_argument(
        "--images-dir",
        default="imgs",
        help="Directory containing template images (default: imgs)",
    )
    parser.add_argument(
        "--threshold-button",
        type=float,
        default=0.82,
        help="Template score threshold for buttons (default: 0.82)",
    )
    parser.add_argument(
        "--threshold-rewards",
        type=float,
        default=0.84,
        help="Template score threshold for rewards text (default: 0.84)",
    )
    parser.add_argument(
        "--scan-interval",
        type=float,
        default=0.35,
        help="Seconds between scans (default: 0.35)",
    )
    parser.add_argument(
        "--loading-wait",
        type=float,
        default=8.0,
        help="Seconds to wait after retry/continue click before scanning for ready (default: 8)",
    )
    parser.add_argument(
        "--decision-roi",
        type=str,
        default=None,
        help="Decision ROI in pixels format x,y,w,h (for rewards/retry/continue detection)",
    )
    parser.add_argument(
        "--ready-roi",
        type=str,
        default=None,
        help="Ready ROI in pixels format x,y,w,h (for ready button detection)",
    )
    parser.add_argument(
        "--suggest-roi",
        action="store_true",
        help="Suggest ROI automatically by sampling current screen",
    )
    parser.add_argument(
        "--suggest-samples",
        type=int,
        default=12,
        help="How many frames to sample for ROI suggestion (default: 12)",
    )
    parser.add_argument(
        "--suggest-interval",
        type=float,
        default=0.15,
        help="Seconds between ROI suggestion samples (default: 0.15)",
    )
    parser.add_argument(
        "--roi-config",
        type=str,
        default="roi_config.json",
        help="Path to ROI config JSON file for load/save (default: roi_config.json)",
    )
    parser.add_argument(
        "--no-load-roi-config",
        action="store_true",
        help="Disable auto-loading ROI from --roi-config",
    )
    parser.add_argument(
        "--no-save-roi-config",
        action="store_true",
        help="Disable auto-saving ROI after --suggest-roi",
    )
    parser.add_argument(
        "--no-hotkeys",
        action="store_true",
        help="Disable global pause/stop hotkeys",
    )
    parser.add_argument(
        "--pause-hotkey",
        type=str,
        default="<f8>",
        help="Global hotkey to toggle pause/resume (default: <f8>)",
    )
    parser.add_argument(
        "--stop-hotkey",
        type=str,
        default="<f9>",
        help="Global hotkey to stop the bot (default: <f9>)",
    )
    parser.add_argument("--debug", action="store_true", help="Print detection scores")
    parser.add_argument("--dry-run", action="store_true", help="Do not click, only print actions")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    roi_config_path = Path(args.roi_config).resolve()
    decision_roi = _parse_roi(args.decision_roi)
    ready_roi = _parse_roi(args.ready_roi)

    if (not args.no_load_roi_config) and roi_config_path.exists():
        try:
            cfg_decision, cfg_ready = _load_roi_config(roi_config_path)
            # CLI values take priority over config file values.
            if decision_roi is None:
                decision_roi = cfg_decision
            if ready_roi is None:
                ready_roi = cfg_ready
            print(f"[INFO] Loaded ROI config from: {roi_config_path}")
        except Exception as exc:
            print(f"[WARN] Failed to load ROI config {roi_config_path}: {exc}")

    config = BotConfig(
        threshold_button=args.threshold_button,
        threshold_rewards=args.threshold_rewards,
        scan_interval=args.scan_interval,
        loading_wait=args.loading_wait,
        decision_roi=decision_roi,
        ready_roi=ready_roi,
        enable_hotkeys=not args.no_hotkeys,
        pause_hotkey=args.pause_hotkey,
        stop_hotkey=args.stop_hotkey,
        debug=args.debug,
        dry_run=args.dry_run,
    )

    images_dir = Path(args.images_dir).resolve()
    if not images_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")

    bot = AdventureBot(images_dir=images_dir, config=config)
    if args.suggest_roi:
        decision_roi, ready_roi = bot.suggest_rois(
            samples=max(1, args.suggest_samples),
            sample_interval=max(0.01, args.suggest_interval),
        )
        if not args.no_save_roi_config:
            try:
                _save_roi_config(roi_config_path, decision_roi, ready_roi)
                print(f"[INFO] ROI config saved to: {roi_config_path}")
            except Exception as exc:
                print(f"[WARN] Failed to save ROI config {roi_config_path}: {exc}")
        return

    bot.run()


if __name__ == "__main__":
    main()
