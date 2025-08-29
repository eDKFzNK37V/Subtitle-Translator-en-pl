# progress_controller.py
import time

class ProgressController:
    def __init__(self, root, progress_var, translation_label, post_label, status_label):
        self.root = root
        self.progress_var = progress_var
        self.translation_label = translation_label
        self.post_label = post_label
        self.status_label = status_label

        # totals and counters
        self.start_time: float = 0.0
        self.total_steps = 0  # = total_lines * 2
        self.done_steps = 0

        self.t_total = 0
        self.p_total = 0
        self.t_current = 0
        self.p_current = 0

    def start(self, total_lines):
        # overall
        self.total_steps = total_lines * 2
        self.done_steps = 0
        self.start_time = time.time()

        # per phase
        self.t_total = total_lines
        self.p_total = total_lines
        self.t_current = 0
        self.p_current = 0

        # UI reset
        self.progress_var.set(0)
        self.translation_label.config(text="Translation: 0%")
        self.post_label.config(text="Post-processing: waiting")
        self._update_ui(0, "Translation: 0% | ETA --:--")

    def _step_ui(self, steps=1):
        if self.total_steps <= 0 or steps <= 0:
            return

        self.done_steps += steps
        if self.done_steps > self.total_steps:
            self.done_steps = self.total_steps

        pct = (self.done_steps / self.total_steps) * 100
        self.progress_var.set(pct)

        elapsed = time.time() - self.start_time
        avg_per_step = (elapsed / self.done_steps) if self.done_steps else 0.0
        rem_secs = avg_per_step * (self.total_steps - self.done_steps)
        mins, secs = divmod(int(rem_secs), 60)

        self._update_ui(pct, f"{int(pct)}% | Time remaining: {mins:02d}:{secs:02d}")

    # ——— Translation updates (thread-safe) ———
    def update_translation_progress(self, current, total):
        if total <= 0:
            return
        self.root.after(0, self._do_translation_update, current, total)

    def _do_translation_update(self, current, total):
        # clamp & compute delta
        current = max(0, min(current, total))
        delta = max(0, current - self.t_current)
        self.t_current = current

        pct = int((current / total) * 100) if total else 0
        self.translation_label.config(text=f"Translation: {pct}%")

        # advance overall by delta steps
        self._step_ui(delta)

    # ——— Post-processing updates (thread-safe) ———
    def update_post_progress(self, current, total):
        if total <= 0:
            return
        self.root.after(0, self._do_post_update, current, total)

    def _do_post_update(self, current, total):
        # clamp & compute delta
        current = max(0, min(current, total))
        delta = max(0, current - self.p_current)
        self.p_current = current

        pct = int((current / total) * 100) if total else 0
        self.post_label.config(text=f"Post-processing: {pct}%")

        # advance overall by delta steps
        self._step_ui(delta)

    def show_post_start(self):
        # switch UI to phase 2 at 50% (no counter change here)
        pct = (self.done_steps / self.total_steps) * 100 if self.total_steps else 0
        elapsed = time.time() - self.start_time
        avg = (elapsed / self.done_steps) if self.done_steps else 0.0
        rem_secs = avg * (self.total_steps - self.done_steps)
        mins, secs = divmod(int(rem_secs), 60)
        self.post_label.config(text="Post-processing: 0%")
        self._update_ui(pct, f"Post-processing: 0% | Time remaining: {mins:02d}:{secs:02d}")

    def reset_ui(self):
        self.progress_var.set(0)
        self.translation_label.config(text="Translation: waiting")
        self.post_label.config(text="Post-processing: waiting")
        self.status_label.config(text="0%")

    def reset(self):
        self.reset_ui()
        # clear counters
        self.start_time = 0.0
        self.total_steps = 0
        self.done_steps = 0
        self.t_total = 0
        self.p_total = 0
        self.t_current = 0
        self.p_current = 0
        self._update_ui(0, "0%")

    def _update_ui(self, pct, status):
        self.status_label.config(text=status)
        self.root.update_idletasks()

    # optional compatibility aliases
    show_post_processing_start = show_post_start