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
        self.post_start_time = 0.0

    def start(self, translation_lines):
        # Use actual translation line count and estimate post-processing
        self.t_total = translation_lines
        self.p_total = translation_lines  # Estimate post-processing as equal to translation
        self.total_steps = self.t_total + self.p_total  # Include both phases from start
        self.done_steps = 0
        self.t_current = 0
        self.p_current = 0
        self.start_time = time.time()

        # UI reset
        self.progress_var.set(0)
        self.translation_label.config(text="Translation: 0%")
        self.post_label.config(text="Post-processing: waiting")
        self._update_ui(0, "Translation: 0% | ETA --:--")

    def set_post_total(self, post_total):
        """
        Update the actual post-processing total, replacing the initial estimate.
        """
        post_total = max(0, int(post_total))
        old_p_total = self.p_total
        self.p_total = post_total
        self.total_steps = self.t_total + self.p_total
        
        # If the post-processing total changed significantly from our estimate,
        # adjust done_steps proportionally to maintain smooth progress
        if old_p_total != self.p_total and old_p_total > 0:
            old_total = self.t_total + old_p_total
            if old_total > 0:
                # Maintain the same proportion of work completed
                progress_ratio = self.done_steps / old_total
                self.done_steps = int(progress_ratio * self.total_steps)
        
        # Clamp done_steps if we've overshot
        if self.done_steps > self.total_steps:
            self.done_steps = self.total_steps
            
        # Update UI to reflect current progress
        pct = (self.done_steps / self.total_steps) * 100 if self.total_steps else 0
        self.progress_var.set(pct)
        self._update_ui(int(pct), f"{int(pct)}% | Time remaining: --:--")
        self.post_start_time = 0.0

    # In progress_controller.py
    def _step_ui(self, steps=1):
        if self.total_steps <= 0 or steps <= 0:
            return

        self.done_steps += steps
        if self.done_steps > self.total_steps:
            self.done_steps = self.total_steps

        pct = (self.done_steps / self.total_steps) * 100 if self.total_steps else 0
        self.progress_var.set(pct)

        # Always update overall progress and ETA
        elapsed = time.time() - self.start_time
        avg_per_step = (elapsed / self.done_steps) if self.done_steps else 0.0
        rem_secs = avg_per_step * (self.total_steps - self.done_steps)
        mins, secs = divmod(int(rem_secs), 60)
        self._update_ui(int(pct), f"{int(pct)}% | Time remaining: {mins:02d}:{secs:02d}")


    # ——— Translation updates (thread-safe) ———
    def update_translation_progress(self, current, total):
        import logging
        if total <= 0:
            return
        logging.debug(f"[ProgressController] update_translation_progress: current={current}, total={total}")
        self.root.after(0, self._do_translation_update, current, total)
        # Force UI update even when window is not in focus
        try:
            self.root.update_idletasks()
        except Exception:
            pass  # Ignore if window is destroyed

    def _do_translation_update(self, current, total):
        import logging
        # clamp & compute delta
        current = max(0, min(current, total))
        delta = max(0, current - self.t_current)
        self.t_current = current

        pct = int((current / total) * 100) if total else 0
        self.translation_label.config(text=f"Translation: {pct}%")

        logging.debug(f"[ProgressController] _do_translation_update: current={current}, total={total}, delta={delta}")
        # advance overall by delta steps
        self._step_ui(delta)
        
        # Force UI update even when window is not in focus
        try:
            self.root.update_idletasks()
        except Exception:
            pass  # Ignore if window is destroyed

    # ——— Post-processing updates (thread-safe) ———
    def update_post_progress(self, current, total):
        import logging
        if total <= 0:
            return
        logging.debug(f"[ProgressController] update_post_progress: current={current}, total={total}")
        self.root.after(0, self._do_post_update, current, total)
        # Force UI update even when window is not in focus
        try:
            self.root.update_idletasks()
        except Exception:
            pass  # Ignore if window is destroyed

    def _do_post_update(self, current, total):
        import logging
        # clamp & compute delta
        current = max(0, min(current, total))
        delta = max(0, current - self.p_current)
        self.p_current = current

        pct = int((current / total) * 100) if total else 0

        # Start post-processing timer on first update
        if self.post_start_time == 0.0 and current > 0:
            self.post_start_time = time.time()

        # Only show percentage in post-processing label (no ETA)
        self.post_label.config(text=f"Post-processing: {pct}%")

        logging.debug(f"[ProgressController] _do_post_update: current={current}, total={total}, delta={delta}")
        # advance overall by delta steps
        self._step_ui(delta)

        # Force UI update even when window is not in focus
        try:
            self.root.update_idletasks()
        except Exception:
            pass  # Ignore if window is destroyed

        # If post-processing is complete, set progress bar and labels to 100%
        if current >= total and total > 0:
            self.progress_var.set(100)
            self.status_label.config(text="100% | Time remaining: 00:00")
            self.post_label.config(text="Post-processing: complete")
            try:
                self.root.update_idletasks()
            except Exception:
                pass  # Ignore if window is destroyed

    def show_post_start(self):
        # Don't change done_steps or total_steps here - they're already correct
        # Just update the UI to show post-processing has started
        self.post_start_time = 0.0
        # Clear or update translation label when post-processing starts
        self.translation_label.config(text="Translation: complete")
        self.post_label.config(text="Post-processing: 0%")
        # Keep current progress - don't recalculate
        current_pct = self.progress_var.get()
        self._update_ui(current_pct, f"{int(current_pct)}% | Post-processing starting...")

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
        self.post_start_time = 0.0
        self._update_ui(0, "0%")

    def _update_ui(self, pct, status):
        self.status_label.config(text=status)
        # Force UI update even when window is not in focus
        try:
            self.root.update_idletasks()
        except Exception:
            pass  # Ignore if window is destroyed

    # optional compatibility aliases
    show_post_processing_start = show_post_start